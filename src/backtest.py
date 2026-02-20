"""
回测模块
用于测试不同阈值参数对N型形态识别的影响
"""
import json
import logging
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from datetime import datetime
from .price_analyzer import PriceAnalyzer, NPattern
from .kline_data_manager import KlineDataManager
from . import config

logger = logging.getLogger(__name__)


class BacktestResult:
    """回测结果"""

    def __init__(self, params: Dict):
        self.params = params  # 测试参数
        self.reversal_count = 0  # 检测到的反转次数
        self.reversal_signals = []  # 所有反转信号
        self.swing_points_count = 0  # 识别到的摇摆点数量
        self.pattern_strengths = []  # 形态强度列表
        self.false_signals = 0  # 疑似误报数量

    def add_reversal(self, reversal_signal: Dict, pattern: Dict):
        """添加反转信号"""
        self.reversal_count += 1
        self.reversal_signals.append({
            'reversal': reversal_signal,
            'pattern': pattern,
            'timestamp': datetime.now().isoformat()
        })
        self.pattern_strengths.append(pattern['strength'])

    def get_avg_strength(self) -> float:
        """获取平均形态强度"""
        if not self.pattern_strengths:
            return 0.0
        return sum(self.pattern_strengths) / len(self.pattern_strengths)

    def get_summary(self) -> Dict:
        """获取回测摘要"""
        return {
            'params': self.params,
            'reversal_count': self.reversal_count,
            'avg_strength': self.get_avg_strength(),
            'min_strength': min(self.pattern_strengths) if self.pattern_strengths else 0,
            'max_strength': max(self.pattern_strengths) if self.pattern_strengths else 0,
            'swing_points_count': self.swing_points_count,
            'false_signals': self.false_signals
        }


