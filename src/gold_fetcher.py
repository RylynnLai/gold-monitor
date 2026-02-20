import logging
import time
import requests
from datetime import datetime
from typing import Optional, Dict, List
from . import config

logger = logging.getLogger(__name__)


class GoldPriceFetcher:
    """黄金价格获取器（使用 Twelve Data API - XAU/USD 现货）"""

    def __init__(self):
        # 使用 Twelve Data API 获取黄金现货价格 XAU/USD
        self.api_key = "9fe93e2197664306a03d90d4d859f26f"
        self.symbol = "XAU/USD"  # 黄金现货美元价格
        self.base_url = "https://api.twelvedata.com"
        self.max_retries = 3  # 最大重试次数
        self.retry_delay = 2  # 重试延迟（秒）

    def get_current_price(self) -> Optional[Dict[str, any]]:
        """
        获取当前黄金价格（使用 Twelve Data API，带重试机制）

        Returns:
            包含价格信息的字典，如果失败则返回 None
            {
                'price': float,  # 当前价格（美元/盎司）
                'change': float,  # 涨跌额
                'change_percent': float,  # 涨跌幅
                'timestamp': str,  # 时间戳
                'name': str,  # 品种名称
                'open': float,  # 今开
                'high': float,  # 最高
                'low': float,  # 最低
                'volume': float  # 成交量（XAU/USD 无成交量）
            }
        """
        # 带重试的获取价格
        for attempt in range(self.max_retries):
            try:
                if attempt > 0:
                    logger.info(f"第 {attempt + 1}/{self.max_retries} 次尝试获取价格...")
                    time.sleep(self.retry_delay)

                result = self._fetch_price()
                if result:
                    return result

            except Exception as e:
                logger.warning(f"第 {attempt + 1} 次尝试失败: {e}")
                if attempt == self.max_retries - 1:
                    logger.error(f"所有 {self.max_retries} 次尝试均失败")
                    logger.debug("详细错误信息: ", exc_info=True)

        return None

    def _fetch_price(self) -> Optional[Dict[str, any]]:
        """内部方法：执行单次价格获取"""
        try:
            logger.debug(f"正在获取 {self.symbol} 实时行情...")

            # 获取当前价格
            price_url = f"{self.base_url}/price"
            params = {
                'symbol': self.symbol,
                'apikey': self.api_key
            }

            response = requests.get(price_url, params=params, timeout=10)
            response.raise_for_status()
            price_data = response.json()

            if 'price' not in price_data:
                logger.error(f"API返回异常: {price_data}")
                return None

            current_price = float(price_data['price'])

            # 获取今日的开高低收数据（使用1天的时间序列）
            quote_url = f"{self.base_url}/quote"
            quote_params = {
                'symbol': self.symbol,
                'apikey': self.api_key
            }

            quote_response = requests.get(quote_url, params=quote_params, timeout=10)
            quote_response.raise_for_status()
            quote_data = quote_response.json()

            # 提取数据
            open_price = float(quote_data.get('open', current_price))
            high_price = float(quote_data.get('high', current_price))
            low_price = float(quote_data.get('low', current_price))

            # 计算涨跌额和涨跌幅
            change = current_price - open_price
            change_percent = (change / open_price * 100) if open_price > 0 else 0

            result = {
                'price': current_price,  # 当前价格
                'change': change,  # 涨跌额
                'change_percent': change_percent,  # 涨跌幅
                'timestamp': datetime.now().isoformat(),
                'name': 'XAU/USD',  # 黄金现货
                'open': open_price,  # 今开
                'high': high_price,  # 最高
                'low': low_price,  # 最低
                'volume': 0,  # XAU/USD 无成交量概念
            }

            logger.info(f"成功获取黄金价格: ${result['price']:.2f}/oz (Twelve Data)")
            logger.debug(f"价格详情: 开${open_price:.2f} 高${high_price:.2f} 低${low_price:.2f}")

            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"API请求失败: {e}")
            raise
        except Exception as e:
            # 这里会重新抛出异常，让外层的重试机制捕获
            raise

    def get_48h_kline_data(self, period: Optional[str] = None, hours: Optional[int] = None) -> Optional[List[Dict]]:
        """
        获取K线数据（支持配置周期和时长）

        Args:
            period: K线周期，支持 '1min', '5min', '15min', '30min', '1h', '1day' 等
                   默认从 config.KLINE_PERIOD 读取
            hours: 数据时长（小时），默认从 config.KLINE_HOURS 读取

        Returns:
            K线数据列表，每条包含 {datetime, open, high, low, close, volume}
            如果失败返回 None
        """
        # 使用配置的默认值
        period = period or config.KLINE_PERIOD
        hours = hours or config.KLINE_HOURS

        for attempt in range(self.max_retries):
            try:
                if attempt > 0:
                    logger.info(f"第 {attempt + 1}/{self.max_retries} 次尝试获取K线数据...")
                    time.sleep(self.retry_delay)

                result = self._fetch_kline_data(period, hours)
                if result:
                    return result

            except Exception as e:
                logger.warning(f"第 {attempt + 1} 次尝试获取K线失败: {e}")
                if attempt == self.max_retries - 1:
                    logger.error(f"所有 {self.max_retries} 次尝试均失败")
                    logger.debug("详细错误信息: ", exc_info=True)

        return None

    def _fetch_kline_data(self, period: str, hours: int = 48) -> Optional[List[Dict]]:
        """
        内部方法：执行单次K线数据获取

        Args:
            period: K线周期
            hours: 数据时长（小时）
        """
        try:
            logger.info(f"正在获取 {self.symbol} 的 {period} K线数据（{hours}小时）...")

            # 映射周期格式（Twelve Data 使用 5min 而不是 5）
            interval_map = {
                '1': '1min',
                '5': '5min',
                '15': '15min',
                '30': '30min',
                '60': '1h',
            }
            interval = interval_map.get(period, period)

            # 计算需要获取的数据量（基于小时数）
            bars_per_hour = {
                '1min': 60,
                '5min': 12,
                '15min': 4,
                '30min': 2,
                '1h': 1,
            }
            output_size = bars_per_hour.get(interval, 12) * hours

            url = f"{self.base_url}/time_series"
            params = {
                'symbol': self.symbol,
                'interval': interval,
                'outputsize': min(output_size, 5000),  # API限制
                'apikey': self.api_key
            }

            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if 'values' not in data:
                logger.error(f"API返回异常: {data}")
                return None

            # 转换为K线数据格式
            kline_data = []
            for item in reversed(data['values']):  # 反转使其按时间正序
                kline_data.append({
                    'datetime': item['datetime'],
                    'open': float(item['open']),
                    'high': float(item['high']),
                    'low': float(item['low']),
                    'close': float(item['close']),
                    'volume': 0,  # XAU/USD 无成交量
                })

            logger.info(f"成功获取 {len(kline_data)} 条K线数据")
            if kline_data:
                logger.debug(f"时间范围: {kline_data[0]['datetime']} 至 {kline_data[-1]['datetime']}")
                logger.debug(f"价格范围: ${min(k['low'] for k in kline_data):.2f} - ${max(k['high'] for k in kline_data):.2f}")

            return kline_data

        except requests.exceptions.RequestException as e:
            logger.error(f"API请求失败: {e}")
            raise
        except Exception as e:
            # 这里会重新抛出异常，让外层的重试机制捕获
            raise


