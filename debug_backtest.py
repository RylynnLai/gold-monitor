#!/usr/bin/env python3
"""
调试版本 - 查看实际检测到的反转
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
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)

# 测试参数
TEST_PARAMS = [
    {'threshold': 0.001, 'window': 2, 'strength': 0.3},
    {'threshold': 0.002, 'window': 2, 'strength': 0.3},
    {'threshold': 0.003, 'window': 2, 'strength': 0.3},
    {'threshold': 0.001, 'window': 3, 'strength': 0.3},
]

# 用户标注的反转时间点
LABELED_REVERSALS = [
    {'time_et': '2026-02-20 13:15', 'type': '上升'},
    {'time_et': '2026-02-20 08:15', 'type': '上升'},
    {'time_et': '2026-02-20 03:45', 'type': '上升'},
    {'time_et': '2026-02-19 18:45', 'type': '上升'},
    {'time_et': '2026-02-19 15:45', 'type': '下降'},
    {'time_et': '2026-02-20 02:45', 'type': '下降'},
]

def convert_et_to_utc(et_time_str):
    """将美国东部时间转换为UTC"""
    dt_et = datetime.fromisoformat(et_time_str).replace(tzinfo=ZoneInfo('America/New_York'))
    dt_utc = dt_et.astimezone(ZoneInfo('UTC'))
    return dt_utc.strftime('%Y-%m-%d %H:%M')

def test_params(kline_data, params):
    """测试一组参数"""
    print(f"\n{'='*80}")
    print(f"测试参数: threshold={params['threshold']}, window={params['window']}, strength={params['strength']}")
    print(f"{'='*80}")

    # 创建分析器
    analyzer = PriceAnalyzer()
    analyzer.min_reversal_threshold = params['threshold']
    analyzer.swing_window_size = params['window']
    analyzer.min_strength = params['strength']

    # 识别摇摆点
    swing_points = analyzer._identify_swing_points_kline(
        kline_data,
        min_threshold=params['threshold']
    )

    print(f"\n识别到 {len(swing_points)} 个摇摆点")

    if len(swing_points) > 0:
        print("\n前10个摇摆点:")
        for sp in swing_points[:10]:
            # 转为ET时间显示
            dt_utc = datetime.fromisoformat(sp['datetime'])
            dt_et = dt_utc.astimezone(ZoneInfo('America/New_York'))
            print(f"  {dt_et.strftime('%m-%d %H:%M')} ET - {sp['type']}, Price: {sp['price']:.2f}, Close: {sp['close']:.2f}")

    if len(swing_points) < 3:
        print("\n摇摆点不足，无法检测N字形")
        return

    # 检测反转
    detected_reversals = []

    for i in range(3, len(swing_points) + 1):
        partial_swings = swing_points[:i]
        current_pattern = analyzer._detect_n_pattern_kline(partial_swings)

        if not current_pattern:
            continue

        reversal_signal = analyzer._check_reversal(
            current_pattern,
            analyzer.n_pattern_state.previous_pattern
        )

        if reversal_signal and reversal_signal.get('detected'):
            detected_reversals.append({
                'time': current_pattern['swing_points'][-1]['datetime'],
                'type': reversal_signal['reversal_type'],
                'confidence': reversal_signal['confidence'],
                'from': reversal_signal['from_pattern'].value,
                'to': reversal_signal['to_pattern'].value
            })

        analyzer.n_pattern_state.previous_pattern = analyzer.n_pattern_state.current_pattern
        analyzer.n_pattern_state.current_pattern = current_pattern

    print(f"\n检测到 {len(detected_reversals)} 个反转:")
    for rev in detected_reversals:
        # 转为ET时间显示
        dt_utc = datetime.fromisoformat(rev['time'])
        dt_et = dt_utc.astimezone(ZoneInfo('America/New_York'))
        print(f"  {dt_et.strftime('%m-%d %H:%M')} ET - {rev['type']}, {rev['from']} → {rev['to']}, 置信度: {rev['confidence']:.3f}")

    # 对比用户标注
    print("\n对比用户标注的反转时间点:")
    for label in LABELED_REVERSALS:
        utc_time = convert_et_to_utc(label['time_et'])
        label_dt = datetime.fromisoformat(utc_time)

        # 查找是否有匹配的检测
        matched = False
        for detected in detected_reversals:
            detected_dt = datetime.fromisoformat(detected['time'])
            time_diff_minutes = abs((detected_dt - label_dt).total_seconds() / 60)

            if time_diff_minutes <= 60:  # 60分钟内
                matched = True
                print(f"  ✓ {label['time_et']} ET ({label['type']}) - 检测到 ({time_diff_minutes:.0f}分钟差异)")
                break

        if not matched:
            print(f"  ✗ {label['time_et']} ET ({label['type']}) - 未检测到")

if __name__ == '__main__':
    # 加载K线数据
    print("\n加载K线数据...")
    manager = KlineDataManager()
    kline_data = manager.load_kline_data()

    if not kline_data:
        print("本地无数据，开始抓取...")
        kline_data = manager.fetch_and_save_48h_data()

    if not kline_data:
        print("无法获取K线数据，退出")
        sys.exit(1)

    print(f"成功加载 {len(kline_data)} 条K线数据")
    print(f"时间范围: {kline_data[0]['datetime']} 至 {kline_data[-1]['datetime']}")

    print(f"\n用户标注了 {len(LABELED_REVERSALS)} 个反转时间点:")
    for label in LABELED_REVERSALS:
        utc_time = convert_et_to_utc(label['time_et'])
        print(f"  {label['time_et']} ET ({utc_time} UTC) - {label['type']}")

    # 测试多组参数
    for params in TEST_PARAMS:
        test_params(kline_data, params)
