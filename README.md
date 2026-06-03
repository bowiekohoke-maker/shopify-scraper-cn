# Shopify 独立站卖家爬虫 (中国发货版)

这是一个专门用于识别和抓取**中国发货、月销售额在5-10万美金的独立站卖家**的Python爬虫项目。

## 🎯 功能特性

- ✅ 批量抓取Shopify独立站信息
- ✅ 智能识别中国发货卖家
- ✅ 估算月销售额
- ✅ 提取联系信息
- ✅ 结构化数据导出（JSON/CSV）
- ✅ 速率限制和反爬虫规避
- ✅ 错误重试机制
- ✅ 详细日志记录

## 📋 系统要求

- Python 3.8+
- 操作系统：Windows/macOS/Linux

## 🚀 快速开始

### 1. 克隆仓库
```bash
git clone https://github.com/bowiekohoke-maker/shopify-scraper-cn.git
cd shopify-scraper-cn
```

### 2. 创建虚拟环境
```bash
python -m venv venv
source venv/bin/activate
```

### 3. 安装依赖
```bash
pip install -r requirements.txt
```

### 4. 运行爬虫
```bash
python main.py --urls store_urls.txt
```

## 📄 许可证

MIT License