# 用户信息节点 - 从 Golang Server 获取用户画像
import httpx
import logging
from typing import Dict, Any
from app.modules.workflow.core.state import WorkflowState
from app.core.config import settings

logger = logging.getLogger(__name__)


async def fetch_user_info_from_golang(access_token: str) -> Dict[str, Any]:
    """从 Golang Server 获取用户信息
    
    Args:
        access_token: 用户的访问令牌
        
    Returns:
        用户信息字典，包含 appUserId, age, gender, companyName 等字段
        
    Raises:
        Exception: Token 验证失败时抛出异常
    """
    if not access_token:
        raise ValueError("access_token 不能为空")
    
    # 构建验证 URL
    verify_url = f"{settings.GOLANG_API_BASE_URL}{settings.GOLANG_VERIFY_ENDPOINT}"
    
    logger.info(f"正在从 Golang Server 获取用户信息...")
    logger.info(f"验证 URL: {verify_url}")
    
    try:
        async with httpx.AsyncClient() as client:
            payload = {"token": access_token}
            
            # 发送 POST 请求
            response = await client.post(verify_url, json=payload, timeout=10.0)
            
            if response.status_code != 200:
                logger.error(f"Golang server 返回错误状态码: {response.status_code}")
                raise Exception(f"Token 验证失败，状态码: {response.status_code}")
            
            # 解析响应
            resp_data = response.json()
            logger.debug(f"Golang 响应数据: {resp_data}")
            
            # 检查响应码（兼容 code=0 或 code=200）
            code = resp_data.get("code")
            if code not in [0, 200]:
                logger.error(f"Token 验证失败: {resp_data}")
                raise Exception(f"Token 验证失败: {resp_data.get('msg', 'Unknown error')}")
            
            # 获取用户数据
            user_data = resp_data.get("data", {})
            
            # 检查 isValid 字段
            if not user_data.get("isValid", False):
                logger.error(f"Token 无效: {resp_data}")
                raise Exception(f"Token 无效或已过期: {resp_data.get('msg', 'Token invalid')}")
            
            logger.info(f"✅ 用户信息获取成功: 用户ID={user_data.get('appUserId')}")
            return user_data
            
    except httpx.RequestError as e:
        logger.error(f"连接 Golang server 失败: {str(e)}")
        raise Exception(f"无法连接到认证服务: {str(e)}")


def user_info_node(state: WorkflowState) -> Dict[str, Any]:
    """用户信息节点 - 同步版本（支持 session 缓存）
    
    职责：
    1. 优先从 session_id 获取缓存的用户信息（Redis）
    2. 如果没有缓存，使用 access_token 从 Golang Server 获取
    3. 提取用户画像字段（company, age, gender）
    4. 更新 state
    
    Args:
        state: 工作流状态
        
    Returns:
        更新后的状态字典
    """
    logger.info("========== 用户信息节点开始 ==========")
    
    import asyncio
    import nest_asyncio
    
    # 允许嵌套事件循环
    nest_asyncio.apply()
    
    try:
        # 优先尝试从 session_id 获取用户信息
        session_id = state.get("session_id")
        
        if session_id:
            logger.info(f"尝试从 session_id 获取用户信息: {session_id[:30]}...")
            
            # 从 Redis 获取会话信息（包含用户画像）
            from app.core.session_token import get_session
            
            # 判断是否已在事件循环中
            try:
                loop = asyncio.get_running_loop()
                # 已在运行事件循环中，创建任务并等待
                task = loop.create_task(get_session(session_id))
                session_data = loop.run_until_complete(task)
            except RuntimeError:
                # 没有运行的事件循环
                session_data = asyncio.run(get_session(session_id))
            
            logger.info(f"🔍 Redis Session 完整数据: {session_data}")
            
            if session_data:
                # 从会话中提取用户画像
                user_id = session_data.get("user_id", "unknown")
                company = session_data.get("company", "未知")
                age = session_data.get("age", "未知")
                gender = session_data.get("gender", "未知")
                
                if user_id != "unknown":
                    logger.info(f"✅ 从 session 缓存获取用户画像成功: ID={user_id}, 公司={company}")
                    return {
                        "user_id": str(user_id),
                        "company": company,
                        "age": str(age),
                        "gender": gender
                    }
                else:
                    logger.warning("Session 中没有完整的用户信息，尝试使用 access_token")
        
        # 如果没有 session 或 session 中没有用户信息，使用 access_token
        access_token = state.get("access_token")
        
        if not access_token:
            logger.warning("access_token 和有效 session 都不存在，使用默认用户画像")
            return {
                "company": "未知",
                "age": "未知",
                "gender": "未知",
                "user_id": "unknown"
            }
        
        logger.info(f"使用 access_token 获取用户信息 (Token 前10位: {access_token[:10]}...)")
        
        # 调用 Golang Server
        try:
            loop = asyncio.get_running_loop()
            task = loop.create_task(fetch_user_info_from_golang(access_token))
            user_data = loop.run_until_complete(task)
        except RuntimeError:
            user_data = asyncio.run(fetch_user_info_from_golang(access_token))
        
        # 提取用户画像字段
        user_id = str(user_data.get("appUserId", "unknown"))
        company = user_data.get("companyName", "未知")
        age = str(user_data.get("age", "未知"))
        gender = user_data.get("gender", "未知")
        
        logger.info(f"✅ 从 Golang Server 获取用户画像成功: ID={user_id}, 公司={company}, 年龄={age}, 性别={gender}")
        
        # 如果有 session_id，更新 session 中的用户信息
        if session_id:
            from app.core.session_token import update_session
            try:
                loop = asyncio.get_running_loop()
                task = loop.create_task(update_session(session_id, {
                    "user_id": user_id,
                    "company": company,
                    "age": age,
                    "gender": gender
                }))
                loop.run_until_complete(task)
            except RuntimeError:
                asyncio.run(update_session(session_id, {
                    "user_id": user_id,
                    "company": company,
                    "age": age,
                    "gender": gender
                }))
            logger.info(f"✅ 已将用户信息缓存到 session: {session_id[:30]}...")
        
        # 返回更新的状态
        return {
            "user_id": user_id,
            "company": company,
            "age": age,
            "gender": gender
        }
        
    except Exception as e:
        error_msg = f"用户信息节点执行失败: {str(e)}"
        logger.error(error_msg)
        # 返回默认值，不中断工作流
        return {
            "company": "未知",
            "age": "未知",
            "gender": "未知",
            "user_id": "unknown",
            "error": error_msg
        }


