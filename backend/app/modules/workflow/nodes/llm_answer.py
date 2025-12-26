# LLM 回答节点 - 构建完整 Prompt 并调用 LLM 生成回答
from typing import Dict, Any, Optional
from langchain_core.runnables import RunnableConfig
from app.modules.workflow.core.state import WorkflowState
from app.modules.llm.core.llm_core import llm_core
from app.utils.prompt import build_full_prompt, ANRAN_SYSTEM_PROMPT
from lmnr import observe
import logging

logger = logging.getLogger(__name__)


@observe(name="llm_answer_node", tags=["node", "llm", "generation"])
async def async_llm_stream_answer_node(state: WorkflowState, config: Optional[RunnableConfig] = None):
    """LLM 异步流式回答节点 - 供 astream_events 使用"""
    try:
        user_input = state.get("user_input", "")
        intent = state.get("intent", "日常对话")
        company = state.get("company", "未知")
        age = state.get("age", "未知")
        gender = state.get("gender", "未知")
        history_text = state.get("history_text", "")
        
        full_prompt = build_full_prompt(
            user_input=user_input,
            history_text=history_text,
            company=company,
            age=age,
            gender=gender,
            current_intent=intent
        )
        
        llm = llm_core.create_llm(
            temperature=0.7,
            max_tokens=2000
        )
        
        # 🔥 关键：使用 ainvoke，LangGraph 的 astream_events 会自动捕获流式输出
        # 当 streaming=True 时，ainvoke 会在内部流式处理，astream_events 能监听到
        logger.info("🔥 开始调用 LLM 生成...")
        print(f"🔥🔥🔥 LLM streaming={llm.streaming}", flush=True)
        
        # 传递 config 以确保回调（callbacks）正确传播，这对于 astream_events 捕获 on_chat_model_stream 至关重要
        response = await llm.ainvoke(full_prompt, config=config)
        full_response = response.content if hasattr(response, 'content') else str(response)
        
        print(f"✅✅✅ LLM 生成完成: {full_response[:50]}...", flush=True)
        logger.info(f"✅ LLM 生成完成: {full_response[:50]}...")
        
        return {
            "full_prompt": full_prompt,
            "llm_response": full_response
        }
        
    except Exception as e:
        logger.error(f"LLM 节点执行失败: {str(e)}", exc_info=True)
        return {
            "error": str(e),
            "full_prompt": "",
            "llm_response": "抱歉，我现在遇到了一些技术问题，请稍后再试。"
        }
