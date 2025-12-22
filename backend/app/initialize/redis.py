import redis.asyncio as redis
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

# 初始化 Redis 连接
redis_client: redis.Redis = None

async def init_redis():
    """初始化 Redis 连接并检查连通性"""
    global redis_client
    try:
        redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
            decode_responses=True
        )
        # Ping 测试
        await redis_client.ping()
        logger.info(f"✅ Redis 启动成功")
    except Exception as e:
        logger.error(f"❌ Redis 连接失败: {e}")
        redis_client = None
        
async def close_redis():
    """关闭 Redis 连接"""
    global redis_client
    if redis_client:
        await redis_client.close()
        logger.info("Redis connection closed")
