import sys
import os
import asyncio

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import chromadb
from chromadb.config import Settings
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ChromaDBTester:
    """ChromaDB 连接测试类"""
    
    def __init__(self, host: str = "localhost", port: int = 8000, use_http: bool = True):
        """初始化测试器
        
        Args:
            host: ChromaDB 服务器地址
            port: ChromaDB 服务器端口
            use_http: 是否使用 HTTP 客户端（True=远程服务器，False=本地持久化）
        """
        self.host = host
        self.port = port
        self.use_http = use_http
        self.client = None
        self.collection = None
    
    def test_connection(self):
        """测试 ChromaDB 连接"""
        print(f"\n{'='*60}")
        print("[TEST] 测试 ChromaDB 初始化连接")
        print(f"{'='*60}\n")
        
        try:
            # 1. 创建 ChromaDB 客户端
            print("[步骤 1] 创建 ChromaDB 客户端...")
            if self.use_http:
                # 连接到自部署的 ChromaDB 服务器
                self.client = chromadb.HttpClient(
                    host=self.host,
                    port=self.port,
                    settings=Settings(
                        anonymized_telemetry=False
                    )
                )
                print(f"  ✅ HTTP 客户端创建成功")
                print(f"  服务器地址: {self.host}:{self.port}\n")
            else:
                # 本地持久化模式
                self.client = chromadb.PersistentClient(
                    path="./test_chroma_data",
                    settings=Settings(
                        anonymized_telemetry=False,
                        allow_reset=True
                    )
                )
                print(f"  ✅ 持久化客户端创建成功")
                print(f"  数据目录: ./test_chroma_data\n")
            
            # 2. 列出所有集合
            print("[步骤 2] 列出现有集合...")
            collections = self.client.list_collections()
            if collections:
                print(f"  现有集合数量: {len(collections)}")
                for col in collections:
                    print(f"    - {col.name}")
            else:
                print("  当前没有任何集合")
            print()
            
            # 3. 创建或获取测试集合
            print("[步骤 3] 创建/获取测试集合...")
            collection_name = "test_collection"
            self.collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata={"description": "测试集合"}
            )
            print(f"  ✅ 集合 '{collection_name}' 准备完成")
            print(f"  集合中文档数量: {self.collection.count()}\n")
            
            # 4. 测试添加文档
            print("[步骤 4] 测试添加文档...")
            test_documents = [
                "ChromaDB 是一个开源的向量数据库",
                "它支持快速的相似度搜索",
                "非常适合 RAG 应用场景"
            ]
            test_ids = ["doc1", "doc2", "doc3"]
            
            self.collection.add(
                documents=test_documents,
                ids=test_ids,
                metadatas=[
                    {"source": "test", "type": "intro"},
                    {"source": "test", "type": "feature"},
                    {"source": "test", "type": "use_case"}
                ]
            )
            print(f"  ✅ 成功添加 {len(test_documents)} 个文档")
            print(f"  更新后集合文档数量: {self.collection.count()}\n")
            
            # 5. 测试查询
            print("[步骤 5] 测试相似度查询...")
            query_text = "向量数据库的用途"
            results = self.collection.query(
                query_texts=[query_text],
                n_results=2
            )
            print(f"  查询文本: '{query_text}'")
            print(f"  返回结果数量: {len(results['documents'][0])}")
            for i, (doc, distance) in enumerate(zip(results['documents'][0], results['distances'][0])):
                print(f"    [{i+1}] 相似度: {1-distance:.4f}")
                print(f"        内容: {doc}")
            print()
            
            # 6. 测试删除文档
            print("[步骤 6] 测试删除文档...")
            self.collection.delete(ids=["doc1"])
            print(f"  ✅ 成功删除文档 'doc1'")
            print(f"  更新后集合文档数量: {self.collection.count()}\n")
            
            # 7. 清理测试数据
            print("[步骤 7] 清理测试数据...")
            self.client.delete_collection(name=collection_name)
            print(f"  ✅ 已删除测试集合 '{collection_name}'\n")
            
            print(f"{'='*60}")
            print("✅ 所有测试通过！ChromaDB 连接正常")
            print(f"{'='*60}\n")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 测试失败: {str(e)}", exc_info=True)
            print(f"\n{'='*60}")
            print(f"❌ 测试失败: {str(e)}")
            print(f"{'='*60}\n")
            return False
    
    def test_async_operations(self):
        """测试异步操作（如果需要）"""
        print(f"\n{'='*60}")
        print("[TEST] 测试 ChromaDB 异步操作")
        print(f"{'='*60}\n")
        
        try:
            # ChromaDB 目前主要是同步 API，这里可以测试在异步环境中使用
            print("[提示] ChromaDB 当前主要使用同步 API")
            print("  可以在异步函数中通过 asyncio.to_thread() 调用\n")
            
            async def async_query():
                """异步查询示例"""
                collection = self.client.get_or_create_collection("async_test")
                
                # 在异步环境中执行同步操作
                await asyncio.to_thread(
                    collection.add,
                    documents=["异步测试文档"],
                    ids=["async_doc1"]
                )
                
                results = await asyncio.to_thread(
                    collection.query,
                    query_texts=["测试"],
                    n_results=1
                )
                
                # 清理
                self.client.delete_collection("async_test")
                
                return results
            
            # 运行异步测试
            results = asyncio.run(async_query())
            print(f"  ✅ 异步操作测试成功")
            print(f"  查询结果: {results['documents'][0]}\n")
            
            print(f"{'='*60}")
            print("✅ 异步操作测试通过！")
            print(f"{'='*60}\n")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 异步测试失败: {str(e)}", exc_info=True)
            return False


def test_chromadb_connection():
    """测试 ChromaDB 连接的主函数"""
    
    # 读取环境变量或使用默认值
    from dotenv import load_dotenv
    load_dotenv()
    
    chroma_host = os.getenv("CHROMA_HOST", "localhost")
    chroma_port = int(os.getenv("CHROMA_PORT", "8000"))
    use_http = os.getenv("CHROMA_USE_HTTP", "true").lower() == "true"
    
    print(f"\n[配置信息]")
    print(f"  模式: {'HTTP 客户端（连接自部署服务器）' if use_http else '本地持久化'}")
    if use_http:
        print(f"  服务器: {chroma_host}:{chroma_port}")
    print()
    
    # 创建测试器
    tester = ChromaDBTester(host=chroma_host, port=chroma_port, use_http=use_http)
    
    # 运行基础连接测试
    success = tester.test_connection()
    
    if success:
        # 运行异步操作测试
        tester.test_async_operations()
    
    # 清理本地测试目录（仅在本地模式）
    if not use_http:
        test_dir = "./test_chroma_data"
        import shutil
        if os.path.exists(test_dir):
            try:
                shutil.rmtree(test_dir)
                print(f"[清理] 已删除测试目录: {test_dir}\n")
            except Exception as e:
                print(f"[警告] 无法删除测试目录: {e}\n")


if __name__ == "__main__":
    # 检查 chromadb 是否已安装
    try:
        import chromadb
        print(f"ChromaDB 版本: {chromadb.__version__}\n")
    except ImportError:
        print("\n❌ 错误: chromadb 未安装")
        print("请运行: pip install chromadb")
        print("或添加到 requirements.txt: chromadb>=0.4.0\n")
        sys.exit(1)
    
    # 运行测试
    test_chromadb_connection()
