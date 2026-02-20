"""
K线数据管理器
用于抓取、存储和更新48小时K线数据
"""
import json
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from pathlib import Path
from .gold_fetcher import GoldPriceFetcher
from . import config

logger = logging.getLogger(__name__)


class KlineDataManager:
    """K线数据管理器（48小时数据）"""

    def __init__(self, data_file: Optional[Path] = None):
        """
        初始化K线数据管理器

        Args:
            data_file: 数据文件路径，默认使用 config.KLINE_DATA_FILE
        """
        self.data_file = data_file or config.KLINE_DATA_FILE
        self.fetcher = GoldPriceFetcher()
        logger.info(f"K线数据管理器初始化完成，数据文件: {self.data_file}")

    def fetch_and_save_48h_data(self, period: str = '5min') -> Optional[List[Dict]]:
        """
        抓取48小时K线数据并保存到本地

        Args:
            period: K线周期，默认 '5min'

        Returns:
            K线数据列表，失败返回 None
        """
        logger.info(f"开始抓取48小时K线数据（周期: {period}）...")

        # 从API获取数据
        kline_data = self.fetcher.get_48h_kline_data(period)

        if not kline_data:
            logger.error("抓取K线数据失败")
            return None

        # 保存到文件
        success = self._save_kline_data(kline_data, period)

        if success:
            logger.info(f"成功抓取并保存 {len(kline_data)} 条K线数据")
            return kline_data
        else:
            logger.error("保存K线数据失败")
            return None

    def update_48h_data(self, period: str = '5min') -> Optional[List[Dict]]:
        """
        更新本地48小时K线数据

        流程：
        1. 加载本地数据
        2. 抓取最新数据
        3. 合并数据（去重、排序）
        4. 保留最近48小时
        5. 保存更新后的数据

        Args:
            period: K线周期，默认 '5min'

        Returns:
            更新后的K线数据列表，失败返回 None
        """
        logger.info(f"开始更新48小时K线数据（周期: {period}）...")

        # 1. 加载本地数据
        local_data = self.load_kline_data()

        # 2. 抓取最新数据
        new_data = self.fetcher.get_48h_kline_data(period)

        if not new_data:
            logger.error("抓取最新K线数据失败")
            # 如果有本地数据，返回本地数据
            if local_data:
                logger.warning("使用本地缓存数据")
                return local_data
            return None

        # 3. 合并数据
        if local_data:
            merged_data = self._merge_kline_data(local_data, new_data)
            logger.info(f"合并数据：本地 {len(local_data)} 条 + 新增 {len(new_data)} 条 = {len(merged_data)} 条")
        else:
            merged_data = new_data
            logger.info(f"首次获取，共 {len(merged_data)} 条数据")

        # 4. 保留最近48小时
        filtered_data = self._filter_48h_data(merged_data)
        logger.info(f"过滤后保留 {len(filtered_data)} 条（48小时内）")

        # 5. 保存更新后的数据
        success = self._save_kline_data(filtered_data, period)

        if success:
            logger.info("K线数据更新成功")
            return filtered_data
        else:
            logger.error("保存更新后的数据失败")
            return filtered_data  # 即使保存失败，也返回数据

    def load_kline_data(self) -> Optional[List[Dict]]:
        """
        从本地文件加载K线数据

        Returns:
            K线数据列表，文件不存在或失败返回 None
        """
        if not self.data_file.exists():
            logger.info("K线数据文件不存在")
            return None

        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            kline_data = data.get('kline_data', [])
            metadata = data.get('metadata', {})

            logger.info(f"成功加载 {len(kline_data)} 条K线数据")
            logger.debug(f"元数据: {metadata}")

            return kline_data

        except Exception as e:
            logger.error(f"加载K线数据失败: {e}")
            return None

    def get_data_info(self) -> Optional[Dict]:
        """
        获取本地K线数据的元信息

        Returns:
            元信息字典，包含数据量、时间范围等
        """
        kline_data = self.load_kline_data()

        if not kline_data:
            return None

        return {
            'count': len(kline_data),
            'start_time': kline_data[0]['datetime'] if kline_data else None,
            'end_time': kline_data[-1]['datetime'] if kline_data else None,
            'price_range': {
                'low': min(k['low'] for k in kline_data) if kline_data else 0,
                'high': max(k['high'] for k in kline_data) if kline_data else 0,
            },
            'file_path': str(self.data_file),
            'file_exists': self.data_file.exists()
        }

    def _save_kline_data(self, kline_data: List[Dict], period: str) -> bool:
        """
        保存K线数据到文件

        Args:
            kline_data: K线数据列表
            period: 周期

        Returns:
            True if successful, False otherwise
        """
        try:
            # 确保目录存在
            self.data_file.parent.mkdir(exist_ok=True)

            # 构建保存数据（包含元数据）
            save_data = {
                'metadata': {
                    'symbol': 'XAU/USD',
                    'period': period,
                    'count': len(kline_data),
                    'start_time': kline_data[0]['datetime'] if kline_data else None,
                    'end_time': kline_data[-1]['datetime'] if kline_data else None,
                    'updated_at': datetime.now().isoformat(),
                    'description': '48小时K线数据（用于回测）'
                },
                'kline_data': kline_data
            }

            # 写入文件
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)

            logger.debug(f"K线数据已保存到 {self.data_file}")
            return True

        except Exception as e:
            logger.error(f"保存K线数据失败: {e}")
            return False

    def _merge_kline_data(self, old_data: List[Dict], new_data: List[Dict]) -> List[Dict]:
        """
        合并K线数据（去重、排序）

        Args:
            old_data: 旧数据
            new_data: 新数据

        Returns:
            合并后的数据列表
        """
        # 使用字典去重（以datetime为key）
        merged_dict = {}

        # 先添加旧数据
        for item in old_data:
            merged_dict[item['datetime']] = item

        # 用新数据覆盖（新数据优先）
        for item in new_data:
            merged_dict[item['datetime']] = item

        # 转换回列表并按时间排序
        merged_list = list(merged_dict.values())
        merged_list.sort(key=lambda x: x['datetime'])

        return merged_list

    def _filter_48h_data(self, kline_data: List[Dict]) -> List[Dict]:
        """
        过滤保留最近48小时的数据

        Args:
            kline_data: K线数据列表

        Returns:
            过滤后的数据列表
        """
        if not kline_data:
            return []

        # 计算48小时前的时间
        cutoff_time = datetime.now() - timedelta(hours=48)

        # 过滤数据
        filtered = [
            item for item in kline_data
            if datetime.fromisoformat(item['datetime'].replace('Z', '+00:00')) >= cutoff_time
        ]

        return filtered