async def async_user_info_node(state: WorkflowState) -> Dict[str, Any]:
    """用户信息节点 - 异步版本（推荐在 LangGraph 中使用）
    
    职责：
    1. 优先从 session_id 获取缓存的用户信息（Redis）
    2. 如果没有缓存，使用 access_token 从 Golang Server 获取
    3. 提取用户画像字段（company, age, gender）
    4. 更新 state
    
    Args:
        state: 工作流状态
        
    Returns:
        更新后的状态字典
    """
    logger.info("========== 用户信息节点开始 ==========")
    
    try:
        # 优先尝试从 session_id 获取用户信息
        session_id = state.get("session_id")
        
        if session_id:
            logger.info(f"尝试从 session_id 获取用户信息: {session_id}")
            
            # 从 Redis 获取会话信息（包含用户画像）
            from app.core.session_token import get_session
            session_data = await get_session(session_id)
            
            logger.info(f"🔍 Redis Session 完整数据: {session_data}")
            
            if session_data:
                # 从会话中提取用户画像
                user_id = session_data.get("user_id", "unknown")
                company = session_data.get("company", "未知")
                age = session_data.get("age", "未知")
                gender = session_data.get("gender", "未知")
                
                if user_id != "unknown":
                    logger.info(f"✅ 从 session 缓存获取用户画像成功: ID={user_id}, 公司={company}")
                    return {
                        "user_id": str(user_id),
                        "company": company,
                        "age": str(age),
                        "gender": gender
                    }
                else:
                    logger.warning("Session 中没有完整的用户信息，尝试使用 access_token")
        
        # 如果没有 session 或 session 中没有用户信息，使用 access_token
        access_token = state.get("access_token")
        
        if not access_token:
            logger.warning("access_token 和有效 session 都不存在，使用默认用户画像")
            return {
                "company": "未知",
                "age": "未知",
                "gender": "未知",
                "user_id": "unknown"
            }
        
        logger.info(f"使用 access_token 获取用户信息 (Token 前10位: {access_token[:10]}...)")
        
        # 异步调用 Golang Server
        user_data = await fetch_user_info_from_golang(access_token)
        
        # 提取用户画像字段
        user_id = str(user_data.get("appUserId", "unknown"))
        company = user_data.get("companyName", "未知")
        age = str(user_data.get("age", "未知"))
        gender = user_data.get("gender", "未知")
        
        logger.info(f"✅ 从 Golang Server 获取用户画像成功: ID={user_id}, 公司={company}, 年龄={age}, 性别={gender}")
        
        # 如果有 session_id，更新 session 中的用户信息
        if session_id:
            from app.core.session_token import update_session
            await update_session(session_id, {
                "user_id": user_id,
                "company": company,
                "age": age,
                "gender": gender
            })
            logger.info(f"✅ 已将用户信息缓存到 session: {session_id}")
        
        # 返回更新的状态
        return {
            "user_id": user_id,
            "company": company,
            "age": age,
            "gender": gender
        }
        
    except Exception as e:
        error_msg = f"用户信息节点执行失败: {str(e)}"
        logger.error(error_msg)
        # 返回默认值，不中断工作流
        return {
            "company": "未知",
            "age": "未知",
            "gender": "未知",
            "user_id": "unknown",
            "error": error_msg
        }
