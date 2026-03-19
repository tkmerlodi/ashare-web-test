from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from Ashare import get_price
import requests as req
import json
import traceback

app = Flask(__name__)
CORS(app)

HEADERS = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}

# 上证50成分股 (2025Q4调整后)
SZ50_CODES = [
    'sh601398','sh601288','sh601988','sh600519','sh601318',
    'sh600036','sh601166','sh600276','sh601888','sh600030',
    'sh600900','sh601012','sh600887','sh601668','sh600309',
    'sh600809','sh600028','sh601857','sh600104','sh601601',
    'sh600000','sh600837','sh601225','sh601088','sh601688',
    'sh600016','sh601390','sh600690','sh601818','sh601628',
    'sh600585','sh601186','sh601766','sh600050','sh601989',
    'sh600196','sh601211','sh603259','sh600048','sh600570',
    'sh601985','sh603993','sh600745','sh601658','sh600009',
    'sh601111','sh601138','sh600660','sh600115','sh601698',
]


def normalize_code(code):
    """统一代码格式: sh600519 / sz000001"""
    c = code.strip().upper().replace('.XSHG', '').replace('.XSHE', '')
    if c.startswith(('SH', 'SZ')):
        return c.lower()
    if c.startswith('6') or c.startswith('9'):
        return 'sh' + c
    return 'sz' + c


def get_secid(code):
    """转换为东方财富 secid 格式: 1.600519 / 0.000001"""
    c = normalize_code(code)
    if c.startswith('sh'):
        return '1.' + c[2:]
    return '0.' + c[2:]


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/stock')
def stock_kline():
    code = request.args.get('code', 'sh000001')
    frequency = request.args.get('frequency', '1d')
    count = int(request.args.get('count', 30))
    end_date = request.args.get('end_date', '')
    try:
        df = get_price(code, end_date=end_date, count=count, frequency=frequency)
        df = df.reset_index()
        df.columns = ['date', 'open', 'close', 'high', 'low', 'volume']
        df['date'] = df['date'].astype(str)
        return jsonify({'code': 0, 'data': df.to_dict(orient='records')})
    except Exception as e:
        return jsonify({'code': -1, 'msg': str(e)})


@app.route('/api/realtime')
def realtime_quote():
    """实时行情 - 新浪接口"""
    code = request.args.get('code', 'sh600519')
    code = normalize_code(code)
    try:
        url = f'https://hq.sinajs.cn/list={code}'
        resp = req.get(url, headers={'Referer': 'https://finance.sina.com.cn'}, timeout=5)
        text = resp.content.decode('gbk')
        fields = text.split('"')[1].split(',')
        if len(fields) < 32:
            return jsonify({'code': -1, 'msg': '无数据'})
        prev_close = float(fields[2])
        cur = float(fields[3])
        change = cur - prev_close
        change_pct = change / prev_close * 100 if prev_close else 0
        data = {
            'name': fields[0],
            'open': float(fields[1]),
            'prev_close': prev_close,
            'price': cur,
            'high': float(fields[4]),
            'low': float(fields[5]),
            'volume': float(fields[8]),
            'amount': float(fields[9]),
            'date': fields[30],
            'time': fields[31],
            'change': round(change, 2),
            'change_pct': round(change_pct, 2),
        }
        return jsonify({'code': 0, 'data': data})
    except Exception as e:
        return jsonify({'code': -1, 'msg': str(e)})


@app.route('/api/profile')
def stock_profile():
    """公司概况 - 东方财富"""
    code = request.args.get('code', 'sh600519')
    nc = normalize_code(code)
    secid = get_secid(code)
    try:
        url = f'https://datacenter.eastmoney.com/securities/api/data/v1/get?reportName=RPT_F10_BASIC_ORGINFO&columns=ALL&filter=(SECURITY_CODE%3D%22{nc[2:]}%22)&pageNumber=1&pageSize=1'
        resp = req.get(url, headers=HEADERS, timeout=5)
        d = resp.json()
        if d.get('result') and d['result'].get('data'):
            info = d['result']['data'][0]
            return jsonify({'code': 0, 'data': {
                'name': info.get('SECURITY_NAME_ABBR', ''),
                'code': info.get('SECURITY_CODE', ''),
                'full_name': info.get('ORG_NAME', ''),
                'industry': info.get('INDUSTRY_CSRC', '') or info.get('INDUSTRY', ''),
                'area': info.get('AREA_NAME', ''),
                'chairman': info.get('CHAIRMAN', ''),
                'manager': info.get('SECRETARY', ''),
                'reg_capital': info.get('REG_CAPITAL', ''),
                'setup_date': info.get('FOUND_DATE', ''),
                'website': info.get('ORG_WEB', ''),
                'email': info.get('ORG_EMAIL', ''),
                'main_business': info.get('MAIN_BUSINESS', ''),
            }})
        return jsonify({'code': -1, 'msg': '未找到公司信息'})
    except Exception as e:
        return jsonify({'code': -1, 'msg': str(e)})