def test_fetcher():
    """测试函数"""
    fetcher = GoldPriceFetcher()

    print("=" * 70)
    print("测试黄金现货价格获取（Twelve Data - XAU/USD）")
    print("=" * 70)

    # 测试获取当前价格
    print("\n1. 获取当前价格:")
    price_info = fetcher.get_current_price()
    if price_info:
        print(f"   当前价格: ${price_info['price']:.2f}/oz")
        print(f"   涨跌额: ${price_info['change']:.2f}")
        print(f"   涨跌幅: {price_info['change_percent']:.2f}%")
        print(f"   今开: ${price_info['open']:.2f}")
        print(f"   最高: ${price_info['high']:.2f}")
        print(f"   最低: ${price_info['low']:.2f}")
    else:
        print("   ❌ 获取价格失败")

    # 测试获取K线数据
    print("\n2. 获取5分钟K线数据:")
    kline_data = fetcher.get_48h_kline_data('5min')
    if kline_data:
        print(f"   ✓ 获取到 {len(kline_data)} 条K线")
        print(f"   时间范围: {kline_data[0]['datetime']} 至 {kline_data[-1]['datetime']}")
        print(f"\n   最新K线:")
        latest = kline_data[-1]
        print(f"   时间: {latest['datetime']}")
        print(f"   开: ${latest['open']:.2f}")
        print(f"   高: ${latest['high']:.2f}")
        print(f"   低: ${latest['low']:.2f}")
        print(f"   收: ${latest['close']:.2f}")
    else:
        print("   ❌ 获取K线失败")

    print("\n" + "=" * 70)
    print("说明:")
    print("- 数据源: Twelve Data API")
    print("- 品种: XAU/USD（黄金现货美元价格）")
    print("- 更新: 实时（1分钟级别）")
    print("- 限制: 800次/天（免费账户）")
    print("=" * 70)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    test_fetcher()
