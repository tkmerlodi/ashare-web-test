# Ashare A股行情数据 Web 测试工具

基于 [Ashare](https://github.com/mpquant/Ashare) 的股票行情查询 Web 应用，支持实时行情、K线图、财务报表查看。

## 功能

- **实时行情** - 新浪财经接口，秒级更新
- **K线图** - 支持日K/周K/月K/5m/15m/30m/60m，ECharts 渲染，可缩放
- **公司概况** - 公司名称、行业、董事长、主营业务等
- **财务报表** - 利润表、资产负债表、现金流量表（东方财富数据源）
- **主要指标** - 每股收益、ROE、毛利率、净利率、资产负债率等

## 快速开始

```bash
cd ashare-web-test
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 app.py
```

浏览器打开 http://localhost:5001

## 预设股票

| 快捷按钮 | 代码 |
|---------|------|
| 贵州茅台 | sh600519 |
| 上证指数 | sh000001 |
| 五粮液 | sz000858 |
| 平安银行 | sz000001 |
| 宁德时代 | sz300750 |
| 中国平安 | sh601318 |

## 技术栈

- 后端: Flask
- 前端: 原生 HTML/JS + ECharts
- 数据源: Ashare (新浪/腾讯) + 东方财富

## 项目结构

```
ashare-web-test/
├── Ashare.py            # Ashare 核心库
├── app.py               # Flask 后端 API
├── templates/
│   └── index.html       # 前端页面
├── requirements.txt
└── README.md
```

## License

MIT
