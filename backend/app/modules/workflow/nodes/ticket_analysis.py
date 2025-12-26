# 工单判断节点 - 分析是否需要创建工单
from typing import Dict, Any
from app.modules.workflow.core.state import WorkflowState
from app.modules.llm.core.llm_core import llm_core
from app.utils.prompt import get_ticket_analysis_prompt
from lmnr import observe
import logging
import json
import re

logger = logging.getLogger(__name__)


@observe(name="ticket_analysis_node", tags=["node", "analysis", "ticket"])
async def async_ticket_analysis_node(state: WorkflowState):
    """
    工单判断节点 - 分析对话内容，判断是否需要创建工单
    
    Args:
        state: 工作流状态，需要包含：
            - user_input: 用户输入
            - llm_response: LLM 回答
            - history_text: 对话历史
    
    Returns:
        更新的状态，包含：
            - need_create_ticket: bool - 是否需要创建工单
            - ticket_reason: str - 判断理由
    """
    try:
        user_input = state.get("user_input", "")
        llm_response = state.get("llm_response", "")
        history_text = state.get("history_text", "")
        
        # 构建分析 Prompt
        ticket_prompt_template = get_ticket_analysis_prompt()
        analysis_prompt = ticket_prompt_template.format(
            history=history_text if history_text else "（这是新对话的开始）",
            user_input=user_input,
            llm_response=llm_response
        )
        
        logger.info("🔍 开始分析是否需要创建工单...")
        
        # 调用 LLM 分析（使用同步调用，完全不产生流式事件）
        llm = llm_core.create_llm(
            temperature=0.1,  # 低温度保证稳定输出
            max_tokens=500
        )
        
        # 使用同步 invoke（在 async 函数中通过 run_in_executor 调用）
        import asyncio
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, llm.invoke, analysis_prompt)
        
        full_response = ""
        if hasattr(response, 'content'):
            content = response.content
            if isinstance(content, str):
                full_response = content
            else:
                full_response = str(content)
        else:
            full_response = str(response)
        
        logger.info(f"📝 分析结果原始输出: {full_response}")
        
        # 解析 JSON 结果
        need_create_ticket = False
        ticket_reason = ""
        
        try:
            # 尝试提取 JSON
            json_match = re.search(r'\{.*"need_ticket".*\}', full_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                result = json.loads(json_str)
                
                need_create_ticket = result.get('need_ticket', False)
                ticket_reason = result.get('reason', '未提供理由')
                
                logger.info(f"✅ 工单判断完成: need_ticket={need_create_ticket}, reason={ticket_reason}")
            else:
                logger.warning("⚠️ 未找到 JSON 格式，默认不创建工单")
        except Exception as parse_error:
            logger.error(f"❌ JSON 解析失败: {str(parse_error)}，默认不创建工单")
        
        result = {
            "need_create_ticket": need_create_ticket,
            "ticket_reason": ticket_reason
        }
        logger.info(f"🔍 [ticket_analysis] 返回 State: {result}")
        return result
        
    except Exception as e:
        logger.error(f"❌ 工单判断节点执行失败: {str(e)}", exc_info=True)
        return {
            "need_create_ticket": False,
            "ticket_reason": f"分析失败: {str(e)}"
        }


@observe(name="ask_user_confirmation_node", tags=["node", "user_interaction", "ticket"])
async def async_ask_user_confirmation_node(state: WorkflowState):
    """
    询问用户确认节点 - 如果需要创建工单，询问用户是否确认
    
    Args:
        state: 工作流状态，需要包含：
            - need_create_ticket: 是否需要创建工单
            - ticket_reason: 工单判断理由
    
    Returns:
        更新的状态，包含：
            - confirmation_message: str - 询问用户的消息（前端显示）
    
    Note:
        这个节点只是准备确认消息，实际的 user_confirmed_ticket 由前端设置
    """
    try:
        need_create_ticket = state.get("need_create_ticket", False)
        ticket_reason = state.get("ticket_reason", "")
        
        if need_create_ticket:
            # 构建确认消息
            confirmation_message = (
                f"📝 检测到您可能需要维权帮助。\n\n"
                f"原因：{ticket_reason}\n\n"
                f"是否需要我帮您创建维权工单？"
            )
            
            logger.info(f"❓ 需要询问用户确认: {confirmation_message[:50]}...")
            
            result = {
                "confirmation_message": confirmation_message
            }
            logger.info(f"🔍 [ask_user_confirmation] 返回 State: {result}")
            return result
        else:
            # 不需要创建工单，直接跳过
            logger.info("✅ 不需要创建工单，跳过确认环节")
            result = {
                "confirmation_message": ""
            }
            logger.info(f"🔍 [ask_user_confirmation] 返回 State: {result}")
            return result
    
    except Exception as e:
        logger.error(f"❌ 询问用户确认节点执行失败: {str(e)}", exc_info=True)
        return {
            "confirmation_message": ""
        }
