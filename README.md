# 黄金价格监控系统

基于 N 型反转形态识别的黄金现货价格智能监控系统。使用 Twelve Data API 获取 XAU/USD 实时行情，通过 K 线数据分析检测价格反转信号，并通过飞书发送通知。

## 核心特性

### 🎯 智能分析
- **N 型反转形态识别**：基于摇摆点（swing points）检测价格反转
- **双向信号检测**：同时检测看涨反转（BULLISH）和看跌反转（BEARISH）
- **形态强度评估**：过滤低质量信号，只通知高置信度的反转
- **5分钟K线分析**：实时跟踪价格波动，捕捉关键转折点

### 📊 数据管理
- **XAU/USD 现货数据**：通过 Twelve Data API 获取黄金美元现货价格
- **K线数据缓存**：本地存储48小时历史K线数据
- **自动更新机制**：合并新旧数据，去重并保持时间窗口

### 🔬 回测系统
- **参数优化**：网格搜索找到最优阈值组合
- **多参数测试**：同时测试反转阈值、窗口大小、形态强度
- **结果分析**：生成详细报告，推荐最佳参数配置
- **灵活配置**：支持自定义测试参数范围

### 🔔 飞书通知
- **实时预警**：检测到反转信号立即推送
- **富文本卡片**：包含价格、形态、K线图等详细信息
- **Webhook 集成**：简单配置即可使用

## 项目结构

```
gold-monitor/
├── src/
│   ├── main.py                 # 主程序（监控服务）
│   ├── config.py               # 配置管理（所有环境变量）
│   ├── gold_fetcher.py         # 黄金价格获取（Twelve Data API）
│   ├── price_analyzer.py       # N型形态识别器
│   ├── feishu_notifier.py      # 飞书通知模块
│   ├── kline_data_manager.py   # K线数据管理器
│   └── backtest.py             # 回测系统
├── data/                       # 数据目录
│   ├── price_history.json      # 价格历史（兼容）
│   ├── kline_48h.json          # 48小时K线数据
│   └── backtest_report.json    # 回测报告
├── logs/                       # 日志目录
│   └── gold_monitor.log        # 运行日志
├── output/                     # 输出目录（K线图等）
├── .env                        # 环境变量配置（需要创建）
├── .env.example                # 环境变量配置模板
├── requirements.txt            # 依赖包
└── README.md                   # 项目文档
```

## 快速开始

### 1. 环境要求

- Python 3.7+
- pip

### 2. 安装依赖

```bash
cd gold-monitor
pip install -r requirements.txt
```

依赖包：
- `python-dotenv>=1.0.0` - 环境变量管理
- `requests>=2.31.0` - HTTP 请求（API 和飞书通知）

### 3. 获取 Twelve Data API Key

