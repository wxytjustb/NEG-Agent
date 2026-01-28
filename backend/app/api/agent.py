# 智能体接口 - Agent API
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from app.schemas.agent_schema import WorkflowChatRequest, HistoryResponse
from app.modules.workflow.workflows.workflow import run_chat_workflow_streaming
from app.modules.chromadb.core.chromadb_core import chromadb_core
from app.core.security import get_current_user, get_current_session
from app.core.session_token import create_or_get_session
from app.core.config import settings
from pydantic import BaseModel
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agent", tags=["Agent"])


@router.post("/init", summary="初始化会话")
async def init_session(user: dict = Depends(get_current_user), access_token: str = Query(..., description="Access Token")):
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
        # 将 access_token 添加到 user_data 中
        user['access_token'] = access_token
        
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
        access_token = user.get("access_token")  # 新增：获取 access_token
        
        # 调试日志
        logger.info(f"[Debug] user keys: {user.keys()}")
        logger.info(f"[Debug] access_token exists: {bool(access_token)}")
        if access_token:
            logger.info(f"[Debug] access_token length: {len(access_token)}")
        
        if not user_id or not session_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无法获取用户ID")
        
        if not access_token:
            logger.warning("⚠️ Session 中没有 access_token，MySQL 保存可能失败")
        
        async def sse_generator():
            try:
                async for content in run_chat_workflow_streaming(
                    user_input=request.user_input,
                    conversation_id=request.conversation_id,  # 传入 conversation_id
                    session_id=session_id,
                    user_id=user_id,
                    username=user.get("username"),
                    access_token=access_token,  # 新增：传递 access_token
                    user_confirmed_ticket=request.user_confirmed_ticket  # 传递用户确认状态
                ):
                    # SSE 格式：data: 内容\n\n
                    yield f"data: {content}\n\n"
                
                # 发送完成信号
                yield "data: [DONE]\n\n"
                
            except Exception as e:
                logger.error(f"Workflow 流式错误: {str(e)}", exc_info=True)
                yield f"data: [ERROR] {str(e)}\n\n"
        
        headers = {
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
        return StreamingResponse(sse_generator(), media_type="text/event-stream", headers=headers)
        
    except Exception as e:
        logger.error(f"Workflow 失败: {str(e)}", exc_info=True)
        async def error_generator():
            yield f"data: [ERROR] {str(e)}\n\n"
        return StreamingResponse(error_generator(), media_type="text/event-stream")