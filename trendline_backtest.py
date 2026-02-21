#!/usr/bin/env python3
"""
基于用户标注进行趋势线算法参数回测
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / 'src'))

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from src.kline_data_manager import KlineDataManager
from src.trendline_analyzer import TrendlineAnalyzer

# 用户标注的反转点
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
    return dt_utc

def test_params(kline_data, window_hours, min_pivot_distance, breakout_threshold, min_cooldown_minutes):
    """测试一组参数"""
    analyzer = TrendlineAnalyzer(
        trend_window_hours=window_hours,
        min_pivot_distance=min_pivot_distance,
        breakout_threshold=breakout_threshold,
        min_trend_points=2
    )

    # 添加冷却时间限制
    last_reversal_time = None

    reversals = []
    for i in range(100, len(kline_data)):
        partial_data = kline_data[:i+1]
        result = analyzer.analyze_kline_data(partial_data)

        if result:
            current_time = datetime.fromisoformat(result['trigger_time']).replace(tzinfo=ZoneInfo('UTC'))

            # 检查冷却时间
            if last_reversal_time:
                time_diff_minutes = (current_time - last_reversal_time).total_seconds() / 60
                if time_diff_minutes < min_cooldown_minutes:
                    continue  # 跳过（冷却期内）

            reversals.append(result)
            last_reversal_time = current_time

    # 匹配用户标注
    matches = 0
    for label in LABELED_REVERSALS:
        label_utc = convert_et_to_utc(label['time_et'])

        for detected in reversals:
            detected_utc = datetime.fromisoformat(detected['trigger_time']).replace(tzinfo=ZoneInfo('UTC'))
            time_diff_minutes = abs((detected_utc - label_utc).total_seconds() / 60)

            if time_diff_minutes <= 60:  # 1小时内算匹配
                # 检查类型
                if (label['type'] == '上升' and '看涨' in detected['reversal_type']) or \
                   (label['type'] == '下降' and '看跌' in detected['reversal_type']):
                    matches += 1
                    break

    match_rate = matches / len(LABELED_REVERSALS)
    false_positives = len(reversals) - matches
    score = match_rate * 100 - false_positives * 3  # 每个误报扣3分

    return {
        'params': {
            'window_hours': window_hours,
            'min_pivot_distance': min_pivot_distance,
            'breakout_threshold': breakout_threshold,
            'min_cooldown_minutes': min_cooldown_minutes
        },
        'matches': matches,
        'total_detected': len(reversals),
        'false_positives': false_positives,
        'match_rate': match_rate,
        'score': score
    }

if __name__ == '__main__':
    # 加载数据
    manager = KlineDataManager()
    kline_data = manager.load_kline_data()

    print("="*80)
    print("趋势线算法参数回测")
    print("="*80)
    print(f"\\n用户标注: {len(LABELED_REVERSALS)} 个反转点")
    print(f"K线数据: {len(kline_data)} 条\\n")

    # 参数网格
    param_grid = [
        # (窗口小时, 摆动点间隔, 突破阈值, 冷却分钟)
        (8, 2, 0.0008, 30),
        (8, 2, 0.0010, 30),
        (8, 3, 0.0008, 30),
        (10, 2, 0.0008, 30),
        (10, 2, 0.0010, 30),
        (10, 3, 0.0010, 30),
        (6, 2, 0.0005, 20),
        (6, 2, 0.0008, 30),
        (12, 2, 0.0010, 40),
        (12, 3, 0.0010, 40),
    ]

    results = []
    for i, (w, p, t, c) in enumerate(param_grid, 1):
        print(f"测试 {i}/{len(param_grid)}: window={w}h, pivot={p}, threshold={t*100:.2f}%, cooldown={c}min")
        result = test_params(kline_data, w, p, t, c)
        results.append(result)

    # 按得分排序
    results.sort(key=lambda x: x['score'], reverse=True)

    print("\\n" + "="*80)
    print("回测结果（按得分排序）")
    print("="*80)

    for i, r in enumerate(results[:5], 1):
        p = r['params']
        print(f"\\n{i}. 得分: {r['score']:.1f}")
        print(f"   参数: window={p['window_hours']}h, pivot={p['min_pivot_distance']}, "
              f"threshold={p['breakout_threshold']*100:.2f}%, cooldown={p['min_cooldown_minutes']}min")
        print(f"   匹配: {r['matches']}/{len(LABELED_REVERSALS)} ({r['match_rate']*100:.0f}%)")
        print(f"   总检测: {r['total_detected']}, 误报: {r['false_positives']}")

    print("\\n" + "="*80)
    print("推荐配置（最佳得分）:")
    print("="*80)
    best = results[0]['params']
    print(f"TREND_WINDOW_HOURS={best['window_hours']}")
    print(f"MIN_PIVOT_DISTANCE={best['min_pivot_distance']}")
    print(f"BREAKOUT_THRESHOLD={best['breakout_threshold']}")
    print(f"MIN_COOLDOWN_MINUTES={best['min_cooldown_minutes']}")
    print()
