#!/usr/bin/env python3
"""
黄金价格监控主程序
定期获取黄金价格，检测趋势，并发送飞书通知
"""

import logging
import time
import signal
import sys
from datetime import datetime
from pathlib import Path

# 添加 src 目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

import config
from config import (
    FEISHU_WEBHOOK_URL,
    CHECK_INTERVAL,
    TREND_COUNT,
    LOG_LEVEL,
    LOG_FILE,
    PRICE_HISTORY_FILE,
    DATA_DIR,
    BASE_DIR
)
from gold_fetcher import GoldPriceFetcher
from trendline_analyzer import TrendlineAnalyzer
from feishu_notifier import FeishuNotifier
from chart_generator import ASCIIChartGenerator
from report_generator import ReportGenerator


class GoldMonitor:
    """黄金价格监控器"""

    def __init__(self):
        self.setup_logging()
        self.logger = logging.getLogger(__name__)

        # 初始化各个组件 (趋势线模式)
        self.fetcher = GoldPriceFetcher()
        self.analyzer = TrendlineAnalyzer(
            trend_window_hours=config.TREND_WINDOW_HOURS,
            min_pivot_distance=config.MIN_PIVOT_DISTANCE,
            breakout_threshold=config.BREAKOUT_THRESHOLD,
            min_trend_points=2
        )
        self.notifier = FeishuNotifier(FEISHU_WEBHOOK_URL)
        self.chart_gen = ASCIIChartGenerator(width=60, height=10, use_unicode=True)
        self.report_gen = ReportGenerator()

        self.running = False
        self.output_dir = BASE_DIR / 'output'
        self.output_dir.mkdir(exist_ok=True)  # 创建输出目录

        self.logger.info("黄金价格监控器初始化完成（趋势线模式）")
        self.logger.info(f"检查间隔: {CHECK_INTERVAL} 秒")
        self.logger.info(
            f"趋势线参数: window={config.TREND_WINDOW_HOURS}h, "
            f"pivot={config.MIN_PIVOT_DISTANCE}, "
            f"threshold={config.BREAKOUT_THRESHOLD*100:.2f}%"
        )

    def setup_logging(self):
        """配置日志"""
        # 创建日志格式
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        date_format = '%Y-%m-%d %H:%M:%S'

        # 获取日志级别（确保大写，避免获取到函数而不是常量）
        log_level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)

        # 配置根日志记录器
        logging.basicConfig(
            level=log_level,
            format=log_format,
            datefmt=date_format,
            handlers=[
                # 文件处理器
                logging.FileHandler(LOG_FILE, encoding='utf-8'),
                # 控制台处理器
                logging.StreamHandler()
            ]
        )

    def _load_notify_state(self):
        """加载上次通知状态"""
        try:
            if self.notify_state_file.exists():
                import json
                with open(self.notify_state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    direction_str = state.get('last_direction')
                    if direction_str:
                        # 将字符串转换回枚举
                        from price_analyzer import TrendDirection
                        for direction in TrendDirection:
                            if direction.value == direction_str:
                                return direction
            return None
        except Exception as e:
            self.logger.error(f"加载通知状态失败: {e}")
            return None

    def _save_notify_state(self):
        """保存通知状态"""
        try:
            import json
            state = {
                'last_direction': self.last_notified_direction.value if self.last_notified_direction else None,
                'updated_at': datetime.now().isoformat()
            }
            with open(self.notify_state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"保存通知状态失败: {e}")

    def check_price(self):
        """检查价格并分析趋势"""
        try:
            # 获取当前价格
            self.logger.debug("开始获取黄金价格...")
            price_info = self.fetcher.get_current_price()

            if not price_info:
                self.logger.warning("获取价格失败，跳过本次检查")
                return

            # 分析趋势
            trend_info = self.analyzer.add_price(price_info)

            # 如果检测到趋势
            if trend_info:
                current_direction = trend_info['direction']

                # 检查是否需要发送通知（避免同一趋势重复通知）
                if current_direction != self.last_notified_direction:
                    self.logger.info("检测到新的趋势，准备发送通知")

                    # 发送飞书通知
                    success = self.notifier.send_trend_notification(trend_info)

                    if success:
                        self.last_notified_direction = current_direction
                        self.logger.info(f"已发送{current_direction.value}趋势通知")
                    else:
                        self.logger.error("发送通知失败")
                else:
                    self.logger.debug(f"趋势{current_direction.value}已通知过，跳过")
            else:
                # 未检测到趋势时，重置通知标记
                self.last_notified_direction = None

        except Exception as e:
            self.logger.error(f"检查价格时发生异常: {e}", exc_info=True)

    def run_once(self):
        """单次运行模式（青龙面板）- 使用趋势线分析"""
        self.logger.info("=" * 50)
        self.logger.info("执行单次价格检查（趋势线模式）")
        self.logger.info("=" * 50)

        try:
            # 1. 获取K线数据（使用配置的周期和时长）
            self.logger.info(f"正在获取K线数据（周期: {config.KLINE_PERIOD}, 时长: {config.KLINE_HOURS}小时）...")
            kline_data = self.fetcher.get_48h_kline_data()  # 使用配置的默认值

            if not kline_data:
                self.logger.warning("获取K线数据失败")
                print("\n❌ 获取K线数据失败，请稍后重试\n")
                return

            # 2. 提取当前价格信息（最后一根K线）
            latest_kline = kline_data[-1]
            price_info = {
                'name': 'AU期货',
                'price': latest_kline['close'],
                'open': latest_kline['open'],
                'high': latest_kline['high'],
                'low': latest_kline['low'],
                'change': latest_kline['close'] - latest_kline['open'],
                'change_percent': ((latest_kline['close'] - latest_kline['open'])
                                  / latest_kline['open'] * 100),
                'timestamp': latest_kline['datetime']
            }

            # 3. 分析K线数据（趋势线突破检测）
            analysis_result = self.analyzer.analyze_kline_data(kline_data)

            # 4. 生成K线图（ASCII蜡烛图）
            kline_chart = self.chart_gen.generate_kline_chart(kline_data, width=80, height=15)

            # 5. 生成综合报告
            report = self.report_gen.generate_trendline_report(price_info, analysis_result, self.analyzer)

            # 6. 输出到控制台
            self._print_formatted_output(price_info, kline_chart, report)

            # 7. 保存到文件
            self._save_to_file(price_info, kline_chart, report)

            # 8. 发送飞书通知（趋势线突破时）
            if analysis_result and analysis_result.get('type') == 'TRENDLINE_BREAKOUT':
                self.logger.info(f"检测到{analysis_result['reversal_type']}，准备发送通知")

                # 检查飞书配置
                if FEISHU_WEBHOOK_URL:
                    success = self.notifier.send_trendline_notification(
                        analysis_result,
                        price_info
                    )

                    if success:
                        # 记录反转历史
                        self._save_reversal_history(analysis_result)
                        self.logger.info(
                            f"已发送{analysis_result['reversal_type']}通知 "
                            f"(突破价格: {analysis_result['breakout_price']:.2f})"
                        )
                    else:
                        self.logger.error("发送飞书通知失败")
                else:
                    self.logger.info("飞书 Webhook 未配置，跳过通知")

            self.logger.info("单次检查完成")

        except Exception as e:
            self.logger.error(f"单次运行时发生异常: {e}", exc_info=True)
            print(f"\n❌ 运行时发生错误: {e}\n")

    def _save_reversal_history(self, reversal_signal: dict):
        """保存反转历史"""
        try:
            import json
            history_file = DATA_DIR / 'reversal_history.json'

            # 加载现有历史
            if history_file.exists():
                with open(history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            else:
                history = []

            # 添加新记录（兼容趋势线格式）
            record = {
                'time': datetime.now().isoformat(),
                'type': reversal_signal['reversal_type'],
                'trigger_price': reversal_signal['breakout_price'],
                'confidence': reversal_signal.get('confidence', 0),
            }

            # 趋势线格式包含额外字段
            if 'from_trend' in reversal_signal:
                record['from'] = reversal_signal['from_trend'].value
                record['to'] = reversal_signal['to_trend'].value
                record['trendline_value'] = reversal_signal.get('trendline_value', 0)
                record['breakout_percent'] = reversal_signal.get('breakout_percent', 0)

            history.append(record)

            # 保存（只保留最近100条）
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(history[-100:], f, ensure_ascii=False, indent=2)

            self.logger.debug("反转历史已保存")

        except Exception as e:
            self.logger.error(f"保存反转历史失败: {e}")

    def _print_formatted_output(self, price_info, chart, report):
        """格式化控制台输出"""
        print("\n" + "=" * 60)
        print("黄金价格监控 - 运行结果".center(56))
        print("=" * 60 + "\n")

        # 输出报告
        print(report)

        # 输出图表
        print("\n" + chart)

        print("\n" + "=" * 60 + "\n")

    def _save_to_file(self, price_info, chart, report):
        """保存运行结果到文件"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = self.output_dir / f"result_{timestamp}.txt"

            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("=" * 60 + "\n")
                f.write("黄金价格监控 - 运行结果\n")
                f.write("=" * 60 + "\n\n")
                f.write(report + "\n\n")
                f.write(chart + "\n")
                f.write("\n" + "=" * 60 + "\n")

            self.logger.info(f"运行结果已保存到: {output_file}")
        except Exception as e:
            self.logger.error(f"保存输出文件失败: {e}")

    def start(self):
        """启动监控"""
        self.logger.info("=" * 50)
        self.logger.info("黄金价格监控系统启动")
        self.logger.info("=" * 50)

        # 验证配置（Webhook 可选）
        if not FEISHU_WEBHOOK_URL:
            self.logger.warning("飞书 Webhook URL 未配置，将不会发送通知")
            self.logger.warning("如需通知功能，请在 .env 文件中配置 FEISHU_WEBHOOK_URL")

        self.running = True

        # 立即执行一次检查
        self.logger.info("执行首次价格检查...")
        self.check_price()

        # 进入监控循环
        try:
            while self.running:
                time.sleep(CHECK_INTERVAL)
                self.check_price()

        except KeyboardInterrupt:
            self.logger.info("收到中断信号")
        finally:
            self.stop()

    def stop(self):
        """停止监控"""
        self.logger.info("=" * 50)
        self.logger.info("黄金价格监控系统停止")
        self.logger.info("=" * 50)
        self.running = False

    def test_connection(self):
        """测试各个组件的连接"""
        self.logger.info("开始测试各组件连接...")

        # 测试价格获取
        self.logger.info("1. 测试价格获取...")
        price_info = self.fetcher.get_current_price()
        if price_info:
            self.logger.info(f"✓ 价格获取成功: {price_info['price']} 元/克")
        else:
            self.logger.error("✗ 价格获取失败")
            return False

        # 测试飞书通知
        self.logger.info("2. 测试飞书通知...")
        success = self.notifier.send_test_message()
        if success:
            self.logger.info("✓ 飞书通知发送成功")
        else:
            self.logger.error("✗ 飞书通知发送失败")
            return False

        self.logger.info("所有组件测试通过!")
        return True


def signal_handler(signum, frame):
    """信号处理器"""
    logger = logging.getLogger(__name__)
    logger.info(f"收到信号 {signum}，准备退出...")
    sys.exit(0)


def main():
    """主函数"""
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 创建监控器实例
    monitor = GoldMonitor()

    # 检查命令行参数
    if len(sys.argv) > 1:
        if sys.argv[1] == 'test':
            # 测试模式
            monitor.test_connection()
        elif sys.argv[1] == 'loop':
            # 循环监控模式（保留兼容性）
            monitor.start()
        else:
            print("用法:")
            print("  python main.py         # 单次运行（青龙模式）")
            print("  python main.py test    # 测试连接")
            print("  python main.py loop    # 循环监控模式")
    else:
        # 默认执行单次运行（青龙面板模式）
        monitor.run_once()


if __name__ == '__main__':
    main()
