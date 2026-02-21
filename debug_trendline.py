#!/usr/bin/env python3
"""
调试趋势线分析器
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from datetime import datetime
from zoneinfo import ZoneInfo
from src.kline_data_manager import KlineDataManager
from src.trendline_analyzer import TrendlineAnalyzer, TrendDirection
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)s - %(message)s'
)

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

if __name__ == '__main__':
    # 加载数据
    manager = KlineDataManager()
    kline_data = manager.load_kline_data()

    if not kline_data:
        print("无法加载K线数据")
        sys.exit(1)

    print(f"\n加载了 {len(kline_data)} 条K线数据\n")

    # 查看用户标注的反转点周围的数据
    for label in LABELED_REVERSALS:
        print(f"\n{'='*80}")
        print(f"分析反转点: {label['time_et']} ET - {label['type']}")
        print(f"{'='*80}")

        target_utc = convert_et_to_utc(label['time_et'])

        # 找到这个时间点的索引
        target_index = None
        for i, k in enumerate(kline_data):
            k_time = datetime.fromisoformat(k['datetime']).replace(tzinfo=ZoneInfo('UTC'))
            if abs((k_time - target_utc).total_seconds()) < 900:  # 15分钟内
                target_index = i
                break

        if target_index is None:
            print(f"  ✗ 未找到对应的K线数据")
            continue

        print(f"  找到K线索引: {target_index}")

        # 获取此时间点前的数据（模拟实时）
        partial_data = kline_data[:target_index + 1]

        # 创建分析器（调整参数）
        analyzer = TrendlineAnalyzer(
            trend_window_hours=6,  # 缩短窗口到6小时
            min_pivot_distance=2,  # 降低摆动点间隔要求
            breakout_threshold=0.0005,  # 降低突破阈值到0.05%
            min_trend_points=2
        )

        # 获取趋势窗口
        window_data = analyzer._get_trend_window(partial_data)
        print(f"  趋势窗口: {len(window_data)} 条K线")

        # 识别趋势
        trend = analyzer.identify_trend(window_data)
        print(f"  识别的趋势: {trend.value}")

        # 查找摆动点
        if trend == TrendDirection.FALLING:
            pivots = analyzer.find_pivot_points(window_data, find_highs=True)
            print(f"  下降趋势 - 识别到 {len(pivots)} 个高点")
        elif trend == TrendDirection.RISING:
            pivots = analyzer.find_pivot_points(window_data, find_highs=False)
            print(f"  上升趋势 - 识别到 {len(pivots)} 个低点")
        else:
            print(f"  震荡行情 - 跳过")
            continue

        if len(pivots) > 0:
            print(f"  摆动点（最近5个）:")
            for p in pivots[-5:]:
                dt_utc = datetime.fromisoformat(p['datetime'])
                dt_et = dt_utc.astimezone(ZoneInfo('America/New_York'))
                print(f"    {dt_et.strftime('%m-%d %H:%M')} ET - {p['price']:.2f}")

        # 计算趋势线
        if len(pivots) >= analyzer.min_trend_points:
            trendline = analyzer.calculate_weighted_trendline(pivots, len(window_data) - 1)
            current_price = partial_data[-1]['close']
            print(f"  当前价格: {current_price:.2f}")
            print(f"  趋势线值: {trendline:.2f}")

            # 检查突破
            is_breakout = analyzer.check_breakout(current_price, trendline, trend)
            print(f"  是否突破: {'是' if is_breakout else '否'}")

            if is_breakout:
                print(f"  ✓ 检测到反转!")
            else:
                # 显示距离突破还差多少
                if trend == TrendDirection.FALLING:
                    diff = (current_price - trendline) / trendline * 100
                    print(f"  距离突破还差: {diff:.2f}% (需要 {analyzer.breakout_threshold*100:.2f}%)")
                else:
                    diff = (trendline - current_price) / trendline * 100
                    print(f"  距离突破还差: {diff:.2f}% (需要 {analyzer.breakout_threshold*100:.2f}%)")
