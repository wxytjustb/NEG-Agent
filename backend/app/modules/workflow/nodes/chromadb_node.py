# ChromaDB 记忆节点 - LangGraph 工作流节点
from typing import Dict, Any, List
from app.modules.chromadb.core.chromadb_core import chromadb_core
from app.modules.workflow.core.state import WorkflowState
import logging

logger = logging.getLogger(__name__)


def get_memory_node(state: WorkflowState) -> Dict[str, Any]:
    """
    获取记忆节点 - 从 ChromaDB 获取用户的对话记忆
    
    职责：
    1. 从 state 中提取 user_id、session_id 和 user_input
    2. 基于当前用户输入检索相关的历史对话记忆（语义搜索）
    3. 将检索到的记忆格式化为文本
    4. 更新 state 中的 history_text
    
    Args:
        state: 工作流状态，需要包含：
            - user_id: 用户ID
            - session_id: 会话ID
            - user_input: 当前用户输入（用于语义搜索）
            
    Returns:
        更新后的状态字典，包含：
            - history_text: 格式化的历史记忆文本
            - memory_count: 检索到的记忆条数
    """
    
    try:
        # 1. 提取必要参数
        user_id = state.get("user_id")
        session_id = state.get("session_id")
        user_input = state.get("user_input", "")
        
        if not user_id or not session_id:
            logger.warning("⚠️ 缺少 user_id 或 session_id，跳过记忆检索")
            return {
                "history_text": "",
                "memory_count": 0
            }
        
        # 2. 从 ChromaDB 检索相关记忆（基于语义相似度）
        memories = chromadb_core.search_memory(
            user_id=user_id,
            session_id=session_id,
            query_text=user_input,
            n_results=10,  # 最多返回 10 条相关记忆
            include_metadata=True
        )
        
        if not memories:
            logger.info("📭 未找到相关记忆")
            return {
                "history_text": "",
                "memory_count": 0
            }
        
        # 3. 格式化记忆为文本
        history_lines = []
        
        for memory in memories:
            role = memory.get("role", "unknown")
            content = memory.get("content", "")
            history_lines.append(f"{role}: {content}")
        
        history_text = "\n".join(history_lines)
        
        logger.info(f"✅ 记忆检索完成，共 {len(memories)} 条")
        
        # 4. 返回更新的状态
        return {
            "history_text": history_text,
            "memory_count": len(memories)
        }
        
    except Exception as e:
        error_msg = f"获取记忆节点执行失败: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "history_text": "",
            "memory_count": 0,
            "error": error_msg
        }


def save_memory_node(state: WorkflowState) -> Dict[str, Any]:
    """
    保存记忆节点 - 将本轮对话保存到 ChromaDB
    
    职责：
    1. 从 state 中提取 user_id、session_id、user_input 和 llm_response
    2. 将用户输入和 LLM 回答分别保存到 ChromaDB
    3. 更新 state 中的保存状态
    
    Args:
        state: 工作流状态，需要包含：
            - user_id: 用户ID
            - session_id: 会话ID
            - user_input: 用户输入
            - llm_response: LLM 回答
            
    Returns:
        更新后的状态字典，包含：
            - memory_saved: 是否成功保存
            - saved_message_ids: 保存的消息ID列表
    """
    
    try:
        # 1. 提取必要参数
        user_id = state.get("user_id")
        session_id = state.get("session_id")
        user_input = state.get("user_input", "")
        llm_response = state.get("llm_response", "")
        
        if not user_id or not session_id:
            logger.warning("⚠️ 缺少 user_id 或 session_id，跳过记忆保存")
            return {
                "memory_saved": False,
                "saved_message_ids": []
            }
        
        if not user_input and not llm_response:
            logger.warning("⚠️ 用户输入和 LLM 回答均为空，跳过记忆保存")
            return {
                "memory_saved": False,
                "saved_message_ids": []
            }
        
        saved_ids = []
        
        # 2. 保存用户消息
        if user_input:
            user_msg_id = chromadb_core.add_message(
                user_id=user_id,
                session_id=session_id,
                role="user",
                content=user_input
            )
            saved_ids.append(user_msg_id)
        
        # 3. 保存助手回复
        if llm_response:
            assistant_msg_id = chromadb_core.add_message(
                user_id=user_id,
                session_id=session_id,
                role="assistant",
                content=llm_response
            )
            saved_ids.append(assistant_msg_id)
        
        logger.info(f"✅ 记忆保存完成，共保存 {len(saved_ids)} 条消息")
        
        # 4. 返回更新的状态
        return {
            "memory_saved": True,
            "saved_message_ids": saved_ids
        }
        
    except Exception as e:
        error_msg = f"保存记忆节点执行失败: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "memory_saved": False,
            "saved_message_ids": [],
            "error": error_msg
        }


def get_all_messages_node(state: WorkflowState) -> Dict[str, Any]:
    """
    获取所有消息节点 - 获取指定会话的所有历史消息（按时间顺序）
    
    职责：
    1. 从 state 中提取 user_id 和 session_id
    2. 获取该会话的所有历史消息
    3. 格式化为文本并更新 state
    
    Args:
        state: 工作流状态，需要包含：
            - user_id: 用户ID
            - session_id: 会话ID
            
    Returns:
        更新后的状态字典，包含：
            - history_text: 格式化的历史消息文本
            - message_count: 消息总数
            - messages: 原始消息列表
    """
    logger.info("========== 获取所有消息节点开始 ==========")
    
    try:
        # 1. 提取必要参数
        user_id = state.get("user_id")
        session_id = state.get("session_id")
        limit = state.get("message_limit", None)  # 可选的数量限制
        
        if not user_id or not session_id:
            logger.warning("⚠️ 缺少 user_id 或 session_id，跳过消息获取")
            return {
                "history_text": "",
                "message_count": 0,
                "messages": []
            }
        
        logger.info(f"用户ID: {user_id}")
        logger.info(f"会话ID: {session_id[:20]}...")
        
        # 2. 从 ChromaDB 获取所有消息
        logger.info("正在获取所有历史消息...")
        messages = chromadb_core.get_all_messages(
            user_id=user_id,
            session_id=session_id,
            limit=limit
        )
        
        if not messages:
            logger.info("📭 未找到历史消息")
            return {
                "history_text": "",
                "message_count": 0,
                "messages": []
            }
        
        # 3. 格式化消息为文本
        logger.info(f"📚 获取到 {len(messages)} 条历史消息")
        history_lines = []
        
        for i, msg in enumerate(messages, 1):
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            timestamp = msg.get("timestamp", "")
            
            history_lines.append(f"{role}: {content}")
            logger.info(f"  [{i}] {timestamp[:19]} - {role[:4]}: {content[:30]}...")
        
        history_text = "\n".join(history_lines)
        
        logger.info(f"✅ 消息获取完成，共 {len(messages)} 条")
        
        # 4. 返回更新的状态
        return {
            "history_text": history_text,
            "message_count": len(messages),
            "messages": messages
        }
        
    except Exception as e:
        error_msg = f"获取所有消息节点执行失败: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "history_text": "",
            "message_count": 0,
            "messages": [],
            "error": error_msg
        }
