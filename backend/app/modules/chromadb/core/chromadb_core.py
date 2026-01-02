# ChromaDB 核心功能 - 短期记忆管理
import chromadb
from typing import List, Dict, Optional
from datetime import datetime
import logging
from app.initialize.chromadb import get_chromadb_client
from app.core.config import settings

logger = logging.getLogger(__name__)


class ChromaDBCore:
    """
    ChromaDB 核心服务 - 管理短期记忆（对话历史）
    
    功能：
    - 将对话消息向量化并存储到 ChromaDB
    - 基于相似度检索用户的短期记忆
    - 支持按 user_id 和 session_id 过滤
    """
    
    def __init__(self):
        """初始化 ChromaDB 核心服务"""
        self.client = None
        self.collection = None
        # 从配置中获取集合名称
        self.collection_name = settings.CHROMADB_COLLECTION
        
    def _ensure_client(self):
        """确保 ChromaDB 客户端已初始化"""
        if self.client is None:
            self.client = get_chromadb_client()
            
    def _get_or_create_collection(self) -> chromadb.Collection:
        """
        获取或创建短期记忆集合
        
        Returns:
            chromadb.Collection: ChromaDB 集合实例
        """
        self._ensure_client()
        
        try:
            # 获取距离度量方式
            distance_metric = settings.CHROMADB_DISTANCE_METRIC.lower()
            
            # 获取或创建集合
            collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={
                    "hnsw:space": distance_metric,  # 从环境变量读取距离度量方式
                    "description": "记忆存储 - 对话历史",
                    "created_at": datetime.now().isoformat()
                }
            )
            return collection
        except Exception as e:
            logger.error(f"❌ 创建/获取集合失败: {e}")
            raise
    
    def add_message(
        self,
        user_id: str,
        session_id: str,
        role: str,
        content: str,
        message_id: Optional[str] = None,
        timestamp: Optional[str] = None,
        check_duplicate: bool = True  # 新增：是否检查重复
    ) -> str:
        """
        添加消息到短期记忆
        
        Args:
            user_id: 用户 ID
            session_id: 会话 ID
            role: 消息角色 (user/assistant)
            content: 消息内容
            message_id: 消息 ID（可选，自动生成）
            timestamp: 时间戳（可选，自动生成）
            check_duplicate: 是否检查重复（默认检查）
            
        Returns:
            str: 消息 ID
        """
        try:
            collection = self._get_or_create_collection()
            
            # 生成时间戳（在检查重复之前）
            if not timestamp:
                timestamp = datetime.now().isoformat()
            
            # 防重复检查：检查最近 5 秒内是否有相同的消息
            if check_duplicate:
                # 获取最近的 3 条消息（按时间降序）
                recent_messages = self.get_all_messages(
                    user_id=user_id,
                    session_id=session_id,
                    limit=3
                )
                
                # 检查是否有完全相同的消息（role 和 content 都相同）
                current_time = datetime.fromisoformat(timestamp)
                for msg in recent_messages:
                    if msg.get("role") == role and msg.get("content") == content:
                        # 检查时间间隔（防止 5 秒内重复）
                        msg_timestamp = msg.get("timestamp")
                        msg_id = msg.get("id")
                        
                        if msg_timestamp and msg_id:
                            msg_time = datetime.fromisoformat(msg_timestamp)
                            time_diff = (current_time - msg_time).total_seconds()
                            
                            if abs(time_diff) < 5:  # 5 秒内的重复消息
                                logger.warning(f"⚠️ 检测到重复消息，跳过保存: {content[:30]}...")
                                logger.warning(f"   时间间隔: {abs(time_diff):.2f} 秒")
                                # 返回已存在的消息 ID
                                return msg_id
            
            # 生成消息 ID
            if not message_id:
                message_id = f"{user_id}_{session_id}_{int(datetime.now().timestamp() * 1000)}"
            
            # 元数据（用于过滤和查询）
            metadata = {
                "user_id": user_id,
                "session_id": session_id,
                "role": role,
                "timestamp": timestamp
            }
            
            # 添加到集合（ChromaDB 会自动生成 embedding）
            collection.add(
                documents=[content],
                metadatas=[metadata],
                ids=[message_id]
            )
            
            return message_id
            
        except Exception as e:
            logger.error(f"❌ 添加消息失败: {e}")
            raise
    
    def search_memory(
        self,
        user_id: str,
        session_id: Optional[str] = None,  # 修改为可选
        query_text: str = "",
        n_results: int = 5,
        include_metadata: bool = True
    ) -> List[Dict]:
        """
        搜索记忆（基于语义相似度）
        
        Args:
            user_id: 用户 ID
            session_id: 会话 ID（可选，None 表示搜索用户所有会话的记忆）
            query_text: 查询文本
            n_results: 返回结果数量
            include_metadata: 是否包含元数据
            
        Returns:
            List[Dict]: 相似的消息列表
        """
        try:
            collection = self._get_or_create_collection()
            
            # 构建过滤条件
            if session_id:
                # 指定会话
                where_filter = {
                    "$and": [
                        {"user_id": {"$eq": user_id}},
                        {"session_id": {"$eq": session_id}}
                    ]
                }
            else:
                # 不限制会话，只按 user_id 过滤
                where_filter = {
                    "user_id": {"$eq": user_id}
                }
            
            # 执行查询
            results = collection.query(
                query_texts=[query_text],
                n_results=n_results,
                where=where_filter,
                include=["documents", "metadatas", "distances"]
            )
            
            # 格式化结果
            formatted_results = []
            if results and results['ids'] and len(results['ids'][0]) > 0:
                for i in range(len(results['ids'][0])):
                    result_item = {
                        "id": results['ids'][0][i],
                        "content": results['documents'][0][i],
                        "distance": results['distances'][0][i]
                    }
                    
                    # 添加元数据
                    if include_metadata and results['metadatas'][0][i]:
                        metadata = results['metadatas'][0][i]
                        result_item.update({
                            "role": metadata.get("role"),
                            "timestamp": metadata.get("timestamp"),
                            "user_id": metadata.get("user_id"),
                            "session_id": metadata.get("session_id")
                        })
                    
                    formatted_results.append(result_item)
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"❌ 搜索记忆失败: {e}")
            raise
    
    def get_all_messages(
        self,
        user_id: str,
        session_id: Optional[str] = None,  # 修改为可选
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        获取指定会话的所有消息（按时间排序）
        
        Args:
            user_id: 用户 ID
            session_id: 会话 ID（可选，None 表示获取用户所有会话的消息）
            limit: 限制返回数量（None 表示全部）
            
        Returns:
            List[Dict]: 消息列表
        """
        try:
            collection = self._get_or_create_collection()
            
            # 构建过滤条件
            if session_id:
                # 指定会话
                where_filter = {
                    "$and": [
                        {"user_id": {"$eq": user_id}},
                        {"session_id": {"$eq": session_id}}
                    ]
                }
            else:
                # 不限制会话，只按 user_id 过滤
                where_filter = {
                    "user_id": {"$eq": user_id}
                }
            
            # 获取所有匹配的记录
            results = collection.get(
                where=where_filter,
                include=["documents", "metadatas"]
            )
            
            # 格式化结果
            formatted_results = []
            if results and results['ids']:
                for i in range(len(results['ids'])):
                    metadata = results['metadatas'][i]
                    formatted_results.append({
                        "id": results['ids'][i],
                        "content": results['documents'][i],
                        "role": metadata.get("role"),
                        "timestamp": metadata.get("timestamp"),
                        "user_id": metadata.get("user_id"),
                        "session_id": metadata.get("session_id")
                    })
            
            # 按时间降序排列（最新的在前）
            formatted_results.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            
            # 限制数量（取最新N条）
            if limit:
                formatted_results = formatted_results[:limit]
            
            # 反转为升序（最旧在前），确保对话按时间流正确排列
            formatted_results.reverse()
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"❌ 获取消息失败: {e}")
            raise
    
    def delete_session_memory(
        self,
        user_id: str,
        session_id: str
    ) -> int:
        """
        删除指定会话的所有记忆
        
        Args:
            user_id: 用户 ID
            session_id: 会话 ID
            
        Returns:
            int: 删除的记录数
        """
        try:
            collection = self._get_or_create_collection()
            
            # 先获取要删除的记录
            where_filter = {
                "$and": [
                    {"user_id": {"$eq": user_id}},
                    {"session_id": {"$eq": session_id}}
                ]
            }
            
            results = collection.get(
                where=where_filter,
                include=["documents"]
            )
            
            # 删除记录
            if results and results['ids']:
                collection.delete(ids=results['ids'])
                count = len(results['ids'])
                return count
            
            return 0
            
        except Exception as e:
            logger.error(f"❌ 删除会话记忆失败: {e}")
            raise
    
    def count_messages(
        self,
        user_id: str,
        session_id: str
    ) -> int:
        """
        统计指定会话的消息数量
        
        Args:
            user_id: 用户 ID
            session_id: 会话 ID
            
        Returns:
            int: 消息数量
        """
        try:
            collection = self._get_or_create_collection()
            
            where_filter = {
                "$and": [
                    {"user_id": {"$eq": user_id}},
                    {"session_id": {"$eq": session_id}}
                ]
            }
            
            results = collection.get(
                where=where_filter,
                include=[]
            )
            
            count = len(results['ids']) if results and results['ids'] else 0
            return count
            
        except Exception as e:
            logger.error(f"❌ 统计消息失败: {e}")
            raise


# 全局实例
chromadb_core = ChromaDBCore()
