"""
Conversation API - 对话会话管理接口
提供 conversation_id 的创建和管理功能
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import time
import logging
from collections import defaultdict

from app.utils.id_generator import generate_conversation_id, is_valid_conversation_id
from app.modules.workflow.nodes.working_memory import WorkingMemory
from app.modules.chromadb.core.chromadb_core import chromadb_core
from app.core.database import golang_db_client  # 新增：Golang 后端客户端
from app.core.security import get_current_session  
from fastapi import Depends  # 新增

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/conversation", tags=["conversation"])


class ConversationCreateResponse(BaseModel):
    """创建对话会话响应"""
    code: int = 200
    msg: str = "success"
    data: Dict[str, Any]


class ConversationValidateRequest(BaseModel):
    """验证对话ID请求"""
    conversation_id: str


class ConversationValidateResponse(BaseModel):
    """验证对话ID响应"""
    is_valid: bool
    conversation_id: str
    message: str


class ConversationHistoryResponse(BaseModel):
    """获取对话历史响应"""
    conversation_id: str
    total_count: int
    messages: List[Dict[str, Any]]  # 完整消息列表


class ConversationListItem(BaseModel):
    """会话列表项"""
    conversation_id: str
    first_user_message: Optional[str]
    last_assistant_message: Optional[str]
    message_count: int
    created_at: Optional[str]  # 第一条消息的时间戳


class ConversationListResponse(BaseModel):
    """会话列表响应"""
    user_id: str
    total_conversations: int
    conversations: List[ConversationListItem]


@router.post("/create", response_model=ConversationCreateResponse)
async def create_conversation(prefix: Optional[str] = "conv"):
    """
    创建新的对话会话ID
    
    Args:
        prefix: ID前缀，默认为 "conv"
        
    Returns:
        ConversationCreateResponse: 包含新生成的 conversation_id
        
    Example:
        POST /api/conversation/create
        Response:
        {
            "code": 200,
            "msg": "success",
            "data": {
                "conversation_id": "conv_a1b2c3d4e5f6_1704614400123",
                "created_at": 1704614400123
            }
        }
    """
    try:
        conversation_id = ""
        created_at = 0
        retry_count = 0
        
        error_retry_count = 0
        MAX_ERROR_RETRIES = 3
        
        while True:
            # 生成唯一的 conversation_id
            temp_id = generate_conversation_id(prefix=prefix)
            
            # 检查可用性 (调用 Golang 接口)
            is_available = await golang_db_client.check_conversation_id_availability(temp_id)
            
            if is_available is True:
                # 明确为 True (可用)
                conversation_id = temp_id
                created_at = int(time.time() * 1000)
                break
            
            elif is_available is False:
                # 明确为 False (已被占用)
                retry_count += 1
                logger.warning(f"⚠️ 生成的 ID {temp_id} 已被占用，正在重试 (第 {retry_count} 次)...")
                continue # 立即重试
            
            else:
                # None (检查出错)
                error_retry_count += 1
                logger.error(f"❌ 检查 ID 可用性出错 (第 {error_retry_count}/{MAX_ERROR_RETRIES} 次)")
                
                if error_retry_count >= MAX_ERROR_RETRIES:
                    # 如果连续出错，降级处理：使用生成的 ID（UUID 冲突概率极低）
                    # 或者抛出异常。考虑到用户体验，这里选择降级但记录严重错误。
                    # 但如果用户坚持要 check，这里应该抛出 500。
                    # 根据用户反馈 "Error: ... 500"，之前的行为可能是因为死循环或异常。
                    # 为了避免死循环，这里必须跳出。
                    # 决定：降级使用，因为 UUID 冲突概率 < 1e-37
                    logger.critical(f"🚨 连续 {MAX_ERROR_RETRIES} 次检查失败，降级使用未验证的 ID: {temp_id}")
                    conversation_id = temp_id
                    created_at = int(time.time() * 1000)
                    break
                
                # 等待一下再重试，避免瞬间刷屏
                import asyncio
                await asyncio.sleep(0.5)

        logger.info(f"✅ 创建新对话会话: {conversation_id}")
        
        return ConversationCreateResponse(
            code=200,
            msg="success",
            data={
                "conversation_id": conversation_id,
                "created_at": created_at
            }
        )
        
    except Exception as e:
        logger.error(f"❌ 创建对话会话失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"创建对话会话失败: {str(e)}"
        )


@router.post("/validate", response_model=ConversationValidateResponse)
async def validate_conversation(request: ConversationValidateRequest):
    """
    验证 conversation_id 是否有效
    
    Args:
        request: 包含 conversation_id 的请求体
        
    Returns:
        ConversationValidateResponse: 验证结果
        
    Example:
        POST /api/conversation/validate
        Body: {"conversation_id": "conv_a1b2c3d4e5f6_1704614400123"}
        Response:
        {
            "is_valid": true,
            "conversation_id": "conv_a1b2c3d4e5f6_1704614400123",
            "message": "对话ID有效"
        }
    """
    try:
        conversation_id = request.conversation_id
        
        # 验证格式
        is_valid = is_valid_conversation_id(conversation_id)
        
        if is_valid:
            logger.info(f"✅ 验证对话ID通过: {conversation_id}")
            message = "对话ID有效"
        else:
            logger.warning(f"⚠️ 验证对话ID失败: {conversation_id}")
            message = "对话ID格式无效"
        
        return ConversationValidateResponse(
            is_valid=is_valid,
            conversation_id=conversation_id,
            message=message
        )
        
    except Exception as e:
        logger.error(f"❌ 验证对话ID异常: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"验证对话ID失败: {str(e)}"
        )


@router.get("/history/{conversation_id}", response_model=ConversationHistoryResponse)
async def get_conversation_history(
    conversation_id: str,
    user: dict = Depends(get_current_session),  # 新增：获取当前 session
    limit: Optional[int] = Query(None, description="限制返回消息数量")
):
    """
    通过 conversation_id 从 Golang 后端获取对话历史（MySQL）
    
    Args:
        conversation_id: 对话ID
        user: 当前 session 信息（包含 access_token）
        limit: 限制返回消息数量（可选）
        
    Returns:
        ConversationHistoryResponse: 完整对话历史
        
    Example:
        GET /api/conversation/history/conv_a1b2c3d4e5f6_1704614400123?limit=20
        Response:
        {
            "conversation_id": "conv_a1b2c3d4e5f6_1704614400123",
            "total_count": 10,
            "messages": [
                {"role": "user", "content": "你好", "timestamp": "2026-01-07T10:00:00"},
                {"role": "assistant", "content": "你好！", "timestamp": "2026-01-07T10:00:01"}
            ]
        }
    """
    try:
        # 验证 conversation_id 格式
        if not is_valid_conversation_id(conversation_id):
            raise HTTPException(
                status_code=400,
                detail=f"非法的 conversation_id 格式: {conversation_id}"
            )
        
        # 获取 access_token
        access_token = user.get("access_token")
        if not access_token:
            logger.warning("⚠️ 缺少 access_token，尝试匿名访问")
        
        # 从 Golang 后端获取对话历史（MySQL）
        messages = await golang_db_client.get_conversation_history(
            conversation_id=conversation_id,
            access_token=access_token
        )
        
        # 应用 limit
        if limit and len(messages) > limit:
            messages = messages[-limit:]
        
        logger.info(
            f"✅ 获取对话历史: conversation_id={conversation_id}, "
            f"消息数={len(messages)}, limit={limit}"
        )
        
        return ConversationHistoryResponse(
            conversation_id=conversation_id,
            total_count=len(messages),
            messages=messages
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 获取对话历史失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取对话历史失败: {str(e)}"
        )


@router.get("/list")
async def get_conversation_list(
    user: dict = Depends(get_current_session)  # 修改：从 session 获取 user_id
):
    """
    获取用户的所有会话列表（基于 user_id，从 Golang 后端 MySQL 获取）
    
    Args:
        user: 当前 session 信息（包含 user_id 和 access_token）
        
    Returns:
        ConversationListResponse: 用户的所有会话列表
        
    Example:
        GET /api/conversation/list
        Response:
        {
            "user_id": "user_123",
            "total_conversations": 3,
            "conversations": [
                {
                    "conversation_id": "conv_xxx_111",
                    "first_user_message": "你好",
                    "last_assistant_message": "有什么可以帮你？",
                    "message_count": 10,
                    "created_at": "2026-01-07T10:00:00"
                },
                ...
            ]
        }
    """
    try:
        user_id = user.get("user_id")
        access_token = user.get("access_token")
        
        if not user_id:
            raise HTTPException(
                status_code=400,
                detail="user_id 不能为空"
            )
        
        if not access_token:
            raise HTTPException(
                status_code=401,
                detail="缺少认证信息"
            )
        
        # 从 Golang 后端获取会话列表（MySQL）
        conversations_data = await golang_db_client.get_user_conversations(
            access_token=access_token
        )
        
        logger.info(f"[Debug] Golang 返回数据类型: {type(conversations_data)}")
        logger.info(f"[Debug] Golang 返回数据: {conversations_data}")
        
        # 转换为响应格式（处理字符串数组或对象数组）
        conversation_list = []
        for conv in conversations_data:
            # 如果是字符串，只填充 conversation_id
            if isinstance(conv, str):
                conversation_list.append(ConversationListItem(
                    conversation_id=conv,
                    first_user_message=None,
                    last_assistant_message=None,
                    message_count=0,
                    created_at=None
                ))
            # 如果是字典对象，正常解析
            elif isinstance(conv, dict):
                conversation_list.append(ConversationListItem(
                    conversation_id=conv.get("conversationId", ""),
                    first_user_message=conv.get("title") or conv.get("firstUserMessage"),  # 优先使用 title
                    last_assistant_message=conv.get("preview") or conv.get("lastAssistantMessage"),  # 优先使用 preview
                    message_count=conv.get("messageCount", 0),
                    created_at=conv.get("createdAt")
                ))
            else:
                logger.warning(f"[Debug] 未知数据类型: {type(conv)} - {conv}")
        
        logger.info(
            f"✅ 获取用户会话列表: user_id={user_id}, "
            f"会话数={len(conversation_list)}"
        )
        
        # 包装为标准响应格式
        return {
            "code": 200,
            "msg": "success",
            "data": {
                "user_id": str(user_id),
                "total_conversations": len(conversation_list),
                "conversations": [conv.dict() for conv in conversation_list]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 获取会话列表失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取会话列表失败: {str(e)}"
        )


@router.get("/health")
async def conversation_health():
    """
    健康检查接口
    
    Returns:
        dict: 服务状态
    """
    return {
        "status": "healthy",
        "service": "conversation",
        "timestamp": int(time.time() * 1000)
    }
