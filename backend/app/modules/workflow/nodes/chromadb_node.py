# ChromaDB 记忆节点 - LangGraph 工作流节点
from typing import Dict, Any, List
from app.modules.chromadb.core.chromadb_core import chromadb_core
from app.modules.workflow.core.state import WorkflowState
from app.core.config import settings
from lmnr import observe
import logging

logger = logging.getLogger(__name__)


@observe(name="get_memory_node", tags=["node", "memory", "retrieval"])
def get_memory_node(state: WorkflowState) -> Dict[str, Any]:
    """
    获取记忆节点 - 从 ChromaDB 获取用户的对话记忆
    
    职责：
    1. 从 state 中提取 user_id、session_id 和 user_input
    2. 获取当前会话最近N条历史消息（按时间顺序，数量由 HISTORY_MESSAGE_LIMIT 配置）
    3. 基于当前用户输入检索当前会话中相似度较高的历史对话记忆（语义搜索）
    4. 分别格式化为文本并更新 state
    
    Args:
        state: 工作流状态，需要包含：
            - user_id: 用户ID
            - session_id: 会话ID
            - user_input: 当前用户输入（用于语义搜索）
            
    Returns:
        更新后的状态字典，包含：
            - history_text: 当前会话最近N条历史消息文本（数量由 HISTORY_MESSAGE_LIMIT 配置）
            - similar_messages: 当前会话中相似度较高的消息文本
            - recent_message_count: 最近消息数量
            - similar_message_count: 相似消息数量
    """
    
    try:
        user_id = state.get("user_id")
        session_id = state.get("session_id")
        user_input = state.get("user_input", "")
        
        if not user_id or not session_id:
            return {
                "history_text": "",
                "similar_messages": "",
                "recent_message_count": 0,
                "similar_message_count": 0
            }
        
        # ========== 1. 获取最近N条历史消息（当前会话） ==========
        recent_messages = chromadb_core.get_all_messages(
            user_id=user_id,
            session_id=session_id,  # 只获取当前会话的历史消息
            limit=settings.HISTORY_MESSAGE_LIMIT  # 从配置文件读取，默认10条
        )
        
        history_text = ""
        if recent_messages:
            history_lines = []
            for msg in recent_messages:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                role_name = "用户" if role == "user" else "安然" if role == "assistant" else role
                history_lines.append(f"{role_name}：{content}")
            history_text = "\n".join(history_lines)
            logger.info(f"✅ 最近消息获取完成（当前会话），共 {len(recent_messages)} 条")
        
        # ========== 2. 基于语义相似度检索相关记忆（当前会话） ==========
        similar_messages_text = ""
        similar_count = 0
        
        if user_input:  # 只有当有用户输入时才进行语义搜索
            memories = chromadb_core.search_memory(
                user_id=user_id,
                session_id=session_id,  # 只搜索当前会话的历史记忆
                query_text=user_input,
                n_results=50,
                include_metadata=True
            )
            
            if memories:
                # 过滤相似度阈值：distance < 0.3 （越小越相似）
                SIMILARITY_THRESHOLD = 0.3
                filtered_memories = [
                    mem for mem in memories 
                    if mem.get("distance", 1.0) < SIMILARITY_THRESHOLD
                ]
                
                if filtered_memories:
                    similar_lines = []
                    for memory in filtered_memories:
                        role = memory.get("role", "unknown")
                        content = memory.get("content", "")
                        distance = memory.get("distance", 1.0)
                        role_name = "用户" if role == "user" else "安然" if role == "assistant" else role
                        # 添加相似度信息
                        similar_lines.append(f"{role_name}：{content} (相似度: {1-distance:.2f})")
                    
                    similar_messages_text = "\n".join(similar_lines)
                    similar_count = len(filtered_memories)
                    logger.info(f"✅ 相似消息搜索完成，共 {similar_count} 条")
        
        return {
            "history_text": history_text,
            "similar_messages": similar_messages_text,
            "recent_message_count": len(recent_messages) if recent_messages else 0,
            "similar_message_count": similar_count
        }
        
    except Exception as e:
        logger.error(f"获取记忆节点执行失败: {str(e)}", exc_info=True)
        return {
            "history_text": "",
            "similar_messages": "",
            "recent_message_count": 0,
            "similar_message_count": 0,
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
        
        # 关键修改：使用统一的时间戳，确保 user 和 assistant 消息顺序正确
        from datetime import datetime, timedelta
        base_timestamp = datetime.now()
        
        if user_input:
            # user 消息使用稍早的时间戳（减去 1 毫秒）
            user_timestamp = (base_timestamp - timedelta(milliseconds=1)).isoformat()
            
            user_msg_id = chromadb_core.add_message(
                user_id=user_id,
                session_id=session_id,
                role="user",
                content=user_input,
                timestamp=user_timestamp  # 使用稍早的时间戳
            )
            saved_ids.append(user_msg_id)
        
        if llm_response:
            # assistant 消息使用基准时间戳（晚于 user）
            assistant_timestamp = base_timestamp.isoformat()
            
            assistant_msg_id = chromadb_core.add_message(
                user_id=user_id,
                session_id=session_id,
                role="assistant",
                content=llm_response,
                timestamp=assistant_timestamp  # 使用基准时间戳
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


def get_recent_messages_node(state: WorkflowState) -> Dict[str, Any]:
    """
    获取最近5条消息节点 - 仅获取最近的5条历史消息（按时间排序）
    
    职责：
    1. 从 state 中提取 user_id 和 session_id
    2. 获取该会话的最近5条历史消息
    3. 格式化为文本并更新 state
    
    Args:
        state: 工作流状态，需要包含：
            - user_id: 用户ID
            - session_id: 会话ID
            
    Returns:
        更新后的状态字典，包含：
            - history_text: 格式化的最近5条消息文本
            - recent_message_count: 消息数量
    """
    try:
        user_id = state.get("user_id")
        session_id = state.get("session_id")
        
        if not user_id or not session_id:
            return {
                "history_text": "",
                "recent_message_count": 0
            }
        
        # 获取最近5条消息
        messages = chromadb_core.get_all_messages(
            user_id=user_id,
            session_id=session_id,
            limit=5  # 只取最近5条
        )
        
        if not messages:
            return {
                "history_text": "",
                "recent_message_count": 0
            }
        
        # 格式化消息为文本
        history_lines = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            role_name = "用户" if role == "user" else "安然" if role == "assistant" else role
            history_lines.append(f"{role_name}：{content}")
        
        history_text = "\n".join(history_lines)
        
        logger.info(f"✅ 最近消息获取完成，共 {len(messages)} 条")
        
        return {
            "history_text": history_text,
            "recent_message_count": len(messages)
        }
        
    except Exception as e:
        logger.error(f"获取最近消息节点执行失败: {str(e)}", exc_info=True)
        return {
            "history_text": "",
            "recent_message_count": 0,
            "error": str(e)
        }


def get_similar_messages_node(state: WorkflowState) -> Dict[str, Any]:
    """
    获取相似消息节点 - 基于语义相似度检索相关记忆
    
    职责：
    1. 从 state 中提取 user_id、session_id 和 user_input
    2. 基于 user_input 检索相似度较高的历史消息
    3. 过滤相似度阈值（distance < 0.3）
    4. 格式化为文本并更新 state
    
    Args:
        state: 工作流状态，需要包含：
            - user_id: 用户ID
            - session_id: 会话ID
            - user_input: 用户输入（用于语义搜索）
            
    Returns:
        更新后的状态字典，包含：
            - similar_messages: 格式化的相似消息文本
            - similar_message_count: 相似消息数量
    """
    try:
        user_id = state.get("user_id")
        session_id = state.get("session_id")
        user_input = state.get("user_input", "")
        
        if not user_id or not session_id or not user_input:
            return {
                "similar_messages": "",
                "similar_message_count": 0
            }
        
        # 基于语义相似度搜索记忆
        memories = chromadb_core.search_memory(
            user_id=user_id,
            session_id=session_id,
            query_text=user_input,
            n_results=50,  # 搜索前50条
            include_metadata=True
        )
        
        if not memories:
            return {
                "similar_messages": "",
                "similar_message_count": 0
            }
        
        # 过滤相似度阈值：distance < 0.3 （越小越相似）
        SIMILARITY_THRESHOLD = 0.3
        filtered_memories = [
            mem for mem in memories 
            if mem.get("distance", 1.0) < SIMILARITY_THRESHOLD
        ]
        
        if not filtered_memories:
            return {
                "similar_messages": "",
                "similar_message_count": 0
            }
        
        # 格式化记忆为文本
        similar_lines = []
        for memory in filtered_memories:
            role = memory.get("role", "unknown")
            content = memory.get("content", "")
            distance = memory.get("distance", 1.0)
            role_name = "用户" if role == "user" else "安然" if role == "assistant" else role
            # 添加相似度信息
            similar_lines.append(f"{role_name}：{content} (相似度: {1-distance:.2f})")
        
        similar_messages = "\n".join(similar_lines)
        
        logger.info(f"✅ 相似消息搜索完成，共 {len(filtered_memories)} 条")
        
        return {
            "similar_messages": similar_messages,
            "similar_message_count": len(filtered_memories)
        }
        
    except Exception as e:
        logger.error(f"搜索相似消息节点执行失败: {str(e)}", exc_info=True)
        return {
            "similar_messages": "",
            "similar_message_count": 0,
            "error": str(e)
        }


def get_all_messages_node(state: WorkflowState) -> Dict[str, Any]:
    """
    获取所有消息节点 - 获取指定会话的所有历史消息（按时间排序）
    
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
