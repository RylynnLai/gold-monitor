# 从飞书应用 API 迁移到 Webhook

## 迁移原因

新版本使用飞书 Webhook 方式，比之前的飞书开放平台应用更简单：

**优势：**
- ✅ 配置更简单（只需一个 URL）
- ✅ 无需维护 access_token
- ✅ 无需创建飞书应用
- ✅ 更稳定可靠

## 迁移步骤

### 1. 获取飞书 Webhook URL

参考 `WEBHOOK_GUIDE.md` 文档获取 Webhook URL。

简要步骤：
1. 打开飞书群聊
2. 设置 → 群机器人 → 添加机器人 → 自定义机器人
3. 复制生成的 Webhook URL

### 2. 更新环境变量

**旧配置（需要删除）：**
```bash
FEISHU_APP_ID=cli_xxxxx
FEISHU_APP_SECRET=xxxxx
FEISHU_CHAT_ID=oc_xxxxx
```

**新配置（仅需一个）：**
```bash
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

### 3. 本地开发环境

编辑 `.env` 文件：

```bash
# 删除这些旧配置
# FEISHU_APP_ID=...
# FEISHU_APP_SECRET=...
# FEISHU_CHAT_ID=...

# 添加新配置
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/your-webhook-token

# 其他配置保持不变
TREND_COUNT=3
LOG_LEVEL=INFO
```

### 4. 青龙面板环境

在青龙面板的「环境变量」页面：

1. **删除旧变量**（如果存在）：
   - `FEISHU_APP_ID`
   - `FEISHU_APP_SECRET`
   - `FEISHU_CHAT_ID`

2. **添加新变量**：
   - 名称：`FEISHU_WEBHOOK_URL`
   - 值：你的 Webhook URL
   - 备注：黄金监控飞书通知

### 5. 更新代码

如果你已经克隆了项目，拉取最新代码：

```bash
cd /path/to/gold-monitor
git pull origin main
```

或直接下载最新版本覆盖。

### 6. 测试新配置

运行测试命令验证配置是否正确：

```bash
# 测试 Webhook 通知
python3 src/feishu_notifier.py

# 运行完整测试
python3 test_mock.py
```

如果成功，你会在飞书群中收到测试消息。

## 配置对比

| 项目 | 旧方式（应用 API） | 新方式（Webhook） |
|------|-------------------|------------------|
| 配置项数量 | 3个 | 1个 |
| 需要创建应用 | 是 | 否 |
| 需要管理 token | 是 | 否 |
| 配置难度 | 较复杂 | 简单 |
| 维护成本 | 高 | 低 |

## 回滚方案

如果需要回退到旧版本：

1. 恢复旧配置到 `.env` 文件
2. 切换到旧代码版本
3. 重启服务

## 常见问题

**Q: 旧版本的数据会丢失吗？**
A: 不会。历史价格数据存储在 `data/price_history.json`，不受配置方式影响。

**Q: 迁移后需要重新部署吗？**
A: 是的，需要更新代码并修改环境变量。

**Q: 可以同时使用两种方式吗？**
A: 不建议。新版本已移除旧方式的支持，只保留 Webhook 方式。

**Q: 通知消息格式有变化吗？**
A: 没有变化，消息格式保持一致。

## 技术变更说明

### 文件变更

**修改的文件：**
- `src/feishu_notifier.py` - 移除 access_token 逻辑，改用 Webhook
- `src/config.py` - 移除应用配置，改用 WEBHOOK_URL
- `src/main.py` - 更新初始化参数
- `.env.example` - 更新配置示例

**新增的文件：**
- `WEBHOOK_GUIDE.md` - Webhook 配置详细指南
- `MIGRATION.md` - 本迁移指南

### 代码变更

**FeishuNotifier 类：**
```python
# 旧版本
notifier = FeishuNotifier(app_id, app_secret, chat_id)

# 新版本
notifier = FeishuNotifier(webhook_url)
```

**配置文件：**
```python
# 旧版本
from config import FEISHU_APP_ID, FEISHU_APP_SECRET, FEISHU_CHAT_ID

# 新版本
from config import FEISHU_WEBHOOK_URL
```

## 获取帮助

如果迁移过程中遇到问题：

1. 查看 `WEBHOOK_GUIDE.md` 详细配置指南
2. 查看 `USAGE.md` 使用说明
3. 查看日志文件 `logs/gold_monitor.log`
4. 提交 Issue 到项目仓库
