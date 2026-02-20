# 青龙面板部署指南

本文档介绍如何在青龙面板上部署和使用黄金价格监控系统。

## 目录

- [什么是青龙面板](#什么是青龙面板)
- [快速开始](#快速开始)
- [方式一：订阅模式（推荐）](#方式一订阅模式推荐)
- [方式二：手动部署](#方式二手动部署)
- [配置说明](#配置说明)
- [常见问题](#常见问题)

## 什么是青龙面板

青龙面板（Qinglong）是一个支持定时任务管理的开源平台，常用于运行各种自动化脚本任务。使用青龙面板可以：

- 定时自动执行监控任务
- 方便管理环境变量和依赖
- 查看任务执行日志
- 支持订阅自动更新脚本

## 快速开始

### 前置要求

1. 已安装并启动青龙面板
2. 青龙面板版本 >= 2.10.0
3. 已配置飞书 Webhook URL

## 方式一：订阅模式（推荐）

### 1. 添加订阅

在青龙面板中，进入「订阅管理」页面：

**方法 A：使用订阅配置文件**

- 名称：`黄金价格监控`
- 类型：`公开仓库`
- 链接：`https://github.com/RylynnLai/gold-monitor.git`
- 分支：`main`
- 定时类型：`crontab`
- 定时规则：`*/15 * * * *`（每15分钟执行一次）
- 白名单：`qinglong_run.py`
- 黑名单：留空
- 依赖文件：`requirements.txt`

**方法 B：直接导入订阅链接**

```
ql repo https://github.com/RylynnLai/gold-monitor.git "qinglong_run" "" "requirements.txt"
```

### 2. 配置环境变量

在青龙面板的「环境变量」页面添加以下变量：

| 变量名 | 值 | 说明 | 必填 |
|--------|-----|------|------|
| `FEISHU_WEBHOOK_URL` | `https://open.feishu.cn/open-apis/bot/v2/hook/...` | 飞书机器人 Webhook URL | ✓ |
| `LOG_LEVEL` | `INFO` | 日志级别（DEBUG/INFO/WARNING/ERROR） | ✗ |

### 3. 安装依赖

订阅后，青龙面板会自动安装 `requirements.txt` 中的依赖。

你也可以手动安装：

```bash
# 在青龙面板的「依赖管理」中添加 Python 依赖
pip3 install -r /ql/scripts/gold-monitor/requirements.txt
```

或者在「依赖管理」→「Python3」中逐个添加：

- `python-dotenv>=1.0.0`
- `akshare>=1.12.0`
- `requests>=2.31.0`

### 4. 运行任务

订阅成功后，在「定时任务」页面会自动创建任务：

- 任务名称：`黄金价格监控`
- 执行命令：`python3 /ql/scripts/gold-monitor/qinglong_run.py`
- 定时规则：`*/15 * * * *`

你可以：

- 点击「运行」按钮立即执行
- 等待定时自动执行
- 调整定时规则（建议15-30分钟一次）

### 5. 查看日志

执行后，可以在以下位置查看日志：

- 青龙面板日志：「定时任务」→「日志」
- 脚本日志：`/ql/scripts/gold-monitor/logs/gold_monitor.log`
- 运行结果：`/ql/scripts/gold-monitor/output/result_*.txt`

## 方式二：手动部署

如果不想使用订阅模式，可以手动部署：

### 1. 克隆代码

在青龙面板的「脚本管理」中，使用终端执行：

```bash
cd /ql/scripts
git clone https://github.com/RylynnLai/gold-monitor.git
cd gold-monitor
```

### 2. 安装依赖

```bash
pip3 install -r requirements.txt
```

### 3. 配置环境变量

在青龙面板的「环境变量」中添加（同订阅模式）。

### 4. 创建定时任务

在青龙面板的「定时任务」页面，点击「添加任务」：

- 名称：`黄金价格监控`
- 命令：`python3 /ql/scripts/gold-monitor/qinglong_run.py`
- 定时规则：`*/15 * * * *`

## 配置说明

### 定时规则推荐

根据你的需求选择合适的执行频率：

| 频率 | Cron 表达式 | 说明 |
|------|------------|------|
| 每15分钟 | `*/15 * * * *` | 高频监控（推荐） |
| 每30分钟 | `*/30 * * * *` | 中频监控 |
| 每小时 | `0 * * * *` | 低频监控 |
| 工作日9-18点每15分钟 | `*/15 9-18 * * 1-5` | 交易时段 |

### 飞书 Webhook 配置

#### 获取 Webhook URL

1. 在飞书群聊中，点击「设置」→「群机器人」
2. 添加「自定义机器人」
3. 设置机器人名称（如：黄金监控）
4. 复制生成的 Webhook URL
5. 将 URL 添加到青龙面板的环境变量中

Webhook URL 格式：
```
https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

## 运行效果

### 执行流程

每次执行时，脚本会：

1. 获取 48 小时黄金 K 线数据（192条15分钟K线）
2. 分析价格趋势和 N 字形反转信号
3. 生成 ASCII 蜡烛图和分析报告
4. 输出到控制台和日志文件
5. 如检测到反转信号，发送飞书通知

### 飞书通知示例

当检测到 N 字形反转时，会收到类似通知：

```
🔄 N字形反转信号

反转类型：看涨反转
信号强度：★★★☆☆ (65%)

形态转换：下降趋势 → 上升趋势
触发价格：500.50 元/克
反转确认时间：2024-01-01 10:15:30

建议操作：
适合做多，关注价格能否持续上涨
止损点位：498.00 元/克

黄金价格监控系统 | 数据来源：东方财富
```

## 常见问题

### Q1: 订阅后没有生成任务？

**A:** 检查以下几点：
- 确认订阅配置中的「白名单」设置为 `qinglong_run.py`
- 查看订阅日志，确认拉取成功
- 手动运行一次订阅更新

### Q2: 执行失败，提示缺少依赖？

**A:** 在「依赖管理」中安装缺失的包：

```bash
cd /ql/scripts/gold-monitor
pip3 install -r requirements.txt
```

或在青龙面板的「依赖管理」→「Python3」界面手动添加。

### Q3: 飞书通知发送失败？

**A:** 检查：
- `FEISHU_WEBHOOK_URL` 是否正确配置
- Webhook URL 是否有效（未过期）
- 机器人是否被移出群聊
- 查看日志文件了解具体错误

### Q4: 如何调整通知频率？

**A:** 脚本默认只在检测到 N 字形反转时发送通知，不会每次执行都通知。如需调整通知条件，可以修改源码：

```python
# src/main.py 第194行
if analysis_result and analysis_result.get('type') == 'N_PATTERN_REVERSAL':
    # 发送通知的逻辑
```

### Q5: 可以同时监控多个品种吗？

**A:** 目前脚本只监控黄金（AU9999）。如需监控其他品种：
1. 复制一份代码到新目录
2. 修改 `src/gold_fetcher.py` 中的 `stock_code`
3. 创建新的定时任务

### Q6: 如何更新脚本到最新版本？

**A:**

**订阅模式：**
在「订阅管理」中，点击订阅的「运行」按钮，会自动拉取最新代码。

**手动模式：**
```bash
cd /ql/scripts/gold-monitor
git pull origin main
pip3 install -r requirements.txt
```

### Q7: 日志文件太大怎么办？

**A:** 脚本会自动管理日志大小。你也可以手动清理：

```bash
# 清空日志
> /ql/scripts/gold-monitor/logs/gold_monitor.log

# 只保留最近的输出结果
cd /ql/scripts/gold-monitor/output
ls -t | tail -n +11 | xargs rm -f
```

### Q8: 青龙面板路径和本地不一样？

**A:** 青龙面板的脚本路径通常是 `/ql/scripts/`。`qinglong_run.py` 已经做了路径适配，会自动处理。

## 进阶配置

### 自定义通知模板

如需修改飞书通知的样式和内容，可以编辑 `src/feishu_notifier.py` 文件。

### 启用更多日志

将环境变量 `LOG_LEVEL` 设置为 `DEBUG`，可以看到更详细的执行信息。

### 数据导出

执行结果会自动保存到 `output/` 目录，文件名格式：`result_YYYYMMDD_HHMMSS.txt`

历史数据保存在 `data/` 目录：
- `price_history.json` - 价格历史
- `reversal_history.json` - 反转信号历史

## 技术支持

如有问题，可以：
- 查看项目 [GitHub Issues](https://github.com/RylynnLai/gold-monitor/issues)
- 查看详细文档 [README.md](README.md)
- 检查执行日志排查问题

## 更新日志

### v1.0.0
- 支持青龙面板订阅模式
- 添加 N 字形反转检测
- 支持 K 线数据分析
- 优化飞书通知

## 许可证

MIT License
