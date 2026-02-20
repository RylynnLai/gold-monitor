import os
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
BASE_DIR = Path(__file__).parent.parent
ENV_FILE = BASE_DIR / '.env'
load_dotenv(ENV_FILE)

# 飞书配置（Webhook 方式）
FEISHU_WEBHOOK_URL = os.getenv('FEISHU_WEBHOOK_URL', '')

# 监控配置
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', 300))
TREND_COUNT = int(os.getenv('TREND_COUNT', 3))

# 日志配置
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_DIR = BASE_DIR / 'logs'
LOG_FILE = LOG_DIR / 'gold_monitor.log'

# 数据配置
DATA_DIR = BASE_DIR / 'data'
PRICE_HISTORY_FILE = DATA_DIR / 'price_history.json'
KLINE_DATA_FILE = DATA_DIR / 'kline_48h.json'

# K线数据配置
KLINE_PERIOD = os.getenv('KLINE_PERIOD', '5min')  # K线周期
KLINE_HOURS = int(os.getenv('KLINE_HOURS', 48))   # K线数据时长（小时）

# 价格分析阈值配置
MIN_REVERSAL_THRESHOLD = float(os.getenv('MIN_REVERSAL_THRESHOLD', 0.003))
SWING_WINDOW_SIZE = int(os.getenv('SWING_WINDOW_SIZE', 2))
MIN_STRENGTH = float(os.getenv('MIN_STRENGTH', 0.5))

# 确保目录存在
LOG_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)
