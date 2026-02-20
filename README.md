# 黄金价格监控系统

一个自动监控现货黄金价格的 Python 程序，通过东方财富公开数据接口获取实时价格，检测价格趋势，并通过飞书发送通知。

## 功能特性

- 定期获取现货黄金（AU9999）实时价格
- 智能分析价格趋势（连续上涨/下跌检测）
- 飞书机器人通知（富文本卡片消息）
- 价格历史数据记录
- 详细的日志记录
- 灵活的配置选项

## 项目结构

```
gold-monitor/
├── src/
│   ├── main.py              # 主程序
│   ├── config.py            # 配置管理
│   ├── gold_fetcher.py      # 黄金价格获取模块
│   ├── price_analyzer.py    # 价格趋势分析模块
│   └── feishu_notifier.py   # 飞书通知模块
├── data/                    # 数据目录（价格历史）
├── logs/                    # 日志目录
├── .env                     # 环境变量配置（需要创建）
├── .env.example             # 环境变量配置模板
├── requirements.txt         # 依赖包
└── README.md               # 项目文档
```

## 部署方式

### 青龙面板部署（推荐）

如果你使用青龙面板，可以通过订阅功能快速部署：

**订阅链接：**
```
ql repo https://github.com/RylynnLai/gold-monitor.git "" "" "requirements.txt"
```

**定时规则：** `*/15 * * * *`（每15分钟执行一次）

**环境变量配置：**
- `FEISHU_WEBHOOK_URL`：飞书机器人 Webhook URL（必填）
- `LOG_LEVEL`：日志级别，默认 INFO（可选）

详细部署指南请查看：**[青龙面板部署指南](QINGLONG_GUIDE.md)**

### 本地部署

## 快速开始

### 1. 环境要求

- Python 3.7+
- pip

### 2. 安装依赖

```bash
cd /Users/imtlll/Documents/gold-monitor
pip install -r requirements.txt
```

### 3. 配置飞书机器人

#### 方式一：使用飞书开放平台应用（当前配置）

