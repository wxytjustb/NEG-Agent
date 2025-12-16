# 工作流执行接口 - LangGraph Workflow API
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.services.langgraph_service import langgraph_service
from app.core.security import get_current_session
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/workflow", tags=["Workflow"])


class ChatWorkflowRequest(BaseModel):
    """LangGraph 对话工作流请求"""
    message: str  # 用户消息


@router.post("/chat", summary="LangGraph 对话工作流（流式）")
async def chat_workflow(request: ChatWorkflowRequest, session_data: dict = Depends(get_current_session)):
    """
    使用 LangGraph 工作流进行对话 - SSE 流式输出
    
    工作流步骤：
    1. analyze_intent - 分析用户意图（通过 AI）
    2. call_llm - 调用 LLM 生成回复（流式输出）
    3. save_to_redis - 保存对话到 Redis
    
    参数:
    - message: 用户消息
    - session_token: 会话 Token (通过 Query 或 Header 传递)
    
    返回:
    - SSE 流式输出
      - data: intent:<用户意图>  # 第一条消息
      - data: <文本内容>         # 后续流式内容
      - data: [DONE]            # 结束标记
    """
    try:
        user_id = session_data.get("user_id")
        username = session_data.get("username", "Unknown")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无法获取用户ID"
            )
        
        logger.info(f"=== LangGraph 工作流请求（流式） ===")
        logger.info(f"用户: {username} (ID: {user_id})")
        logger.info(f"消息: {request.message[:100]}...")
        
        # SSE 流式输出生成器
        async def sse_generator():
            try:
                logger.info(">>> 开始 SSE 流式输出（工作流）")
                chunk_count = 0
                
                # 执行 LangGraph 工作流（流式）
                async for chunk in langgraph_service.run_chat_workflow_stream(
                    session_data=session_data,
                    user_message=request.message
                ):
                    if chunk:
                        chunk_count += 1
                        logger.info(f"[WorkflowStream 第{chunk_count}个chunk] 发送: {repr(chunk)[:80]}")
                        yield f"data: {chunk}\n\n"
                
                yield "data: [DONE]\n\n"
                logger.info(f"<<< SSE 流式输出完成（工作流），共发送 {chunk_count} 个chunk")
                
            except Exception as e:
                logger.error(f"!!! SSE 流式输出错误（工作流）: {str(e)}", exc_info=True)
                yield f"data: [ERROR] {str(e)}\n\n"
                yield "data: [DONE]\n\n"
        
        headers = {
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
        return StreamingResponse(sse_generator(), media_type="text/event-stream", headers=headers)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"工作流执行失败: {str(e)}", exc_info=True)
        # 即使发生异常，也返回流式响应
        async def error_generator():
            yield f"data: [ERROR] {str(e)}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(error_generator(), media_type="text/event-stream")
