# Token 鉴权
import httpx
import logging
import json
import redis.asyncio as redis
from fastapi import HTTPException, status, Security, Query, Depends
from fastapi.security import APIKeyHeader
from app.core.config import settings
from app.initialize import redis

logger = logging.getLogger(__name__)

# 定义 API Key Header Scheme (可选支持 Header 传参)
api_key_header = APIKeyHeader(name="Authorization", auto_error=False)

async def verify_token_with_go_server(token: str) -> dict:
    """
    向 Golang Server 验证 Token (仅用于会话初始化)
    注意: 此函数不再缓存结果,缓存由 session_token 模块管理
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing access token",
        )

    # 请求 Golang Server 验证
    verify_url = f"{settings.GOLANG_API_BASE_URL}{settings.GOLANG_VERIFY_ENDPOINT}"
    
    try:
        async with httpx.AsyncClient() as client:
            payload = {"token": token}
            logger.info(f"Verifying token with Golang server: {verify_url}")
            
            response = await client.post(verify_url, json=payload, timeout=10.0)
            
            if response.status_code != 200:
                logger.error(f"Golang server returned status {response.status_code}: {response.text}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token verification failed on upstream server",
                )
            
            resp_data = response.json()
            # 兼容 code=0 或 code=200 为成功
            code = resp_data.get("code")
            if code != 200 and code != 0:
                 logger.warning(f"Token verification failed: {resp_data}")
                 raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=resp_data.get("msg", "Invalid token"),
                )
            
            user_data = resp_data.get("data", {})
            
            # 检查 isValid 字段
            is_valid = user_data.get("isValid", False)
            if not is_valid:
                logger.warning(f"Token is invalid: {resp_data}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=resp_data.get("msg", "Token无效或已过期"),
                )
            
            logger.info(f"Token verification successful. User ID: {user_data.get('appUserId', 'unknown')}")
            return user_data

    except httpx.RequestError as e:
        logger.error(f"Failed to connect to Golang server: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        )


async def get_current_session(
    session_token: str = Query(None, description="Session Token via Query Param"),
    header_token: str = Security(api_key_header)
) -> dict:
    """
    获取当前会话依赖 (用于已初始化的会话)
    优先使用 Query Param (session_token=xxx),其次使用 Header (Authorization: xxx)
    """
    from app.core.session_token import get_session, refresh_session
    
    token = session_token
    
    # 如果 Query Param 没有,尝试从 Header 获取
    if not token and header_token:
        # 处理 Bearer 前缀
        if header_token.startswith("Bearer "):
            token = header_token.split(" ")[1]
        else:
            token = header_token
            
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated - session token required",
        )
    
    # 从 Redis 获取会话信息
    session_data = await get_session(token)
    if not session_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )
    
    # 刷新会话过期时间
    await refresh_session(token)
    
    # 返回用户信息
    return session_data.get("user", {})


async def get_current_user(
    access_token: str = Query(None, description="Access Token via Query Param"),
    header_token: str = Security(api_key_header)
):
    """
    获取当前用户依赖 (用于会话初始化)
    优先使用 Query Param (access_token=xxx),其次使用 Header (Authorization: xxx)
    
    注意: 此函数仅用于 /api/agent/init 接口,其他接口应使用 get_current_session
    """
    token = access_token
    
    # 如果 Query Param 没有,尝试从 Header 获取
    if not token and header_token:
        # 处理 Bearer 前缀
        if header_token.startswith("Bearer "):
            token = header_token.split(" ")[1]
        else:
            token = header_token
            
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
        
    user_info = await verify_token_with_go_server(token)
    return user_info

