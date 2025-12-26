"""ChromaDB 服务层"""
import chromadb
from chromadb.config import Settings
from django.conf import settings
from typing import List, Dict, Any, Optional
from langchain_text_splitters import RecursiveCharacterTextSplitter
import uuid
import os


class ChromaDBService:
    """ChromaDB 服务类"""
    
    def __init__(self, collection_name: str = None):
        """初始化 ChromaDB 客户端"""
        # 使用传入的 collection_name，如果没有则使用配置的默认值
        self.collection_name = collection_name or settings.CHROMADB_DEFAULT_COLLECTION
        
        # 根据连接类型初始化客户端
        connection_type = getattr(settings, 'CHROMADB_CONNECTION_TYPE', 'http')
        
        if connection_type == 'http':
            # HTTP 连接模式
            host = getattr(settings, 'CHROMADB_HOST', 'localhost')
            port = getattr(settings, 'CHROMADB_PORT', 8000)
            
            self.client = chromadb.HttpClient(
                host=host,
                port=port,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
        else:
            # 本地持久化模式
            self.persist_directory = str(settings.CHROMADB_PERSIST_DIRECTORY)
            os.makedirs(self.persist_directory, exist_ok=True)
            
            self.client = chromadb.PersistentClient(
                path=self.persist_directory,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
        
        # 获取或创建集合
        distance_function = getattr(settings, 'CHROMADB_DISTANCE_FUNCTION', 'cosine')
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": distance_function}  # 使用配置的相似度计算方式
        )
    
    def get_collection_data(self) -> Dict[str, Any]:
        """
        获取 collection 中的所有数据
        
        Returns:
            包含所有文档数据的字典
        """
        try:
            # 获取集合中的所有数据，不包含 embeddings 避免 JSON 序列化问题
            all_data = self.collection.get(
                include=["documents", "metadatas"]  # 移除 embeddings
            )
            
            return {
                'collection_name': self.collection_name,
                'count': len(all_data.get('ids', [])),
                'ids': all_data.get('ids', []),
                'documents': all_data.get('documents', []),
                'metadatas': all_data.get('metadatas', [])
            }
        except Exception as e:
            return {
                'error': str(e),
                'collection_name': self.collection_name,
                'count': 0
            }
    
    def add_text_chunks(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        添加文本并自动分块存储到向量数据库
        
        Args:
            text: 文本内容
            metadata: 元数据
            chunk_size: 分块大小，如果不传则使用配置的默认值
            chunk_overlap: 分块重叠，如果不传则使用配置的默认值
            
        Returns:
            包含添加结果的字典
        """
        try:
            # 使用配置中的默认值
            chunk_size = chunk_size or getattr(settings, 'CHUNK_SIZE', 1000)
            chunk_overlap = chunk_overlap or getattr(settings, 'CHUNK_OVERLAP', 200)
            # 文本分块
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                length_function=len,
            )
            chunks = text_splitter.split_text(text)
            
            # 为每个块生成 ID 和元数据
            ids = []
            documents = []
            metadatas = []
            
            for i, chunk in enumerate(chunks):
                chunk_id = str(uuid.uuid4())
                ids.append(chunk_id)
                documents.append(chunk)
                
                chunk_metadata = metadata.copy() if metadata else {}
                chunk_metadata.update({
                    'chunk_index': i,
                    'total_chunks': len(chunks),
                    'chunk_size': len(chunk)
                })
                metadatas.append(chunk_metadata)
            
            # 添加到向量数据库
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            
            return {
                'success': True,
                'collection_name': self.collection_name,
                'chunk_count': len(chunks),
                'ids': ids,
                'message': f'成功添加 {len(chunks)} 个文本块到向量数据库'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': '添加文本失败'
            }
    
    def similarity_search(
        self,
        query: str,
        n_results: Optional[int] = None,
        where: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        相似度搜索
        
        Args:
            query: 查询文本
            n_results: 返回结果数量，如果不传则使用配置的默认值
            where: 元数据过滤条件
            
        Returns:
            搜索结果
        """
        try:
            # 使用配置中的默认值
            n_results = n_results or getattr(settings, 'DEFAULT_TOP_K', 5)
            # 执行查询
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where,
                include=["documents", "metadatas", "distances"]
            )
            
            # 格式化结果
            formatted_results = []
            if results and results.get('ids') and results['ids'][0]:
                for i in range(len(results['ids'][0])):
                    formatted_results.append({
                        'id': results['ids'][0][i],
                        'document': results['documents'][0][i] if results.get('documents') else '',
                        'metadata': results['metadatas'][0][i] if results.get('metadatas') else {},
                        'distance': results['distances'][0][i] if results.get('distances') else 0,
                        'similarity': 1 - results['distances'][0][i] if results.get('distances') else 0
                    })
            
            return {
                'success': True,
                'collection_name': self.collection_name,
                'query': query,
                'results': formatted_results,
                'count': len(formatted_results)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': '搜索失败'
            }