@app.route('/api/finance')
def finance_report():
    """财务报表 - 东方财富 (利润表/资产负债表/现金流量表)"""
    code = request.args.get('code', 'sh600519')
    report_type = request.args.get('type', 'income')  # income / balance / cashflow
    nc = normalize_code(code)
    table_map = {
        'income': 'RPT_DMSK_FN_INCOME',
        'balance': 'RPT_DMSK_FN_BALANCE',
        'cashflow': 'RPT_DMSK_FN_CASHFLOW',
    }
    report_name = table_map.get(report_type, 'RPT_DMSK_FN_INCOME')

    income_cols = 'SECURITY_CODE,SECURITY_NAME_ABBR,REPORT_DATE,TOTAL_OPERATE_INCOME,OPERATE_COST,OPERATE_PROFIT,PARENT_NETPROFIT,TOI_RATIO,OPERATE_PROFIT_RATIO,PARENT_NETPROFIT_RATIO'
    balance_cols = 'SECURITY_CODE,SECURITY_NAME_ABBR,REPORT_DATE,TOTAL_ASSETS,TOTAL_LIABILITIES,TOTAL_EQUITY,MONETARYFUNDS,INVENTORY,ACCOUNTS_RECE,CURRENT_RATIO,DEBT_ASSET_RATIO'
    cashflow_cols = 'SECURITY_CODE,SECURITY_NAME_ABBR,REPORT_DATE,NETCASH_OPERATE,NETCASH_INVEST,NETCASH_FINANCE,SALES_SERVICES,CONSTRUCT_LONG_ASSET,PAY_STAFF_CASH'

    cols_map = {'income': income_cols, 'balance': balance_cols, 'cashflow': cashflow_cols}
    columns = cols_map.get(report_type, income_cols)

    try:
        url = (f'https://datacenter-web.eastmoney.com/api/data/v1/get?'
               f'sortColumns=REPORT_DATE&sortTypes=-1&pageSize=8&pageNumber=1'
               f'&reportName={report_name}&columns={columns}'
               f'&filter=(SECURITY_CODE%3D%22{nc[2:]}%22)')
        resp = req.get(url, headers=HEADERS, timeout=8)
        d = resp.json()
        if d.get('result') and d['result'].get('data'):
            return jsonify({'code': 0, 'data': d['result']['data']})
        return jsonify({'code': -1, 'msg': '无财务数据'})
    except Exception as e:
        return jsonify({'code': -1, 'msg': str(e)})


@app.route('/api/keyindicators')
def key_indicators():
    """主要指标"""
    code = request.args.get('code', 'sh600519')
    nc = normalize_code(code)
    try:
        url = (f'https://datacenter-web.eastmoney.com/api/data/v1/get?'
               f'sortColumns=REPORT_DATE&sortTypes=-1&pageSize=8&pageNumber=1'
               f'&reportName=RPT_F10_FINANCE_MAINFINADATA&columns=ALL'
               f'&filter=(SECURITY_CODE%3D%22{nc[2:]}%22)')
        resp = req.get(url, headers=HEADERS, timeout=8)
        d = resp.json()
        if d.get('result') and d['result'].get('data'):
            raw = d['result']['data']
            cols = ['REPORT_DATE', 'EPSJB', 'ROEJQ', 'XSMLL', 'XSJLL',
                    'TOAZZL', 'LD', 'ZCFZL', 'TOTALOPERATEREVETZ', 'PARENTNETPROFITTZ']
            data = [{k: r.get(k) for k in cols} for r in raw]
            return jsonify({'code': 0, 'data': data})
        return jsonify({'code': -1, 'msg': '无数据'})
    except Exception as e:
        return jsonify({'code': -1, 'msg': str(e)})


@app.route('/api/sz50')
def sz50():
    """上证50成分股批量行情 - 新浪接口"""
    try:
        codes_str = ','.join(SZ50_CODES)
        url = f'https://hq.sinajs.cn/list={codes_str}'
        resp = req.get(url, headers={'Referer': 'https://finance.sina.com.cn'}, timeout=8)
        text = resp.content.decode('gbk')
        results = []
        for line in text.strip().split('\n'):
            line = line.strip()
            if not line or '=""' in line:
                continue
            code = line.split('=')[0].split('_')[-1]
            fields = line.split('"')[1].split(',')
            if len(fields) < 32:
                continue
            name = fields[0]
            prev_close = float(fields[2])
            price = float(fields[3])
            high = float(fields[4])
            low = float(fields[5])
            volume = float(fields[8])
            amount = float(fields[9])
            change = price - prev_close
            change_pct = change / prev_close * 100 if prev_close else 0
            amplitude = (high - low) / prev_close * 100 if prev_close else 0
            results.append({
                'code': code,
                'name': name,
                'price': round(price, 2),
                'open': round(float(fields[1]), 2),
                'high': round(high, 2),
                'low': round(low, 2),
                'prev_close': round(prev_close, 2),
                'change': round(change, 2),
                'change_pct': round(change_pct, 2),
                'amplitude': round(amplitude, 2),
                'volume': volume,
                'amount': amount,
                'date': fields[30],
                'time': fields[31],
            })
        return jsonify({'code': 0, 'count': len(results), 'data': results})
    except Exception as e:
        return jsonify({'code': -1, 'msg': str(e)})


if __name__ == '__main__':
    app.run(debug=True, port=5001)