def test_manager():
    """测试K线数据管理器"""
    print("=" * 70)
    print("测试K线数据管理器")
    print("=" * 70)

    manager = KlineDataManager()

    # 测试1: 抓取并保存48小时数据
    print("\n1. 抓取并保存48小时数据:")
    kline_data = manager.fetch_and_save_48h_data('5min')
    if kline_data:
        print(f"   ✓ 成功抓取 {len(kline_data)} 条K线数据")
        print(f"   时间范围: {kline_data[0]['datetime']} 至 {kline_data[-1]['datetime']}")
    else:
        print("   ❌ 抓取失败")

    # 测试2: 加载本地数据
    print("\n2. 加载本地数据:")
    loaded_data = manager.load_kline_data()
    if loaded_data:
        print(f"   ✓ 成功加载 {len(loaded_data)} 条K线数据")
    else:
        print("   ❌ 加载失败")

    # 测试3: 获取数据信息
    print("\n3. 获取数据信息:")
    info = manager.get_data_info()
    if info:
        print(f"   数据量: {info['count']} 条")
        print(f"   时间范围: {info['start_time']} 至 {info['end_time']}")
        print(f"   价格范围: ${info['price_range']['low']:.2f} - ${info['price_range']['high']:.2f}")
    else:
        print("   ❌ 获取信息失败")

    # 测试4: 更新数据
    print("\n4. 更新48小时数据:")
    updated_data = manager.update_48h_data('5min')
    if updated_data:
        print(f"   ✓ 成功更新，共 {len(updated_data)} 条K线数据")
    else:
        print("   ❌ 更新失败")

    print("\n" + "=" * 70)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    test_manager()
