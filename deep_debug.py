#!/usr/bin/env python3
"""
深度调试 - 查看N字形形态检测过程
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from datetime import datetime
from zoneinfo import ZoneInfo
from src.kline_data_manager import KlineDataManager
from src.price_analyzer import PriceAnalyzer
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(message)s'
)

TEST_THRESHOLD = 0.0005  # 更低的阈值
TEST_WINDOW = 2
TEST_STRENGTH = 0.15  # 更低的强度要求

if __name__ == '__main__':
    # 加载K线数据
    print("\n加载K线数据...")
    manager = KlineDataManager()
    kline_data = manager.load_kline_data()

    if not kline_data:
        print("无法获取K线数据，退出")
        sys.exit(1)

    print(f"成功加载 {len(kline_data)} 条K线数据\n")

    # 创建分析器
    analyzer = PriceAnalyzer()
    analyzer.min_reversal_threshold = TEST_THRESHOLD
    analyzer.swing_window_size = TEST_WINDOW
    analyzer.min_strength = TEST_STRENGTH

    print(f"参数: threshold={TEST_THRESHOLD}, window={TEST_WINDOW}, strength={TEST_STRENGTH}\n")

    # 识别摇摆点
    swing_points = analyzer._identify_swing_points_kline(
        kline_data,
        min_threshold=TEST_THRESHOLD
    )

    print(f"\n识别到 {len(swing_points)} 个摇摆点\n")
    print("摇摆点列表（前20个）:")
    for i, sp in enumerate(swing_points[:20]):
        dt_utc = datetime.fromisoformat(sp['datetime'])
        dt_et = dt_utc.astimezone(ZoneInfo('America/New_York'))
        print(f"  {i:2d}. {dt_et.strftime('%m-%d %H:%M')} ET - {sp['type']:4s}, Price: {sp['price']:7.2f}, Close: {sp['close']:7.2f}")

    print(f"\n开始逐步检测N字形形态...")
    print("="*80)

    # 逐步增加摇摆点，检测N字形
    patterns_detected = []
    reversals_detected = []

    for i in range(3, len(swing_points) + 1):  # 检测所有摇摆点
        partial_swings = swing_points[:i]

        current_pattern = analyzer._detect_n_pattern_kline(partial_swings)

        if current_pattern:
            # 转换时间为ET
            dt_utc = datetime.fromisoformat(current_pattern['swing_points'][2]['datetime'])
            dt_et = dt_utc.astimezone(ZoneInfo('America/New_York'))

            pattern_info = (
                f"{i:2d}个点 -> {current_pattern['pattern'].value:7s} "
                f"强度:{current_pattern['strength']:.3f} "
                f"at {dt_et.strftime('%m-%d %H:%M')} ET"
            )
            patterns_detected.append(pattern_info)

            # 检查反转
            reversal_signal = analyzer._check_reversal(
                current_pattern,
                analyzer.n_pattern_state.previous_pattern
            )

            if reversal_signal and reversal_signal.get('detected'):
                print(f"\n🔔 检测到反转! {pattern_info}")
                print(f"   反转类型: {reversal_signal['reversal_type']}")
                print(f"   从 {reversal_signal['from_pattern'].value} → {reversal_signal['to_pattern'].value}")
                reversals_detected.append(reversal_signal)

            # 更新状态
            analyzer.n_pattern_state.previous_pattern = analyzer.n_pattern_state.current_pattern
            analyzer.n_pattern_state.current_pattern = current_pattern

    print(f"\n总结:")
    print(f"  检测到 {len(patterns_detected)} 个N字形形态")
    print(f"  检测到 {len(reversals_detected)} 个反转信号")

    print(f"\n所有N字形形态:")
    for p in patterns_detected:
        print(f"  {p}")