class Backtester:
    """回测器"""

    def __init__(self, kline_data_manager: Optional[KlineDataManager] = None):
        """
        初始化回测器

        Args:
            kline_data_manager: K线数据管理器，默认创建新实例
        """
        self.data_manager = kline_data_manager or KlineDataManager()
        logger.info("回测器初始化完成")

    def run_single_test(
        self,
        kline_data: List[Dict],
        min_reversal_threshold: float = 0.003,
        swing_window_size: int = 2,
        min_strength: float = 0.5
    ) -> BacktestResult:
        """
        运行单次回测

        Args:
            kline_data: K线数据
            min_reversal_threshold: 最小反转阈值
            swing_window_size: 摇摆点窗口大小
            min_strength: 最小形态强度

        Returns:
            回测结果
        """
        params = {
            'min_reversal_threshold': min_reversal_threshold,
            'swing_window_size': swing_window_size,
            'min_strength': min_strength
        }

        logger.info(f"开始回测 - 参数: {params}")

        # 创建分析器（临时修改阈值）
        analyzer = PriceAnalyzer()
        analyzer.min_reversal_threshold = min_reversal_threshold
        analyzer.swing_window_size = swing_window_size
        analyzer.min_strength = min_strength

        result = BacktestResult(params)

        # 识别摇摆点
        swing_points = analyzer._identify_swing_points_kline(
            kline_data,
            min_threshold=min_reversal_threshold
        )
        result.swing_points_count = len(swing_points)

        logger.info(f"识别到 {len(swing_points)} 个摇摆点")

        if len(swing_points) < 3:
            logger.warning("摇摆点不足，无法进行形态分析")
            return result

        # 滑动窗口检测N型形态
        # 模拟实时检测过程：逐步增加数据点
        for i in range(3, len(swing_points) + 1):
            partial_swings = swing_points[:i]

            # 检测当前形态
            current_pattern = analyzer._detect_n_pattern_kline(partial_swings)

            if not current_pattern:
                continue

            # 检测反转（与上一次形态比较）
            reversal_signal = analyzer._check_reversal(
                current_pattern,
                analyzer.n_pattern_state.previous_pattern
            )

            if reversal_signal and reversal_signal.get('detected'):
                result.add_reversal(reversal_signal, current_pattern)
                logger.debug(f"检测到反转: {reversal_signal['reversal_type']} at {current_pattern['swing_points'][-1]['datetime']}")

            # 更新状态
            analyzer.n_pattern_state.previous_pattern = analyzer.n_pattern_state.current_pattern
            analyzer.n_pattern_state.current_pattern = current_pattern

        logger.info(f"回测完成 - 检测到 {result.reversal_count} 次反转")
        return result

    def run_grid_search(
        self,
        kline_data: List[Dict],
        threshold_range: List[float] = [0.001, 0.003, 0.005, 0.007, 0.01],
        window_sizes: List[int] = [2, 3, 4],
        strength_range: List[float] = [0.3, 0.5, 0.7]
    ) -> List[BacktestResult]:
        """
        网格搜索最优参数

        Args:
            kline_data: K线数据
            threshold_range: 反转阈值范围
            window_sizes: 窗口大小范围
            strength_range: 形态强度范围

        Returns:
            所有测试结果列表
        """
        logger.info("开始网格搜索...")
        logger.info(f"参数空间: threshold={threshold_range}, window={window_sizes}, strength={strength_range}")

        results = []

        total_tests = len(threshold_range) * len(window_sizes) * len(strength_range)
        current_test = 0

        for threshold in threshold_range:
            for window in window_sizes:
                for strength in strength_range:
                    current_test += 1
                    logger.info(f"测试 {current_test}/{total_tests}: threshold={threshold}, window={window}, strength={strength}")

                    result = self.run_single_test(
                        kline_data,
                        min_reversal_threshold=threshold,
                        swing_window_size=window,
                        min_strength=strength
                    )

                    results.append(result)

        logger.info(f"网格搜索完成，共测试 {len(results)} 组参数")
        return results

    def analyze_results(self, results: List[BacktestResult]) -> Dict:
        """
        分析回测结果，找出最优参数

        Args:
            results: 所有回测结果

        Returns:
            分析报告
        """
        if not results:
            return {'error': '没有回测结果'}

        # 按反转次数排序（找到检测敏感度适中的参数）
        # 太少可能漏掉信号，太多可能误报
        sorted_by_count = sorted(results, key=lambda r: r.reversal_count)

        # 按平均强度排序
        sorted_by_strength = sorted(
            results,
            key=lambda r: r.get_avg_strength(),
            reverse=True
        )

        # 综合评分：反转次数适中（3-8次）+ 高平均强度
        def score(r: BacktestResult) -> float:
            # 反转次数得分（3-8次为理想）
            count_score = 0
            if 3 <= r.reversal_count <= 8:
                count_score = 1.0
            elif r.reversal_count < 3:
                count_score = r.reversal_count / 3
            else:
                count_score = max(0, 1.0 - (r.reversal_count - 8) * 0.1)

            # 强度得分
            strength_score = r.get_avg_strength()

            # 综合得分（权重：次数40%，强度60%）
            return count_score * 0.4 + strength_score * 0.6

        sorted_by_score = sorted(results, key=score, reverse=True)

        # 统计分析
        reversal_counts = [r.reversal_count for r in results]
        avg_strengths = [r.get_avg_strength() for r in results]

        report = {
            'total_tests': len(results),
            'statistics': {
                'reversal_count': {
                    'min': min(reversal_counts),
                    'max': max(reversal_counts),
                    'avg': sum(reversal_counts) / len(reversal_counts)
                },
                'avg_strength': {
                    'min': min(avg_strengths),
                    'max': max(avg_strengths),
                    'avg': sum(avg_strengths) / len(avg_strengths)
                }
            },
            'best_by_score': sorted_by_score[0].get_summary(),
            'best_by_strength': sorted_by_strength[0].get_summary(),
            'most_sensitive': sorted_by_count[-1].get_summary(),  # 检测最多
            'least_sensitive': sorted_by_count[0].get_summary()   # 检测最少
        }

        return report

    def print_report(self, report: Dict):
        """打印回测报告"""
        print("\n" + "=" * 80)
        print("回测报告")
        print("=" * 80)

        print(f"\n总测试数: {report['total_tests']}")

        print("\n统计数据:")
        stats = report['statistics']
        print(f"  反转次数: 最少 {stats['reversal_count']['min']}, "
              f"最多 {stats['reversal_count']['max']}, "
              f"平均 {stats['reversal_count']['avg']:.2f}")
        print(f"  平均强度: 最低 {stats['avg_strength']['min']:.3f}, "
              f"最高 {stats['avg_strength']['max']:.3f}, "
              f"平均 {stats['avg_strength']['avg']:.3f}")

        print("\n推荐参数（综合评分最高）:")
        best = report['best_by_score']
        print(f"  - MIN_REVERSAL_THRESHOLD: {best['params']['min_reversal_threshold']}")
        print(f"  - SWING_WINDOW_SIZE: {best['params']['swing_window_size']}")
        print(f"  - MIN_STRENGTH: {best['params']['min_strength']}")
        print(f"  - 反转次数: {best['reversal_count']}")
        print(f"  - 平均强度: {best['avg_strength']:.3f}")

        print("\n其他参考:")
        print("\n  最高强度参数:")
        best_strength = report['best_by_strength']
        print(f"    MIN_REVERSAL_THRESHOLD={best_strength['params']['min_reversal_threshold']}, "
              f"SWING_WINDOW_SIZE={best_strength['params']['swing_window_size']}, "
              f"MIN_STRENGTH={best_strength['params']['min_strength']}")
        print(f"    反转次数: {best_strength['reversal_count']}, 平均强度: {best_strength['avg_strength']:.3f}")

        print("\n  最敏感参数（检测次数最多）:")
        most_sensitive = report['most_sensitive']
        print(f"    MIN_REVERSAL_THRESHOLD={most_sensitive['params']['min_reversal_threshold']}, "
              f"SWING_WINDOW_SIZE={most_sensitive['params']['swing_window_size']}, "
              f"MIN_STRENGTH={most_sensitive['params']['min_strength']}")
        print(f"    反转次数: {most_sensitive['reversal_count']}, 平均强度: {most_sensitive['avg_strength']:.3f}")

        print("\n" + "=" * 80)


