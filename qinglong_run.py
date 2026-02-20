#!/usr/bin/env python3
"""
青龙面板专用启动脚本
适配青龙面板的目录结构和环境变量
"""

import os
import sys
from pathlib import Path

# 获取脚本所在目录（青龙面板的 scripts 目录下）
SCRIPT_DIR = Path(__file__).parent.absolute()

# 将 src 目录添加到 Python 路径
sys.path.insert(0, str(SCRIPT_DIR / 'src'))

# 确保青龙面板的环境变量生效
# 青龙面板会自动加载 .env 文件，但为了兼容性，我们也读取一次
def load_env_file():
    """加载 .env 文件（如果存在）"""
    env_file = SCRIPT_DIR / '.env'
    if env_file.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(env_file)
            print(f"✓ 已加载环境变量文件: {env_file}")
        except ImportError:
            print("⚠ python-dotenv 未安装，跳过 .env 文件加载")
            print("  青龙面板会自动加载环境变量，无需担心")
    else:
        print(f"⚠ 环境变量文件不存在: {env_file}")
        print("  请在青龙面板的环境变量中配置所需参数")


def check_dependencies():
    """检查必要的依赖"""
    required_modules = ['requests']
    optional_modules = ['akshare', 'dotenv']

    missing_required = []
    missing_optional = []

    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing_required.append(module)

    for module in optional_modules:
        try:
            __import__(module)
        except ImportError:
            missing_optional.append(module)

    if missing_required:
        print(f"❌ 缺少必要依赖: {', '.join(missing_required)}")
        print(f"   请在青龙面板中运行: pip3 install -r {SCRIPT_DIR}/requirements.txt")
        return False

    if missing_optional:
        print(f"⚠ 缺少可选依赖: {', '.join(missing_optional)}")
        print(f"   建议运行: pip3 install -r {SCRIPT_DIR}/requirements.txt")

    return True


def ensure_directories():
    """确保必要的目录存在"""
    dirs = ['data', 'logs', 'output']
    for dir_name in dirs:
        dir_path = SCRIPT_DIR / dir_name
        dir_path.mkdir(exist_ok=True)
    print(f"✓ 目录结构检查完成")


def main():
    """主函数"""
    print("=" * 60)
    print("黄金价格监控 - 青龙面板模式".center(56))
    print("=" * 60)

    # 1. 加载环境变量
    load_env_file()

    # 2. 检查依赖
    if not check_dependencies():
        sys.exit(1)

    # 3. 确保目录存在
    ensure_directories()

    # 4. 导入并运行主程序
    try:
        # 切换工作目录到脚本目录
        os.chdir(SCRIPT_DIR)

        from src.main import GoldMonitor

        print("\n" + "-" * 60)
        print("开始执行监控任务...".center(56))
        print("-" * 60 + "\n")

        # 创建监控器并执行单次检查
        monitor = GoldMonitor()
        monitor.run_once()

        print("\n" + "-" * 60)
        print("任务执行完成".center(56))
        print("-" * 60)

    except Exception as e:
        print(f"\n❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
