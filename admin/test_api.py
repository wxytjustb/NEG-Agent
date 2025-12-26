"""测试知识库 API 接口"""
import requests
import json

BASE_URL = "http://127.0.0.1:8000/app/aiagent/knowledge"


def test_add_text():
    """测试接口2: 添加文本到向量数据库"""
    print("\n" + "="*50)
    print("测试接口2: 添加文本到向量数据库")
    print("="*50)
    
    url = f"{BASE_URL}/add-text/"
    
    data = {
        "text": """
        Python是一种解释型、面向对象、动态数据类型的高级程序设计语言。
        Python由Guido van Rossum于1989年底发明,第一个公开发行版发行于1991年。
        Python的设计哲学强调代码的可读性和简洁的语法。
        Python拥有动态类型系统和垃圾回收功能,能够自动管理内存使用。
        """,
        "collection_name": "test_collection",
        "metadata": {
            "title": "Python基础介绍",
            "source": "测试文档",
            "category": "编程语言"
        },
        "chunk_size": 500,
        "chunk_overlap": 100
    }
    
    response = requests.post(url, json=data)
    print(f"状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")
    
    return response.json()


def test_add_more_text():
    """添加更多测试文本"""
    print("\n添加更多测试文本...")
    
    url = f"{BASE_URL}/add-text/"
    
    texts = [
        {
            "text": "Django是一个开放源代码的Web应用框架,由Python编写。采用了MTV的框架模式。Django的主要目的是简便、快速地开发数据库驱动的网站。",
            "metadata": {"title": "Django介绍", "category": "Web框架"}
        },
        {
            "text": "ChromaDB是一个开源的向量数据库,专为AI应用设计。它可以存储文档、元数据和嵌入向量,并提供高效的相似度搜索功能。",
            "metadata": {"title": "ChromaDB介绍", "category": "向量数据库"}
        }
    ]
    
    for item in texts:
        data = {
            "text": item["text"],
            "collection_name": "test_collection",
            "metadata": item["metadata"]
        }
        response = requests.post(url, json=data)
        print(f"  - 添加 {item['metadata']['title']}: {response.json().get('message')}")


def test_get_collection_data():
    """测试接口1: 获取collection数据"""
    print("\n" + "="*50)
    print("测试接口1: 获取collection数据")
    print("="*50)
    
    url = f"{BASE_URL}/collection-data/"
    params = {"collection_name": "test_collection"}
    
    response = requests.get(url, params=params)
    print(f"状态码: {response.status_code}")
    
    result = response.json()
    print(f"Collection名称: {result['data']['collection_name']}")
    print(f"文档数量: {result['data']['count']}")
    print(f"文档ID列表: {result['data']['ids'][:3]}...")  # 只显示前3个
    
    return result


def test_similarity_search():
    """测试接口3: 相似度搜索"""
    print("\n" + "="*50)
    print("测试接口3: 相似度搜索")
    print("="*50)
    
    url = f"{BASE_URL}/similarity-search/"
    
    queries = [
        "Python是什么?",
        "Web框架有哪些?",
        "向量数据库的用途"
    ]
    
    for query in queries:
        print(f"\n查询: {query}")
        print("-" * 40)
        
        data = {
            "query": query,
            "collection_name": "test_collection",
            "n_results": 3
        }
        
        response = requests.post(url, json=data)
        result = response.json()
        
        if result['code'] == 200:
            print(f"找到 {result['data']['count']} 个相关结果:")
            for i, item in enumerate(result['data']['results'], 1):
                print(f"\n[{i}] 相似度: {item['similarity']:.4f}")
                print(f"    文档: {item['document'][:100]}...")
                print(f"    元数据: {item['metadata']}")
        else:
            print(f"搜索失败: {result['message']}")


def test_search_with_filter():
    """测试带过滤条件的搜索"""
    print("\n" + "="*50)
    print("测试带过滤条件的相似度搜索")
    print("="*50)
    
    url = f"{BASE_URL}/similarity-search/"
    
    print("\n查询: Python (只搜索编程语言类别)")
    print("-" * 40)
    
    data = {
        "query": "Python",
        "collection_name": "test_collection",
        "n_results": 5,
        "where": {"category": "编程语言"}  # 元数据过滤
    }
    
    response = requests.post(url, json=data)
    result = response.json()
    
    if result['code'] == 200:
        print(f"找到 {result['data']['count']} 个相关结果:")
        for i, item in enumerate(result['data']['results'], 1):
            print(f"\n[{i}] 相似度: {item['similarity']:.4f}")
            print(f"    类别: {item['metadata'].get('category')}")
            print(f"    文档: {item['document'][:100]}...")


if __name__ == "__main__":
    print("开始测试知识库 API")
    print("确保 Django 服务已启动: python manage.py runserver")
    print()
    
    try:
        # 测试顺序
        test_add_text()
        test_add_more_text()
        test_get_collection_data()
        test_similarity_search()
        test_search_with_filter()
        
        print("\n" + "="*50)
        print("所有测试完成!")
        print("="*50)
        
    except requests.exceptions.ConnectionError:
        print("\n错误: 无法连接到服务器")
        print("请先启动 Django 服务: python manage.py runserver")
    except Exception as e:
        print(f"\n测试失败: {str(e)}")
