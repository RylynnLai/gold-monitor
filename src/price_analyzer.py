import json
import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from enum import Enum
from . import config

logger = logging.getLogger(__name__)


class TrendDirection(Enum):
    """趋势方向"""
    UP = "上涨"
    DOWN = "下跌"
    FLAT = "持平"


class NPattern(Enum):
    """N字形形态"""
    RISING = "上升N字形"     # 更高的高点 + 更高的低点
    FALLING = "下降N字形"    # 更低的高点 + 更低的低点
    UNDEFINED = "未定义"


class NPatternState:
    """N字形状态管理"""
    def __init__(self):
        self.current_pattern: Optional[Dict] = None      # 当前N字形形态
        self.previous_pattern: Optional[Dict] = None     # 上一次形态
        self.swing_points_history: List[Dict] = []       # 摇摆点历史
        self.last_reversal_time: Optional[datetime] = None
        self.reversal_count: int = 0


class PriceAnalyzer:
    """价格趋势分析器（基于K线数据）"""

    def __init__(self):
        """
        初始化分析器（K线模式，从config读取阈值参数）
        """
        # N字形分析相关属性
        self.n_pattern_state = NPatternState()

        # 从配置文件读取阈值参数
        self.min_reversal_threshold = config.MIN_REVERSAL_THRESHOLD
        self.swing_window_size = config.SWING_WINDOW_SIZE
        self.min_strength = config.MIN_STRENGTH

        # 兼容性：保留空的price_history以支持旧的统计方法
        self.price_history = []

        logger.info(f"价格分析器初始化完成（K线模式）- 阈值: reversal={self.min_reversal_threshold}, "
                   f"window={self.swing_window_size}, strength={self.min_strength}")

    def _load_history(self):
        """从文件加载历史数据"""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    self.price_history = json.load(f)
                logger.info(f"加载了 {len(self.price_history)} 条历史记录")
            except Exception as e:
                logger.error(f"加载历史数据失败: {e}")
                self.price_history = []
        else:
            logger.info("历史文件不存在，将创建新文件")
            self.price_history = []

    def _save_history(self):
        """保存历史数据到文件"""
        try:
            # 只保留最近 1000 条记录，避免文件过大
            if len(self.price_history) > 1000:
                self.price_history = self.price_history[-1000:]

            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.price_history, f, ensure_ascii=False, indent=2)
            logger.debug("历史数据已保存")
        except Exception as e:
            logger.error(f"保存历史数据失败: {e}")

    def add_price(self, price_info: Dict) -> Optional[Dict]:
        """
        添加新的价格记录并分析趋势

        Args:
            price_info: 价格信息字典

        Returns:
            如果检测到N字形反转，返回反转信息字典，否则返回 None
        """
        # 添加到历史记录
        record = {
            'price': price_info['price'],
            'timestamp': price_info['timestamp'],
            'change': price_info.get('change', 0)
        }
        self.price_history.append(record)
        self._save_history()

        # 使用N字形分析替代原有的趋势分析
        return self._analyze_trend_n_pattern()

    def _analyze_trend(self) -> Optional[Dict]:
        """
        分析最近的价格趋势

        Returns:
            如果检测到连续趋势，返回趋势信息
        """
        if len(self.price_history) < self.trend_count:
            logger.debug(f"历史记录不足 {self.trend_count} 条，无法分析趋势")
            return None

        # 获取最近 N 条记录
        recent_prices = [record['price'] for record in self.price_history[-self.trend_count:]]

        # 检查是否连续上涨
        is_continuous_up = all(
            recent_prices[i] < recent_prices[i + 1]
            for i in range(len(recent_prices) - 1)
        )

        # 检查是否连续下跌
        is_continuous_down = all(
            recent_prices[i] > recent_prices[i + 1]
            for i in range(len(recent_prices) - 1)
        )

        if is_continuous_up:
            direction = TrendDirection.UP
        elif is_continuous_down:
            direction = TrendDirection.DOWN
        else:
            logger.debug("未检测到连续趋势")
            return None

        # 计算变化幅度
        start_price = recent_prices[0]
        current_price = recent_prices[-1]
        change_percent = ((current_price - start_price) / start_price) * 100

        trend_info = {
            'direction': direction,
            'count': self.trend_count,
            'current_price': current_price,
            'start_price': start_price,
            'change_percent': change_percent,
            'prices': recent_prices,
            'timestamps': [record['timestamp'] for record in self.price_history[-self.trend_count:]]
        }

        logger.info(
            f"检测到连续{direction.value}趋势: "
            f"{start_price:.2f} → {current_price:.2f} "
            f"({change_percent:+.2f}%)"
        )

        return trend_info

    def get_recent_history(self, count: int = 10) -> List[Dict]:
        """
        获取最近的价格历史

        Args:
            count: 获取的记录数量

        Returns:
            最近的价格记录列表
        """
        return self.price_history[-count:]

    def get_today_history(self) -> List[Dict]:
        """
        获取今天的所有价格记录

        Returns:
            今天的价格记录列表
        """
        today = datetime.now().date()
        return [
            record for record in self.price_history
            if datetime.fromisoformat(record['timestamp']).date() == today
        ]

    def get_summary_stats(self) -> Dict:
        """
        获取统计摘要

        Returns:
            统计信息字典
        """
        today_records = self.get_today_history()

        stats = {
            'total_records': len(self.price_history),
            'today_count': len(today_records),
            'today_high': 0,
            'today_low': 0,
        }

        if today_records:
            stats['today_high'] = max(r['price'] for r in today_records)
            stats['today_low'] = min(r['price'] for r in today_records)

        return stats

    def clear_history(self):
        """清空历史记录"""
        self.price_history = []
        self._save_history()
        logger.info("历史记录已清空")

    # ==================== N字形分析方法 ====================

    def _get_48h_history(self) -> List[Dict]:
        """
        获取最近48小时的价格数据

        Returns:
            最近48小时的价格记录列表
        """
        cutoff_time = datetime.now() - timedelta(hours=48)
        return [
            record for record in self.price_history
            if datetime.fromisoformat(record['timestamp']) >= cutoff_time
        ]

    def _identify_swing_points(self, price_data: List[Dict],
                               min_threshold: float = 0.003) -> List[Dict]:
        """
        识别价格数据中的摇摆点（局部高点和低点）

        Args:
            price_data: 价格历史数据
            min_threshold: 最小幅度阈值（默认0.3%）

        Returns:
            摇摆点列表，每个包含 {index, price, timestamp, type: 'HIGH'/'LOW'}
        """
        if len(price_data) < 5:
            logger.debug(f"数据点不足（{len(price_data)}），需要至少5个点识别摇摆点")
            return []

        swing_points = []
        window_size = self.swing_window_size  # 左右各看2个点

        for i in range(window_size, len(price_data) - window_size):
            current_price = price_data[i]['price']

            # 检查局部高点和低点
            left_prices = [price_data[j]['price'] for j in range(i - window_size, i)]
            right_prices = [price_data[j]['price'] for j in range(i + 1, i + window_size + 1)]

            is_high = all(current_price > p for p in left_prices + right_prices)
            is_low = all(current_price < p for p in left_prices + right_prices)

            if is_high or is_low:
                # 幅度过滤：与上一个摇摆点比较
                if swing_points:
                    last_swing = swing_points[-1]
                    price_change_pct = abs(current_price - last_swing['price']) / last_swing['price']

                    if price_change_pct < min_threshold:
                        continue  # 幅度不足，跳过

                swing_points.append({
                    'index': i,
                    'price': current_price,
                    'timestamp': price_data[i]['timestamp'],
                    'type': 'HIGH' if is_high else 'LOW'
                })

        logger.debug(f"识别到 {len(swing_points)} 个摇摆点")
        return swing_points

    def _calculate_pattern_strength(self, swing_points: List[Dict]) -> float:
        """
        计算N字形形态强度（0-1）

        考虑因素：
        1. 价格变化幅度（越大越强）- 权重70%
        2. 摇摆点间的幅度一致性 - 权重30%

        Args:
            swing_points: 摇摆点列表

        Returns:
            形态强度 (0-1)
        """
        if len(swing_points) < 3:
            return 0.0

        # 1. 价格幅度得分
        price_range = abs(swing_points[-1]['price'] - swing_points[0]['price'])
        amplitude_score = min(price_range / swing_points[0]['price'] / 0.02, 1.0)  # 2%为满分

        # 2. 一致性得分（相邻摇摆点间幅度的一致性）
        changes = []
        for i in range(len(swing_points) - 1):
            change = abs(swing_points[i + 1]['price'] - swing_points[i]['price'])
            changes.append(change)

        if changes:
            avg_change = sum(changes) / len(changes)
            if avg_change > 0:
                consistency = 1.0 - (max(changes) - min(changes)) / avg_change
            else:
                consistency = 0.5
        else:
            consistency = 0.5

        # 综合得分
        strength = (amplitude_score * 0.7 + consistency * 0.3)
        return max(0.0, min(1.0, strength))

    def _detect_n_pattern(self, swing_points: List[Dict]) -> Optional[Dict]:
        """
        检测当前N字形形态

        需要至少3个摇摆点形成一个完整的"N"

        Args:
            swing_points: 摇摆点列表

        Returns:
            N字形形态信息，如果未检测到则返回None
        """
        if len(swing_points) < 3:
            logger.debug(f"摇摆点不足（{len(swing_points)}），需要至少3个")
            return None

        # 提取最近3个摇摆点
        recent_swings = swing_points[-3:]

        pattern = None

        # 上升N字形检测: LOW-HIGH-LOW 且第3个LOW > 第1个LOW
        if (recent_swings[0]['type'] == 'LOW' and
                recent_swings[1]['type'] == 'HIGH' and
                recent_swings[2]['type'] == 'LOW'):

            # 检查是否形成更高的低点
            if recent_swings[2]['price'] > recent_swings[0]['price']:
                # 进一步检查高点也在抬升（如果有足够历史）
                if len(swing_points) >= 5:
                    prev_high = next((sp for sp in swing_points[-5:-2] if sp['type'] == 'HIGH'), None)
                    if prev_high and recent_swings[1]['price'] > prev_high['price']:
                        pattern = NPattern.RISING
                else:
                    pattern = NPattern.RISING

        # 下降N字形检测: HIGH-LOW-HIGH 且第3个HIGH < 第1个HIGH
        elif (recent_swings[0]['type'] == 'HIGH' and
              recent_swings[1]['type'] == 'LOW' and
              recent_swings[2]['type'] == 'HIGH'):

            # 检查是否形成更低的高点
            if recent_swings[2]['price'] < recent_swings[0]['price']:
                # 进一步检查低点也在下移
                if len(swing_points) >= 5:
                    prev_low = next((sp for sp in swing_points[-5:-2] if sp['type'] == 'LOW'), None)
                    if prev_low and recent_swings[1]['price'] < prev_low['price']:
                        pattern = NPattern.FALLING
                else:
                    pattern = NPattern.FALLING

        if pattern:
            strength = self._calculate_pattern_strength(recent_swings)
            change_percent = ((recent_swings[-1]['price'] - recent_swings[0]['price'])
                             / recent_swings[0]['price'] * 100)

            result = {
                'pattern': pattern,
                'swing_points': recent_swings,
                'strength': strength,
                'start_price': recent_swings[0]['price'],
                'end_price': recent_swings[-1]['price'],
                'change_percent': change_percent
            }

            logger.debug(f"检测到{pattern.value}，强度{strength:.2f}，幅度{change_percent:+.2f}%")
            return result

        return None

    def _check_reversal(self, current_pattern: Dict,
                       previous_pattern: Optional[Dict]) -> Optional[Dict]:
        """
        检测趋势反转信号

        反转条件：
        1. 形态确实发生改变（RISING ↔ FALLING）
        2. 新形态幅度 >= 0.3%
        3. 新形态强度 >= 0.5

        Args:
            current_pattern: 当前N字形形态
            previous_pattern: 上一次形态

        Returns:
            反转信号，如果未检测到反转则返回None
        """
        if not current_pattern or not previous_pattern:
            return None

        current_type = current_pattern['pattern']
        previous_type = previous_pattern['pattern']

        # 检测形态改变
        if current_type == previous_type:
            return None

        # 检测幅度阈值（使用配置的 min_reversal_threshold）
        min_change_percent = self.min_reversal_threshold * 100  # 转换为百分比
        if abs(current_pattern['change_percent']) < min_change_percent:
            logger.debug(f"形态幅度不足: {current_pattern['change_percent']:.2f}% (最小要求: {min_change_percent:.2f}%)")
            return None

        # 检测形态强度
        if current_pattern['strength'] < self.min_strength:
            logger.debug(f"形态强度不足: {current_pattern['strength']:.2f}")
            return None

        # 创建反转信号
        reversal_signal = {
            'detected': True,
            'from_pattern': previous_type,
            'to_pattern': current_type,
            'confidence': current_pattern['strength'],
            'trigger_price': current_pattern['end_price'],
            'trigger_time': current_pattern['swing_points'][-1]['timestamp'],
            'change_percent': current_pattern['change_percent']
        }

        # 判断反转类型
        if current_type == NPattern.RISING and previous_type == NPattern.FALLING:
            reversal_signal['reversal_type'] = 'BULLISH'  # 看涨反转
            logger.info("检测到BULLISH反转: 下降N字形 → 上升N字形")
        elif current_type == NPattern.FALLING and previous_type == NPattern.RISING:
            reversal_signal['reversal_type'] = 'BEARISH'  # 看跌反转
            logger.info("检测到BEARISH反转: 上升N字形 → 下降N字形")

        return reversal_signal

    def _analyze_trend_n_pattern(self) -> Optional[Dict]:
        """
        使用N字形分析趋势（替代原有的 _analyze_trend）

        流程：
        1. 获取48小时数据
        2. 识别摇摆点
        3. 检测N字形形态
        4. 检测反转
        5. 更新状态

        Returns:
            分析结果，包含反转信号等信息
        """
        # 1. 获取48小时数据
        price_data_48h = self._get_48h_history()

        if len(price_data_48h) < 10:  # 至少需要10个数据点
            logger.debug(f"48小时内数据点不足（{len(price_data_48h)}），无法进行N字形分析")
            return None

        # 2. 识别摇摆点
        swing_points = self._identify_swing_points(price_data_48h, self.min_reversal_threshold)

        if len(swing_points) < 3:
            logger.debug(f"摇摆点不足（{len(swing_points)}），需要至少3个")
            return None

        # 3. 检测N字形形态
        current_pattern = self._detect_n_pattern(swing_points)

        if not current_pattern:
            logger.debug("未检测到有效的N字形形态")
            return None

        # 4. 检测反转
        reversal_signal = self._check_reversal(
            current_pattern,
            self.n_pattern_state.previous_pattern
        )

        # 5. 更新状态
        self.n_pattern_state.previous_pattern = self.n_pattern_state.current_pattern
        self.n_pattern_state.current_pattern = current_pattern
        self.n_pattern_state.swing_points_history = swing_points

        if reversal_signal and reversal_signal.get('detected'):
            self.n_pattern_state.last_reversal_time = datetime.now()
            self.n_pattern_state.reversal_count += 1

            return {
                'type': 'N_PATTERN_REVERSAL',
                'reversal_signal': reversal_signal,
                'current_pattern': current_pattern,
                'swing_points': swing_points,
                'analysis_window': '48h',
                'data_points': len(price_data_48h)
            }

        return None


    # ==================== K线数据分析方法 ====================

    def _identify_swing_points_kline(self, kline_data: List[Dict],
                                     min_threshold: float = 0.003) -> List[Dict]:
        """
        从K线数据识别摇摆点（使用High/Low）

        Args:
            kline_data: K线数据列表 [{datetime, open, high, low, close, volume, hold}, ...]
            min_threshold: 最小幅度阈值（默认0.3%）

        Returns:
            摇摆点列表 [{'index': int, 'price': float, 'datetime': str, 'type': 'HIGH'/'LOW', 'close': float}]
        """
        if len(kline_data) < 5:
            logger.debug(f"K线数据不足（{len(kline_data)}），需要至少5条")
            return []

        swing_points = []
        window_size = self.swing_window_size

        for i in range(window_size, len(kline_data) - window_size):
            current_kline = kline_data[i]

            # 检查局部高点 - 使用 High 价格
            left_highs = [kline_data[j]['high'] for j in range(i - window_size, i)]
            right_highs = [kline_data[j]['high'] for j in range(i + 1, i + window_size + 1)]
            is_high = all(current_kline['high'] > h for h in left_highs + right_highs)

            # 检查局部低点 - 使用 Low 价格
            left_lows = [kline_data[j]['low'] for j in range(i - window_size, i)]
            right_lows = [kline_data[j]['low'] for j in range(i + 1, i + window_size + 1)]
            is_low = all(current_kline['low'] < l for l in left_lows + right_lows)

            if is_high or is_low:
                # 确定摇摆点价格：High用于高点，Low用于低点
                swing_price = current_kline['high'] if is_high else current_kline['low']

                # 幅度过滤：与上一个摇摆点比较
                if swing_points:
                    last_swing = swing_points[-1]
                    price_change_pct = abs(swing_price - last_swing['price']) / last_swing['price']

                    if price_change_pct < min_threshold:
                        continue  # 幅度不足，跳过

                swing_points.append({
                    'index': i,
                    'price': swing_price,            # High或Low
                    'close': current_kline['close'], # 收盘价（用于形态方向判断）
                    'datetime': current_kline['datetime'],
                    'type': 'HIGH' if is_high else 'LOW'
                })

        logger.debug(f"识别到 {len(swing_points)} 个摇摆点（基于K线High/Low）")
        return swing_points

    def _detect_n_pattern_kline(self, swing_points: List[Dict]) -> Optional[Dict]:
        """
        检测N字形形态（基于摇摆点的Close价格判断方向）

        Args:
            swing_points: 摇摆点列表（包含Close价格）

        Returns:
            N字形形态信息，如果未检测到则返回None
        """
        if len(swing_points) < 3:
            logger.debug(f"摇摆点不足（{len(swing_points)}），需要至少3个")
            return None

        # 提取最近3个摇摆点
        recent_swings = swing_points[-3:]

        pattern = None

        # 上升N字形检测: LOW-HIGH-LOW 且 Close价格呈上升趋势
        if (recent_swings[0]['type'] == 'LOW' and
                recent_swings[1]['type'] == 'HIGH' and
                recent_swings[2]['type'] == 'LOW'):

            # 使用Close价格判断：第3个Low的Close > 第1个Low的Close
            if recent_swings[2]['close'] > recent_swings[0]['close']:
                # 进一步检查：第2个High也高于历史High
                if len(swing_points) >= 5:
                    prev_high = next((sp for sp in swing_points[-5:-2] if sp['type'] == 'HIGH'), None)
                    if prev_high and recent_swings[1]['close'] > prev_high['close']:
                        pattern = NPattern.RISING
                else:
                    pattern = NPattern.RISING

        # 下降N字形检测: HIGH-LOW-HIGH 且 Close价格呈下降趋势
        elif (recent_swings[0]['type'] == 'HIGH' and
              recent_swings[1]['type'] == 'LOW' and
              recent_swings[2]['type'] == 'HIGH'):

            # 使用Close价格判断：第3个High的Close < 第1个High的Close
            if recent_swings[2]['close'] < recent_swings[0]['close']:
                # 进一步检查：第2个Low也低于历史Low
                if len(swing_points) >= 5:
                    prev_low = next((sp for sp in swing_points[-5:-2] if sp['type'] == 'LOW'), None)
                    if prev_low and recent_swings[1]['close'] < prev_low['close']:
                        pattern = NPattern.FALLING
                else:
                    pattern = NPattern.FALLING

        if pattern:
            strength = self._calculate_pattern_strength(recent_swings)
            # 使用Close价格计算变化百分比
            change_percent = ((recent_swings[-1]['close'] - recent_swings[0]['close'])
                             / recent_swings[0]['close'] * 100)

            result = {
                'pattern': pattern,
                'swing_points': recent_swings,
                'strength': strength,
                'start_price': recent_swings[0]['close'],
                'end_price': recent_swings[-1]['close'],
                'change_percent': change_percent
            }

            logger.debug(f"检测到{pattern.value}，强度{strength:.2f}，幅度{change_percent:+.2f}%")
            return result

        return None

    def analyze_kline_data(self, kline_data: List[Dict]) -> Optional[Dict]:
        """
        分析K线数据，检测N字形反转（新的主入口）

        Args:
            kline_data: 48小时K线数据

        Returns:
            分析结果，包含反转信号等信息
        """
        if len(kline_data) < 10:
            logger.debug(f"K线数据不足（{len(kline_data)}），无法分析")
            return None

        # 1. 识别摇摆点（使用High/Low）
        swing_points = self._identify_swing_points_kline(kline_data, self.min_reversal_threshold)

        if len(swing_points) < 3:
            logger.debug(f"摇摆点不足（{len(swing_points)}），需要至少3个")
            return None

        # 2. 检测N字形形态（使用Close）
        current_pattern = self._detect_n_pattern_kline(swing_points)

        if not current_pattern:
            logger.debug("未检测到有效的N字形形态")
            return None

        # 3. 检测反转
        reversal_signal = self._check_reversal(
            current_pattern,
            self.n_pattern_state.previous_pattern
        )

        # 4. 更新状态
        self.n_pattern_state.previous_pattern = self.n_pattern_state.current_pattern
        self.n_pattern_state.current_pattern = current_pattern
        self.n_pattern_state.swing_points_history = swing_points

        if reversal_signal and reversal_signal.get('detected'):
            self.n_pattern_state.last_reversal_time = datetime.now()
            self.n_pattern_state.reversal_count += 1

            return {
                'type': 'N_PATTERN_REVERSAL',
                'reversal_signal': reversal_signal,
                'current_pattern': current_pattern,
                'swing_points': swing_points,
                'kline_data': kline_data,  # 传递完整K线数据用于绘图
                'analysis_window': '48h',
                'data_points': len(kline_data)
            }

        return None


def test_analyzer():
    """测试函数"""
    from pathlib import Path
    test_file = Path('/tmp/test_price_history.json')

    analyzer = PriceAnalyzer(test_file, trend_count=3)

    # 模拟连续上涨
    test_prices = [
        {'price': 500.0, 'timestamp': '2024-01-01T10:00:00'},
        {'price': 501.0, 'timestamp': '2024-01-01T10:05:00'},
        {'price': 502.0, 'timestamp': '2024-01-01T10:10:00'},
    ]

    for price_info in test_prices:
        trend = analyzer.add_price(price_info)
        if trend:
            print(f"检测到趋势: {trend}")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    test_analyzer()
