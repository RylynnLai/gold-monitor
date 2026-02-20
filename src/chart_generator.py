import logging
from typing import List, Dict
from datetime import datetime

logger = logging.getLogger(__name__)


class ASCIIChartGenerator:
    """ASCII 字符图表生成器"""

    def __init__(self, width: int = 60, height: int = 10, use_unicode: bool = True):
        """
        初始化图表生成器

        Args:
            width: 图表宽度（字符数）
            height: 图表高度（行数）
            use_unicode: 是否使用 Unicode 字符（更美观），设为 False 使用基础 ASCII
        """
        self.width = width
        self.height = height
        self.use_unicode = use_unicode

        # 字符集
        if use_unicode:
            self.chars = {
                'horizontal': '─',
                'vertical': '│',
                'corner_tl': '┌',
                'corner_tr': '┐',
                'corner_bl': '└',
                'corner_br': '┘',
                'cross': '┼',
                'tick_left': '┤',
                'tick_bottom': '┬',
                'line': '━',
                'point': '●',
                'up': '↗',
                'down': '↘',
            }
        else:
            self.chars = {
                'horizontal': '-',
                'vertical': '|',
                'corner_tl': '+',
                'corner_tr': '+',
                'corner_bl': '+',
                'corner_br': '+',
                'cross': '+',
                'tick_left': '+',
                'tick_bottom': '+',
                'line': '=',
                'point': '*',
                'up': '^',
                'down': 'v',
            }

    def generate_daily_chart(self, price_records: List[Dict]) -> str:
        """
        生成当天价格走势图

        Args:
            price_records: 价格记录列表

        Returns:
            ASCII 图表字符串
        """
        # 筛选今天的数据
        today = datetime.now().date()
        today_records = [
            record for record in price_records
            if datetime.fromisoformat(record['timestamp']).date() == today
        ]

        if not today_records:
            return self._no_data_message("今日暂无数据")

        if len(today_records) < 2:
            return self._no_data_message(f"今日数据不足（仅 {len(today_records)} 条），需至少 2 条才能绘图")

        # 提取价格和时间
        prices = [record['price'] for record in today_records]
        timestamps = [datetime.fromisoformat(record['timestamp']) for record in today_records]

        # 计算统计信息
        price_max = max(prices)
        price_min = min(prices)
        price_range = price_max - price_min

        if price_range == 0:
            price_range = price_max * 0.01  # 避免除零，使用 1% 作为范围

        # 生成图表
        chart_lines = []

        # 标题
        title = f"当天黄金价格走势 ({today.strftime('%Y-%m-%d')})"
        chart_lines.append(title)
        chart_lines.append(self.chars['line'] * len(title))

        # 创建图表矩阵
        matrix = [[' ' for _ in range(self.width)] for _ in range(self.height)]

        # 绘制价格线
        for i, price in enumerate(prices):
            # 计算 X 坐标（时间轴）
            x = int((i / (len(prices) - 1)) * (self.width - 1)) if len(prices) > 1 else 0

            # 计算 Y 坐标（价格轴，从底部开始）
            normalized = (price - price_min) / price_range
            y = self.height - 1 - int(normalized * (self.height - 1))

            # 标记点
            matrix[y][x] = self.chars['point']

            # 连线（简单的直线连接）
            if i > 0:
                prev_price = prices[i - 1]
                prev_x = int(((i - 1) / (len(prices) - 1)) * (self.width - 1)) if len(prices) > 1 else 0
                prev_normalized = (prev_price - price_min) / price_range
                prev_y = self.height - 1 - int(prev_normalized * (self.height - 1))

                # 绘制连接线
                self._draw_line(matrix, prev_x, prev_y, x, y)

        # 渲染图表
        for row_idx, row in enumerate(matrix):
            # 计算该行对应的价格值
            normalized_y = (self.height - 1 - row_idx) / (self.height - 1)
            price_value = price_min + normalized_y * price_range

            # 价格标签
            price_label = f"{price_value:6.2f}"

            # 添加行
            line = f"{price_label} {self.chars['tick_left']}{''.join(row)}"
            chart_lines.append(line)

        # 底部轴线
        axis_line = f"       {self.chars['corner_bl']}" + self.chars['horizontal'] * self.width
        chart_lines.append(axis_line)

        # 时间标签
        time_labels = self._generate_time_labels(timestamps)
        chart_lines.append(time_labels)

        # 统计信息
        chart_lines.append(self.chars['line'] * len(title))
        stats = f"最高: {price_max:.2f}  最低: {price_min:.2f}  振幅: {price_range:.2f}  数据点: {len(prices)}"
        chart_lines.append(stats)

        return '\n'.join(chart_lines)

    def _draw_line(self, matrix, x1, y1, x2, y2):
        """在矩阵中绘制连接线"""
        # 使用 Bresenham 算法绘制直线
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx - dy

        x, y = x1, y1

        while True:
            # 不覆盖已有的点标记
            if 0 <= y < len(matrix) and 0 <= x < len(matrix[0]):
                if matrix[y][x] == ' ':
                    if abs(x - x2) > abs(y - y2):
                        matrix[y][x] = self.chars['horizontal']
                    else:
                        matrix[y][x] = self.chars['vertical']

            if x == x2 and y == y2:
                break

            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy

    def _generate_time_labels(self, timestamps: List[datetime]) -> str:
        """生成时间轴标签"""
        if not timestamps:
            return ""

        # 选择几个关键时间点显示
        num_labels = min(6, len(timestamps))
        indices = [int(i * (len(timestamps) - 1) / (num_labels - 1)) for i in range(num_labels)] if num_labels > 1 else [0]

        label_parts = []
        label_parts.append("       ")  # 与价格标签对齐

        for i in range(self.width):
            # 检查这个位置是否需要标签
            closest_idx = round(i / (self.width - 1) * (len(timestamps) - 1)) if len(timestamps) > 1 else 0
            if closest_idx in indices and i % 10 == 0:
                time_str = timestamps[closest_idx].strftime('%H')
                if len(time_str) > 0 and i + len(time_str) <= self.width:
                    label_parts.append(time_str)
                    i += len(time_str) - 1
                else:
                    label_parts.append(' ')
            else:
                label_parts.append(' ')

        # 简化版：只显示首尾时间
        first_time = timestamps[0].strftime('%H:%M')
        last_time = timestamps[-1].strftime('%H:%M')
        label_line = f"        {first_time}" + " " * (self.width - len(first_time) - len(last_time) - 2) + last_time

        return label_line

    def generate_kline_chart(self, kline_data: List[Dict],
                            width: int = 80, height: int = 15) -> str:
        """
        生成ASCII蜡烛图（K线图）

        Args:
            kline_data: K线数据列表 [{datetime, open, high, low, close}, ...]
            width: 图表宽度
            height: 图表高度

        Returns:
            ASCII蜡烛图字符串
        """
        if not kline_data or len(kline_data) < 2:
            return "K线数据不足，无法绘图"

        lines = []

        # 1. 标题
        start_time = kline_data[0]['datetime']
        end_time = kline_data[-1]['datetime']
        title = f"黄金5分钟K线图 ({start_time[:16]} 至 {end_time[:16]})"
        lines.append(title)
        lines.append(self.chars['line'] * min(len(title), width))

        # 2. 计算价格范围
        all_highs = [k['high'] for k in kline_data]
        all_lows = [k['low'] for k in kline_data]
        price_max = max(all_highs)
        price_min = min(all_lows)
        price_range = price_max - price_min

        if price_range == 0:
            return "价格无变化，无法绘图"

        # 3. 价格刻度映射
        def price_to_y(price):
            return int(height - 1 - (price - price_min) / price_range * (height - 1))

        # 4. 采样K线（根据宽度）
        n_klines = len(kline_data)
        x_offset = 10  # 左侧留出价格刻度空间
        available_width = width - x_offset - 2
        sample_step = max(1, n_klines // available_width)
        sampled_klines = kline_data[::sample_step]

        # 5. 创建画布
        canvas = [[' ' for _ in range(width)] for _ in range(height)]

        # 6. 绘制K线蜡烛
        x_step = max(2, available_width // len(sampled_klines))

        for i, kline in enumerate(sampled_klines):
            x = x_offset + i * x_step

            if x >= width - 1:
                break

            high_y = max(0, min(height - 1, price_to_y(kline['high'])))
            low_y = max(0, min(height - 1, price_to_y(kline['low'])))
            open_y = max(0, min(height - 1, price_to_y(kline['open'])))
            close_y = max(0, min(height - 1, price_to_y(kline['close'])))

            # 判断阴阳线
            is_bullish = kline['close'] >= kline['open']  # 阳线（收盘 >= 开盘）

            # 绘制影线（上影线 + 下影线）
            for y in range(min(high_y, low_y), max(high_y, low_y) + 1):
                if 0 <= y < height and x < width:
                    if canvas[y][x] == ' ':
                        canvas[y][x] = self.chars['vertical']

            # 绘制实体（开盘价到收盘价）
            body_top = min(open_y, close_y)
            body_bottom = max(open_y, close_y)

            for y in range(body_top, body_bottom + 1):
                if 0 <= y < height and x < width:
                    if is_bullish:
                        canvas[y][x] = self.chars['vertical']  # 阳线实体（空心）
                    else:
                        canvas[y][x] = '█'  # 阴线实体（填充）

        # 7. 绘制价格刻度（左侧）
        for i in range(height):
            price = price_min + (height - 1 - i) / (height - 1) * price_range
            label = f"{price:8.2f} {self.chars['tick_left']}"
            for j, char in enumerate(label):
                if j < len(label) and j < x_offset:
                    canvas[i][j] = char

        # 8. 转换画布为字符串
        for row in canvas:
            lines.append(''.join(row))

        # 9. 添加底部横坐标轴
        axis_line = ' ' * x_offset + self.chars['corner_bl'] + self.chars['horizontal'] * (width - x_offset - 1)
        lines.append(axis_line)

        # 10. 添加时间标签（横坐标）
        time_labels = [' '] * width
        # 计算合适的标签数量（避免重叠，每个标签需要至少6个字符宽度）
        label_width = 6  # "HH:MM" + 空格
        max_possible_labels = (width - x_offset) // label_width
        num_labels = min(max_possible_labels, len(sampled_klines), 12)  # 最多12个标签

        if num_labels > 1:
            label_indices = [int(i * (len(sampled_klines) - 1) / (num_labels - 1)) for i in range(num_labels)]
        else:
            label_indices = [0]

        for idx in label_indices:
            if idx < len(sampled_klines):
                kline = sampled_klines[idx]
                # 提取时间标签（时:分）
                time_str = kline['datetime'][11:16]  # 格式: HH:MM
                x_pos = x_offset + idx * x_step

                # 确保标签不越界且不重叠
                if x_pos + len(time_str) <= width:
                    # 检查该位置是否已被占用
                    can_place = all(time_labels[x_pos + i] == ' ' for i in range(len(time_str)) if x_pos + i < width)
                    if can_place:
                        for i, char in enumerate(time_str):
                            if x_pos + i < width:
                                time_labels[x_pos + i] = char

        lines.append(''.join(time_labels))

        # 11. 底部信息
        lines.append(self.chars['line'] * width)
        stats = f"最高: {price_max:.2f}  最低: {price_min:.2f}  振幅: {price_range:.2f}  K线数: {len(kline_data)}"
        lines.append(stats)

        return '\n'.join(lines)

    def _no_data_message(self, message: str) -> str:
        """生成无数据提示信息"""
        lines = []
        lines.append("=" * 50)
        lines.append(message.center(50))
        lines.append("=" * 50)
        return '\n'.join(lines)


def test_chart():
    """测试函数"""
    from datetime import timedelta

    # 模拟今天的数据
    now = datetime.now()
    test_records = []

    base_price = 500.0
    for i in range(20):
        timestamp = now - timedelta(hours=10 - i * 0.5)
        price = base_price + (i % 5) * 0.5 - 1.0
        test_records.append({
            'price': price,
            'timestamp': timestamp.isoformat()
        })

    generator = ASCIIChartGenerator(width=60, height=10, use_unicode=True)
    chart = generator.generate_daily_chart(test_records)
    print(chart)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    test_chart()
