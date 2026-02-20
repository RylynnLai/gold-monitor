#!/usr/bin/env python3
"""
测试脚本：模拟数据验证功能
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# 添加 src 目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from price_analyzer import PriceAnalyzer
from chart_generator import ASCIIChartGenerator
from report_generator import ReportGenerator
from config import PRICE_HISTORY_FILE, TREND_COUNT

def test_with_mock_data():
    """使用模拟数据测试"""
    print("=" * 60)
    print("黄金监控系统功能测试 - 使用模拟数据")
    print("=" * 60 + "\n")

    # 创建分析器
    analyzer = PriceAnalyzer(PRICE_HISTORY_FILE, TREND_COUNT)
    chart_gen = ASCIIChartGenerator(width=60, height=10, use_unicode=True)
    report_gen = ReportGenerator()

    # 生成模拟数据（今天的数据，连续上涨）
    base_time = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
    base_price = 500.0

    print("1. 添加模拟价格数据（连续上涨趋势）...\n")

    for i in range(15):
        timestamp = base_time + timedelta(minutes=i * 30)
        price = base_price + i * 0.3 + (i % 3) * 0.1  # 小幅上涨带波动

        price_info = {
            'price': price,
            'timestamp': timestamp.isoformat(),
            'change': price - base_price,
            'change_percent': ((price - base_price) / base_price) * 100,
            'name': 'AU9999',
            'open': base_price,
            'high': price + 0.5,
            'low': base_price - 0.2,
            'volume': 1000 + i * 100
        }

        trend_info = analyzer.add_price(price_info)

        if trend_info:
            print(f"   [{timestamp.strftime('%H:%M')}] 价格: {price:.2f} - 检测到{trend_info['direction'].value}趋势")
        else:
            print(f"   [{timestamp.strftime('%H:%M')}] 价格: {price:.2f}")

    print("\n2. 生成 ASCII 走势图...\n")
    chart = chart_gen.generate_daily_chart(analyzer.price_history)
    print(chart)

    print("\n3. 生成综合分析报告...\n")
    # 使用最后一次的价格信息
    latest_trend = analyzer._analyze_trend()
    report = report_gen.generate_report(price_info, latest_trend, analyzer)
    print(report)

    print("\n4. 统计信息...\n")
    stats = analyzer.get_summary_stats()
    print(f"   总记录数: {stats['total_records']}")
    print(f"   今日记录: {stats['today_count']}")
    print(f"   今日最高: {stats['today_high']:.2f}")
    print(f"   今日最低: {stats['today_low']:.2f}")

    print("\n" + "=" * 60)
    print("测试完成！所有功能正常运行。")
    print("=" * 60)

if __name__ == '__main__':
    test_with_mock_data()
