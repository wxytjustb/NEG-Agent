# Session Token 管理模块
import uuid
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from app.initialize import redis
from app.core.config import settings

logger = logging.getLogger(__name__)


def generate_session_token() -> str:
    """
    生成唯一的会话 Token
    格式: sess_<uuid>_<timestamp>
    """
    timestamp = int(datetime.now().timestamp())
    unique_id = uuid.uuid4().hex
    return f"sess_{unique_id}_{timestamp}"


async def create_session(user_data: Dict[str, Any]) -> str:
    """
    创建会话并存储到 Redis
    
    Args:
        user_data: 用户信息字典 (来自 Golang Server 验证结果)
    
    Returns:
        session_token: 生成的会话 Token
    """
    session_token = generate_session_token()
    cache_key = f"{settings.SESSION_REDIS_PREFIX}{session_token}"
    
    # 会话数据包含用户信息和元数据
    session_data = {
        "user": user_data,
        "created_at": datetime.now().isoformat(),
        "last_activity": datetime.now().isoformat(),
    }
    
    try:
        # 存储到 Redis,设置过期时间
        await redis.redis_client.set(
            cache_key,
            json.dumps(session_data),
            ex=settings.SESSION_TOKEN_EXPIRE_MINUTES * 60
        )
        logger.info(f"Session created: {session_token[:20]}... for user {user_data.get('id', 'unknown')}")
        return session_token
    except Exception as e:
        logger.error(f"Failed to create session in Redis: {e}")
        raise


async def get_session(session_token: str) -> Optional[Dict[str, Any]]:
    """
    从 Redis 获取会话信息
    
    Args:
        session_token: 会话 Token
    
    Returns:
        session_data: 会话数据字典,如果不存在则返回 None
    """
    cache_key = f"{settings.SESSION_REDIS_PREFIX}{session_token}"
    
    try:
        cached_data = await redis.redis_client.get(cache_key)
        if cached_data:
            session_data = json.loads(cached_data)
            logger.info(f"Session retrieved from cache: {session_token[:20]}...")
            return session_data
        else:
            logger.warning(f"Session not found or expired: {session_token[:20]}...")
            return None
    except Exception as e:
        logger.error(f"Failed to get session from Redis: {e}")
        return None


async def refresh_session(session_token: str) -> bool:
    """
    刷新会话过期时间并更新最后活动时间
    
    Args:
        session_token: 会话 Token
    
    Returns:
        bool: 刷新成功返回 True,失败返回 False
    """
    cache_key = f"{settings.SESSION_REDIS_PREFIX}{session_token}"
    
    try:
        # 获取当前会话数据
        session_data = await get_session(session_token)
        if not session_data:
            return False
        
        # 更新最后活动时间
        session_data["last_activity"] = datetime.now().isoformat()
        
        # 重新设置到 Redis 并刷新过期时间
        await redis.redis_client.set(
            cache_key,
            json.dumps(session_data),
            ex=settings.SESSION_TOKEN_EXPIRE_MINUTES * 60
        )
        logger.info(f"Session refreshed: {session_token[:20]}...")
        return True
    except Exception as e:
        logger.error(f"Failed to refresh session: {e}")
        return False


async def delete_session(session_token: str) -> bool:
    """
    删除会话 (用于登出等场景)
    
    Args:
        session_token: 会话 Token
    
    Returns:
        bool: 删除成功返回 True,失败返回 False
    """
    cache_key = f"{settings.SESSION_REDIS_PREFIX}{session_token}"
    
    try:
        result = await redis.redis_client.delete(cache_key)
        if result:
            logger.info(f"Session deleted: {session_token[:20]}...")
            return True
        else:
            logger.warning(f"Session not found for deletion: {session_token[:20]}...")
            return False
    except Exception as e:
        logger.error(f"Failed to delete session: {e}")
        return False


async def get_session_by_user_id(user_id: str) -> Optional[str]:
    """
    根据用户 ID 查找现有的会话 Token
    
    Args:
        user_id: 用户 ID
    
    Returns:
        session_token: 如果找到则返回会话 Token,否则返回 None
    """
    user_session_key = f"{settings.USER_SESSION_PREFIX}{user_id}"
    
    try:
        session_token = await redis.redis_client.get(user_session_key)
        if session_token:
            # 验证 session 是否仍然有效
            session_data = await get_session(session_token.decode('utf-8') if isinstance(session_token, bytes) else session_token)
            if session_data:
                logger.info(f"Found existing session for user {user_id}: {session_token[:20] if isinstance(session_token, str) else session_token.decode('utf-8')[:20]}...")
                return session_token.decode('utf-8') if isinstance(session_token, bytes) else session_token
            else:
                # Session 已过期,清除映射
                await redis.redis_client.delete(user_session_key)
                logger.info(f"Expired session mapping cleared for user {user_id}")
        return None
    except Exception as e:
        logger.error(f"Failed to get session by user_id: {e}")
        return None


async def create_or_get_session(user_data: Dict[str, Any]) -> str:
    """
    创建或获取用户的会话 Token
    如果用户已有活跃会话,则返回现有的 session_token
    否则创建新的会话
    
    Args:
        user_data: 用户信息字典 (来自 Golang Server 验证结果)
    
    Returns:
        session_token: 会话 Token (现有的或新创建的)
    """
    # 从 Golang 返回的数据中提取用户 ID (字段名为 appUserId)
    user_id = str(user_data.get('appUserId', user_data.get('id', user_data.get('user_id', ''))))
    
    if not user_id or user_id == '0':
        logger.warning(f"User data missing valid 'appUserId' field: {user_data}, creating new session without user mapping")
        return await create_session(user_data)
    
    # 检查是否已有活跃会话
    existing_session = await get_session_by_user_id(user_id)
    if existing_session:
        logger.info(f"Reusing existing session for user {user_id}")
        # 刷新会话过期时间
        await refresh_session(existing_session)
        return existing_session
    
    # 创建新会话
    session_token = generate_session_token()
    cache_key = f"{settings.SESSION_REDIS_PREFIX}{session_token}"
    user_session_key = f"{settings.USER_SESSION_PREFIX}{user_id}"
    
    # 会话数据包含用户信息和元数据
    session_data = {
        "user": user_data,
        "created_at": datetime.now().isoformat(),
        "last_activity": datetime.now().isoformat(),
    }
    
    try:
        # 使用 pipeline 原子性地创建两个映射
        pipe = redis.redis_client.pipeline()
        
        # 1. 存储会话数据
        pipe.set(
            cache_key,
            json.dumps(session_data),
            ex=settings.SESSION_TOKEN_EXPIRE_MINUTES * 60
        )
        
        # 2. 存储用户到会话的映射
        pipe.set(
            user_session_key,
            session_token,
            ex=settings.SESSION_TOKEN_EXPIRE_MINUTES * 60
        )
        
        await pipe.execute()
        logger.info(f"New session created: {session_token[:20]}... for user {user_id}")
        return session_token
    except Exception as e:
        logger.error(f"Failed to create session in Redis: {e}")
        raise
