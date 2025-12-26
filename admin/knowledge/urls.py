"""知识库 API 路由配置"""
from django.urls import path
from .views import (
    GetCollectionDataView,
    AddTextToVectorDBView,
    SimilaritySearchView
)
from .admin import knowledge_dashboard

app_name = 'knowledge'

urlpatterns = [
    # 管理界面
    path('dashboard/', knowledge_dashboard, name='dashboard'),
    
    # 接口1: 获取 collection 数据
    path('collection-data/', GetCollectionDataView.as_view(), name='collection_data'),
    
    # 接口2: 添加文本到向量数据库
    path('add-text/', AddTextToVectorDBView.as_view(), name='add_text'),
    
    # 接口3: 相似度搜索
    path('similarity-search/', SimilaritySearchView.as_view(), name='similarity_search'),
]
