# LLM 回答节点 - 构建完整 Prompt 并调用 LLM 生成回答
from typing import Dict, Any
from app.modules.workflow.core.state import WorkflowState
from app.modules.llm.core.llm_core import llm_core
from app.utils.prompt import build_full_prompt, ANRAN_SYSTEM_PROMPT
import logging

logger = logging.getLogger(__name__)


def llm_answer_node(state: WorkflowState) -> Dict[str, Any]:
    """复制代码LLM 回答节点 - 构建完整 Prompt 并调用 LLM 生成回答
    
    职责：
    1. 从 state 中获取意图、用户画像、对话历史等信息
    2. 使用 build_full_prompt() 填充占位符，生成完整 Prompt
    3. 调用 LLM 生成回答
    
    Args:
        state: 工作流状态，包含所有上下文信息
        
    Returns:
        更新后的状态字典（包含 full_prompt 和 llm_response）
    """
    logger.info("========== LLM 回答节点开始 ===========")
    
    try:
        # 1. 从 state 中提取信息
        user_input = state.get("user_input", "")
        intent = state.get("intent", "日常对话")
        company = state.get("company", "未知")
        age = state.get("age", "未知")
        gender = state.get("gender", "未知")
        history_text = state.get("history_text", "")
        
        logger.info(f"用户输入: {user_input[:50]}...")
        logger.info(f"识别意图: {intent}")
        logger.info(f"用户画像: 公司={company}, 年龄={age}, 性别={gender}")
        
        # 2. 构建完整的 Prompt（填充所有占位符）
        logger.info("正在构建完整 Prompt...")
        full_prompt = build_full_prompt(
            user_input=user_input,
            history_text=history_text,
            company=company,
            age=age,
            gender=gender,
            current_intent=intent
        )
        
        logger.info(f"✅ Prompt 构建完成，长度: {len(full_prompt)} 字符")
        
        # 3. 调用 LLM 生成回答
        logger.info("正在调用 LLM...")
        llm = llm_core.create_llm(provider="deepseek")
        response = llm.invoke(full_prompt)
        llm_response = response.content if hasattr(response, 'content') else str(response)
        
        logger.info(f"✅ LLM 回答完成，长度: {len(llm_response)} 字符")
        
        return {
            "full_prompt": full_prompt,
            "llm_response": llm_response
        }
        
    except Exception as e:
        error_msg = f"LLM 回答节点执行失败: {str(e)}"
        logger.error(error_msg)
        return {
            "error": error_msg,
            "full_prompt": "",
            "llm_response": "抱歉，我现在遇到了一些技术问题，请稍后再试。"
        }


def llm_stream_answer_node(state: WorkflowState):
    """LLM 流式回答节点 - 构建完整 Prompt 并流式调用 LLM
    
    职责：
    与 llm_answer_node 相同，但使用流式输出
    适用于需要实时显示回答的场景
    
    Args:
        state: 工作流状态
        
    Yields:
        LLM 流式输出的 token
    """
    logger.info("========== LLM 流式回答节点开始 ==========")
    
    try:
        # 1. 从 state 中提取信息
        user_input = state.get("user_input", "")
        intent = state.get("intent", "日常对话")
        company = state.get("company", "未知")
        age = state.get("age", "未知")
        gender = state.get("gender", "未知")
        history_text = state.get("history_text", "")
        
        # 2. 构建完整的 Prompt
        full_prompt = build_full_prompt(
            user_input=user_input,
            history_text=history_text,
            company=company,
            age=age,
            gender=gender,
            current_intent=intent
        )
        
        # 3. 流式调用 LLM
        logger.info("正在流式调用 LLM...")
        llm = llm_core.create_llm(
            temperature=0.7,
            max_tokens=2000
        )
        
        full_response = ""
        for chunk in llm.stream(full_prompt):
            if hasattr(chunk, 'content') and chunk.content:
                token = str(chunk.content)
                full_response += token
                yield token
        
        logger.info(f"✅ LLM 流式回答完成，总长度: {len(full_response)} 字符")
        
        # 更新状态（流式结束后）
        state["full_prompt"] = full_prompt
        state["llm_response"] = full_response
        
    except Exception as e:
        error_msg = f"LLM 流式回答节点执行失败: {str(e)}"
        logger.error(error_msg)
        yield "抱歉，我现在遇到了一些技术问题，请稍后再试。"
