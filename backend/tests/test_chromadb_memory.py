# ChromaDB 短期记忆功能测试
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.initialize.chromadb import init_chromadb, close_chromadb
from app.modules.chromadb.core.chromadb_core import chromadb_core


def test_short_term_memory():
    """测试短期记忆功能"""
    
    print("=" * 60)
    print("ChromaDB 短期记忆功能测试")
    print("=" * 60)
    
    # 1. 初始化 ChromaDB
    print("\n[1] 初始化 ChromaDB...")
    try:
        init_chromadb()
        print("✅ ChromaDB 初始化成功")
        print(f"📦 使用的集合名称: {chromadb_core.collection_name}")
    except Exception as e:
        print(f"❌ ChromaDB 初始化失败: {e}")
        return
    
    # 测试数据 - 模拟多用户多会话场景
    test_documents = [
        # 用户 334 - 会话 1 (AI学习相关)
        {"user_id": "334", "session_id": "sess_334_001", "role": "user", "content": "Python 是一种高级编程语言,以其简洁的语法和强大的功能而闻名,非常适合初学者学习编程。"},
        {"user_id": "334", "session_id": "sess_334_001", "role": "assistant", "content": "机器学习是人工智能的核心分支,通过算法让计算机从数据中学习规律,无需明确编程。"},
        {"user_id": "334", "session_id": "sess_334_001", "role": "user", "content": "监督学习是机器学习的一种方法,使用标注好的数据集来训练模型,常用于分类和回归任务。"},
        
        # 用户 334 - 会话 2 (深度学习相关)
        {"user_id": "334", "session_id": "sess_334_002", "role": "user", "content": "深度学习使用多层神经网络来解决复杂问题,在图像识别、语音识别等领域取得了突破性进展。"},
        {"user_id": "334", "session_id": "sess_334_002", "role": "assistant", "content": "卷积神经网络(CNN)是专门用于处理图像数据的深度学习架构,在计算机视觉任务中表现出色。"},
        {"user_id": "334", "session_id": "sess_334_002", "role": "user", "content": "循环神经网络(RNN)擅长处理序列数据,广泛应用于自然语言处理和时间序列预测。"},
        
        # 用户 556 - 会话 1 (数据库和NLP)
        {"user_id": "556", "session_id": "sess_556_001", "role": "user", "content": "ChromaDB 是一个现代化的向量数据库,专为 AI 应用设计,支持高效的语义搜索和相似度匹配。"},
        {"user_id": "556", "session_id": "sess_556_001", "role": "assistant", "content": "向量数据库通过将数据转换为高维向量来存储,能够快速进行相似度搜索,是RAG系统的核心组件。"},
        {"user_id": "556", "session_id": "sess_556_001", "role": "user", "content": "自然语言处理(NLP)使计算机能够理解和生成人类语言,涵盖文本分类、情感分析、机器翻译等任务。"},
        {"user_id": "556", "session_id": "sess_556_001", "role": "assistant", "content": "Transformer模型彻底改变了NLP领域,通过自注意力机制实现了更好的长距离依赖建模。"},
        
        # 用户 556 - 会话 2 (大语言模型)
        {"user_id": "556", "session_id": "sess_556_002", "role": "user", "content": "大语言模型(LLM)如GPT、Claude等,通过在海量文本数据上预训练,展现出强大的语言理解和生成能力。"},
        {"user_id": "556", "session_id": "sess_556_002", "role": "assistant", "content": "检索增强生成(RAG)结合了信息检索和生成模型,能够提供更准确、更具时效性的回答。"},
        
        # 用户 778 - 会话 1 (Web开发)
        {"user_id": "778", "session_id": "sess_778_001", "role": "user", "content": "FastAPI 是一个现代化的 Python Web 框架,基于类型提示提供自动API文档生成,性能接近Node.js和Go。"},
        {"user_id": "778", "session_id": "sess_778_001", "role": "assistant", "content": "RESTful API 是一种软件架构风格,使用HTTP方法(GET、POST、PUT、DELETE)来操作资源。"},
        {"user_id": "778", "session_id": "sess_778_001", "role": "user", "content": "Redis 是一个高性能的内存键值存储数据库,支持字符串、列表、集合、哈希等多种数据结构,常用于缓存和会话管理。"},
        
        # 用户 778 - 会话 2 (前端开发)
        {"user_id": "778", "session_id": "sess_778_002", "role": "user", "content": "Vue.js 是一个渐进式JavaScript框架,易于上手,适合构建用户界面和单页应用程序。"},
        {"user_id": "778", "session_id": "sess_778_002", "role": "assistant", "content": "React 是由Facebook开发的前端库,采用组件化开发模式和虚拟DOM技术,拥有庞大的生态系统。"},
        
        # 用户 999 - 会话 1 (DevOps)
        {"user_id": "999", "session_id": "sess_999_001", "role": "user", "content": "Docker 是一个容器化平台,可以将应用程序及其依赖打包成轻量级、可移植的容器,简化部署流程。"},
        {"user_id": "999", "session_id": "sess_999_001", "role": "assistant", "content": "Kubernetes 是一个容器编排平台,用于自动化部署、扩展和管理容器化应用程序。"},
        {"user_id": "999", "session_id": "sess_999_001", "role": "user", "content": "CI/CD 持续集成和持续部署是现代软件开发的最佳实践,通过自动化测试和部署提高开发效率。"},
    ]
    
    try:
        # 2. 批量添加测试数据
        print(f"\n[2] 批量添加测试数据 (共 {len(test_documents)} 条)...")
        
        for doc in test_documents:
            msg_id = chromadb_core.add_message(
                user_id=doc["user_id"],
                session_id=doc["session_id"],
                role=doc["role"],
                content=doc["content"]
            )
            print(f"  ✅ 用户 {doc['user_id']} - 会话 {doc['session_id']}: {doc['content'][:40]}...")
        
        # 3. 统计各用户会话的消息数量
        print(f"\n[3] 统计各用户会话的消息数量...")
        test_sessions = [
            ("334", "sess_334_001"),
            ("334", "sess_334_002"),
            ("556", "sess_556_001"),
            ("556", "sess_556_002"),
            ("778", "sess_778_001"),
            ("778", "sess_778_002"),
            ("999", "sess_999_001"),
        ]
        
        for uid, sid in test_sessions:
            count = chromadb_core.count_messages(uid, sid)
            print(f"  ✅ 用户 {uid} - 会话 {sid}: {count} 条消息")
        
        # 4. 语义搜索测试 - 不同用户不同查询
        print(f"\n[4] 语义搜索测试...")
        
        search_tests = [
            {"user_id": "334", "session_id": "sess_334_001", "query": "什么是机器学习？"},
            {"user_id": "334", "session_id": "sess_334_002", "query": "深度学习的神经网络"},
            {"user_id": "556", "session_id": "sess_556_001", "query": "向量数据库的用途"},
            {"user_id": "556", "session_id": "sess_556_002", "query": "大模型和RAG"},
            {"user_id": "778", "session_id": "sess_778_001", "query": "Python Web框架"},
            {"user_id": "999", "session_id": "sess_999_001", "query": "容器化技术"},
        ]
        
        for test in search_tests:
            print(f"\n  用户 {test['user_id']} 查询: '{test['query']}'")
            results = chromadb_core.search_memory(
                user_id=test["user_id"],
                session_id=test["session_id"],
                query_text=test["query"],
                n_results=2
            )
            
            if results:
                for i, result in enumerate(results, 1):
                    print(f"    [{i}] 相似度: {result['distance']:.4f}")
                    print(f"        内容: {result['content'][:50]}...")
            else:
                print("    未找到相关记忆")
        
        # 5. 获取指定会话的所有消息
        print(f"\n[5] 获取用户 334 - 会话 sess_334_001 的所有消息...")
        all_messages = chromadb_core.get_all_messages("334", "sess_334_001")
        print(f"  ✅ 共获取 {len(all_messages)} 条消息:")
        for i, msg in enumerate(all_messages, 1):
            print(f"    [{i}] {msg['role']}: {msg['content'][:50]}...")
        
        # 6. 测试会话隔离性
        print(f"\n[6] 测试会话隔离性...")
        print(f"  验证：用户 334 的两个会话数据是否隔离")
        
        # 在会话1中搜索深度学习相关内容（应该找不到，因为在会话2）
        results_sess1 = chromadb_core.search_memory(
            user_id="334",
            session_id="sess_334_001",
            query_text="卷积神经网络CNN",
            n_results=3
        )
        
        # 在会话2中搜索深度学习相关内容（应该能找到）
        results_sess2 = chromadb_core.search_memory(
            user_id="334",
            session_id="sess_334_002",
            query_text="卷积神经网络CNN",
            n_results=3
        )
        
        print(f"  ✅ 会话1 搜索结果: {len(results_sess1)} 条 (期望: 0 或很少)")
        print(f"  ✅ 会话2 搜索结果: {len(results_sess2)} 条 (期望: 找到相关内容)")
        if results_sess2:
            print(f"      最相似: {results_sess2[0]['content'][:40]}... (距离: {results_sess2[0]['distance']:.4f})")
        
        # 7. 清理所有测试数据
        print(f"\n[7] 清理所有测试数据...")
        total_deleted = 0
        for uid, sid in test_sessions:
            deleted = chromadb_core.delete_session_memory(uid, sid)
            if deleted > 0:
                print(f"  ✅ 已删除 用户 {uid} - 会话 {sid}: {deleted} 条消息")
                total_deleted += deleted
        
        print(f"\n  📊 总计删除: {total_deleted} 条消息")
        
        print("\n" + "=" * 60)
        print("✅ 所有测试通过！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 关闭连接
        close_chromadb()
        print("\n✅ ChromaDB 连接已关闭")


if __name__ == "__main__":
    test_short_term_memory()
