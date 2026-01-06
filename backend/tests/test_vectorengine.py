"""测试向量引擎连接"""
import sys
import os
from pathlib import Path

# 添加 backend 目录到 Python 路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# 加载环境变量
from dotenv import load_dotenv
env_path = backend_dir / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"✅ 已加载环境变量: {env_path}")
else:
    print(f"⚠️ .env 文件不存在: {env_path}")

from app.initialize.vectorengine import test_connection
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """运行测试"""
    logger.info("\n" + "=" * 80)
    logger.info("向量引擎连接测试")
    logger.info("=" * 80)
    
    result = test_connection()
    
    logger.info("\n" + "=" * 80)
    if result:
        logger.info("🎉 测试通过！向量引擎工作正常")
    else:
        logger.error("⚠️ 测试失败，请检查配置和日志")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
