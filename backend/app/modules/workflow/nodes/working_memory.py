"""
工作记忆节点 (Working Memory) - 存储最近10轮对话的 FIFO 队列
"""
import json
import logging
from typing import Dict, Any, List
from app.initialize import redis
from app.core.config import settings
from app.core.session_token import get_session

logger = logging.getLogger(__name__)


class WorkingMemory:
    """工作记忆管理节点 (Working Memory)"""
    
    # Redis 键前缀
    MEMORY_PREFIX = "short_memory:"
    # 最大保留对话轮数（1轮 = user + assistant 2条消息）
    MAX_ROUNDS = 10
    MAX_MESSAGES = MAX_ROUNDS * 2  # 20条消息
    
    @staticmethod
    async def get_ttl_from_session(session_token: str) -> int:
        """
        从 session_token 获取过期时间（TTL）
        
        Args:
            session_token: 会话 Token
            
        Returns:
            int: 过期时间（秒），如果获取失败则返回默认值
        """
        try:
            # 获取 session 的 TTL
            session_key = f"{settings.SESSION_REDIS_PREFIX}{session_token}"
            ttl = await redis.redis_client.ttl(session_key)
            
            if ttl > 0:
                logger.info(f"📅 从 session 获取 TTL: {ttl} 秒")
                return ttl
            else:
                # Session 已过期或不存在，返回默认值
                default_ttl = settings.SESSION_TOKEN_EXPIRE_MINUTES * 60
                logger.warning(f"⚠️ Session TTL 无效 (ttl={ttl})，使用默认值: {default_ttl} 秒")
                return default_ttl
        except Exception as e:
            logger.error(f"❌ 获取 session TTL 失败: {e}")
            return settings.SESSION_TOKEN_EXPIRE_MINUTES * 60
    
    @staticmethod
    async def save_message(
        session_token: str,
        role: str,
        content: str,
        metadata: Dict[str, Any] = None
    ) -> bool:
        """
        保存单条消息到 Redis（自动维护 10 轮 FIFO 队列）
        
        Args:
            session_token: 会话 Token（用作 Redis 键）
            role: 消息角色 (user/assistant/system)
            content: 消息内容
            metadata: 额外元数据
            
        Returns:
            bool: 保存成功返回 True
        """
        if not redis.redis_client:
            logger.warning("⚠️ Redis 客户端未初始化")
            return False
        
        try:
            cache_key = f"{WorkingMemory.MEMORY_PREFIX}{session_token}"
            
            # 1. 获取现有消息列表
            existing_data = await redis.redis_client.get(cache_key)
            messages = []
            
            if existing_data:
                try:
                    data = json.loads(existing_data)
                    messages = data.get("messages", [])
                except json.JSONDecodeError:
                    logger.warning(f"⚠️ Redis 数据格式异常，重新初始化")
                    messages = []
            
            # 2. 构造新消息
            new_message = {
                "role": role,
                "content": content,
                "metadata": metadata or {}
            }
            
            # 3. 追加消息
            messages.append(new_message)
            
            # 4. FIFO 裁剪：保留最近 20 条消息（10轮对话）
            if len(messages) > WorkingMemory.MAX_MESSAGES:
                # 删除最早的消息
                removed_count = len(messages) - WorkingMemory.MAX_MESSAGES
                messages = messages[removed_count:]
                logger.info(f"🗑️ FIFO 裁剪：删除最早的 {removed_count} 条消息")
            
            # 5. 获取 session 的 TTL 并同步
            ttl = await WorkingMemory.get_ttl_from_session(session_token)
            
            # 6. 保存到 Redis，使用与 session 相同的过期时间
            data = {
                "session_token": session_token,
                "messages": messages,
                "total_messages": len(messages),
                "max_rounds": WorkingMemory.MAX_ROUNDS
            }
            
            await redis.redis_client.set(
                cache_key,
                json.dumps(data, ensure_ascii=False),
                ex=ttl  # 使用 session 的 TTL
            )
            
            logger.info(
                f"✅ 消息已保存 | session={session_token[:20]}... | "
                f"role={role} | 当前消息数={len(messages)}/{WorkingMemory.MAX_MESSAGES} | "
                f"TTL={ttl}秒"
            )
            return True
            
        except Exception as e:
            logger.error(f"❌ 保存消息失败: {e}", exc_info=True)
            return False
    
    @staticmethod
    async def get_messages(session_token: str) -> List[Dict[str, Any]]:
        """
        获取指定 session 的所有短期记忆消息
        
        Args:
            session_token: 会话 Token
            
        Returns:
            List[Dict]: 消息列表，格式 [{"role": "user", "content": "...", "metadata": {}}, ...]
        """
        if not redis.redis_client:
            logger.warning("⚠️ Redis 客户端未初始化")
            return []
        
        try:
            cache_key = f"{WorkingMemory.MEMORY_PREFIX}{session_token}"
            cached_data = await redis.redis_client.get(cache_key)
            
            if cached_data:
                data = json.loads(cached_data)
                messages = data.get("messages", [])
                logger.info(
                    f"📚 获取短期记忆 | session={session_token[:20]}... | "
                    f"消息数={len(messages)}"
                )
                return messages
            else:
                logger.info(f"📭 无短期记忆 | session={session_token[:20]}...")
                return []
                
        except Exception as e:
            logger.error(f"❌ 获取消息失败: {e}")
            return []
    
    @staticmethod
    async def get_recent_messages(session_token: str, limit: int = None) -> List[Dict[str, Any]]:
        """
        获取最近的 N 条消息
        
        Args:
            session_token: 会话 Token
            limit: 限制返回条数（None 表示返回全部）
            
        Returns:
            List[Dict]: 消息列表
        """
        messages = await WorkingMemory.get_messages(session_token)
        
        if limit and len(messages) > limit:
            return messages[-limit:]
        
        return messages
    
    @staticmethod
    async def clear_messages(session_token: str) -> bool:
        """
        清空指定 session 的短期记忆
        
        Args:
            session_token: 会话 Token
            
        Returns:
            bool: 清空成功返回 True
        """
        if not redis.redis_client:
            logger.warning("⚠️ Redis 客户端未初始化")
            return False
        
        try:
            cache_key = f"{WorkingMemory.MEMORY_PREFIX}{session_token}"
            result = await redis.redis_client.delete(cache_key)
            
            if result:
                logger.info(f"🗑️ 短期记忆已清空 | session={session_token[:20]}...")
                return True
            else:
                logger.warning(f"⚠️ 短期记忆不存在 | session={session_token[:20]}...")
                return False
                
        except Exception as e:
            logger.error(f"❌ 清空消息失败: {e}")
            return False
    
    @staticmethod
    async def get_memory_info(session_token: str) -> Dict[str, Any]:
        """
        获取短期记忆的统计信息
        
        Args:
            session_token: 会话 Token
            
        Returns:
            Dict: 统计信息，包含消息数、轮数、TTL 等
        """
        if not redis.redis_client:
            return {"error": "Redis 客户端未初始化"}
        
        try:
            cache_key = f"{WorkingMemory.MEMORY_PREFIX}{session_token}"
            
            # 获取数据
            cached_data = await redis.redis_client.get(cache_key)
            
            # 获取 TTL
            ttl = await redis.redis_client.ttl(cache_key)
            
            if cached_data:
                data = json.loads(cached_data)
                messages = data.get("messages", [])
                
                # 计算对话轮数（user + assistant = 1轮）
                user_count = sum(1 for msg in messages if msg.get("role") == "user")
                assistant_count = sum(1 for msg in messages if msg.get("role") == "assistant")
                rounds = min(user_count, assistant_count)
                
                return {
                    "session_token": session_token[:20] + "...",
                    "total_messages": len(messages),
                    "user_messages": user_count,
                    "assistant_messages": assistant_count,
                    "conversation_rounds": rounds,
                    "max_rounds": WorkingMemory.MAX_ROUNDS,
                    "ttl_seconds": ttl if ttl > 0 else 0,
                    "is_expired": ttl <= 0
                }
            else:
                return {
                    "session_token": session_token[:20] + "...",
                    "total_messages": 0,
                    "conversation_rounds": 0,
                    "max_rounds": WorkingMemory.MAX_ROUNDS,
                    "is_expired": True
                }
                
        except Exception as e:
            logger.error(f"❌ 获取记忆信息失败: {e}")
            return {"error": str(e)}


# 创建全局实例
working_memory = WorkingMemory()
