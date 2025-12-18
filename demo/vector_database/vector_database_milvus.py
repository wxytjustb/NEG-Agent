"""
Milvus 连接和使用示例
演示如何连接、创建集合、插入数据、查询数据等操作
"""

from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility
import requests
import logging

# 从配置文件导入配置
from config import (
    MILVUS_HOST,
    MILVUS_PORT,
    COLLECTION_NAME,
    OLLAMA_MODEL,
    OLLAMA_EMBED_URL,
    VECTOR_DIMENSION,
    MILVUS_INDEX_TYPE,
    MILVUS_METRIC_TYPE,
    MILVUS_INDEX_PARAMS,
    MILVUS_SEARCH_PARAMS,
    DEFAULT_N_RESULTS,
    LOG_LEVEL,
    LOG_FORMAT
)

# 配置日志
logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)
logger = logging.getLogger(__name__)


# ==================== 测试数据准备 ====================

class TestData:
    """测试数据配置类"""
    
    @staticmethod
    def get_sample_documents():
        """获取示例文档数据(包含多个用户和会话)"""
        return [
            # 用户 334 - 会话 1 (AI学习相关)
            {"document": "Python 是一种高级编程语言,以其简洁的语法和强大的功能而闻名,非常适合初学者学习编程。",
             "metadata": {"category": "编程", "source": "教程", "difficulty": "初级"},
             "user_id": "334", "session_id": "sess_334_001"},
            
            {"document": "机器学习是人工智能的核心分支,通过算法让计算机从数据中学习规律,无需明确编程。",
             "metadata": {"category": "AI", "source": "教程", "difficulty": "中级"},
             "user_id": "334", "session_id": "sess_334_001"},
            
            {"document": "监督学习是机器学习的一种方法,使用标注好的数据集来训练模型,常用于分类和回归任务。",
             "metadata": {"category": "AI", "source": "教程", "difficulty": "中级"},
             "user_id": "334", "session_id": "sess_334_001"},
            
            # 用户 334 - 会话 2 (深度学习相关)
            {"document": "深度学习使用多层神经网络来解决复杂问题,在图像识别、语音识别等领域取得了突破性进展。",
             "metadata": {"category": "AI", "source": "教程", "difficulty": "高级"},
             "user_id": "334", "session_id": "sess_334_002"},
            
            {"document": "卷积神经网络(CNN)是专门用于处理图像数据的深度学习架构,在计算机视觉任务中表现出色。",
             "metadata": {"category": "AI", "source": "论文", "difficulty": "高级"},
             "user_id": "334", "session_id": "sess_334_002"},
            
            {"document": "循环神经网络(RNN)擅长处理序列数据,广泛应用于自然语言处理和时间序列预测。",
             "metadata": {"category": "AI", "source": "论文", "difficulty": "高级"},
             "user_id": "334", "session_id": "sess_334_002"},
            
            # 用户 556 - 会话 1 (数据库和NLP)
            {"document": "Milvus 是一个高性能的向量数据库,专为 AI 应用设计,支持海量向量数据的高效检索。",
             "metadata": {"category": "数据库", "source": "文档", "difficulty": "中级"},
             "user_id": "556", "session_id": "sess_556_001"},
            
            {"document": "向量数据库通过将数据转换为高维向量来存储,能够快速进行相似度搜索,是RAG系统的核心组件。",
             "metadata": {"category": "数据库", "source": "文档", "difficulty": "中级"},
             "user_id": "556", "session_id": "sess_556_001"},
            
            {"document": "自然语言处理(NLP)使计算机能够理解和生成人类语言,涵盖文本分类、情感分析、机器翻译等任务。",
             "metadata": {"category": "AI", "source": "教程", "difficulty": "中级"},
             "user_id": "556", "session_id": "sess_556_001"},
            
            {"document": "Transformer模型彻底改变了NLP领域,通过自注意力机制实现了更好的长距离依赖建模。",
             "metadata": {"category": "AI", "source": "论文", "difficulty": "高级"},
             "user_id": "556", "session_id": "sess_556_001"},
            
            # 用户 556 - 会话 2 (大语言模型)
            {"document": "大语言模型(LLM)如GPT、Claude等,通过在海量文本数据上预训练,展现出强大的语言理解和生成能力。",
             "metadata": {"category": "AI", "source": "研究", "difficulty": "高级"},
             "user_id": "556", "session_id": "sess_556_002"},
            
            {"document": "检索增强生成(RAG)结合了信息检索和生成模型,能够提供更准确、更具时效性的回答。",
             "metadata": {"category": "AI", "source": "研究", "difficulty": "高级"},
             "user_id": "556", "session_id": "sess_556_002"},
            
            # 用户 778 - 会话 1 (Web开发)
            {"document": "FastAPI 是一个现代化的 Python Web 框架,基于类型提示提供自动API文档生成,性能接近Node.js和Go。",
             "metadata": {"category": "Web开发", "source": "文档", "difficulty": "中级"},
             "user_id": "778", "session_id": "sess_778_001"},
            
            {"document": "RESTful API 是一种软件架构风格,使用HTTP方法(GET、POST、PUT、DELETE)来操作资源。",
             "metadata": {"category": "Web开发", "source": "教程", "difficulty": "初级"},
             "user_id": "778", "session_id": "sess_778_001"},
            
            {"document": "Redis 是一个高性能的内存键值存储数据库,支持字符串、列表、集合、哈希等多种数据结构,常用于缓存和会话管理。",
             "metadata": {"category": "数据库", "source": "文档", "difficulty": "中级"},
             "user_id": "778", "session_id": "sess_778_001"},
            
            # 用户 778 - 会话 2 (前端开发)
            {"document": "Vue.js 是一个渐进式JavaScript框架,易于上手,适合构建用户界面和单页应用程序。",
             "metadata": {"category": "前端开发", "source": "文档", "difficulty": "初级"},
             "user_id": "778", "session_id": "sess_778_002"},
            
            {"document": "React 是由Facebook开发的前端库,采用组件化开发模式和虚拟DOM技术,拥有庞大的生态系统。",
             "metadata": {"category": "前端开发", "source": "文档", "difficulty": "中级"},
             "user_id": "778", "session_id": "sess_778_002"},
            
            # 用户 999 - 会话 1 (DevOps)
            {"document": "Docker 是一个容器化平台,可以将应用程序及其依赖打包成轻量级、可移植的容器,简化部署流程。",
             "metadata": {"category": "DevOps", "source": "文档", "difficulty": "中级"},
             "user_id": "999", "session_id": "sess_999_001"},
            
            {"document": "Kubernetes 是一个容器编排平台,用于自动化部署、扩展和管理容器化应用程序。",
             "metadata": {"category": "DevOps", "source": "文档", "difficulty": "高级"},
             "user_id": "999", "session_id": "sess_999_001"},
            
            {"document": "CI/CD 持续集成和持续部署是现代软件开发的最佳实践,通过自动化测试和部署提高开发效率。",
             "metadata": {"category": "DevOps", "source": "教程", "difficulty": "中级"},
             "user_id": "999", "session_id": "sess_999_001"},
        ]


