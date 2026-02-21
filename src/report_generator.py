import logging
from typing import Dict, Optional
from datetime import datetime
from price_analyzer import TrendDirection
from trendline_analyzer import TrendDirection as TrendlineTrendDirection

logger = logging.getLogger(__name__)


class ReportGenerator:
    """综合分析报告生成器"""

    def __init__(self):
        """初始化报告生成器"""
        pass

    def generate_report(
        self,
        price_info: Dict,
        trend_info: Optional[Dict],
        analyzer
    ) -> str:
        """
        生成综合分析报告

        Args:
            price_info: 当前价格信息
            trend_info: 趋势分析信息（可为 None）
            analyzer: PriceAnalyzer 实例

        Returns:
            格式化的报告文本
        """
        lines = []

        # 标题
        lines.append("═" * 50)
        lines.append("黄金交易分析报告".center(46))
        lines.append("═" * 50)
        lines.append("")

        # 1. 即时行情
        lines.append("【即时行情】")
        lines.append(f"  品种名称: {price_info.get('name', 'AU9999')}")
        lines.append(f"  当前价格: {price_info['price']:.2f} 元/克")
        lines.append(f"  今日开盘: {price_info.get('open', 0):.2f} 元/克")
        lines.append(f"  最高价格: {price_info.get('high', 0):.2f} 元/克")
        lines.append(f"  最低价格: {price_info.get('low', 0):.2f} 元/克")

        change = price_info.get('change', 0)
        change_pct = price_info.get('change_percent', 0)
        lines.append(f"  涨跌额:   {change:+.2f} 元")
        lines.append(f"  涨跌幅:   {change_pct:+.2f}%")
        lines.append("")

        # 2. 趋势分析
        lines.append("【趋势分析】")
        if trend_info and trend_info.get('type') == 'N_PATTERN_REVERSAL':
            # N字形反转分析
            reversal = trend_info['reversal_signal']
            pattern = trend_info['current_pattern']

            reversal_icon = "↗" if reversal['reversal_type'] == 'BULLISH' else "↘"
            lines.append(f"  检测结果: {reversal['reversal_type']}反转 {reversal_icon}")
            lines.append(f"  形态变化: {reversal['from_pattern'].value} → {reversal['to_pattern'].value}")
            lines.append(f"  形态强度: {reversal['confidence']:.1%}")
            lines.append(f"  触发价格: {reversal['trigger_price']:.2f} 元/克")
            lines.append(f"  价格幅度: {reversal['change_percent']:+.2f}%")
        elif trend_info:
            # 旧的连续涨跌逻辑（保持兼容）
            direction = trend_info['direction']
            count = trend_info['count']
            start_price = trend_info['start_price']
            current_price = trend_info['current_price']
            change_percent = trend_info['change_percent']

            # 趋势方向图标
            if direction == TrendDirection.UP:
                icon = "↗"
            elif direction == TrendDirection.DOWN:
                icon = "↘"
            else:
                icon = "→"

            lines.append(f"  检测结果: 连续{count}次{direction.value} {icon}")
            lines.append(f"  起始价格: {start_price:.2f} 元/克")
            lines.append(f"  当前价格: {current_price:.2f} 元/克")
            lines.append(f"  累计涨幅: {change_percent:+.2f}%")

            # 价格序列
            prices_str = " → ".join([f"{p:.2f}" for p in trend_info['prices']])
            lines.append(f"  价格序列: {prices_str}")
        else:
            lines.append("  检测结果: 未形成明显趋势")
            lines.append("  市场状态: 震荡行情")
        lines.append("")

        # 3. 交易建议
        lines.append("【交易建议】")
        suggestion = self._generate_suggestion(price_info, trend_info)
        lines.append(f"  操作建议: {suggestion['action']}")
        lines.append(f"  理由:     {suggestion['reason']}")
        lines.append(f"  风险等级: {suggestion['risk']}")
        lines.append("")

        # 4. 统计摘要
        lines.append("【统计摘要】")
        stats = analyzer.get_summary_stats()
        lines.append(f"  历史记录: {stats['total_records']} 条")
        lines.append(f"  今日检查: {stats['today_count']} 次")

        if trend_info:
            lines.append(f"  趋势次数: {trend_info['count']} 次连续")

        if stats['today_count'] > 0:
            lines.append(f"  今日最高: {stats['today_high']:.2f} 元/克")
            lines.append(f"  今日最低: {stats['today_low']:.2f} 元/克")
            today_range = stats['today_high'] - stats['today_low']
            lines.append(f"  今日振幅: {today_range:.2f} 元/克")

        lines.append("")

        # 5. 底部信息
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        lines.append(f"运行时间: {current_time}")
        lines.append("═" * 50)

        return '\n'.join(lines)

    def generate_trendline_report(
        self,
        price_info: Dict,
        analysis_result: Optional[Dict],
        analyzer
    ) -> str:
        """
        生成趋势线分析报告

        Args:
            price_info: 当前价格信息
            analysis_result: 趋势线分析结果（可为 None）
            analyzer: TrendlineAnalyzer 实例

        Returns:
            格式化的报告文本
        """
        lines = []

        # 标题
        lines.append("═" * 50)
        lines.append("黄金交易分析报告（趋势线模式）".center(46))
        lines.append("═" * 50)
        lines.append("")

        # 1. 即时行情
        lines.append("【即时行情】")
        lines.append(f"  品种名称: {price_info.get('name', 'AU期货')}")
        lines.append(f"  当前价格: {price_info['price']:.2f} 元/克")
        lines.append(f"  今日开盘: {price_info.get('open', 0):.2f} 元/克")
        lines.append(f"  最高价格: {price_info.get('high', 0):.2f} 元/克")
        lines.append(f"  最低价格: {price_info.get('low', 0):.2f} 元/克")

        change = price_info.get('change', 0)
        change_pct = price_info.get('change_percent', 0)
        lines.append(f"  涨跌额:   {change:+.2f} 元")
        lines.append(f"  涨跌幅:   {change_pct:+.2f}%")
        lines.append("")

        # 2. 趋势线分析
        lines.append("【趋势线分析】")
        if analysis_result and analysis_result.get('type') == 'TRENDLINE_BREAKOUT':
            # 趋势线突破分析
            reversal_type = analysis_result['reversal_type']
            from_trend = analysis_result['from_trend']
            to_trend = analysis_result['to_trend']
            breakout_price = analysis_result['breakout_price']
            trendline_value = analysis_result['trendline_value']
            breakout_percent = analysis_result['breakout_percent']
            pivot_count = analysis_result['pivot_points_count']
            confidence = analysis_result['confidence']

            reversal_icon = "↗" if '看涨' in reversal_type else "↘"
            lines.append(f"  检测结果: {reversal_type} {reversal_icon}")
            lines.append(f"  趋势变化: {from_trend.value} → {to_trend.value}")
            lines.append(f"  突破价格: {breakout_price:.2f} 元/克")
            lines.append(f"  趋势线值: {trendline_value:.2f} 元/克")
            lines.append(f"  突破幅度: {breakout_percent:.2f}%")
            lines.append(f"  摆动点数: {pivot_count} 个")
            lines.append(f"  置信度:   {confidence:.1%}")
        else:
            # 未检测到突破，显示当前趋势状态
            trend_info = analyzer.get_current_trend_info()
            current_trend = trend_info['trend']
            trendline_value = trend_info['trendline_value']

            # 趋势图标
            if current_trend == TrendlineTrendDirection.RISING:
                icon = "↗"
                trend_desc = "上升趋势"
            elif current_trend == TrendlineTrendDirection.FALLING:
                icon = "↘"
                trend_desc = "下降趋势"
            else:
                icon = "→"
                trend_desc = "震荡行情"

            lines.append(f"  当前趋势: {trend_desc} {icon}")
            if trendline_value:
                lines.append(f"  趋势线值: {trendline_value:.2f} 元/克")
                # 计算当前价格与趋势线的距离
                distance_percent = abs(price_info['price'] - trendline_value) / trendline_value * 100
                lines.append(f"  距趋势线: {distance_percent:.2f}%")

                # 计算并显示反转阈值价格
                if current_trend == TrendlineTrendDirection.RISING:
                    # 上升趋势中，向下突破的阈值价格
                    reversal_price = trendline_value * (1 - analyzer.breakout_threshold)
                    lines.append(f"  反转阈值: {reversal_price:.2f} 元/克 (向下突破)")
                elif current_trend == TrendlineTrendDirection.FALLING:
                    # 下降趋势中，向上突破的阈值价格
                    reversal_price = trendline_value * (1 + analyzer.breakout_threshold)
                    lines.append(f"  反转阈值: {reversal_price:.2f} 元/克 (向上突破)")
            else:
                lines.append(f"  趋势线值: 尚未建立")
            lines.append(f"  检测结果: 未检测到趋势线突破")
        lines.append("")

        # 3. 交易建议
        lines.append("【交易建议】")
        suggestion = self._generate_trendline_suggestion(price_info, analysis_result)
        lines.append(f"  操作建议: {suggestion['action']}")
        lines.append(f"  理由:     {suggestion['reason']}")
        lines.append(f"  风险等级: {suggestion['risk']}")
        lines.append("")

        # 4. 系统参数
        lines.append("【系统参数】")
        lines.append(f"  趋势窗口: {analyzer.trend_window_hours} 小时")
        lines.append(f"  突破阈值: {analyzer.breakout_threshold * 100:.2f}%")
        lines.append(f"  最小摆动: {analyzer.min_pivot_distance} 个K线")
        lines.append("")

        # 5. 底部信息
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        lines.append(f"运行时间: {current_time}")
        lines.append("═" * 50)

        return '\n'.join(lines)

    def _generate_trendline_suggestion(
        self,
        price_info: Dict,
        analysis_result: Optional[Dict]
    ) -> Dict[str, str]:
        """
        生成趋势线交易建议

        Returns:
            {
                'action': str,  # 操作建议
                'reason': str,  # 理由
                'risk': str     # 风险等级
            }
        """
        if not analysis_result or analysis_result.get('type') != 'TRENDLINE_BREAKOUT':
            return {
                'action': '持有观望',
                'reason': '未检测到趋势线突破，建议等待清晰信号',
                'risk': '低'
            }

        reversal_type = analysis_result['reversal_type']
        confidence = analysis_result['confidence']
        breakout_percent = analysis_result['breakout_percent']

        # 看涨反转
        if '看涨' in reversal_type:
            if confidence >= 0.6 and breakout_percent >= 0.1:
                return {
                    'action': '强烈建议买入',
                    'reason': f'趋势线向上突破，信号强烈（置信度{confidence:.1%}，突破{breakout_percent:.2f}%）',
                    'risk': '中'
                }
            elif confidence >= 0.4:
                return {
                    'action': '建议买入',
                    'reason': f'趋势线向上突破，可小仓位试探（置信度{confidence:.1%}）',
                    'risk': '中'
                }
            else:
                return {
                    'action': '谨慎观望',
                    'reason': f'反转信号较弱（置信度{confidence:.1%}），等待进一步确认',
                    'risk': '低'
                }

        # 看跌反转
        else:
            if confidence >= 0.6 and breakout_percent >= 0.1:
                return {
                    'action': '强烈建议卖出',
                    'reason': f'趋势线向下突破，风险较高（置信度{confidence:.1%}，突破{breakout_percent:.2f}%）',
                    'risk': '高'
                }
            elif confidence >= 0.4:
                return {
                    'action': '建议卖出',
                    'reason': f'趋势线向下突破，建议减仓（置信度{confidence:.1%}）',
                    'risk': '高'
                }
            else:
                return {
                    'action': '谨慎观望',
                    'reason': f'反转信号较弱（置信度{confidence:.1%}），继续观察',
                    'risk': '中'
                }

    def _generate_suggestion(
        self,
        price_info: Dict,
        trend_info: Optional[Dict]
    ) -> Dict[str, str]:
        """
        生成交易建议

        Returns:
            {
                'action': str,  # 操作建议
                'reason': str,  # 理由
                'risk': str     # 风险等级
            }
        """
        if not trend_info:
            return {
                'action': '持有观望',
                'reason': '未形成明显趋势，建议等待清晰信号',
                'risk': '低'
            }

        # 优先处理N字形反转信号
        if trend_info.get('type') == 'N_PATTERN_REVERSAL':
            reversal = trend_info['reversal_signal']
            confidence = reversal['confidence']
            reversal_type = reversal['reversal_type']

            if reversal_type == 'BULLISH':
                if confidence >= 0.7:
                    return {
                        'action': '强烈建议买入',
                        'reason': f'看涨反转信号，形态可靠度{confidence:.1%}，建议入场',
                        'risk': '中'
                    }
                elif confidence >= 0.5:
                    return {
                        'action': '建议买入',
                        'reason': f'看涨反转信号，信号有效，可小仓位试探',
                        'risk': '中'
                    }
                else:
                    return {
                        'action': '谨慎观望',
                        'reason': f'反转信号较弱（可靠度{confidence:.1%}），等待进一步确认',
                        'risk': '低'
                    }
            else:  # BEARISH
                if confidence >= 0.7:
                    return {
                        'action': '强烈建议卖出',
                        'reason': f'看跌反转信号，形态可靠度{confidence:.1%}，及时止损',
                        'risk': '高'
                    }
                elif confidence >= 0.5:
                    return {
                        'action': '建议卖出',
                        'reason': f'看跌反转信号，信号有效，建议减仓',
                        'risk': '高'
                    }
                else:
                    return {
                        'action': '谨慎观望',
                        'reason': f'反转信号较弱（可靠度{confidence:.1%}），继续观察',
                        'risk': '中'
                    }

        # 兼容旧的连续涨跌逻辑
        direction = trend_info['direction']
        change_percent = abs(trend_info['change_percent'])

        # 决策逻辑
        if direction == TrendDirection.UP:
            if change_percent > 0.5:
                return {
                    'action': '建议买入',
                    'reason': f'连续上涨趋势明显，涨幅达 {change_percent:.2f}%，趋势向好',
                    'risk': '中'
                }
            else:
                return {
                    'action': '持有观望',
                    'reason': f'虽有上涨趋势，但涨幅较小（{change_percent:.2f}%），建议继续观察',
                    'risk': '低'
                }

        elif direction == TrendDirection.DOWN:
            if change_percent > 0.5:
                return {
                    'action': '建议卖出',
                    'reason': f'连续下跌趋势，跌幅达 {change_percent:.2f}%，建议止损',
                    'risk': '高'
                }
            else:
                return {
                    'action': '持有观望',
                    'reason': f'虽有下跌趋势，但跌幅较小（{change_percent:.2f}%），可等待反弹',
                    'risk': '中'
                }

        else:
            return {
                'action': '持有观望',
                'reason': '价格平稳，无明显趋势',
                'risk': '低'
            }

    def generate_summary(self, price_info: Dict) -> str:
        """
        生成简短摘要（用于通知或日志）

        Args:
            price_info: 价格信息

        Returns:
            简短摘要文本
        """
        return (
            f"黄金价格: {price_info['price']:.2f} 元/克 "
            f"({price_info.get('change_percent', 0):+.2f}%)"
        )


def test_report():
    """测试函数"""
    # 模拟数据
    price_info = {
        'name': 'AU9999',
        'price': 501.85,
        'open': 500.20,
        'high': 502.30,
        'low': 500.10,
        'change': 1.65,
        'change_percent': 0.33
    }

    trend_info = {
        'direction': TrendDirection.UP,
        'count': 3,
        'start_price': 500.50,
        'current_price': 501.85,
        'change_percent': 0.27,
        'prices': [500.50, 501.20, 501.85]
    }

    # 创建模拟的 analyzer
    class MockAnalyzer:
        def get_summary_stats(self):
            return {
                'total_records': 128,
                'today_count': 15,
                'today_high': 502.30,
                'today_low': 500.10
            }

    generator = ReportGenerator()
    report = generator.generate_report(price_info, trend_info, MockAnalyzer())
    print(report)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    test_report()
