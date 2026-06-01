# Air New Zealand Flight Tracker

一个用于实时爬取新西兰航空飞行数据的 Python 爬虫项目。

## 项目功能

- 🛫 **实时爬取航班数据** - 从奥克兰出发到以下城市的航班信息：
  - 长沙 (Changsha, CSX)
  - 悉尼 (Sydney, SYD)
  - 惠灵顿 (Wellington, WLG)
  - 纽约 (New York, NYC)
  - 墨尔本 (Melbourne, MEL)

- 📊 **数据持久化** - 支持 CSV 和 JSON 格式保存
- 📈 **数据分析** - 提供航班数据统计和分析
- ⏰ **定时爬取** - 支持自动定时爬取任务
- 🔄 **错误重试** - 自动重试机制确保数据完整性

## 项目结构

```
air-new-zealand-tracker/
├── config.py              # 项目配置
├── flight_scraper.py      # 主爬虫程序
├── scheduler.py           # 定时任务调度器
├── data_analyzer.py       # 数据分析工具
├── requirements.txt       # 项目依赖
├── README.md             # 本文件
├── data/                 # 爬取数据存储目录
│   ├── flight_data.csv   # CSV 格式数据
│   └── flight_data.json  # JSON 格式数据
└── logs/                 # 日志目录
    └── flight_scraper.log # 爬虫日志
```

## 环境要求

- Python 3.8+
- Google Chrome 浏览器（用于 Selenium）
- ChromeDriver（与 Chrome 版本匹配）

## 安装和使用

### 1. 克隆项目

```bash
git clone https://github.com/yiminyuan4-creator/air-new-zealand-tracker.git
cd air-new-zealand-tracker
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 下载 ChromeDriver

从 [ChromeDriver 官网](https://chromedriver.chromium.org/) 下载与你的 Chrome 版本匹配的驱动程序，放在项目目录中或添加到系统 PATH。

### 4. 运行爬虫

#### 方式一：单次爬取

```bash
python flight_scraper.py
```

这将：
- 爬取未来 7 天的所有路由航班数据
- 将数据保存到 `data/flight_data.csv` 和 `data/flight_data.json`
- 生成详细的日志文件

#### 方式二：定时自动爬取

```bash
python scheduler.py
```

这将：
- 立即执行一次爬取
- 然后每 6 小时自动运行一次（可在 `config.py` 中修改 `SCRAPE_INTERVAL_HOURS`）

### 5. 数据分析

```bash
python data_analyzer.py
```

这将：
- 显示航班数据统计摘要
- 按路由统计航班数量
- 计算票价统计信息
- 生成详细的分析报告到 `data/flight_analysis_report.json`

## 配置说明

在 `config.py` 中可以配置：

```python
# 监控的路由
ROUTES = [
    {"departure": "AKL", "arrival": "CSX", ...},
    # ...
]

# 浏览器设置
HEADLESS_BROWSER = True           # 是否使用无头浏览器
BROWSER_TIMEOUT = 30              # 浏览器超时时间（秒）
RETRY_ATTEMPTS = 3                # 失败重试次数

# 定时任务间隔（小时）
SCRAPE_INTERVAL_HOURS = 6
```

## 数据输出格式

### CSV 格式示例

```csv
departure_code,arrival_code,departure_time,arrival_time,duration,airline,price,currency,stops,scraped_at,departure_name,arrival_name
AKL,SYD,06:15,07:45,1h 30m,Air New Zealand,NZ$199.00,NZD,0,2026-06-01T10:30:00,...
```

### JSON 格式示例

```json
[
  {
    "departure_code": "AKL",
    "arrival_code": "SYD",
    "departure_time": "06:15",
    "arrival_time": "07:45",
    "duration": "1h 30m",
    "airline": "Air New Zealand",
    "price": "NZ$199.00",
    "currency": "NZD",
    "stops": 0,
    "aircraft": null,
    "scraped_at": "2026-06-01T10:30:00",
    "departure_name": "Auckland",
    "arrival_name": "Sydney"
  }
]
```

## 日志文件

日志文件位置：`logs/flight_scraper.log`

包含以下信息：
- 爬虫启动/停止时间
- 网页加载情况
- 数据解析过程
- 错误和异常信息

## 常见问题

### Q: 爬虫无法找到元素怎么办？
A: 这通常是因为网站页面结构改变了。需要更新 CSS 选择器。可以：
1. 打开浏览器开发者工具（F12）
2. 检查相关元素的选择器
3. 更新 `flight_scraper.py` 中的选择器

### Q: 爬虫超时怎么办？
A: 可以在 `config.py` 中增加 `BROWSER_TIMEOUT` 的值（单位为秒）

### Q: 如何修改爬取的航班数量和日期？
A: 修改 `flight_scraper.py` 中 `scrape_all_routes()` 方法的 `search_dates` 参数

## 注意事项

⚠️ **重要提示**：
- 使用本爬虫请遵守目标网站的 `robots.txt` 和服务条款
- 不要以过高的频率爬取数据，建议间隔 6 小时以上
- 仅用于学习和研究目的
- 请在获得网站所有者的同意下使用

## 许可证

MIT License

## 联系方式

如有问题或建议，请提交 Issue 或 Pull Request。

---

**更新日期**：2026-06-01  
**版本**：1.0.0
