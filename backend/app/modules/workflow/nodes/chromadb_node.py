# ChromaDB 记忆节点 - LangGraph 工作流节点
from typing import Dict, Any, List
from app.modules.chromadb.core.chromadb_core import chromadb_core
from app.modules.workflow.core.state import WorkflowState
from app.core.config import settings
from lmnr import observe
import logging
import asyncio

logger = logging.getLogger(__name__)


@observe(name="get_memory_node", tags=["node", "memory", "retrieval"])
async def get_memory_node(state: WorkflowState) -> Dict[str, Any]:
    """
    获取记忆节点 - 从 ChromaDB 获取用户的对话记忆
    
    职责：
    1. 从 state 中提取 user_id、conversation_id 和 user_input
    2. 基于当前用户输入检索当前会话中相似度较高的历史对话记忆（语义搜索）
    3. 格式化为文本并更新 state
    
    Args:
        state: 工作流状态，需要包含：
            - user_id: 用户ID
            - conversation_id: 会话ID (优先)
            - session_id: 会话ID (后备)
            - user_input: 当前用户输入（用于语义搜索）
            
    Returns:
        更新后的状态字典，包含：
            - history_text: (已弃用) 空字符串
            - similar_messages: 当前会话中相似度较高的消息文本
            - recent_message_count: (已弃用) 0
            - similar_message_count: 相似消息数量
    """
    
    try:
        user_id = state.get("user_id")
        session_id = state.get("conversation_id") or state.get("session_id")
        user_input = state.get("user_input", "")
        
        if not user_id or not session_id:
            return {
                "history_text": "",
                "similar_messages": "",
                "recent_message_count": 0,
                "similar_message_count": 0
            }
        
        # ========== 2. 基于语义相似度检索相关记忆（当前会话） ==========
        similar_messages_text = ""
        similar_count = 0
        
        if user_input:  # 只有当有用户输入时才进行语义搜索
            memories = await asyncio.to_thread(
                chromadb_core.search_memory,
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
                        intent = memory.get("intent", "")  # 获取意图
                        role_name = "用户" if role == "user" else "安然" if role == "assistant" else role
                        
                        # 如果有意图，拼接到消息后面
                        if intent:
                            similar_lines.append(f"{role_name}：{content}（意图是{intent}，相似度: {1-distance:.2f}）")
                        else:
                            similar_lines.append(f"{role_name}：{content} (相似度: {1-distance:.2f})")
                    
                    similar_messages_text = "\n".join(similar_lines)
                    similar_count = len(filtered_memories)
                    logger.info(f"✅ 相似消息搜索完成，共 {similar_count} 条")
        
        return {
            "history_text": "",
            "similar_messages": similar_messages_text,
            "recent_message_count": 0,
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
async def save_memory_node(state: WorkflowState) -> Dict[str, Any]:
    """
    保存记忆节点 - 将本轮对话保存到 ChromaDB
    
    职责：
    1. 从 state 中提取 user_id、conversation_id (或 session_id)、user_input 和 llm_response
    2. 将用户输入和 LLM 回答分别保存到 ChromaDB（用于相似度检索）
    3. 对于 assistant 消息，添加意图信息到元数据
    4. 更新 state 中的保存状态
    
    Args:
        state: 工作流状态，需要包含：
            - user_id: 用户ID
            - conversation_id: 会话ID (优先)
            - session_id: 会话ID (后备)
            - user_input: 用户输入
            - llm_response: LLM 回答
            - intent: 意图（可选）
            - intent_confidence: 意图置信度（可选）
            - intents: 所有意图列表（可选）
            
    Returns:
        更新后的状态字典，包含：
            - memory_saved: 是否成功保存
            - saved_message_ids: 保存的消息ID列表
    """
    
    try:
        user_id = state.get("user_id")
        # 优先使用 conversation_id，如果没有则使用 session_id
        session_id = state.get("conversation_id") or state.get("session_id")
        user_input = state.get("user_input", "")
        llm_response = state.get("llm_response", "")
        
        # 获取意图信息
        intent = state.get("intent", "")
        intent_confidence = state.get("intent_confidence", 0.0)
        intents = state.get("intents", [])
        
        if not user_id or not session_id:
            return {
                "memory_saved": False,
                "saved_message_ids": []
            }
            
        # 0. 防止重复执行 (Graph 可能会因多路汇聚触发多次)
        if state.get("memory_saved"):
            logger.info("⚠️ ChromaDB 记忆已保存，跳过重复执行")
            return {}
        
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
            
            user_msg_id = await asyncio.to_thread(
                chromadb_core.add_message,
                user_id=user_id,
                session_id=session_id,
                role="user",
                content=user_input,
                timestamp=user_timestamp,
                intent=intent if intent else None,
                intent_confidence=intent_confidence if intent_confidence > 0 else None,
                intents=intents if intents else None
            )
            saved_ids.append(user_msg_id)
        
        if llm_response:
            # assistant 消息使用基准时间戳（晚于 user）
            assistant_timestamp = base_timestamp.isoformat()
            
            assistant_msg_id = await asyncio.to_thread(
                chromadb_core.add_message,
                user_id=user_id,
                session_id=session_id,
                role="assistant",
                content=llm_response,
                timestamp=assistant_timestamp,
                intent=intent if intent else None,
                intent_confidence=intent_confidence if intent_confidence > 0 else None,
                intents=intents if intents else None
            )
            saved_ids.append(assistant_msg_id)
        
        logger.info(f"✅ ChromaDB 记忆保存完成，共保存 {len(saved_ids)} 条消息")
        if intent:
            logger.info(f"🎯 已将意图信息保存: {intent} (置信度: {intent_confidence:.2f})")
        
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
        # 注意：这里如果也被用到，也应该改为异步，但目前主要是 get_similar_messages_node 被使用
        # 为了保险起见，暂不修改此未使用节点的签名，以免影响其他未知的引用
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


async def get_similar_messages_node(state: WorkflowState) -> Dict[str, Any]:
    """
    获取相似消息节点 - 基于语义相似度检索相关记忆
    
    职责：
    1. 从 state 中提取 user_id、conversation_id (或 session_id) 和 user_input
    2. 基于 user_input 检索相似度较高的历史消息
    3. 过滤相似度阈值（distance < 0.3）
    4. 格式化为文本并更新 state
    
    Args:
        state: 工作流状态，需要包含：
            - user_id: 用户ID
            - conversation_id: 会话ID (优先)
            - session_id: 会话ID (后备)
            - user_input: 用户输入（用于语义搜索）
            
    Returns:
        更新后的状态字典，包含：
            - similar_messages: 格式化的相似消息文本
            - similar_message_count: 相似消息数量
    """
    try:
        user_id = state.get("user_id")
        # 优先使用 conversation_id，如果没有则使用 session_id
        session_id = state.get("conversation_id") or state.get("session_id")
        user_input = state.get("user_input", "")
        
        if not user_id or not session_id or not user_input:
            return {
                "similar_messages": "",
                "similar_message_count": 0
            }
        
        # 基于语义相似度搜索记忆
        memories = await asyncio.to_thread(
            chromadb_core.search_memory,
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
