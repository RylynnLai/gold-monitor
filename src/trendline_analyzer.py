"""
基于趋势线突破的反转检测分析器
"""
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class TrendDirection(Enum):
    """趋势方向"""
    RISING = "上升"
    FALLING = "下降"
    NEUTRAL = "震荡"


class TrendlineAnalyzer:
    """趋势线分析器"""

    def __init__(
        self,
        trend_window_hours: int = 12,  # 趋势识别窗口（小时）
        min_pivot_distance: int = 3,   # 最小摆动点间隔（K线数）
        breakout_threshold: float = 0.001,  # 突破阈值（0.1%）
        min_trend_points: int = 2  # 最少需要的趋势点数
    ):
        """
        初始化趋势线分析器

        Args:
            trend_window_hours: 趋势识别窗口（小时）
            min_pivot_distance: 最小摆动点间隔
            breakout_threshold: 突破阈值（百分比）
            min_trend_points: 最少趋势点数
        """
        self.trend_window_hours = trend_window_hours
        self.min_pivot_distance = min_pivot_distance
        self.breakout_threshold = breakout_threshold
        self.min_trend_points = min_trend_points

        # 状态
        self.current_trend = TrendDirection.NEUTRAL
        self.trendline_value = None  # 当前趋势线的值
        self.trend_start_time = None  # 趋势开始时间
        self.last_reversal_time = None  # 上次反转时间

        logger.info(
            f"趋势线分析器初始化 - 窗口:{trend_window_hours}h, "
            f"突破阈值:{breakout_threshold*100:.2f}%, "
            f"最少点数:{min_trend_points}"
        )

    def identify_trend(self, kline_data: List[Dict]) -> TrendDirection:
        """
        识别当前趋势方向（使用线性回归）

        Args:
            kline_data: K线数据

        Returns:
            趋势方向
        """
        if len(kline_data) < 3:
            return TrendDirection.NEUTRAL

        # 使用收盘价进行线性回归
        closes = [k['close'] for k in kline_data]
        n = len(closes)

        # 计算线性回归斜率
        x_mean = (n - 1) / 2
        y_mean = sum(closes) / n

        numerator = sum((i - x_mean) * (closes[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return TrendDirection.NEUTRAL

        slope = numerator / denominator

        # 根据斜率判断趋势（进一步降低阈值）
        slope_percent = (slope / y_mean) * 100  # 转换为百分比

        if slope_percent > 0.005:  # 上升趋势（降低到0.005%）
            return TrendDirection.RISING
        elif slope_percent < -0.005:  # 下降趋势（降低到0.005%）
            return TrendDirection.FALLING
        else:
            return TrendDirection.NEUTRAL

    def find_pivot_points(
        self,
        kline_data: List[Dict],
        find_highs: bool = True
    ) -> List[Dict]:
        """
        识别摆动点（高点或低点）

        Args:
            kline_data: K线数据
            find_highs: True=查找高点，False=查找低点

        Returns:
            摆动点列表 [{index, price, datetime}, ...]
        """
        if len(kline_data) < self.min_pivot_distance * 2 + 1:
            return []

        pivots = []
        window = self.min_pivot_distance

        for i in range(window, len(kline_data) - window):
            current = kline_data[i]
            price_key = 'high' if find_highs else 'low'
            current_price = current[price_key]

            # 检查是否为局部极值
            is_pivot = True

            # 左侧窗口
            for j in range(i - window, i):
                if find_highs:
                    if kline_data[j]['high'] >= current_price:
                        is_pivot = False
                        break
                else:
                    if kline_data[j]['low'] <= current_price:
                        is_pivot = False
                        break

            # 右侧窗口
            if is_pivot:
                for j in range(i + 1, i + window + 1):
                    if find_highs:
                        if kline_data[j]['high'] >= current_price:
                            is_pivot = False
                            break
                    else:
                        if kline_data[j]['low'] <= current_price:
                            is_pivot = False
                            break

            if is_pivot:
                pivots.append({
                    'index': i,
                    'price': current_price,
                    'datetime': current['datetime']
                })

        return pivots

    def calculate_weighted_trendline(
        self,
        pivot_points: List[Dict],
        current_index: int
    ) -> Optional[float]:
        """
        计算加权平均趋势线（近期点权重更高）

        Args:
            pivot_points: 摆动点列表
            current_index: 当前K线索引

        Returns:
            趋势线在当前位置的值
        """
        if len(pivot_points) < self.min_trend_points:
            return None

        # 计算加权平均（线性权重，近期权重更高）
        total_weight = 0
        weighted_sum = 0

        for i, point in enumerate(pivot_points):
            weight = i + 1  # 权重：1, 2, 3, ...（越晚的点权重越高）
            weighted_sum += point['price'] * weight
            total_weight += weight

        if total_weight == 0:
            return None

        weighted_avg = weighted_sum / total_weight

        # 计算趋势线斜率（使用加权线性回归）
        if len(pivot_points) >= 2:
            # 简化版：使用第一个和最后一个点计算斜率
            first_point = pivot_points[0]
            last_point = pivot_points[-1]

            index_diff = last_point['index'] - first_point['index']
            if index_diff > 0:
                slope = (last_point['price'] - first_point['price']) / index_diff

                # 延长到当前位置
                extension = current_index - last_point['index']
                trendline_value = last_point['price'] + slope * extension

                return trendline_value

        return weighted_avg

    def check_breakout(
        self,
        current_price: float,
        trendline_value: float,
        trend: TrendDirection
    ) -> bool:
        """
        检查是否突破趋势线

        Args:
            current_price: 当前价格
            trendline_value: 趋势线值
            trend: 当前趋势

        Returns:
            是否突破
        """
        if trend == TrendDirection.FALLING:
            # 下降趋势中，价格突破高点趋势线（向上突破）
            breakout_price = trendline_value * (1 + self.breakout_threshold)
            return current_price > breakout_price

        elif trend == TrendDirection.RISING:
            # 上升趋势中，价格突破低点趋势线（向下突破）
            breakout_price = trendline_value * (1 - self.breakout_threshold)
            return current_price < breakout_price

        return False

    def analyze_kline_data(self, kline_data: List[Dict]) -> Optional[Dict]:
        """
        分析K线数据，检测趋势反转

        Args:
            kline_data: K线数据列表

        Returns:
            反转信号，如果未检测到则返回None
        """
        if len(kline_data) < 10:
            logger.debug("K线数据不足")
            return None

        # 1. 获取趋势窗口内的数据
        window_data = self._get_trend_window(kline_data)

        if len(window_data) < 5:
            logger.debug("窗口数据不足")
            return None

        # 2. 识别当前趋势
        trend = self.identify_trend(window_data)

        if trend == TrendDirection.NEUTRAL:
            logger.debug("当前为震荡行情，未形成明确趋势")
            self.current_trend = TrendDirection.NEUTRAL
            return None

        # 3. 根据趋势方向提取摆动点
        if trend == TrendDirection.FALLING:
            # 下降趋势：提取高点
            pivot_points = self.find_pivot_points(window_data, find_highs=True)
        else:
            # 上升趋势：提取低点
            pivot_points = self.find_pivot_points(window_data, find_highs=False)

        if len(pivot_points) < self.min_trend_points:
            logger.debug(f"摆动点不足（{len(pivot_points)}），需要至少{self.min_trend_points}个")
            return None

        # 4. 计算趋势线
        current_index = len(window_data) - 1
        trendline_value = self.calculate_weighted_trendline(pivot_points, current_index)

        if trendline_value is None:
            logger.debug("无法计算趋势线")
            return None

        # 5. 检测突破
        current_kline = kline_data[-1]
        current_price = current_kline['close']

        is_breakout = self.check_breakout(current_price, trendline_value, trend)

        # 6. 更新状态和生成信号
        if is_breakout:
            # 检测到突破 = 反转
            if trend == TrendDirection.FALLING:
                new_trend = TrendDirection.RISING
                reversal_type = "看涨反转"
            else:
                new_trend = TrendDirection.FALLING
                reversal_type = "看跌反转"

            # 避免重复通知（5分钟内）
            current_time = datetime.fromisoformat(current_kline['datetime'])
            if self.last_reversal_time:
                time_diff = (current_time - self.last_reversal_time).total_seconds() / 60
                if time_diff < 5:  # 5分钟内不重复通知
                    logger.debug(f"距离上次反转仅{time_diff:.1f}分钟，跳过")
                    return None

            self.last_reversal_time = current_time
            self.current_trend = new_trend

            logger.info(
                f"检测到{reversal_type}: {trend.value} → {new_trend.value}, "
                f"突破价格:{current_price:.2f}, 趋势线:{trendline_value:.2f}"
            )

            return {
                'type': 'TRENDLINE_BREAKOUT',
                'reversal_type': reversal_type,
                'from_trend': trend,
                'to_trend': new_trend,
                'breakout_price': current_price,
                'trendline_value': trendline_value,
                'breakout_percent': abs(current_price - trendline_value) / trendline_value * 100,
                'trigger_time': current_kline['datetime'],
                'pivot_points_count': len(pivot_points),
                'confidence': min(1.0, len(pivot_points) / 5)  # 基于摆动点数量的置信度
            }

        # 未检测到反转，但更新当前趋势状态
        self.current_trend = trend
        self.trendline_value = trendline_value

        return None

    def _get_trend_window(self, kline_data: List[Dict]) -> List[Dict]:
        """
        获取趋势识别窗口内的数据

        Args:
            kline_data: 完整K线数据

        Returns:
            窗口内的K线数据
        """
        if not kline_data:
            return []

        # 计算窗口时间范围
        latest_time = datetime.fromisoformat(kline_data[-1]['datetime'])
        window_start = latest_time - timedelta(hours=self.trend_window_hours)

        # 过滤窗口内的数据
        window_data = [
            k for k in kline_data
            if datetime.fromisoformat(k['datetime']) >= window_start
        ]

        return window_data

    def get_current_trend_info(self) -> Dict:
        """
        获取当前趋势信息

        Returns:
            趋势信息字典
        """
        return {
            'trend': self.current_trend,
            'trendline_value': self.trendline_value,
            'trend_start_time': self.trend_start_time,
            'last_reversal_time': self.last_reversal_time
        }


def test_trendline_analyzer():
    """测试趋势线分析器"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

    from kline_data_manager import KlineDataManager

    print("=" * 80)
    print("测试趋势线分析器")
    print("=" * 80)

    # 加载数据
    manager = KlineDataManager()
    kline_data = manager.load_kline_data()

    if not kline_data:
        print("无法加载K线数据")
        return

    print(f"\n加载了 {len(kline_data)} 条K线数据")
    print(f"时间范围: {kline_data[0]['datetime']} 至 {kline_data[-1]['datetime']}")

    # 创建分析器
    analyzer = TrendlineAnalyzer(
        trend_window_hours=12,
        min_pivot_distance=3,
        breakout_threshold=0.001,
        min_trend_points=2
    )

    # 模拟实时检测（逐步增加数据）
    print("\n开始模拟实时检测...")
    reversals = []

    for i in range(50, len(kline_data)):
        partial_data = kline_data[:i+1]
        result = analyzer.analyze_kline_data(partial_data)

        if result:
            from zoneinfo import ZoneInfo
            dt_utc = datetime.fromisoformat(result['trigger_time'])
            dt_et = dt_utc.astimezone(ZoneInfo('America/New_York'))

            print(f"\n🔔 {result['reversal_type']}!")
            print(f"   时间: {dt_et.strftime('%m-%d %H:%M')} ET")
            print(f"   {result['from_trend'].value} → {result['to_trend'].value}")
            print(f"   突破价格: {result['breakout_price']:.2f}")
            print(f"   趋势线值: {result['trendline_value']:.2f}")
            print(f"   突破幅度: {result['breakout_percent']:.2f}%")
            print(f"   置信度: {result['confidence']:.2f}")

            reversals.append(result)

    print(f"\n总计检测到 {len(reversals)} 个反转信号")


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s - %(message)s'
    )
    test_trendline_analyzer()
