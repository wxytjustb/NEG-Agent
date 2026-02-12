from typing import Dict, Any
from app.modules.workflow.core.state import WorkflowState
from app.services.ticket_summary_service import ticket_summary_service
from app.services.ticket_service import ticket_service
from app.schemas.ticket_schema import AppTicket
from lmnr import observe
import logging

logger = logging.getLogger(__name__)

@observe(name="ticket_summary_node", tags=["node", "summary", "ticket"])
async def async_ticket_summary_node(state: WorkflowState) -> Dict[str, Any]:
    """
    工单总结节点 - 在关键词触发时，使用专门的总结服务生成工单内容
    
    Args:
        state: 工作流状态
    
    Returns:
        更新的状态，包含工单详情
    """
    try:
        user_input = state.get("user_input", "")
        conversation_id = state.get("conversation_id")
        user_id = state.get("user_id")
        access_token = state.get("access_token")
        
        # 获取意图信息
        intent = state.get("intent", "")
        intent_confidence = state.get("intent_confidence", 0.0)
        intents = state.get("intents", [])
        
        intent_info = ""
        if intent:
            intent_info = f"主要意图：{intent} (置信度: {intent_confidence:.0%})"
            if intents and len(intents) > 1:
                intent_info += f", 次要意图：{intents[1].get('intent')} (置信度: {intents[1].get('confidence'):.0%})"
        
        logger.info(f"🚀 [ticket_summary] 开始执行自动总结 (Conversation: {conversation_id})")
        
        # 调用总结服务
        # 注意：这里会重新拉取历史记录
        ticket: AppTicket = await ticket_summary_service.summarize_ticket(
            text=user_input,
            user_id=str(user_id) if user_id else None,
            conversation_id=conversation_id,
            access_token=access_token,
            intent_info=intent_info
        )
        
        logger.info(f"✅ [ticket_summary] 总结完成: {ticket.title}")

        # 获取服务分类，用于匹配一级分类
        ticket_parent_category = ""
        if access_token and ticket.issue_type:
            try:
                categories_data = await ticket_service.get_volunteer_service_categories(access_token)
                if categories_data and (categories_data.get("code") == 0 or categories_data.get("code") == 200):
                     categories = categories_data.get("data", [])
                     if categories:
                         for cat_l1 in categories:
                             l1_name = cat_l1.get("name")
                             children = cat_l1.get("children") or cat_l1.get("subCategories") or []
                             
                             if children:
                                 for cat_l2 in children:
                                     l2_name = cat_l2.get("name")
                                     if l2_name == ticket.issue_type:
                                         ticket_parent_category = l1_name
                                         break
                             elif l1_name == ticket.issue_type:
                                 ticket_parent_category = l1_name
                             
                             if ticket_parent_category:
                                 break
            except Exception as e:
                logger.warning(f"Failed to match parent category: {e}")
        
        # 详细打印总结结果到控制台
        logger.info("=" * 60)
        
        # 强制打印到控制台 (stdout)
        print("\n" + "=" * 60)
        print("📝 [工单自动总结结果]")
        print(f"标题: {ticket.title}")
        print(f"类型: {ticket.issue_type} (一级分类: {ticket_parent_category})")
        print(f"平台: {ticket.platform}")
        print(f"诉求: {ticket.user_request}")
        print(f"事实: {ticket.brief_facts}")
        print(f"人数: {ticket.people_needing_help}")
        print("=" * 60 + "\n")

        # 转换结果到 State
        result = {
            "need_create_ticket": True, # 强制设为 True
            "ticket_reason": "关键词快速通道触发，AI自动总结工单内容",
            "problem_type": ticket.issue_type,
            "ticket_parent_category": ticket_parent_category,
            "title": ticket.title,
            "facts": ticket.brief_facts,
            "user_appeal": ticket.user_request,
            "company": ticket.platform,
            # 尝试根据 issue_type 填充 ticket_parent_category (如果能匹配到)
            # 这里简单处理，如果 ticket_summary_service 没有返回父分类，暂时留空
            # 前端展示时可能需要容错
        }
        
        return result
        
    except Exception as e:
        error_msg = f"❌ [ticket_summary] 节点执行失败: {str(e)}"
        logger.error(error_msg, exc_info=True)
        print(error_msg) # 确保控制台可见错误
        # 降级处理：返回基本的 True，让后续节点或前端处理
        return {
            "need_create_ticket": True,
            "ticket_reason": f"自动总结失败，请人工补充详情 ({str(e)})",
            "title": "维权求助（自动生成）",
            "facts": "系统尝试总结失败，请用户补充",
            "user_appeal": "维权/求助",
            "problem_type": "权益咨询",  # 默认值
            "ticket_parent_category": "权益咨询", # 默认值
            "company": ""
        }
