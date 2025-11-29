# Redis 服务层 - 负责对话历史存储管理
from typing import List, Dict, Optional, Any
from app.initialize import redis
import json
import uuid
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class RedisService:
    """Redis 服务类 - 负责对话历史和会话元数据管理"""
    
    # Redis 键前缀
    CHAT_HISTORY_PREFIX = "chat:history:"
    # 对话历史默认过期时间（秒）- 7天
    CHAT_HISTORY_TTL = 604800  # 7 * 24 * 60 * 60
    
    async def get_chat_history(self, user_id: str) -> List[Dict[str, str]]:
        """从 Redis 获取对话历史
        
        Args:
            user_id: 用户ID（作为 Redis 键）
            
        Returns:
            对话历史列表，格式 [{"role": "user", "content": "..."}, ...]
        """
        if not redis.redis_client:
            logger.warning("Redis 客户端未初始化，跳过历史加载")
            return []
        
        try:
            cache_key = f"{self.CHAT_HISTORY_PREFIX}{user_id}"
            cached_data = await redis.redis_client.get(cache_key)
            
            if cached_data:
                data = json.loads(cached_data)
                # 兼容旧格式（直接是数组）和新格式（包含 metadata）
                if isinstance(data, list):
                    logger.info(f"从 Redis 加载对话历史（旧格式），用户ID: {user_id}, 消息数: {len(data)}")
                    return data
                elif isinstance(data, dict) and "messages" in data:
                    messages = data["messages"]
                    metadata = data.get("metadata", {})
                    conv_count = metadata.get("conversation_count", 0)
                    conv_id = metadata.get("conversation_id", "unknown")
                    logger.info(f"从 Redis 加载对话历史，用户ID: {user_id}, 会话ID: {conv_id}, 对话轮次: {conv_count}, 消息数: {len(messages)}")
                    return messages
                else:
                    logger.warning(f"对话历史格式异常，用户ID: {user_id}，返回空列表")
                    return []
            else:
                logger.info(f"Redis 中无对话历史，用户ID: {user_id}，返回空列表")
                return []
        except Exception as e:
            logger.error(f"读取对话历史失败，用户ID: {user_id}, 错误: {str(e)}")
            return []
    
    async def save_chat_history(self, user_id: str, session_id: str, messages: List[Dict[str, str]], increment_count: bool = False):
        """保存对话历史到 Redis（以 user_id 为键）
        
        Args:
            user_id: 用户ID（作为 Redis 键）
            session_id: 会话ID（存储在 metadata 中）
            messages: 对话历史列表
            increment_count: 是否增加对话轮次计数
        """
        logger.info(f"🔍 [RedisService] save_chat_history 被调用")
        logger.info(f"🔍 [RedisService] user_id={user_id}, messages_count={len(messages)}")
        
        if not redis.redis_client:
            logger.warning("⚠️ [RedisService] Redis 客户端未初始化，跳过历史保存")
            return
        
        logger.info(f"✅ [RedisService] Redis 客户端已初始化")
        
        try:
            cache_key = f"{self.CHAT_HISTORY_PREFIX}{user_id}"
            logger.info(f"🔑 [RedisService] 完整 Redis 键: {cache_key}")
            
            # 获取现有元数据（如果存在）
            existing_data = await redis.redis_client.get(cache_key)
            metadata = {}
            
            if existing_data:
                logger.info(f"📚 [RedisService] 找到现有数据")
                try:
                    existing = json.loads(existing_data)
                    if isinstance(existing, dict) and "metadata" in existing:
                        metadata = existing["metadata"]
                        logger.info(f"📚 [RedisService] 加载现有元数据: {metadata}")
                except Exception as parse_error:
                    logger.warning(f"⚠️ [RedisService] 解析现有数据失败: {parse_error}")
            else:
                logger.info(f"🆕 [RedisService] 未找到现有数据，将创建新记录")
            
            # 更新或初始化元数据
            if not metadata:
                # 首次创建
                metadata = {
                    "conversation_id": f"conv_{uuid.uuid4().hex[:12]}_{int(datetime.now().timestamp())}",
                    "conversation_count": 1,
                    "user_id": user_id,
                    "started_at": datetime.now().isoformat(),
                    "last_updated": datetime.now().isoformat()
                }
                logger.info(f"🆕 [RedisService] 首次创建对话历史，用户ID: {user_id}, 会话ID: {metadata['conversation_id']}")
            else:
                # 更新现有元数据
                if increment_count:
                    metadata["conversation_count"] = metadata.get("conversation_count", 0) + 1
                    metadata["conversation_id"] = f"conv_{uuid.uuid4().hex[:12]}_{int(datetime.now().timestamp())}"
                metadata["last_updated"] = datetime.now().isoformat()
                logger.info(f"🔄 [RedisService] 更新元数据")
            
            # 构建新格式数据
            data = {
                "metadata": metadata,
                "messages": messages
            }
            
            logger.info(f"💾 [RedisService] 开始写入 Redis...")
            await redis.redis_client.set(
                cache_key,
                json.dumps(data, ensure_ascii=False),
                ex=self.CHAT_HISTORY_TTL
            )
            logger.info(f"✅ [RedisService] 对话历史已保存，用户ID: {user_id}, 会话ID: {metadata['conversation_id']}, 对话轮次: {metadata['conversation_count']}, 消息数: {len(messages)}")
            
            # 验证写入
            verify_data = await redis.redis_client.get(cache_key)
            if verify_data:
                logger.info(f"✅ [RedisService] 验证成功：Redis 中确实存在该键")
            else:
                logger.error(f"❌ [RedisService] 验证失败：Redis 中未找到该键")
                
        except Exception as e:
            logger.error(f"❌ [RedisService] 保存对话历史失败，用户ID: {user_id}, 错误: {str(e)}", exc_info=True)
    
    async def append_message(self, user_id: str, session_id: str, role: str, content: str, increment_count: bool = False):
        """追加单条消息到对话历史
        
        Args:
            user_id: 用户ID（作为 Redis 键）
            session_id: 会话ID（存储在 metadata 中）
            role: 消息角色 (user/assistant/system)
            content: 消息内容
            increment_count: 是否增加对话轮次计数
        """
        logger.info(f"🔍 [RedisService] append_message 被调用")
        logger.info(f"🔍 [RedisService] user_id={user_id}, role={role}, content_length={len(content)}")
        logger.info(f"🔍 [RedisService] Redis 键: chat:history:{user_id}")
        
        history = await self.get_chat_history(user_id)
        logger.info(f"🔍 [RedisService] 当前历史消息数: {len(history)}")
        
        history.append({"role": role, "content": content})
        logger.info(f"🔍 [RedisService] 追加后消息数: {len(history)}")
        
        await self.save_chat_history(user_id, session_id, history, increment_count=increment_count)
        logger.info(f"✅ [RedisService] append_message 完成")
    
    async def get_conversation_metadata(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取对话元数据（会话ID、对话轮次等）
        
        Args:
            user_id: 用户ID
            
        Returns:
            元数据字典，包含 conversation_id, conversation_count, current_session_id 等
        """
        if not redis.redis_client:
            return None
        
        try:
            cache_key = f"{self.CHAT_HISTORY_PREFIX}{user_id}"
            cached_data = await redis.redis_client.get(cache_key)
            
            if cached_data:
                data = json.loads(cached_data)
                if isinstance(data, dict) and "metadata" in data:
                    return data["metadata"]
            return None
        except Exception as e:
            logger.error(f"获取对话元数据失败，用户ID: {user_id}, 错误: {str(e)}")
            return None
    
    async def start_new_conversation(self, user_id: str, session_id: str):
        """开始新对话，增加 conversation_count 并生成新的 conversation_id
        
        Args:
            user_id: 用户ID（作为 Redis 键）
            session_id: 会话ID（存储在 metadata 中）
        """
        if not redis.redis_client:
            logger.warning("Redis 客户端未初始化，跳过新对话")
            return
        
        try:
            cache_key = f"{self.CHAT_HISTORY_PREFIX}{user_id}"
            existing_data = await redis.redis_client.get(cache_key)
            
            messages = []
            metadata = {}
            
            if existing_data:
                data = json.loads(existing_data)
                if isinstance(data, dict):
                    messages = data.get("messages", [])
                    metadata = data.get("metadata", {})
                elif isinstance(data, list):
                    messages = data
            
            # 生成新的 conversation_id 并增加计数
            new_metadata = {
                "conversation_id": f"conv_{uuid.uuid4().hex[:12]}_{int(datetime.now().timestamp())}",
                "conversation_count": metadata.get("conversation_count", 0) + 1,
                "user_id": user_id,
                "started_at": metadata.get("started_at", datetime.now().isoformat()),
                "last_updated": datetime.now().isoformat()
            }
            
            # 保存更新后的数据
            data = {
                "metadata": new_metadata,
                "messages": messages
            }
            
            await redis.redis_client.set(
                cache_key,
                json.dumps(data, ensure_ascii=False),
                ex=self.CHAT_HISTORY_TTL
            )
            
            logger.info(f"开始新对话: 用户ID={user_id}, 会话ID={new_metadata['conversation_id']}, 轮次={new_metadata['conversation_count']}")
        except Exception as e:
            logger.error(f"开始新对话失败，用户ID: {user_id}, 错误: {str(e)}")
    
    async def clear_chat_history(self, user_id: str):
        """清空对话历史（对话结束时调用）
        
        Args:
            user_id: 用户ID
        """
        if not redis.redis_client:
            logger.warning("Redis 客户端未初始化，跳过历史清空")
            return
        
        try:
            cache_key = f"{self.CHAT_HISTORY_PREFIX}{user_id}"
            await redis.redis_client.delete(cache_key)
            logger.info(f"对话历史已清空: 用户ID={user_id}")
        except Exception as e:
            logger.error(f"清空对话历史失败，用户ID: {user_id}, 错误: {str(e)}")


# 创建全局服务实例
redis_service = RedisService()