def run_backtest():
    """运行完整回测流程"""
    print("=" * 80)
    print("N型形态回测 - 参数优化")
    print("=" * 80)

    # 1. 初始化数据管理器
    print("\n步骤1: 初始化数据管理器...")
    data_manager = KlineDataManager()

    # 2. 加载或抓取K线数据（使用配置的周期和时长）
    print(f"\n步骤2: 加载K线数据（周期: {config.KLINE_PERIOD}, 时长: {config.KLINE_HOURS}小时）...")
    kline_data = data_manager.load_kline_data()

    if not kline_data:
        print("  本地无数据，开始抓取...")
        kline_data = data_manager.fetch_and_save_48h_data()  # 使用默认配置参数

    if not kline_data:
        print("  ❌ 无法获取K线数据，回测终止")
        return

    print(f"  ✓ 成功加载 {len(kline_data)} 条K线数据")
    print(f"  时间范围: {kline_data[0]['datetime']} 至 {kline_data[-1]['datetime']}")

    # 3. 初始化回测器
    print("\n步骤3: 初始化回测器...")
    backtester = Backtester(data_manager)

    # 4. 运行网格搜索
    print("\n步骤4: 运行网格搜索（这可能需要几分钟）...")
    results = backtester.run_grid_search(
        kline_data,
        threshold_range=[0.001, 0.003, 0.005, 0.007, 0.01],
        window_sizes=[2, 3, 4],
        strength_range=[0.3, 0.5, 0.7]
    )

    # 5. 分析结果
    print("\n步骤5: 分析结果...")
    report = backtester.analyze_results(results)

    # 6. 打印报告
    backtester.print_report(report)

    # 7. 保存详细结果
    report_file = config.DATA_DIR / 'backtest_report.json'
    try:
        with open(report_file, 'w', encoding='utf-8') as f:
            # 转换结果为可序列化格式
            serializable_results = [r.get_summary() for r in results]
            save_data = {
                'report': report,
                'all_results': serializable_results,
                'created_at': datetime.now().isoformat()
            }
            json.dump(save_data, f, ensure_ascii=False, indent=2)
        print(f"\n详细报告已保存到: {report_file}")
    except Exception as e:
        logger.error(f"保存报告失败: {e}")

    print("\n" + "=" * 80)
    print("回测完成！")
    print("=" * 80)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    run_backtest()
