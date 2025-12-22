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
            logger.info(f"✅ 集合 '{self.collection_name}' 已就绪 (距离度量: {distance_metric})")
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
        timestamp: Optional[str] = None
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
            
        Returns:
            str: 消息 ID
        """
        try:
            collection = self._get_or_create_collection()
            
            # 生成消息 ID
            if not message_id:
                message_id = f"{user_id}_{session_id}_{int(datetime.now().timestamp() * 1000)}"
            
            # 生成时间戳
            if not timestamp:
                timestamp = datetime.now().isoformat()
            
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
            
            logger.info(f"✅ 消息已存储: {message_id[:50]}...")
            return message_id
            
        except Exception as e:
            logger.error(f"❌ 添加消息失败: {e}")
            raise
    
    def search_memory(
        self,
        user_id: str,
        session_id: str,
        query_text: str,
        n_results: int = 5,
        include_metadata: bool = True
    ) -> List[Dict]:
        """
        搜索记忆（基于语义相似度）
        
        Args:
            user_id: 用户 ID
            session_id: 会话 ID
            query_text: 查询文本
            n_results: 返回结果数量
            include_metadata: 是否包含元数据
            
        Returns:
            List[Dict]: 相似的消息列表，格式：
                [
                    {
                        "id": "消息ID",
                        "content": "消息内容",
                        "role": "user/assistant",
                        "timestamp": "2024-01-01T00:00:00",
                        "distance": 0.123  # 相似度距离（越小越相似）
                    },
                    ...
                ]
        """
        try:
            collection = self._get_or_create_collection()
            
            # 构建过滤条件（只查询指定用户和会话的记忆）
            where_filter = {
                "$and": [
                    {"user_id": {"$eq": user_id}},
                    {"session_id": {"$eq": session_id}}
                ]
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
            
            logger.info(f"✅ 检索到 {len(formatted_results)} 条记忆")
            return formatted_results
            
        except Exception as e:
            logger.error(f"❌ 搜索记忆失败: {e}")
            raise
    
    def get_all_messages(
        self,
        user_id: str,
        session_id: str,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        获取指定会话的所有消息（按时间顺序）
        
        Args:
            user_id: 用户 ID
            session_id: 会话 ID
            limit: 限制返回数量（None 表示全部）
            
        Returns:
            List[Dict]: 消息列表
        """
        try:
            collection = self._get_or_create_collection()
            
            # 构建过滤条件
            where_filter = {
                "$and": [
                    {"user_id": {"$eq": user_id}},
                    {"session_id": {"$eq": session_id}}
                ]
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
            
            # 按时间排序
            formatted_results.sort(key=lambda x: x.get("timestamp", ""))
            
            # 限制数量
            if limit:
                formatted_results = formatted_results[:limit]
            
            logger.info(f"✅ 获取到 {len(formatted_results)} 条消息")
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
                logger.info(f"✅ 已删除 {count} 条会话记忆")
                return count
            
            logger.info("⚠️ 未找到需要删除的记忆")
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
            logger.info(f"✅ 会话消息数: {count}")
            return count
            
        except Exception as e:
            logger.error(f"❌ 统计消息失败: {e}")
            raise


# 全局实例
chromadb_core = ChromaDBCore()
