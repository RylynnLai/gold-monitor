import requests
import logging
from typing import Dict, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class FeishuNotifier:
    """飞书 Webhook 通知器"""

    def __init__(self, webhook_url: str):
        """
        初始化飞书 Webhook 通知器

        Args:
            webhook_url: 飞书机器人 Webhook URL
        """
        self.webhook_url = webhook_url

    def send_trend_notification(self, trend_info: Dict) -> bool:
        """
        发送趋势通知

        Args:
            trend_info: 趋势信息字典

        Returns:
            发送是否成功
        """
        direction = trend_info['direction'].value
        count = trend_info['count']
        current_price = trend_info['current_price']
        start_price = trend_info['start_price']
        change_percent = trend_info['change_percent']
        prices = trend_info['prices']

        # 构造消息内容
        emoji = "📈" if change_percent > 0 else "📉"
        color = "red" if change_percent > 0 else "green"

        message = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {
                        "content": f"{emoji} 黄金价格{direction}预警",
                        "tag": "plain_text"
                    },
                    "template": color
                },
                "elements": [
                    {
                        "tag": "div",
                        "fields": [
                            {
                                "is_short": True,
                                "text": {
                                    "tag": "lark_md",
                                    "content": f"**当前价格**\\n{current_price:.2f} 元/克"
                                }
                            },
                            {
                                "is_short": True,
                                "text": {
                                    "tag": "lark_md",
                                    "content": f"**起始价格**\\n{start_price:.2f} 元/克"
                                }
                            },
                            {
                                "is_short": True,
                                "text": {
                                    "tag": "lark_md",
                                    "content": f"**变化幅度**\\n{change_percent:+.2f}%"
                                }
                            },
                            {
                                "is_short": True,
                                "text": {
                                    "tag": "lark_md",
                                    "content": f"**趋势次数**\\n连续 {count} 次{direction}"
                                }
                            }
                        ]
                    },
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": f"**价格序列**\\n{' → '.join([f'{p:.2f}' for p in prices])}"
                        }
                    },
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": f"**通知时间**\\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                        }
                    },
                    {
                        "tag": "hr"
                    },
                    {
                        "tag": "note",
                        "elements": [
                            {
                                "tag": "plain_text",
                                "content": "黄金价格监控系统 | 数据来源：东方财富"
                            }
                        ]
                    }
                ]
            }
        }

        return self._send_message(message)

    def _send_message(self, payload: Dict) -> bool:
        """
        发送消息到飞书 Webhook

        Args:
            payload: 消息内容

        Returns:
            发送是否成功
        """
        if not self.webhook_url:
            logger.warning("Webhook URL 未配置，跳过发送")
            return False

        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()

            data = response.json()

            # 飞书 webhook 成功返回: {"StatusCode": 0, "StatusMessage": "success"}
            # 或: {"code": 0, "msg": "success"}
            if data.get('StatusCode') == 0 or data.get('code') == 0:
                logger.info("成功发送飞书 Webhook 通知")
                return True
            else:
                logger.error(f"发送 Webhook 失败: {data}")
                return False

        except Exception as e:
            logger.error(f"发送 Webhook 异常: {e}")
            return False

    def send_trendline_notification(self, analysis_result: Dict,
                                    price_info: Dict) -> bool:
        """
        发送趋势线突破通知

        Args:
            analysis_result: 趋势线分析结果字典
            price_info: 当前价格信息

        Returns:
            发送是否成功
        """
        try:
            reversal_type = analysis_result['reversal_type']
            from_trend = analysis_result['from_trend']
            to_trend = analysis_result['to_trend']
            breakout_price = analysis_result['breakout_price']
            trendline_value = analysis_result['trendline_value']
            breakout_percent = analysis_result['breakout_percent']
            pivot_count = analysis_result['pivot_points_count']
            confidence = analysis_result['confidence']
            trigger_time = analysis_result['trigger_time']

            # 图标和颜色
            emoji = "📈" if '看涨' in reversal_type else "📉"
            color = "red" if '看涨' in reversal_type else "green"

            # 生成交易建议
            trading_advice = self._generate_trendline_trading_advice(analysis_result)

            # 构造消息内容（使用文本消息格式，更简洁）
            content = f"""【{emoji} {reversal_type}】黄金趋势线突破信号

🔄 趋势变化
  从: {from_trend.value}
  到: {to_trend.value}

💰 突破信息
  突破价格: {breakout_price:.2f} 元/克
  趋势线值: {trendline_value:.2f} 元/克
  突破幅度: {breakout_percent:.2f}%
  触发时间: {trigger_time}

📊 信号强度
  摆动点数: {pivot_count} 个
  置信度: {confidence:.1%}

📈 当前行情
  开盘价: {price_info.get('open', 0):.2f} 元/克
  最高价: {price_info.get('high', 0):.2f} 元/克
  最低价: {price_info.get('low', 0):.2f} 元/克
  当前价: {price_info['price']:.2f} 元/克
  涨跌幅: {price_info.get('change_percent', 0):+.2f}%

💡 交易建议
  {trading_advice}

⏰ 通知时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

            payload = {
                "msg_type": "text",
                "content": {"text": content}
            }

            return self._send_message(payload)

        except Exception as e:
            logger.error(f"发送趋势线通知异常: {e}", exc_info=True)
            return False

    def _generate_trendline_trading_advice(self, analysis_result: Dict) -> str:
        """
        生成趋势线交易建议

        Args:
            analysis_result: 趋势线分析结果

        Returns:
            交易建议文本
        """
        confidence = analysis_result['confidence']
        reversal_type = analysis_result['reversal_type']
        breakout_percent = analysis_result['breakout_percent']

        if '看涨' in reversal_type:
            if confidence >= 0.6 and breakout_percent >= 0.1:
                return "强烈建议买入 - 趋势线向上突破，信号强烈"
            elif confidence >= 0.4:
                return "建议买入 - 趋势线向上突破，可小仓位试探"
            else:
                return "谨慎观望 - 反转信号较弱，等待进一步确认"
        else:  # 看跌
            if confidence >= 0.6 and breakout_percent >= 0.1:
                return "强烈建议卖出 - 趋势线向下突破，风险较高"
            elif confidence >= 0.4:
                return "建议卖出 - 趋势线向下突破，建议减仓"
            else:
                return "谨慎观望 - 反转信号较弱，继续观察"

    def send_test_message(self) -> bool:
        """发送测试消息"""
        payload = {
            "msg_type": "text",
            "content": {
                "text": f"黄金价格监控系统测试消息\n发送时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            }
        }

        return self._send_message(payload)

    def send_reversal_notification(self, reversal_signal: Dict,
                                   analysis_result: Dict) -> bool:
        """
        发送N字形反转通知

        Args:
            reversal_signal: 反转信号字典
            analysis_result: 分析结果字典

        Returns:
            发送是否成功
        """
        try:
            reversal_type_cn = "看涨反转 ↗" if reversal_signal['reversal_type'] == 'BULLISH' else "看跌反转 ↘"

            # 格式化摇摆点序列
            swing_points_str = self._format_swing_points(analysis_result.get('swing_points', []))

            # 生成交易建议
            trading_advice = self._generate_trading_advice(reversal_signal)

            # 提取K线统计信息
            kline_data = analysis_result.get('kline_data', [])
            if kline_data:
                kline_summary = self._format_kline_summary(kline_data)
            else:
                kline_summary = "  无K线数据"

            content = f"""【{reversal_type_cn}】黄金价格N字形反转信号

