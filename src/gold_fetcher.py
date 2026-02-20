import logging
import time
from datetime import datetime
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)


class GoldPriceFetcher:
    """黄金价格获取器（使用 AKShare）"""

    def __init__(self):
        # 使用 AKShare 获取黄金现货价格
        # AU9999 是上海黄金交易所的现货黄金代码
        self.symbol = "Au99.99"  # AKShare 中的品种代码
        self.max_retries = 3  # 最大重试次数
        self.retry_delay = 2  # 重试延迟（秒）

    def get_main_contract_code(self) -> str:
        """
        动态获取黄金期货主力合约代码

        Returns:
            主力合约代码，如 'au2604'
        """
        try:
            # 简化实现：根据当前月份推算主力合约
            # 黄金期货主力合约通常是偶数月：2, 4, 6, 8, 10, 12月
            now = datetime.now()
            year = now.year % 100  # 两位年份
            month = now.month

            # 找到下一个偶数月
            if month % 2 == 0:
                contract_month = month if now.day < 15 else month + 2
            else:
                contract_month = month + 1

            if contract_month > 12:
                contract_month = contract_month - 12
                year = year + 1

            symbol = f"au{year:02d}{contract_month:02d}"
            logger.debug(f"计算得到主力合约: {symbol}")

            return symbol

        except Exception as e:
            logger.warning(f"动态获取合约失败: {e}，使用默认值")
            return "au2604"  # 降级返回默认值

    def get_current_price(self) -> Optional[Dict[str, any]]:
        """
        获取当前黄金价格（使用 AKShare，带重试机制）

        Returns:
            包含价格信息的字典，如果失败则返回 None
            {
                'price': float,  # 当前价格（元/克）
                'change': float,  # 涨跌额
                'change_percent': float,  # 涨跌幅
                'timestamp': str,  # 时间戳
                'name': str,  # 品种名称
                'open': float,  # 今开
                'high': float,  # 最高
                'low': float,  # 最低
                'volume': float  # 成交量
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
            import akshare as ak
            import json

            # 方法1：获取实时行情（最新价格）
            logger.debug("正在获取上海黄金交易所实时行情...")

            try:
                quotations_df = ak.spot_quotations_sge()
            except json.JSONDecodeError as e:
                logger.error(f"JSON 解析错误: {e}")
                logger.error("可能是网络问题或 API 返回了非 JSON 数据")
                raise
            except Exception as e:
                logger.error(f"获取实时行情失败: {e}")
                raise

            # 检查数据框是否为空
            if quotations_df is None or quotations_df.empty:
                logger.error("实时行情数据为空")
                return None

            # 筛选 AU9999 数据
            au9999_data = quotations_df[quotations_df['品种'] == self.symbol]

            if au9999_data.empty:
                logger.error(f"未找到 {self.symbol} 数据")
                logger.debug(f"可用品种: {quotations_df['品种'].unique().tolist()}")
                return None

            latest_quote = au9999_data.iloc[-1]
            current_price = float(latest_quote['现价'])

            logger.debug(f"获取到实时价格: {current_price} 元/克")

            # 方法2：尝试获取历史数据（开盘价、最高最低价）
            open_price, high_price, low_price = self._fetch_historical_data(current_price)

            # 计算涨跌额和涨跌幅
            change = current_price - open_price
            change_percent = (change / open_price * 100) if open_price > 0 else 0

            result = {
                'price': current_price,  # 当前价格
                'change': change,  # 涨跌额
                'change_percent': change_percent,  # 涨跌幅
                'timestamp': datetime.now().isoformat(),
                'name': 'AU9999',
                'open': open_price,  # 今开
                'high': high_price,  # 最高
                'low': low_price,  # 最低
                'volume': 0,  # 成交量（AKShare 未提供）
            }

            logger.info(f"成功获取黄金价格: {result['price']:.2f} 元/克 (AKShare)")
            logger.debug(f"价格详情: 开{open_price:.2f} 高{high_price:.2f} 低{low_price:.2f}")

            return result

        except ImportError:
            logger.error("AKShare 库未安装，请运行: pip install akshare")
            return None
        except Exception as e:
            # 这里会重新抛出异常，让外层的重试机制捕获
            raise

    def _fetch_historical_data(self, fallback_price: float) -> tuple:
        """
        获取历史数据（开盘价、最高最低价）

        Args:
            fallback_price: 降级使用的价格（当历史数据不可用时）

        Returns:
            (open_price, high_price, low_price)
        """
        try:
            import akshare as ak

            logger.debug("尝试获取历史数据...")
            hist_df = ak.spot_hist_sge(symbol="AU9999")

            if not hist_df.empty:
                # 获取最新一天的数据
                latest_hist = hist_df.iloc[-1]

                # 检查数据是否有效（不为0）
                if latest_hist['open'] > 0:
                    open_price = float(latest_hist['open'])
                    high_price = float(latest_hist['high'])
                    low_price = float(latest_hist['low'])
                    logger.debug(f"历史数据有效: 开{open_price} 高{high_price} 低{low_price}")
                    return (open_price, high_price, low_price)

            # 历史数据无效或为空，使用降级价格
            logger.debug("历史数据无效，使用当前价格作为降级")
            return (fallback_price, fallback_price, fallback_price)

        except Exception as e:
            logger.debug(f"获取历史数据失败: {e}，使用当前价格")
            return (fallback_price, fallback_price, fallback_price)

    def get_48h_kline_data(self, period: str = '5') -> Optional[List[Dict]]:
        """
        获取48小时的K线数据（576条5分钟K线）

        Args:
            period: K线周期 ('5' = 5分钟)

        Returns:
            K线数据列表，每条包含 {datetime, open, high, low, close, volume, hold}
            如果失败返回 None
        """
        for attempt in range(self.max_retries):
            try:
                if attempt > 0:
                    logger.info(f"第 {attempt + 1}/{self.max_retries} 次尝试获取K线数据...")
                    time.sleep(self.retry_delay)

                result = self._fetch_kline_data(period)
                if result:
                    return result

            except Exception as e:
                logger.warning(f"第 {attempt + 1} 次尝试获取K线失败: {e}")
                if attempt == self.max_retries - 1:
                    logger.error(f"所有 {self.max_retries} 次尝试均失败")
                    logger.debug("详细错误信息: ", exc_info=True)

        return None

    def _fetch_kline_data(self, period: str) -> Optional[List[Dict]]:
        """内部方法：执行单次K线数据获取"""
        try:
            import akshare as ak

            # 1. 获取当前主力合约代码
            symbol = self.get_main_contract_code()

            logger.info(f"正在获取黄金期货 {symbol} 的{period}分钟K线数据...")

            # 2. 获取K线数据
            df = ak.futures_zh_minute_sina(symbol=symbol, period=period)

            if df is None or df.empty:
                logger.error("K线数据为空")
                return None

            # 3. 提取最近576条（48小时 = 576个5分钟）
            n_bars = 576
            df_48h = df.tail(n_bars)

            # 4. 转换为字典列表
            kline_data = []
            for _, row in df_48h.iterrows():
                kline_data.append({
                    'datetime': str(row['datetime']),
                    'open': float(row['open']),
                    'high': float(row['high']),
                    'low': float(row['low']),
                    'close': float(row['close']),
                    'volume': int(row.get('volume', 0)),
                    'hold': int(row.get('hold', 0))
                })

            logger.info(f"成功获取 {len(kline_data)} 条K线数据")
            logger.debug(f"时间范围: {kline_data[0]['datetime']} 至 {kline_data[-1]['datetime']}")
            logger.debug(f"价格范围: {min(k['low'] for k in kline_data):.2f} - {max(k['high'] for k in kline_data):.2f}")

            return kline_data

        except ImportError:
            logger.error("AKShare 库未安装")
            return None
        except Exception as e:
            # 这里会重新抛出异常，让外层的重试机制捕获
            raise


def test_fether():
    """测试函数"""
    fetcher = GoldPriceFetcher()
    price_info = fetcher.get_current_price()
    if price_info:
        print(f"当前价格: {price_info['price']} 元/克")
        print(f"涨跌额: {price_info['change']} 元")
        print(f"涨跌幅: {price_info['change_percent']}%")
    else:
        print("获取价格失败")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    test_fetcher()
