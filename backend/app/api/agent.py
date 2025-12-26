# 智能体接口 - Agent API
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from app.schemas.agent_schema import WorkflowChatRequest
from app.modules.workflow.workflows.workflow import run_chat_workflow_streaming
from app.modules.chromadb.core.chromadb_core import chromadb_core
from app.core.security import get_current_user, get_current_session
from app.core.session_token import create_or_get_session
from pydantic import BaseModel
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agent", tags=["Agent"])


@router.post("/init", summary="初始化会话")
async def init_session(user: dict = Depends(get_current_user)):
    """
    初始化 Agent 会话
    
    使用用户的 access_token (来自 Golang Server) 验证身份后,
    生成新的 session_token 用于后续对话。
    
    参数:
    - access_token: 用户认证 Token (通过 Query 或 Header 传递)
    
    返回:
    - session_token: 会话 Token
    - user: 用户信息
    - expires_in: 会话过期时间 (秒)
    """
    try:
        # 创建或获取会话 (如果用户已有活跃会话则复用)
        from app.core.config import settings
        session_token = await create_or_get_session(user)
        
        logger.info(f"Session initialized for user {user.get('id', 'unknown')}")
        
        return {
            "code": 200,
            "msg": "Session initialized successfully",
            "data": {
                "session_token": session_token,
                "user": user,
                "expires_in": settings.SESSION_TOKEN_EXPIRE_MINUTES * 60
            }
        }
    except Exception as e:
        logger.error(f"Failed to initialize session: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialize session"
        )


@router.post("/chat", summary="Workflow 对话接口（基于 LangGraph - 流式）")
async def chat_with_workflow(request: WorkflowChatRequest, user: dict = Depends(get_current_session)):
    """
    流式对话 - 返回 JSON流式数据
    
    响应格式：每个 token 都是一个独立的 JSON 对象
    {"type": "token", "content": "你", "session_id": "xxx"}
    {"type": "token", "content": "好", "session_id": "xxx"}
    {"type": "done", "session_id": "xxx"}
    """
    try:
        user_id = user.get("user_id")
        session_id = user.get("session_token")
        
        if not user_id or not session_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无法获取用户ID")
        
        async def json_stream_generator():
            import json
            try:
                async for content in run_chat_workflow_streaming(
                    user_input=request.user_input,
                    session_id=session_id,
                    user_id=user_id,
                    username=user.get("username")
                ):
                    # 每个 token 包装为 JSON
                    chunk = json.dumps({
                        "type": "token",
                        "content": content,
                        "session_id": session_id
                    }, ensure_ascii=False)
                    yield f"{chunk}\n"
                
                # 发送完成信号
                done_chunk = json.dumps({
                    "type": "done",
                    "session_id": session_id
                }, ensure_ascii=False)
                yield f"{done_chunk}\n"
                
            except Exception as e:
                logger.error(f"Workflow 流式错误: {str(e)}", exc_info=True)
                error_chunk = json.dumps({
                    "type": "error",
                    "message": str(e),
                    "session_id": session_id
                }, ensure_ascii=False)
                yield f"{error_chunk}\n"
        
        headers = {
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
        return StreamingResponse(json_stream_generator(), media_type="application/x-ndjson", headers=headers)
        
    except Exception as e:
        logger.error(f"Workflow 失败: {str(e)}", exc_info=True)
        async def error_generator():
            import json
            error_chunk = json.dumps({
                "type": "error",
                "message": str(e)
            }, ensure_ascii=False)
            yield f"{error_chunk}\n"
        return StreamingResponse(error_generator(), media_type="application/x-ndjson")


class HistoryResponse(BaseModel):
    """历史对话响应模型"""
    user_id: str
    session_id: str
    total_count: int
    messages: List[dict]


@router.get("/history/{session_id}", response_model=HistoryResponse, summary="获取指定会话的所有历史对话")
async def get_session_history(
    session_id: str,
    limit: Optional[int] = None,
    user: dict = Depends(get_current_session)
):
    """
    获取指定会话的所有历史对话记录
    
    Args:
        session_id: 会话ID
        limit: 限制返回数量（可选，不传则返回全部）
        user: 当前登录用户信息（自动注入）
    
    Returns:
        HistoryResponse: 包含所有历史消息的响应
            - user_id: 用户ID
            - session_id: 会话ID
            - total_count: 消息总数
            - messages: 消息列表，每条消息包含：
                - id: 消息ID
                - role: 角色（user/assistant）
                - content: 消息内容
                - timestamp: 时间戳
    
    Example:
        GET /api/agent/history/abc123?limit=10
    """
    try:
        user_id = user.get("user_id")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无法获取用户ID"
            )
        
        # 从 ChromaDB 获取历史消息
        messages = chromadb_core.get_all_messages(
            user_id=str(user_id),
            session_id=session_id,
            limit=limit
        )
        
        logger.info(f"✅ 获取历史对话成功: user_id={user_id}, session_id={session_id[:20]}..., count={len(messages)}")
        
        return HistoryResponse(
            user_id=str(user_id),
            session_id=session_id,
            total_count=len(messages),
            messages=messages
        )
        
    except Exception as e:
        logger.error(f"❌ 获取历史对话失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取历史对话失败: {str(e)}"
        )
