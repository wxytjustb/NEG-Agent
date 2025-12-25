# ChromaDB 记忆节点 - LangGraph 工作流节点
from typing import Dict, Any, List
from app.modules.chromadb.core.chromadb_core import chromadb_core
from app.modules.workflow.core.state import WorkflowState
from lmnr import observe
import logging

logger = logging.getLogger(__name__)


@observe(name="get_memory_node", tags=["node", "memory", "retrieval"])
def get_memory_node(state: WorkflowState) -> Dict[str, Any]:
    """
    获取记忆节点 - 从 ChromaDB 获取用户的对话记忆
    
    职责：
    1. 从 state 中提取 user_id、session_id 和 user_input
    2. 基于当前用户输入检索相关的历史对话记忆（语义搜索）
    3. 过滤相似度 > 0.7 的记忆（distance < 0.3，因为distance越小越相似）
    4. 将检索到的记忆格式化为文本
    5. 更新 state 中的 history_text
    
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
        user_id = state.get("user_id")
        session_id = state.get("session_id")
        user_input = state.get("user_input", "")
        
        if not user_id or not session_id:
            return {
                "history_text": "",
                "memory_count": 0
            }
        
        memories = chromadb_core.search_memory(
            user_id=user_id,
            session_id=session_id,
            query_text=user_input,
            n_results=50,
            include_metadata=True
        )
        
        if not memories:
            return {
                "history_text": "",
                "memory_count": 0
            }
        
        # 过滤相似度阈值：distance < 0.3
        SIMILARITY_THRESHOLD = 0.3
        filtered_memories = [
            mem for mem in memories 
            if mem.get("distance", 1.0) < SIMILARITY_THRESHOLD
        ]
        
        if not filtered_memories:
            return {
                "history_text": "",
                "memory_count": 0
            }
        
        # 格式化记忆为文本
        history_lines = []
        for memory in filtered_memories:
            role = memory.get("role", "unknown")
            content = memory.get("content", "")
            role_name = "用户" if role == "user" else "安然" if role == "assistant" else role
            history_lines.append(f"{role_name}：{content}")
        
        history_text = "\n".join(history_lines)
        
        logger.info(f"✅ 记忆检索完成，共 {len(filtered_memories)} 条")
        
        return {
            "history_text": history_text,
            "memory_count": len(filtered_memories)
        }
        
    except Exception as e:
        logger.error(f"获取记忆节点执行失败: {str(e)}", exc_info=True)
        return {
            "history_text": "",
            "memory_count": 0,
            "error": str(e)
        }


@observe(name="save_memory_node", tags=["node", "memory", "storage"])
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
        user_id = state.get("user_id")
        session_id = state.get("session_id")
        user_input = state.get("user_input", "")
        llm_response = state.get("llm_response", "")
        
        if not user_id or not session_id:
            return {
                "memory_saved": False,
                "saved_message_ids": []
            }
        
        if not user_input and not llm_response:
            return {
                "memory_saved": False,
                "saved_message_ids": []
            }
        
        saved_ids = []
        
        if user_input:
            user_msg_id = chromadb_core.add_message(
                user_id=user_id,
                session_id=session_id,
                role="user",
                content=user_input
            )
            saved_ids.append(user_msg_id)
        
        if llm_response:
            assistant_msg_id = chromadb_core.add_message(
                user_id=user_id,
                session_id=session_id,
                role="assistant",
                content=llm_response
            )
            saved_ids.append(assistant_msg_id)
        
        logger.info(f"✅ 记忆保存完成，共保存 {len(saved_ids)} 条消息")
        
        return {
            "memory_saved": True,
            "saved_message_ids": saved_ids
        }
        
    except Exception as e:
        logger.error(f"保存记忆节点执行失败: {str(e)}", exc_info=True)
        return {
            "memory_saved": False,
            "saved_message_ids": [],
            "error": str(e)
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
    try:
        user_id = state.get("user_id")
        session_id = state.get("session_id")
        limit = state.get("message_limit", None)
        
        if not user_id or not session_id:
            return {
                "history_text": "",
                "message_count": 0,
                "messages": []
            }
        
        messages = chromadb_core.get_all_messages(
            user_id=user_id,
            session_id=session_id,
            limit=limit
        )
        
        if not messages:
            return {
                "history_text": "",
                "message_count": 0,
                "messages": []
            }
        
        # 格式化消息为文本
        history_lines = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            role_name = "用户" if role == "user" else "安然" if role == "assistant" else role
            history_lines.append(f"{role_name}：{content}")
        
        history_text = "\n".join(history_lines)
        
        logger.info(f"✅ 消息获取完成，共 {len(messages)} 条")
        
        return {
            "history_text": history_text,
            "message_count": len(messages),
            "messages": messages
        }
        
    except Exception as e:
        logger.error(f"获取所有消息节点执行失败: {str(e)}", exc_info=True)
        return {
            "history_text": "",
            "message_count": 0,
            "messages": [],
            "error": str(e)
        }
