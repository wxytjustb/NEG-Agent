# 工单判断节点 - 分析是否需要创建工单
from typing import Dict, Any
from app.modules.workflow.core.state import WorkflowState, format_workflow_state
from app.modules.llm.core.llm_core import llm_core
from app.utils.prompt import get_ticket_analysis_prompt
from app.services.ticket_service import ticket_service
from app.core.config import settings
from langchain_openai import ChatOpenAI
from pydantic import SecretStr
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
            - intent: 主意图（意图识别结果）
            - intent_confidence: 意图置信度
            - intents: 所有意图列表
    
    Returns:
        更新的状态，包含：
            - need_create_ticket: bool - 是否需要创建工单
            - ticket_reason: str - 判断理由
    """
    try:
        user_input = state.get("user_input", "")
        llm_response = state.get("llm_response", "")
        # 优先使用 working_memory_text (Redis短期记忆)，如果为空则尝试 history_text (ChromaDB记忆)
        wm_text = state.get("working_memory_text")
        logger.info(f"🔍 [ticket_analysis] working_memory_text length: {len(wm_text) if wm_text else 0}")
        logger.info(f"🔍 [ticket_analysis] working_memory_text content preview: {wm_text[:50] if wm_text else 'None'}")
        
        history_text = wm_text or state.get("history_text", "")
        
        # 获取意图识别结果
        intent = state.get("intent", "")
        intent_confidence = state.get("intent_confidence", 0.0)
        intents = state.get("intents", [])
        
        # 格式化意图信息（供 Prompt 使用）
        intent_info = ""
        if intent:
            if len(intents) > 1:
                # 混合意图
                intent_parts = []
                for intent_item in intents:
                    intent_name = intent_item.get("intent", "")
                    confidence = intent_item.get("confidence", 0.0)
                    intent_parts.append(f"{intent_name}({confidence:.0%})")
                intent_info = f"当前意图：{' + '.join(intent_parts)}"
            else:
                # 单一意图
                intent_info = f"当前意图：{intent}({intent_confidence:.0%})"
        else:
            intent_info = "当前意图：未识别"
        
        # 获取服务分类，用于动态填充 Prompt
        access_token = state.get("access_token")
        category_options = "权益咨询/心理疏导/同行帮助"  # 默认兜底值（与前端保持一致）
        level2_to_level1_map = {}  # Map Level 2 Name -> Level 1 Name
        
        if access_token:
            try:
                categories_data = await ticket_service.get_volunteer_service_categories(access_token)
                if categories_data and (categories_data.get("code") == 0 or categories_data.get("code") == 200):
                     categories = categories_data.get("data", [])
                     if categories:
                         level2_names = []
                         for cat_l1 in categories:
                             l1_name = cat_l1.get("name")
                             # 尝试获取子分类，兼容 children 或 subCategories
                             children = cat_l1.get("children") or cat_l1.get("subCategories") or []
                             
                             if children:
                                 for cat_l2 in children:
                                     l2_name = cat_l2.get("name")
                                     if l2_name:
                                         level2_names.append(l2_name)
                                         if l1_name:
                                             level2_to_level1_map[l2_name] = l1_name
                             else:
                                 # 如果没有子分类，尝试直接使用一级分类
                                 if l1_name:
                                     level2_names.append(l1_name)
                                     level2_to_level1_map[l1_name] = l1_name

                         if level2_names:
                             category_options = "/".join(level2_names)
                             logger.info(f"Using dynamic categories for prompt: {category_options}")
            except Exception as e:
                logger.error(f"Failed to fetch categories for prompt: {e}")

        # 构建分析 Prompt
        ticket_prompt_template = get_ticket_analysis_prompt()
        analysis_prompt = ticket_prompt_template.format(
            history=history_text if history_text else "（这是新对话的开始）",
            user_input=user_input,
            llm_response=llm_response,
            intent_info=intent_info,  # 新增：意图信息
            category_options=category_options
        )
        
        logger.info(f"🔍 开始分析是否需要创建工单... (意图: {intent})")
        
        # 调用 LLM 分析（使用同步调用，完全不产生流式事件）
        # 注意：此处明确使用阿里云模型 (ALIYUN_MODEL) 进行分析，以获得更准确的中文语境理解
        # 对于某些模型（如 DeepSeek-R1 等），非流式调用必须显式禁用 thinking
        llm = ChatOpenAI(
            model=settings.ALIYUN_MODEL,
            api_key=SecretStr(settings.ALIYUN_API_KEY) if settings.ALIYUN_API_KEY else None,
            base_url=settings.ALIYUN_API_BASE_URL,
            temperature=0.1,  # 低温度保证稳定输出
            max_tokens=500,
            model_kwargs={"extra_body": {"enable_thinking": False}}  # 显式禁用 thinking，通过 extra_body 传递
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
        problem_type = ""
        title = ""
        facts = ""
        user_appeal = ""
        
        try:
            # 尝试提取 JSON
            # 1. 移除 Markdown 代码块标记
            cleaned_response = re.sub(r'```json\s*|\s*```', '', full_response).strip()
            
            # 2. 尝试直接解析
            try:
                result = json.loads(cleaned_response)
            except json.JSONDecodeError:
                # 3. 如果直接解析失败，尝试提取 {} 中的内容
                json_match = re.search(r'\{.*\}', cleaned_response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    result = json.loads(json_str)
                else:
                    raise ValueError("无法在响应中找到有效的 JSON 对象")

            need_create_ticket = result.get('need_ticket', False)
            ticket_reason = result.get('reason', '未提供理由')
            problem_type = result.get('problem_type', '')
            company = result.get('company', '')
            title = result.get('title', '')
            facts = result.get('facts', '')
            user_appeal = result.get('user_appeal', '')
            
            logger.info(f"✅ 工单判断完成: need_ticket={need_create_ticket}, reason={ticket_reason}, company={company}")

        except Exception as parse_error:
            logger.error(f"❌ JSON 解析失败: {str(parse_error)}，默认不创建工单")
        
        # 尝试匹配一级分类
        ticket_parent_category = ""
        if need_create_ticket and problem_type:
            ticket_parent_category = level2_to_level1_map.get(problem_type, "")
            if ticket_parent_category:
                logger.info(f"Matched ticket category: {ticket_parent_category} -> {problem_type}")
            else:
                logger.warning(f"Could not find parent category for: {problem_type}")

        result = {
            "need_create_ticket": need_create_ticket,
            "ticket_reason": ticket_reason,
            "problem_type": problem_type,
            "ticket_parent_category": ticket_parent_category,
            "company": company if 'company' in locals() else "",
            "title": title,
            "facts": facts,
            "user_appeal": user_appeal
        }
        
        # 🐛 [DEBUG] 打印完整 State 信息
        logger.info("=" * 60)
        logger.info("🐛 [ticket_analysis] FULL STATE DUMP:")
        try:
            # 使用 format_workflow_state 确保打印所有字段
            logger.info(json.dumps(format_workflow_state(state), ensure_ascii=False, indent=2, default=str))
        except Exception:
            # 降级打印
            logger.info(state)
        logger.info("=" * 60)
        
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
                f"原因：{ticket_reason}\n"
            )
            
            problem_type = state.get("problem_type")
            facts = state.get("facts")
            user_appeal = state.get("user_appeal")
            
            if problem_type:
                confirmation_message += f"类型：{problem_type}\n"
            if facts:
                confirmation_message += f"事实：{facts}\n"
            if user_appeal:
                confirmation_message += f"诉求：{user_appeal}\n"
                
            confirmation_message += f"\n是否需要我帮您创建维权工单？"
            
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
