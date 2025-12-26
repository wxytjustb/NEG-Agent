# LLM 回答节点 - 构建完整 Prompt 并调用 LLM 生成回答
from typing import Dict, Any
from app.modules.workflow.core.state import WorkflowState
from app.modules.llm.core.llm_core import llm_core
from app.utils.prompt import build_full_prompt, ANRAN_SYSTEM_PROMPT
from lmnr import observe
import logging

logger = logging.getLogger(__name__)


@observe(name="llm_answer_node", tags=["node", "llm", "generation"])
async def async_llm_stream_answer_node(state: WorkflowState):
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
        
        # ✅ 使用 ainvoke 而不是 astream，让 astream_events 监听 LLM 调用
        # LangGraph 的 astream_events 会自动监听 LLM 的流式输出
        result = await llm.ainvoke(full_prompt)
        
        return {
            "full_prompt": full_prompt,
            "llm_response": result.content if hasattr(result, 'content') else str(result)
        }
        
    except Exception as e:
        logger.error(f"LLM 节点执行失败: {str(e)}", exc_info=True)
        return {
            "error": str(e),
            "full_prompt": "",
            "llm_response": "抱歉，我现在遇到了一些技术问题，请稍后再试。"
        }
