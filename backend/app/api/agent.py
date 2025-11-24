# 智能体接口 - Agent API
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from app.schemas.agent_schema import AgentChatRequest
from app.services.agent_service import agent_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agent", tags=["Agent"])


@router.post("/chat", summary="流式对话接口")
async def chat(request: AgentChatRequest):
    """
    Agent 流式对话接口 - SSE 流式输出
    
    参数:
    - messages: 对话消息列表，每条消息包含 role 和 content
      - role: system/user/assistant
      - content: 消息内容
    - provider: LLM 提供商，'deepseek' 或 'ollama'，默认 'ollama'
    - temperature: 温度参数，控制生成的随机性 (0.0-2.0)，默认 0.7
    - max_tokens: 最大生成 token 数，默认 2000
    - model: 指定模型名称（可选）
    
    返回:
    - SSE 流式输出，每个 chunk 以 "data: <text>\n\n" 发送，最后发送 "data: [DONE]\n\n"
    """
    try:
        # 将 Pydantic 模型转换为字典
        messages = [msg.model_dump() for msg in request.messages]
        logger.info(f"=== 接收到流式请求 ===")
        logger.info(f"消息数量: {len(messages)}, provider={request.provider}")

        # SSE 流式输出生成器
        async def sse_generator():
            try:
                logger.info(">>> 开始 SSE 流式输出")
                chunk_count = 0
                async for chunk in agent_service.chat_stream(
                    messages=messages,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens,
                    model=request.model,
                    provider=request.provider
                ):
                    if chunk:
                        chunk_count += 1
                        logger.info(f"[第{chunk_count}个chunk] 发送: {repr(chunk)[:80]}")
                        yield f"data: {chunk}\n\n"
                
                yield "data: [DONE]\n\n"
                logger.info(f"<<< SSE 流式输出完成，共发送 {chunk_count} 个chunk")
            except Exception as e:
                logger.error(f"!!! SSE 流式输出错误: {str(e)}", exc_info=True)
                yield f"data: [ERROR] {str(e)}\n\n"
                yield "data: [DONE]\n\n"

        headers = {
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
        return StreamingResponse(sse_generator(), media_type="text/event-stream", headers=headers)

    except Exception as e:
        logger.error(f"!!! 对话接口调用失败: {str(e)}", exc_info=True)
        # 即使发生异常，也返回流式响应
        async def error_generator():
            yield f"data: [ERROR] {str(e)}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(error_generator(), media_type="text/event-stream")
