from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.conf import settings
from .chromadb_service import ChromaDBService
import json


@method_decorator(csrf_exempt, name='dispatch')
class GetCollectionDataView(View):
    """接口1: 获取向量数据库 collection 中的数据"""
    
    def get(self, request):
        """
        GET /app/aiagent/knowledge/collection-data/
        Query参数:
            - collection_name: collection 名称(可选,默认为 knowledge_base)
        """
        try:
            collection_name = request.GET.get('collection_name', settings.CHROMADB_DEFAULT_COLLECTION)
            
            # 初始化服务
            service = ChromaDBService(collection_name=collection_name)
            
            # 获取数据
            data = service.get_collection_data()
            
            return JsonResponse({
                'code': 200,
                'message': '获取成功',
                'data': data
            })
            
        except Exception as e:
            return JsonResponse({
                'code': 500,
                'message': f'获取失败: {str(e)}',
                'data': None
            }, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class AddTextToVectorDBView(View):
    """接口2: 创建文本向量并存储到向量数据库"""
    
    def post(self, request):
        """
        POST /app/aiagent/knowledge/add-text/
        Body参数:
            - text: 文本内容(必填)
            - collection_name: collection 名称(可选,默认为 knowledge_base)
            - metadata: 元数据(可选)
            - chunk_size: 分块大小(可选,默认 1000)
            - chunk_overlap: 分块重叠(可选,默认 200)
        """
        try:
            # 解析请求数据
            data = json.loads(request.body)
            
            text = data.get('text')
            if not text:
                return JsonResponse({
                    'code': 400,
                    'message': '文本内容不能为空',
                    'data': None
                }, status=400)
            
            collection_name = data.get('collection_name', settings.CHROMADB_DEFAULT_COLLECTION)
            metadata = data.get('metadata', {})
            chunk_size = data.get('chunk_size', settings.CHUNK_SIZE)
            chunk_overlap = data.get('chunk_overlap', settings.CHUNK_OVERLAP)
            
            # 初始化服务
            service = ChromaDBService(collection_name=collection_name)
            
            # 添加文本
            result = service.add_text_chunks(
                text=text,
                metadata=metadata,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
            
            if result.get('success'):
                return JsonResponse({
                    'code': 200,
                    'message': result.get('message'),
                    'data': {
                        'collection_name': result.get('collection_name'),
                        'chunk_count': result.get('chunk_count'),
                        'ids': result.get('ids')
                    }
                })
            else:
                return JsonResponse({
                    'code': 500,
                    'message': result.get('message'),
                    'data': None
                }, status=500)
            
        except json.JSONDecodeError:
            return JsonResponse({
                'code': 400,
                'message': '无效的 JSON 格式',
                'data': None
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'code': 500,
                'message': f'添加失败: {str(e)}',
                'data': None
            }, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class SimilaritySearchView(View):
    """接口3: 相似度匹配搜索"""
    
    def post(self, request):
        """
        POST /app/aiagent/knowledge/similarity-search/
        Body参数:
            - query: 查询文本(必填)
            - collection_name: collection 名称(可选,默认为 knowledge_base)
            - n_results: 返回结果数量(可选,默认 5)
            - where: 元数据过滤条件(可选)
        """
        try:
            # 解析请求数据
            data = json.loads(request.body)
            
            query = data.get('query')
            if not query:
                return JsonResponse({
                    'code': 400,
                    'message': '查询文本不能为空',
                    'data': None
                }, status=400)
            
            collection_name = data.get('collection_name', settings.CHROMADB_DEFAULT_COLLECTION)
            n_results = data.get('n_results', settings.DEFAULT_TOP_K)
            where = data.get('where')
            
            # 初始化服务
            service = ChromaDBService(collection_name=collection_name)
            
            # 执行搜索
            result = service.similarity_search(
                query=query,
                n_results=n_results,
                where=where
            )
            
            if result.get('success'):
                return JsonResponse({
                    'code': 200,
                    'message': '搜索成功',
                    'data': {
                        'collection_name': result.get('collection_name'),
                        'query': result.get('query'),
                        'count': result.get('count'),
                        'results': result.get('results')
                    }
                })
            else:
                return JsonResponse({
                    'code': 500,
                    'message': result.get('message'),
                    'data': None
                }, status=500)
            
        except json.JSONDecodeError:
            return JsonResponse({
                'code': 400,
                'message': '无效的 JSON 格式',
                'data': None
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'code': 500,
                'message': f'搜索失败: {str(e)}',
                'data': None
            }, status=500)