🔄 形态变化
  从: {reversal_signal['from_pattern'].value}
  到: {reversal_signal['to_pattern'].value}

💰 触发信息
  触发价格: {reversal_signal['trigger_price']:.2f} 元/克
  触发时间: {reversal_signal['trigger_time']}
  幅度: {reversal_signal['change_percent']:+.2f}%

📊 形态强度: {reversal_signal['confidence']:.1%}

💡 交易建议
  {trading_advice}

📈 摇摆点序列
  {swing_points_str}

📉 K线统计
{kline_summary}

⏰ 分析窗口: {analysis_result.get('analysis_window', '48h')}
📌 数据点数: {analysis_result.get('data_points', 0)} 条K线
"""

            payload = {
                "msg_type": "text",
                "content": {"text": content}
            }

            return self._send_message(payload)

        except Exception as e:
            logger.error(f"发送反转通知异常: {e}", exc_info=True)
            return False

    def _generate_trading_advice(self, signal: Dict) -> str:
        """
        生成交易建议

        Args:
            signal: 反转信号字典

        Returns:
            交易建议文本
        """
        confidence = signal['confidence']
        reversal_type = signal['reversal_type']

        if reversal_type == 'BULLISH':
            if confidence >= 0.7:
                return "建议买入 - 强烈看涨信号，形态可靠"
            elif confidence >= 0.5:
                return "考虑买入 - 看涨信号，但需观察确认"
            else:
                return "谨慎观望 - 信号较弱，等待进一步确认"
        else:  # BEARISH
            if confidence >= 0.7:
                return "建议卖出 - 强烈看跌信号，建议止损"
            elif confidence >= 0.5:
                return "考虑卖出 - 看跌信号，但需观察确认"
            else:
                return "谨慎观望 - 信号较弱，等待进一步确认"

    def _format_swing_points(self, swing_points: List[Dict]) -> str:
        """
        格式化摇摆点序列

        Args:
            swing_points: 摇摆点列表

        Returns:
            格式化的摇摆点字符串
        """
        if not swing_points:
            return "无数据"

        points_str = []
        for sp in swing_points[-5:]:  # 显示最近5个摇摆点
            icon = "🔺" if sp['type'] == 'HIGH' else "🔻"
            try:
                time_str = datetime.fromisoformat(sp['timestamp']).strftime('%m-%d %H:%M')
            except:
                time_str = sp['timestamp']
            points_str.append(f"{icon} {sp['price']:.2f} ({time_str})")

        return "\n  ".join(points_str)

    def _format_kline_summary(self, kline_data: List[Dict]) -> str:
        """
        格式化K线统计摘要

        Args:
            kline_data: K线数据列表

        Returns:
            格式化的K线统计字符串
        """
        if not kline_data:
            return "  无数据"

        latest = kline_data[-1]
        all_highs = [k['high'] for k in kline_data]
        all_lows = [k['low'] for k in kline_data]

        return f"""  最新K线: 开{latest['open']:.2f} 高{latest['high']:.2f} 低{latest['low']:.2f} 收{latest['close']:.2f}
  48H最高: {max(all_highs):.2f}
  48H最低: {min(all_lows):.2f}
  48H振幅: {max(all_highs) - min(all_lows):.2f}"""


def test_notifier():
    """测试函数"""
    import os
    from dotenv import load_dotenv

    load_dotenv()

    webhook_url = os.getenv('FEISHU_WEBHOOK_URL')

    if not webhook_url:
        print("请先配置 FEISHU_WEBHOOK_URL 环境变量")
        return

    notifier = FeishuNotifier(webhook_url)
    success = notifier.send_test_message()
    print(f"测试消息发送{'成功' if success else '失败'}")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    test_notifier()
