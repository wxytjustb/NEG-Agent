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
    
    # 提取关键用户信息（轻量化）
    user_id = user_data.get('appUserId') or user_data.get('ID') or user_data.get('id') or user_data.get('username', 'unknown')
    
    # 会话数据只存储必要信息
    session_data = {
        "user_id": str(user_id),
        "username": user_data.get('username', ''),
        "created_at": datetime.now().isoformat(),
        "last_activity": datetime.now().isoformat(),
        # 添加用户画像字段（从 Golang Server 返回的数据中提取）
        "company": user_data.get('companyName', '未知'),
        "age": str(user_data.get('age', '未知')),
        "gender": user_data.get('gender', '未知'),
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
            logger.info(f"Session retrieved from Redis: {session_token[:20]}...")
            return session_data
        else:
            # Session 不存在或已过期
            # 注意：无法在此处清除 user_session 映射，因为我们无法从过期的 session 中获取 user_id
            # user_session 映射会在下次用户初始化时由 get_session_by_user_id 清除
            logger.warning(f"Session not found or expired in Redis: {session_token[:20]}... (可能是 Redis 过期或已删除)")
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


async def get_or_create_session(user_data: Dict[str, Any]) -> str:
    """
    创建用户会话（简化版，不再维护 user_id 映射）
    
    逻辑:
    每次调用都创建新的 session_token
    如果需要复用 session，应该由前端存储 session_token 并传递
    
    Args:
        user_data: 用户信息字典
    
    Returns:
        session_token: 会话 Token
    """
    if not redis.redis_client:
        logger.warning("Redis 客户端未初始化，无法创建 session")
        # 降级方案：生成临时 token（不存储）
        return generate_session_token()
    
    try:
        # 直接创建新的 session
        new_session_token = await create_session(user_data)
        
        user_id = user_data.get('appUserId') or user_data.get('ID') or user_data.get('id') or user_data.get('username', 'unknown')
        logger.info(f"✅ 创建新 session: user_id={user_id}, token={new_session_token[:20]}...")
        return new_session_token
        
    except Exception as e:
        logger.error(f"❌ 创建 session 失败: {str(e)}", exc_info=True)
        # 降级方案：生成临时 token
        return generate_session_token()


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


async def update_session(session_token: str, update_data: Dict[str, Any]) -> bool:
    """
    更新会话信息（合并新数据）
    
    Args:
        session_token: 会话 Token
        update_data: 要更新的数据字典
    
    Returns:
        bool: 更新成功返回 True,失败返回 False
    """
    cache_key = f"{settings.SESSION_REDIS_PREFIX}{session_token}"
    
    try:
        # 获取当前会话数据
        session_data = await get_session(session_token)
        if not session_data:
            logger.warning(f"Cannot update non-existent session: {session_token[:20]}...")
            return False
        
        # 合并新数据
        session_data.update(update_data)
        
        # 更新最后活动时间
        session_data["last_activity"] = datetime.now().isoformat()
        
        # 重新设置到 Redis 并刷新过期时间
        await redis.redis_client.set(
            cache_key,
            json.dumps(session_data),
            ex=settings.SESSION_TOKEN_EXPIRE_MINUTES * 60
        )
        logger.info(f"Session updated: {session_token[:20]}... with data: {list(update_data.keys())}")
        return True
    except Exception as e:
        logger.error(f"Failed to update session: {e}")
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
        
        # 获取现有 session 的数据
        session_data = await get_session(existing_session)
        
        # 检查是否需要更新用户画像（如果旧 session 没有画像字段）
        needs_update = False
        if session_data:
            if not session_data.get('company') or session_data.get('company') == '未知':
                needs_update = True
                logger.info(f"⚠️ 旧 Session 缺少用户画像，将更新: user_id={user_id}")
        
        # 如果需要更新，添加用户画像字段
        if needs_update:
            await update_session(existing_session, {
                "company": user_data.get('companyName', '未知'),
                "age": str(user_data.get('age', '未知')),
                "gender": user_data.get('gender', '未知'),
            })
            logger.info(f"✅ 已更新 Session 的用户画像: company={user_data.get('companyName')}, age={user_data.get('age')}, gender={user_data.get('gender')}")
        
        # 刷新会话过期时间
        await refresh_session(existing_session)
        return existing_session
    
    # 创建新会话
    session_token = generate_session_token()
    cache_key = f"{settings.SESSION_REDIS_PREFIX}{session_token}"
    user_session_key = f"{settings.USER_SESSION_PREFIX}{user_id}"
    
    # 会话数据（轻量化格式，只存储必要信息）
    session_data = {
        "user_id": user_id,
        "username": user_data.get('username', ''),
        "created_at": datetime.now().isoformat(),
        "last_activity": datetime.now().isoformat(),
        # 添加用户画像字段（从 Golang Server 返回的数据中提取）
        "company": user_data.get('companyName', '未知'),
        "age": str(user_data.get('age', '未知')),
        "gender": user_data.get('gender', '未知'),
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
