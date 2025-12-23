# 大模型调用
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from app.schemas.agent_schema import WorkflowChatRequest
from app.modules.workflow.workflows.workflow import get_chat_workflow
from app.modules.workflow.core.state import WorkflowState
from app.core.security import get_current_session
import logging
import json

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agent", tags=["LLM"])


@router.post("/chat1", summary="Workflow 对话接口（基于 LangGraph - 流式）")
async def chat_with_workflow(request: WorkflowChatRequest, user: dict = Depends(get_current_session)):
    """流式对话 - 使用 LangGraph 的 astream_events 监听 LLM 流式输出"""
    try:
        user_id = user.get("user_id")
        session_id = user.get("session_token")
        
        if not user_id or not session_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无法获取用户ID")
        
        async def sse_generator():
            try:
                logger.info(f"开始 Workflow 流式对话: user_id={user_id}")
                logger.info(f"🔍 Session 数据: {user}")
                
                # 准备初始状态
                initial_state: WorkflowState = {
                    "user_input": request.user_input,
                    "session_id": session_id,
                    "history_text": request.history_text or "",
                    "long_term_memory": "",
                    "is_streaming": False,
                    "user_id": user_id
                }
                
                # 获取 workflow
                workflow = get_chat_workflow()
                
                # 使用 astream_events 监听 LLM 的流式输出
                async for event in workflow.astream_events(initial_state, version="v1"):
                    kind = event["event"]
                    
                    # 监听 LLM 的流式输出（on_chat_model_stream 事件）
                    if kind == "on_chat_model_stream":
                        content = event["data"]["chunk"].content
                        if content:
                            yield f"data: {content}\n\n"
                
                logger.info("Workflow 执行完成")
                yield "data: [DONE]\n\n"
                
            except Exception as e:
                logger.error(f"Workflow 流式错误: {str(e)}", exc_info=True)
                yield f"data: [ERROR] {str(e)}\n\n"
                yield "data: [DONE]\n\n"
        
        headers = {"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"}
        return StreamingResponse(sse_generator(), media_type="text/event-stream", headers=headers)
        
    except Exception as e:
        logger.error(f"Workflow 失败: {str(e)}", exc_info=True)
        async def error_generator():
            yield f"data: [ERROR] {str(e)}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(error_generator(), media_type="text/event-stream")
