#!/usr/bin/env python3
"""
基于用户标注的反转时间点进行参数优化
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
    level=logging.WARNING,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# 用户标注的反转时间点（美国东部时间）
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

def find_nearest_kline_index(kline_data, target_time_utc):
    """找到最接近目标时间的K线索引"""
    target_time = target_time_utc[:16]  # 只比较到分钟
    for i, k in enumerate(kline_data):
        if k['datetime'].startswith(target_time):
            return i
    return None

def evaluate_params(kline_data, min_threshold, window_size, min_strength):
    """
    评估一组参数的效果

    返回：检测到的反转数、匹配度得分、误报数
    """
    # 创建分析器
    analyzer = PriceAnalyzer()
    analyzer.min_reversal_threshold = min_threshold
    analyzer.swing_window_size = window_size
    analyzer.min_strength = min_strength

    # 识别摇摆点
    swing_points = analyzer._identify_swing_points_kline(
        kline_data,
        min_threshold=min_threshold
    )

    if len(swing_points) < 3:
        return 0, 0.0, 0

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
                'confidence': reversal_signal['confidence']
            })

        analyzer.n_pattern_state.previous_pattern = analyzer.n_pattern_state.current_pattern
        analyzer.n_pattern_state.current_pattern = current_pattern

    # 计算匹配度
    # 将用户标注的反转时间转换为UTC
    labeled_utc_times = []
    for label in LABELED_REVERSALS:
        utc_time = convert_et_to_utc(label['time_et'])
        labeled_utc_times.append({
            'time': utc_time,
            'type': label['type']
        })

    # 匹配：检测到的反转与实际反转的时间差在30分钟内算匹配
    matches = 0
    for label in labeled_utc_times:
        label_dt = datetime.fromisoformat(label['time'])
        for detected in detected_reversals:
            detected_dt = datetime.fromisoformat(detected['time'])
            time_diff_minutes = abs((detected_dt - label_dt).total_seconds() / 60)

            # 时间差在30分钟内，且类型匹配
            if time_diff_minutes <= 30:
                # 检查类型是否匹配（简化判断）
                if (label['type'] == '上升' and '上升' in detected['type']) or \
                   (label['type'] == '下降' and '下降' in detected['type']):
                    matches += 1
                    break

    # 计算误报（检测到的反转数 - 匹配数）
    false_positives = len(detected_reversals) - matches

    # 计算得分
    # 匹配度得分 = (匹配数 / 标注数) * 100
    # 减去误报惩罚
    match_rate = matches / len(LABELED_REVERSALS) if len(LABELED_REVERSALS) > 0 else 0
    score = match_rate * 100 - false_positives * 5  # 每个误报扣5分

    return matches, score, false_positives

def run_grid_search(kline_data):
    """运行网格搜索"""
    print("=" * 80)
    print("参数优化 - 基于用户标注的反转时间点")
    print("=" * 80)

    print(f"\n用户标注了 {len(LABELED_REVERSALS)} 个反转时间点:")
    for label in LABELED_REVERSALS:
        utc_time = convert_et_to_utc(label['time_et'])
        print(f"  {label['time_et']} ET ({utc_time} UTC) - {label['type']}")

    # 参数范围
    threshold_range = [0.0005, 0.001, 0.002, 0.003, 0.005]
    window_sizes = [2, 3, 4, 5]
    strength_range = [0.2, 0.3, 0.4, 0.5]

    print(f"\n参数搜索空间:")
    print(f"  MIN_REVERSAL_THRESHOLD: {threshold_range}")
    print(f"  SWING_WINDOW_SIZE: {window_sizes}")
    print(f"  MIN_STRENGTH: {strength_range}")
    print(f"  总组合数: {len(threshold_range) * len(window_sizes) * len(strength_range)}")

    best_score = -999999
    best_params = None
    best_matches = 0

    results = []

    print("\n开始搜索...")
    total = len(threshold_range) * len(window_sizes) * len(strength_range)
    current = 0

    for threshold in threshold_range:
        for window in window_sizes:
            for strength in strength_range:
                current += 1

                matches, score, false_pos = evaluate_params(
                    kline_data,
                    threshold,
                    window,
                    strength
                )

                results.append({
                    'threshold': threshold,
                    'window': window,
                    'strength': strength,
                    'matches': matches,
                    'score': score,
                    'false_positives': false_pos
                })

                if score > best_score:
                    best_score = score
                    best_params = (threshold, window, strength)
                    best_matches = matches

                if current % 10 == 0 or current == total:
                    print(f"  进度: {current}/{total} ({current*100//total}%)")

    # 打印结果
    print("\n" + "=" * 80)
    print("搜索完成！")
    print("=" * 80)

    print(f"\n最佳参数:")
    print(f"  MIN_REVERSAL_THRESHOLD = {best_params[0]}")
    print(f"  SWING_WINDOW_SIZE = {best_params[1]}")
    print(f"  MIN_STRENGTH = {best_params[2]}")
    print(f"\n效果:")
    print(f"  匹配数: {best_matches}/{len(LABELED_REVERSALS)} ({best_matches*100/len(LABELED_REVERSALS):.1f}%)")
    print(f"  综合得分: {best_score:.1f}")

    # 显示前5名
    print("\n" + "-" * 80)
    print("前5名参数组合:")
    print("-" * 80)
    sorted_results = sorted(results, key=lambda x: x['score'], reverse=True)[:5]

    for i, r in enumerate(sorted_results, 1):
        print(f"\n{i}. threshold={r['threshold']}, window={r['window']}, strength={r['strength']}")
        print(f"   匹配: {r['matches']}/{len(LABELED_REVERSALS)}, "
              f"误报: {r['false_positives']}, "
              f"得分: {r['score']:.1f}")

    return best_params

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

    # 运行网格搜索
    best_params = run_grid_search(kline_data)

    print("\n" + "=" * 80)
    print("建议：将以下参数更新到 .env 文件:")
    print("=" * 80)
    print(f"MIN_REVERSAL_THRESHOLD={best_params[0]}")
    print(f"SWING_WINDOW_SIZE={best_params[1]}")
    print(f"MIN_STRENGTH={best_params[2]}")
    print()