# ==================== 核心业务逻辑 ====================

class MilvusClient:
    """Milvus 客户端封装类"""
    
    def __init__(self, host: str = MILVUS_HOST, port: int = MILVUS_PORT):
        """初始化 Milvus 客户端"""
        self.host = host
        self.port = port
        self.collection = None
        self.alias = "default"
    
    def connect(self):
        """连接到 Milvus 服务器"""
        try:
            connections.connect(
                alias=self.alias,
                host=self.host,
                port=self.port
            )
            logger.info(f"✅ 成功连接到 Milvus 服务器: {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"❌ 连接 Milvus 失败: {str(e)}")
            raise
    
    def create_collection(self, collection_name: str = COLLECTION_NAME):
        """创建或获取集合"""
        try:
            # 如果集合已存在，先删除
            if utility.has_collection(collection_name):
                utility.drop_collection(collection_name)
                logger.info(f"🗑️ 删除已存在的集合: {collection_name}")
            
            # 定义字段 Schema
            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=VECTOR_DIMENSION),
                FieldSchema(name="document", dtype=DataType.VARCHAR, max_length=65535),
                FieldSchema(name="user_id", dtype=DataType.VARCHAR, max_length=100),
                FieldSchema(name="session_id", dtype=DataType.VARCHAR, max_length=200),
                FieldSchema(name="category", dtype=DataType.VARCHAR, max_length=100),
                FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=100),
                FieldSchema(name="difficulty", dtype=DataType.VARCHAR, max_length=50),
            ]
            
            # 创建集合 Schema
            schema = CollectionSchema(
                fields=fields,
                description=f"使用 {OLLAMA_MODEL} 的集合"
            )
            
            # 创建集合
            self.collection = Collection(
                name=collection_name,
                schema=schema
            )
            
            logger.info(f"✅ 集合 '{collection_name}' 已创建")
            
            # 创建索引（使用 IP 内积，更适合归一化向量）
            index_params = {
                "index_type": MILVUS_INDEX_TYPE,
                "metric_type": MILVUS_METRIC_TYPE,
                "params": MILVUS_INDEX_PARAMS
            }
            self.collection.create_index(
                field_name="embedding",
                index_params=index_params
            )
            logger.info(f"✅ 向量索引已创建 (使用 {MILVUS_METRIC_TYPE} 度量)")
            
            return self.collection
        except Exception as e:
            logger.error(f"❌ 创建集合失败: {str(e)}")
            raise
    
    def get_embedding(self, text: str):
        """使用 Ollama 生成文本嵌入向量"""
        try:
            response = requests.post(
                OLLAMA_EMBED_URL,
                json={
                    "model": OLLAMA_MODEL,
                    "input": text
                }
            )
            response.raise_for_status()
            embedding = response.json()["embeddings"][0]
            return embedding
        except Exception as e:
            logger.error(f"❌ 生成嵌入向量失败: {str(e)}")
            raise
    
    def add_documents(self, documents_data: list):
        """添加文档到集合"""
        try:
            logger.info(f"🔧 使用 Ollama 模型: {OLLAMA_MODEL}")
            
            embeddings = []
            documents = []
            user_ids = []
            session_ids = []
            categories = []
            sources = []
            difficulties = []
            
            for data in documents_data:
                # 生成嵌入向量
                embedding = self.get_embedding(data["document"])
                embeddings.append(embedding)
                
                # 提取字段
                documents.append(data["document"])
                user_ids.append(data["user_id"])
                session_ids.append(data["session_id"])
                categories.append(data["metadata"].get("category", ""))
                sources.append(data["metadata"].get("source", ""))
                difficulties.append(data["metadata"].get("difficulty", ""))
            
            # 插入数据
            entities = [
                embeddings,
                documents,
                user_ids,
                session_ids,
                categories,
                sources,
                difficulties
            ]
            
            self.collection.insert(entities)
            self.collection.flush()
            
            logger.info(f"✅ 成功添加 {len(documents_data)} 个文档")
        except Exception as e:
            logger.error(f"❌ 添加文档失败: {str(e)}")
            raise
    
    def query_documents(self, query_text: str, n_results: int = DEFAULT_N_RESULTS,
                       user_id: str = None, session_id: str = None):
        """查询相似文档"""
        try:
            # 加载集合到内存
            self.collection.load()
            
            # 生成查询向量
            query_embedding = self.get_embedding(query_text)
            
            # 构建过滤表达式
            expr = None
            if user_id and session_id:
                expr = f'user_id == "{user_id}" && session_id == "{session_id}"'
            elif user_id:
                expr = f'user_id == "{user_id}"'
            elif session_id:
                expr = f'session_id == "{session_id}"'
            
            if expr:
                logger.info(f"🔍 使用过滤条件查询: {expr}")
            
            # 执行搜索（使用 IP 内积度量）
            search_params = {
                "metric_type": MILVUS_METRIC_TYPE,
                "params": MILVUS_SEARCH_PARAMS
            }
            
            results = self.collection.search(
                data=[query_embedding],
                anns_field="embedding",
                param=search_params,
                limit=n_results,
                expr=expr,
                output_fields=["document", "user_id", "session_id", "category", "source", "difficulty"]
            )
            
            logger.info(f"✅ 查询成功,返回 {len(results[0])} 个结果")
            return results[0]
        except Exception as e:
            logger.error(f"❌ 查询失败: {str(e)}")
            raise
    
    def get_collection_info(self):
        """获取集合信息"""
        try:
            self.collection.flush()
            count = self.collection.num_entities
            logger.info(f"📊 集合中共有 {count} 个文档")
            return count
        except Exception as e:
            logger.error(f"❌ 获取集合信息失败: {str(e)}")
            raise
    
    def disconnect(self):
        """断开连接"""
        try:
            connections.disconnect(self.alias)
            logger.info("✅ 已断开 Milvus 连接")
        except Exception as e:
            logger.error(f"❌ 断开连接失败: {str(e)}")