1. 访问 [飞书开放平台](https://open.feishu.cn/) 创建应用
2. 获取 `App ID` 和 `App Secret`
3. 在应用权限管理中添加以下权限：
   - `im:message`（发送消息）
   - `im:message:send_as_bot`（以应用身份发消息）
4. 获取接收消息的群聊 ID：
   - 将机器人添加到群聊
   - 通过飞书开放平台 API 获取 chat_id，或使用以下方法：
     ```python
     # 临时代码获取 chat_id
     import requests
     token = "你的access_token"
     response = requests.get(
         "https://open.feishu.cn/open-apis/im/v1/chats",
         headers={"Authorization": f"Bearer {token}"}
     )
     print(response.json())
     ```

#### 方式二：使用自定义机器人 Webhook（简化版）

如果想使用更简单的 Webhook 方式，可以：
1. 在飞书群聊中添加自定义机器人
2. 获取 Webhook URL
3. 修改 `feishu_notifier.py` 使用 Webhook 方式发送消息

### 4. 配置环境变量

复制 `.env.example` 为 `.env` 并填写配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```ini
# 飞书开放平台应用配置
FEISHU_APP_ID=cli_xxxxxxxxxxxxxxxx
FEISHU_APP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxx
FEISHU_CHAT_ID=oc_xxxxxxxxxxxxxxxx

# 监控配置
CHECK_INTERVAL=300  # 检查间隔（秒），默认 5 分钟
TREND_COUNT=3      # 连续多少次同方向变化才触发通知

# 日志配置
LOG_LEVEL=INFO
```

### 5. 测试连接

在启动监控前，建议先测试各组件连接：

```bash
cd src
python main.py test
```

这将测试：
- 黄金价格接口是否正常
- 飞书通知是否能成功发送

### 6. 运行程序

#### 启动监控（持续运行）

```bash
cd src
python main.py
```

#### 单次检查（测试用）

```bash
cd src
python main.py check
```

#### 后台运行（推荐生产环境）

使用 `nohup` 或 `screen` 在后台运行：

```bash
# 使用 nohup
cd src
nohup python main.py > ../logs/nohup.out 2>&1 &

# 或使用 screen
screen -S gold-monitor
cd src
python main.py
# 按 Ctrl+A+D 分离会话
```

#### 使用 systemd（Linux 系统推荐）

创建服务文件 `/etc/systemd/system/gold-monitor.service`：

```ini
[Unit]
Description=Gold Price Monitor
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/Users/imtlll/Documents/gold-monitor/src
ExecStart=/usr/bin/python3 /Users/imtlll/Documents/gold-monitor/src/main.py
Restart=on-failure
RestartSec=10

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

## 配置说明

### 检查间隔 (CHECK_INTERVAL)

- 默认值：300 秒（5 分钟）
- 建议值：
  - 高频监控：300 秒（5 分钟）
  - 中频监控：1800 秒（30 分钟）
  - 低频监控：3600 秒（1 小时）

### 趋势次数 (TREND_COUNT)

- 默认值：3
- 说明：连续多少次同方向（上涨或下跌）变化时触发通知
- 建议值：
  - 敏感监控：2-3 次
  - 普通监控：3-5 次
  - 保守监控：5+ 次

## 通知示例

当检测到连续 3 次上涨时，将收到如下飞书通知：

```
📈 黄金价格上涨预警

当前价格         起始价格
500.50 元/克     498.20 元/克

变化幅度         趋势次数
+0.46%          连续 3 次上涨

价格序列
498.20 → 499.30 → 500.50

通知时间
2024-01-01 10:15:30

黄金价格监控系统 | 数据来源：东方财富
```

## 日志文件

日志文件位于 `logs/gold_monitor.log`，包含：
- 程序启动/停止记录
- 价格获取记录
- 趋势检测记录
- 通知发送记录
- 错误和异常信息

查看最新日志：

```bash
tail -f logs/gold_monitor.log
```

## 数据存储

价格历史数据存储在 `data/price_history.json`，格式如下：

```json
[
  {
    "price": 500.50,
    "timestamp": "2024-01-01T10:00:00",
    "change": 0.30
  }
]
```

程序会自动保留最近 1000 条记录。

## 故障排查

### 1. 获取价格失败

检查网络连接和东方财富接口是否正常：

```bash
curl "http://push2.eastmoney.com/api/qt/stock/get?secid=116.00916001"
```

### 2. 飞书通知失败

- 检查 `.env` 文件中的飞书配置是否正确
- 确认应用权限已正确配置
- 查看日志文件了解具体错误信息
- 使用 `python main.py test` 测试连接

### 3. 程序崩溃

- 查看 `logs/gold_monitor.log` 了解错误原因
- 确保所有依赖包已正确安装
- 检查 Python 版本是否满足要求

## 高级功能

### 自定义通知条件

如需添加其他通知条件（如涨跌幅超过阈值、突破价格区间等），可以修改 `src/price_analyzer.py` 中的 `_analyze_trend` 方法。

### 监控多个品种

可以复制项目并修改 `src/gold_fetcher.py` 中的 `stock_code` 来监控其他贵金属或商品。

### 数据导出

价格历史数据以 JSON 格式存储，可以轻松导出并用于数据分析：

```python
import json
import pandas as pd

with open('data/price_history.json', 'r') as f:
    data = json.load(f)

df = pd.DataFrame(data)
df.to_csv('price_export.csv', index=False)
```

## 注意事项

1. 请遵守东方财富网站的使用条款和爬虫政策
2. 不要设置过于频繁的检查间隔，避免对服务器造成压力
3. 价格数据仅供参考，投资决策请以官方渠道为准
4. 定期备份配置文件和历史数据
5. 生产环境建议使用进程管理工具（如 systemd）确保程序稳定运行

## 许可证

MIT License

## 作者

Created with Claude Code

## 更新日志

### v1.0.0 (2024-01-01)
- 初始版本发布
- 支持黄金价格监控
- 支持飞书通知
- 支持趋势分析
