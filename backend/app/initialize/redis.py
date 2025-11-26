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
        logger.info(f"尝试连接 Redis: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
        redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
            decode_responses=True
        )
        # Ping 测试
        await redis_client.ping()
        logger.info(f"✅ Redis connected: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
    except Exception as e:
        logger.error(f"❌ Redis connection failed: {e}")
        logger.error(f"Redis 配置: host={settings.REDIS_HOST}, port={settings.REDIS_PORT}, db={settings.REDIS_DB}")
        redis_client = None
        # 如果 Redis 连接失败，可以选择抛出异常阻止启动，或者仅记录日志（降级处理）
        # 这里仅记录日志，后续 verify_token 会 fallback 到 upstream
        
async def close_redis():
    """关闭 Redis 连接"""
    global redis_client
    if redis_client:
        await redis_client.close()
        logger.info("Redis connection closed")