# ==================== 辅助函数 ====================

def initialize_client():
    """初始化并连接 Milvus 客户端"""
    print("\n" + "="*60)
    print("🚀 初始化 Milvus 客户端")
    print("="*60)
    
    client = MilvusClient()
    client.connect()
    client.create_collection()
    return client


def load_sample_data(client: MilvusClient):
    """加载示例文档数据"""
    print("\n" + "="*60)
    print("📝 添加示例文档")
    print("="*60)
    
    sample_data = TestData.get_sample_documents()
    client.add_documents(sample_data)
    
    # 统计信息
    user_ids = set(d["user_id"] for d in sample_data)
    session_ids = set(d["session_id"] for d in sample_data)
    print(f"\n📊 数据统计:")
    print(f"   - 用户数: {len(user_ids)} ({', '.join(sorted(user_ids))})")
    print(f"   - 会话数: {len(session_ids)}")


def print_query_results(query: str, results, show_details: bool = True):
    """打印查询结果"""
    print(f"\n查询: '{query}'")
    print(f"找到 {len(results)} 个结果\n")
    
    if show_details:
        for i, hit in enumerate(results, 1):
            print(f"{i}. [{hit.entity.get('category')}] {hit.entity.get('document')[:60]}...")
            print(f"   用户: {hit.entity.get('user_id')}, "
                  f"会话: {hit.entity.get('session_id')}, "
                  f"距离: {hit.distance:.4f}")


