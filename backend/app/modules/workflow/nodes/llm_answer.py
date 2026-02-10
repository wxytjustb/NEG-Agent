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
        intents = state.get("intents", [])  # 新增：获取所有意图
        company = state.get("company", "未知")
        age = state.get("age", "未知")
        gender = state.get("gender", "未知")
        history_text = state.get("history_text", "")  # ChromaDB 历史消息
        working_memory_text = state.get("working_memory_text", "")  # Redis 短期记忆
        similar_messages = state.get("similar_messages", "")  # 相似度较高的消息
        feedback_summary = state.get("feedback_summary", "")  # 用户反馈趋势摘要
        
        full_prompt = build_full_prompt(
            user_input=user_input,
            working_memory_text=working_memory_text,  # 传入 working_memory_text
            history_text=history_text,
            similar_messages=similar_messages,
            company=company,
            age=age,
            gender=gender,
            current_intent=intent,
            intents=intents,  # 新增：传入所有意图
            feedback_summary=feedback_summary  # 新增：传入反馈摘要
        )
        
        llm = llm_core.create_llm(
            temperature=0.7,
            max_tokens=2000
        )
        
        # 🔥 关键：使用 ainvoke + config，让 astream_events 能捕获流式事件
        # 当 streaming=True 时，ainvoke 内部会流式处理，astream_events 能监听到
        # 注入特殊 tag 以便在 workflow 中过滤
        if config:
            # 确保不修改原始 config 对象
            import copy
            config = copy.copy(config)
            tags = config.get("tags", [])
            if tags is None:
                tags = []
            if "answer_generator" not in tags:
                tags.append("answer_generator")
            config["tags"] = tags
        else:
            config = {"tags": ["answer_generator"]}

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