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
    """显LLM 异步流式回答节点 - 供 astream_events 使用
    
    注意：此节点在意图识别之前执行，不使用意图信息生成回答
    """
    try:
        user_input = state.get("user_input", "")
        # ❗ 此时意图识别还未执行，不使用意图信息
        company = state.get("company", "未知")
        age = state.get("age", "未知")
        gender = state.get("gender", "未知")
        history_text = state.get("history_text", "")  # 最近10条历史消息
        similar_messages = state.get("similar_messages", "")  # 相似度较高的消息
        
        full_prompt = build_full_prompt(
            user_input=user_input,
            history_text=history_text,
            similar_messages=similar_messages,
            company=company,
            age=age,
            gender=gender,
            current_intent="",  # 意图识别还未执行，传空值
            intents=[]  # 空列表
        )
        
        llm = llm_core.create_llm(
            temperature=0.7,
            max_tokens=2000
        )
        
        # 🔥 关键：使用 ainvoke + config，让 astream_events 能捕获流式事件
        # 当 streaming=True 时，ainvoke 内部会流式处理，astream_events 能监听到
        response = await llm.ainvoke(full_prompt, config=config)
        full_response = response.content if hasattr(response, 'content') else str(response)
        
        
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