# ==================== 主程序 ====================

if __name__ == "__main__":
    try:
        # 1. 初始化客户端
        milvus_client = initialize_client()
        
        # 2. 加载示例数据
        load_sample_data(milvus_client)
        
        # 3. 查看集合信息
        print("\n" + "="*60)
        print("📊 集合信息")
        print("="*60)
        milvus_client.get_collection_info()
        
        # 4. 查询测试 - 全局查询
        print("\n" + "="*60)
        print("🔍 全局查询测试")
        print("="*60)
        
        test_query = "人工智能和机器学习"
        results = milvus_client.query_documents(
            query_text=test_query,
            n_results=5
        )
        print_query_results(test_query, results)
        
        # 5. 查询测试 - 按用户过滤
        print("\n" + "="*60)
        print("👥 按用户查询测试")
        print("="*60)
        
        for user_id in ["334", "556", "778"]:
            print(f"\n--- 用户 {user_id} ---")
            results = milvus_client.query_documents(
                query_text=test_query,
                n_results=3,
                user_id=user_id
            )
            print_query_results(f"{test_query} (user={user_id})", results, show_details=False)
            
            for i, hit in enumerate(results, 1):
                print(f"  {i}. {hit.entity.get('document')[:50]}... (距离: {hit.distance:.4f})")
        
        # 6. 查询测试 - 按会话过滤
        print("\n" + "="*60)
        print("💬 按会话查询测试")
        print("="*60)
        
        for session_id in ["sess_334_001", "sess_556_001", "sess_778_002"]:
            print(f"\n--- 会话 {session_id} ---")
            results = milvus_client.query_documents(
                query_text="深度学习技术",
                n_results=2,
                session_id=session_id
            )
            print(f"找到 {len(results)} 个结果")
            for i, hit in enumerate(results, 1):
                print(f"  {i}. {hit.entity.get('document')[:50]}...")
        
        # 7. 多查询词测试
        print("\n" + "="*60)
        print("🔍 多查询词测试")
        print("="*60)
        
        for query in ["向量数据库", "Web框架", "DevOps"]:
            results = milvus_client.query_documents(
                query_text=query,
                n_results=2
            )
            print(f"\n查询: '{query}' - 找到 {len(results)} 个结果")
            for i, hit in enumerate(results, 1):
                print(f"  {i}. [{hit.entity.get('category')}] {hit.entity.get('document')[:45]}...")
        
        print("\n" + "="*60)
        print("✅ 演示完成")
        print("="*60)
        
        # 8. 断开连接
        milvus_client.disconnect()
        
    except Exception as e:
        logger.error(f"❌ 程序执行失败: {str(e)}")
        import traceback
        traceback.print_exc()
