"""
Database 节点 - MySQL 数据库保存节点
通过 Golang API 将对话保存到 MySQL
"""
from typing import Dict, Any
from app.modules.workflow.core.state import WorkflowState
from app.core.database import golang_db_client
from lmnr import observe
import logging

logger = logging.getLogger(__name__)


@observe(name="save_database_node", tags=["node", "database", "mysql", "storage"])
async def save_database_node(state: WorkflowState) -> Dict[str, Any]:
    """
    保存到数据库节点 - 将本轮对话保存到 MySQL
    
    职责：
    1. 从 state 中提取 conversation_id、user_input 和 llm_response
    2. 通过 Golang API 将用户输入和 LLM 回答保存到 MySQL
    3. 返回保存状态
    
    Args:
        state: 工作流状态，需要包含：
            - conversation_id: 对话ID
            - user_input: 用户输入
            - llm_response: LLM 回答
            - saved_message_ids: ChromaDB 保存的消息ID列表（用作 MySQL 的 message_id）
            
    Returns:
        更新后的状态字典，包含：
            - database_saved: 是否成功保存到数据库
    """
    
    try:
        conversation_id = state.get("conversation_id")
        user_input = state.get("user_input", "")
        llm_response = state.get("llm_response", "")
        saved_message_ids = state.get("saved_message_ids", [])
        access_token = state.get("access_token")  # 新增：获取 access_token
        
        # 调试日志
        logger.info(f"[Debug] state keys: {list(state.keys())}")
        logger.info(f"[Debug] access_token in state: {bool(access_token)}")
        if access_token:
            logger.info(f"[Debug] access_token length: {len(access_token)}")
        
        if not conversation_id:
            logger.warning("⚠️ 缺少 conversation_id，跳过数据库保存")
            return {"database_saved": False}
        
        if not access_token:
            logger.warning("⚠️ 缺少 access_token，跳过数据库保存")
            return {"database_saved": False}
        
        if not user_input and not llm_response:
            logger.warning("⚠️ 没有消息需要保存")
            return {"database_saved": False}
        
        # 用于记录保存结果
        save_results = []
        
        # 保存用户消息
        if user_input:
            user_msg_id = saved_message_ids[0] if len(saved_message_ids) > 0 else f"{conversation_id}_user"
            
            success = await golang_db_client.save_message(
                conversation_id=conversation_id,
                message_content=user_input,
                role="user",
                message_id=user_msg_id,
                access_token=access_token  # 传递 access_token
            )
            save_results.append(success)
        
        # 保存助手消息
        if llm_response:
            assistant_msg_id = saved_message_ids[1] if len(saved_message_ids) > 1 else f"{conversation_id}_assistant"
            
            success = await golang_db_client.save_message(
                conversation_id=conversation_id,
                message_content=llm_response,
                role="assistant",
                message_id=assistant_msg_id,
                access_token=access_token  # 传递 access_token
            )
            save_results.append(success)
        
        # 判断是否全部成功
        all_success = all(save_results)
        
        if all_success:
            logger.info(
                f"✅ MySQL 数据库保存完成 | conversation_id={conversation_id[:20]}... | "
                f"共保存 {len(save_results)} 条消息"
            )
        else:
            logger.error(
                f"❌ MySQL 数据库保存部分失败 | conversation_id={conversation_id[:20]}... | "
                f"成功 {sum(save_results)}/{len(save_results)} 条"
            )
        
        return {
            "database_saved": all_success
        }
        
    except Exception as e:
        logger.error(f"❌ 数据库保存节点执行失败: {str(e)}", exc_info=True)
        return {
            "database_saved": False,
            "error": str(e)
        }