1. 访问 [Twelve Data](https://twelvedata.com/)
2. 注册免费账号
3. 获取 API Key（免费额度：800次/天）
4. 记录你的 API Key

### 4. 配置飞书 Webhook

1. 在飞书群聊中：设置 → 群机器人 → 添加机器人 → 自定义机器人
2. 设置机器人名称和描述
3. 复制 Webhook 地址（格式：`https://open.feishu.cn/open-apis/bot/v2/hook/...`）

### 5. 配置环境变量

复制 `.env.example` 为 `.env`：

```bash
cp .env.example .env
```

编辑 `.env` 文件，至少配置以下必填项：

```ini
# 飞书 Webhook 配置（必填）
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/your-webhook-token

# 监控配置
CHECK_INTERVAL=300  # 检查间隔（秒），默认 5 分钟
TREND_COUNT=3       # 连续多少次同方向变化才触发通知（旧版兼容，N型模式不使用）

# 日志配置
LOG_LEVEL=INFO

# K线数据配置
KLINE_PERIOD=5min   # K线周期：1min, 5min, 15min, 30min, 1h
KLINE_HOURS=48      # K线数据时长（小时），用于分析和回测

# 价格分析阈值配置（用于 N 型反转形态识别）
MIN_REVERSAL_THRESHOLD=0.003  # 最小反转阈值（0.3%），低于此值的波动将被忽略
SWING_WINDOW_SIZE=2           # 摇摆点识别窗口大小
MIN_STRENGTH=0.5              # 最小形态强度（0-1），形态强度低于此值将不触发通知
```

**重要提示**：
- **必须**修改 `FEISHU_WEBHOOK_URL` 为你自己的飞书 Webhook 地址
- 其他参数使用默认值即可开始使用
- 建议先使用默认参数，运行回测后再根据结果调整

### 6. 测试组件

在启动之前，测试各组件是否正常工作：

#### 测试价格获取

```bash
cd src
python3 -m gold_fetcher
```

预期输出：
```
✓ 成功获取黄金价格: $2850.50/oz (Twelve Data)
✓ 成功获取 576 条K线数据
```

#### 测试K线数据管理器

```bash
python3 -m kline_data_manager
```

预期输出：
```
✓ 成功抓取 576 条K线数据
✓ 成功加载 576 条K线数据
✓ 成功更新，共 576 条K线数据
```

### 7. 运行回测（可选但推荐）

在正式运行监控前，建议先运行回测找到最优参数：

```bash
python3 -m src.backtest
```

回测会：
1. 抓取48小时历史K线数据
2. 测试45组不同参数组合
3. 生成详细报告（保存到 `data/backtest_report.json`）
4. 推荐最优参数配置

根据回测结果，调整 `.env` 中的参数：
```ini
MIN_REVERSAL_THRESHOLD=0.005  # 示例：如果回测推荐更高的阈值
SWING_WINDOW_SIZE=3           # 示例：如果回测推荐更大的窗口
MIN_STRENGTH=0.6              # 示例：如果回测推荐更高的强度
```

### 8. 运行监控

```bash
cd src
python3 main.py
```

程序会：
1. 每5分钟获取最新K线数据
2. 分析48小时数据窗口
3. 检测N型反转形态
4. 发现反转信号时发送飞书通知

## 配置参数详解

### K线数据配置

| 参数 | 默认值 | 说明 | 调整建议 |
|------|--------|------|----------|
| `KLINE_PERIOD` | 5min | K线周期 | 1min（高频）/ 5min（推荐）/ 15min（中频）/ 1h（低频） |
| `KLINE_HOURS` | 48 | 数据窗口（小时） | 24（短期）/ 48（推荐）/ 72（长期）/ 168（7天） |

**示例场景**：
- **日内交易**: `KLINE_PERIOD=1min, KLINE_HOURS=24`
- **短线波段**: `KLINE_PERIOD=5min, KLINE_HOURS=48`（推荐）
- **中线趋势**: `KLINE_PERIOD=15min, KLINE_HOURS=72`
- **长线分析**: `KLINE_PERIOD=1h, KLINE_HOURS=168`

### 形态识别参数

| 参数 | 默认值 | 说明 | 效果 |
|------|--------|------|------|
| `MIN_REVERSAL_THRESHOLD` | 0.003 | 最小反转阈值（0.3%） | ↑ 减少噪音、减少信号；↓ 增加灵敏度、增加信号 |
| `SWING_WINDOW_SIZE` | 2 | 摇摆点识别窗口 | ↑ 过滤更多小波动；↓ 捕捉更多细节 |
| `MIN_STRENGTH` | 0.5 | 最小形态强度（0-1） | ↑ 只要高质量信号；↓ 允许更多信号 |

**参数调优策略**：

**保守型配置**（减少误报）：
```ini
MIN_REVERSAL_THRESHOLD=0.007  # 0.7%
SWING_WINDOW_SIZE=3
MIN_STRENGTH=0.7
```

**积极型配置**（捕捉更多机会）：
```ini
MIN_REVERSAL_THRESHOLD=0.001  # 0.1%
SWING_WINDOW_SIZE=2
MIN_STRENGTH=0.3
```

**推荐配置**（平衡）：
```ini
MIN_REVERSAL_THRESHOLD=0.003  # 0.3%（默认）
SWING_WINDOW_SIZE=2
MIN_STRENGTH=0.5
```

## 使用场景

### 场景1：实时监控

持续运行程序，自动检测价格反转并通知：

```bash
# 前台运行
python3 src/main.py

# 后台运行（推荐）
nohup python3 src/main.py > logs/nohup.out 2>&1 &

# 使用 screen
screen -S gold-monitor
python3 src/main.py
# Ctrl+A+D 分离会话
```

### 场景2：参数优化

使用回测系统找到最优参数：

```bash
# 标准回测（45组参数）
python3 -m src.backtest

# 查看回测报告
cat data/backtest_report.json
```

### 场景3：数据管理

手动管理K线数据：

```bash
# 抓取并保存最新数据
python3 -m src.kline_data_manager

# 在Python中使用
from src.kline_data_manager import KlineDataManager

manager = KlineDataManager()
kline_data = manager.update_48h_data()  # 更新数据
info = manager.get_data_info()          # 查看信息
```

### 场景4：自定义分析

```python
from src.price_analyzer import PriceAnalyzer
from src.kline_data_manager import KlineDataManager

# 加载K线数据
manager = KlineDataManager()
kline_data = manager.load_kline_data()

# 分析N型形态
analyzer = PriceAnalyzer()
result = analyzer.analyze_kline_data(kline_data)

if result and result.get('type') == 'N_PATTERN_REVERSAL':
    reversal = result['reversal_signal']
    print(f"检测到{reversal['reversal_type']}反转")
    print(f"置信度: {reversal['confidence']:.2f}")
```

## 部署方式

### 青龙面板部署（推荐）

**订阅链接：**
```
ql repo https://github.com/RylynnLai/gold-monitor.git "qinglong_run.py" "" "requirements.txt"
```

**说明：**
- 第二个参数 `"qinglong_run.py"` 是白名单，只运行这一个文件作为定时任务
- 这样可以避免青龙扫描 `src/` 目录下的其他 Python 文件（如 gold_fetcher.py, price_analyzer.py 等）

**定时规则：** `*/5 * * * *`（每5分钟执行一次）

**环境变量配置：**
- `FEISHU_WEBHOOK_URL`：飞书机器人 Webhook URL（必填）
- `KLINE_PERIOD`：K线周期，默认 5min
- `KLINE_HOURS`：K线时长，默认 48
- `MIN_REVERSAL_THRESHOLD`：最小反转阈值，默认 0.003
- `SWING_WINDOW_SIZE`：摇摆点窗口，默认 2
- `MIN_STRENGTH`：最小形态强度，默认 0.5
- `LOG_LEVEL`：日志级别，默认 INFO

详细部署指南请查看：**[青龙面板部署指南](QINGLONG_GUIDE.md)**

### systemd 服务（Linux 推荐）

创建 `/etc/systemd/system/gold-monitor.service`：

```ini
[Unit]
Description=Gold Price Monitor with N-Pattern Detection
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/gold-monitor
ExecStart=/usr/bin/python3 /path/to/gold-monitor/src/main.py
EnvironmentFile=/path/to/gold-monitor/.env
Restart=on-failure
RestartSec=30

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable gold-monitor
sudo systemctl start gold-monitor
sudo systemctl status gold-monitor
```

### Docker 部署

创建 `Dockerfile`：

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
CMD ["python3", "src/main.py"]
```

构建并运行：

```bash
docker build -t gold-monitor .
docker run -d --name gold-monitor --env-file .env gold-monitor
```

## 通知示例

当检测到看涨反转时，将收到如下飞书通知：

```
🟢 黄金价格看涨反转信号

反转类型: BULLISH（看涨）
当前价格: $2,850.50/oz
形态强度: 0.75（高）

形态信息
- 类型: 上升N字形（RISING）
- 起始价格: $2,835.20/oz
- 结束价格: $2,850.50/oz
- 变化幅度: +0.54%

摇摆点序列
$2,835.20 → $2,847.80 → $2,850.50

分析窗口: 48小时 K线数据（576条）
触发时间: 2026-02-20 22:00:00

⚠️ 此为算法分析结果，仅供参考，不构成投资建议

黄金价格监控系统 | 数据来源：Twelve Data (XAU/USD)
```

## 数据文件说明

### K线数据文件 (`data/kline_48h.json`)

```json
{
  "metadata": {
    "symbol": "XAU/USD",
    "period": "5min",
    "count": 576,
    "start_time": "2026-02-19 00:50:00",
    "end_time": "2026-02-21 00:45:00",
    "updated_at": "2026-02-20T22:00:00",
    "description": "48小时K线数据（用于回测）"
  },
  "kline_data": [
    {
      "datetime": "2026-02-19 00:50:00",
      "open": 2850.10,
      "high": 2852.30,
      "low": 2849.50,
      "close": 2851.20,
      "volume": 0
    }
  ]
}
```

### 回测报告 (`data/backtest_report.json`)

包含详细的参数测试结果和推荐配置。

## 日志文件

日志位于 `logs/gold_monitor.log`，包含：
- K线数据获取记录
- 摇摆点识别结果
- N型形态检测记录
- 反转信号触发记录
- 飞书通知发送状态
- 错误和异常信息

查看实时日志：

```bash
tail -f logs/gold_monitor.log
```

## 故障排查

### 1. API Key 问题

**错误**：`API请求失败: 401 Unauthorized`

**解决**：
1. 确认已注册 Twelve Data 账号
2. 在 `gold_fetcher.py` 中正确设置 `self.api_key`
3. 检查 API Key 是否有效（登录官网查看）

### 2. 请求限制

**错误**：`API请求失败: 429 Too Many Requests`

**解决**：
1. 免费账户限制：800次/天
2. 减少 `CHECK_INTERVAL`（增加间隔时间）
3. 或升级到付费账户

### 3. 没有检测到反转

**可能原因**：
1. 市场处于单边趋势或震荡，没有明显反转
2. 阈值参数设置过于保守

**解决**：
1. 运行回测查看历史数据中是否有反转
2. 适当降低 `MIN_REVERSAL_THRESHOLD` 和 `MIN_STRENGTH`
3. 查看日志中的摇摆点识别情况

### 4. 误报过多

**解决**：
1. 提高 `MIN_REVERSAL_THRESHOLD`（如 0.005 或 0.007）
2. 增大 `SWING_WINDOW_SIZE`（如 3 或 4）
3. 提高 `MIN_STRENGTH`（如 0.7）
4. 运行回测找到最佳平衡点

### 5. 飞书通知失败

**检查项**：
1. Webhook URL 是否正确
2. 机器人是否已添加到群聊
3. 网络连接是否正常
4. 查看日志了解具体错误

```bash
# 测试 Webhook
curl -X POST "YOUR_WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d '{"msg_type":"text","content":{"text":"测试消息"}}'
```

## 技术原理

### N 型反转形态识别

本系统使用基于摇摆点（Swing Points）的 N 型形态识别算法：

1. **摇摆点识别**：
   - 局部高点：周围窗口内的最高价
   - 局部低点：周围窗口内的最低价
   - 幅度过滤：只保留变化幅度 ≥ MIN_REVERSAL_THRESHOLD 的点

2. **N 型形态检测**：
   - **上升 N 字形**（看涨）：LOW → HIGH → LOW，且第二个LOW > 第一个LOW
   - **下降 N 字形**（看跌）：HIGH → LOW → HIGH，且第二个HIGH < 第一个HIGH

3. **形态强度计算**：
   - 价格幅度得分（70%权重）
   - 摇摆点一致性得分（30%权重）
   - 综合得分 0-1，越高表示形态越明显

4. **反转信号触发**：
   - 形态改变：RISING ↔ FALLING
   - 幅度达标：≥ MIN_REVERSAL_THRESHOLD
   - 强度达标：≥ MIN_STRENGTH

### 数据流程

```
Twelve Data API
    ↓
获取 XAU/USD 5分钟K线数据（48小时）
    ↓
识别摇摆点（基于 High/Low 价格）
    ↓
检测 N 型形态（使用 Close 价格判断方向）
    ↓
计算形态强度
    ↓
检测反转信号
    ↓
发送飞书通知（如果检测到反转）
```

## API 使用说明

### Twelve Data API

- **文档**: https://twelvedata.com/docs
- **免费额度**: 800次/天
- **延迟**: 实时数据（1分钟级别）
- **数据类型**: XAU/USD 现货价格

### 请求示例

```python
# 获取实时价格
GET https://api.twelvedata.com/price?symbol=XAU/USD&apikey=YOUR_KEY

# 获取K线数据
GET https://api.twelvedata.com/time_series?symbol=XAU/USD&interval=5min&outputsize=576&apikey=YOUR_KEY
```

## 最佳实践

### 1. 参数调优流程

```bash
# 步骤1: 运行回测
python3 -m src.backtest

# 步骤2: 查看回测报告
cat data/backtest_report.json | jq '.report.best_by_score'

# 步骤3: 更新 .env 配置
vim .env

# 步骤4: 重启监控
pkill -f "python3 src/main.py"
python3 src/main.py &
```

### 2. 监控建议

- **检查间隔**: 5分钟（实时监控）或 15分钟（节省 API 请求）
- **数据窗口**: 48小时（平衡灵敏度和稳定性）
- **K线周期**: 5分钟（适合日内波段）

### 3. 通知管理

- 测试期：降低阈值，观察信号质量
- 正式运行：根据回测结果调整到最优参数
- 避免过度通知：适当提高 MIN_STRENGTH

### 4. 数据备份

定期备份关键文件：

```bash
# 备份配置和数据
tar -czf backup_$(date +%Y%m%d).tar.gz .env data/ logs/
```

## 进阶功能

### 自定义回测参数范围

编辑 `src/backtest.py` 中的 `run_grid_search` 调用：

```python
results = backtester.run_grid_search(
    kline_data,
    threshold_range=[0.001, 0.002, 0.003, 0.005, 0.007],  # 自定义阈值范围
    window_sizes=[2, 3, 4, 5],                             # 自定义窗口大小
    strength_range=[0.3, 0.4, 0.5, 0.6, 0.7]              # 自定义强度范围
)
```

### 导出K线数据

```python
from src.kline_data_manager import KlineDataManager
import pandas as pd

manager = KlineDataManager()
kline_data = manager.load_kline_data()

df = pd.DataFrame(kline_data)
df.to_csv('kline_export.csv', index=False)
```

### 分析特定时间段

```python
from src.price_analyzer import PriceAnalyzer
from datetime import datetime

analyzer = PriceAnalyzer()

# 筛选特定时间段的K线
filtered_klines = [
    k for k in kline_data
    if '2026-02-20' in k['datetime']
]

result = analyzer.analyze_kline_data(filtered_klines)
```

## 注意事项

1. **API 限制**：免费账户每天800次请求，请合理设置检查间隔
2. **数据延迟**：Twelve Data 提供实时数据（1分钟级别），但不保证毫秒级精度
3. **投资警告**：本系统仅供技术分析参考，不构成投资建议，投资有风险
4. **合规使用**：请遵守 Twelve Data 使用条款和飞书机器人使用规范
5. **数据备份**：定期备份配置文件和历史数据，避免数据丢失
6. **监控稳定性**：生产环境建议使用 systemd 或 Docker 确保服务稳定运行

## 数据源说明

### 当前数据源

- **API**: Twelve Data (https://twelvedata.com/)
- **品种**: XAU/USD（黄金现货美元价格）
- **单位**: USD/盎司
- **更新频率**: 实时（1分钟级别）
- **数据质量**: 专业金融数据，来自全球市场

### 历史数据源

- **v1.0**: 东方财富网 AU9999（人民币/克）- 已废弃
- **v2.0**: Twelve Data XAU/USD（美元/盎司）- 当前使用

详细的数据源调查报告请查看：`/Users/imtlll/securities-data-sources/黄金现货XAU_USD方案.md`

## 更新日志

### v2.0.0 (2026-02-20)

**重大更新**：

- ✨ 切换到 Twelve Data API（XAU/USD 现货）
- ✨ 实现 N 型反转形态识别算法
- ✨ 添加 K 线数据管理器
- ✨ 添加回测系统（参数优化）
- ✨ 所有阈值参数可配置化
- ✨ K 线周期和时长可配置
- 🔧 简化飞书配置（改用 Webhook）
- 📚 完全重写文档

**配置变更**：

- 新增：`KLINE_PERIOD`, `KLINE_HOURS`
- 新增：`MIN_REVERSAL_THRESHOLD`, `SWING_WINDOW_SIZE`, `MIN_STRENGTH`
- 移除：飞书 App ID/Secret/Chat ID（改用 Webhook）

**文件变更**：

- 新增：`src/kline_data_manager.py` - K线数据管理
- 新增：`src/backtest.py` - 回测系统
- 修改：`src/gold_fetcher.py` - 适配 Twelve Data API
- 修改：`src/price_analyzer.py` - N型形态识别
- 修改：`src/config.py` - 新增配置参数

### v1.0.0 (2024-01-01)

- 初始版本发布
- 支持黄金价格监控（东方财富 AU9999）
- 支持飞书通知
- 支持简单趋势分析

## 许可证

MIT License

## 致谢

- **Twelve Data** - 提供高质量的金融数据 API
- **飞书开放平台** - 提供便捷的消息推送能力
- **Claude Code** - AI 辅助开发

## 作者

Created with ❤️ by Claude Code

---

**免责声明**：本软件仅供学习和研究使用。使用本软件进行投资决策的一切风险由使用者自行承担。作者不对任何投资损失负责。
