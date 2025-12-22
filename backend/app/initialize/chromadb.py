# ChromaDB 初始化
import chromadb
from chromadb.config import Settings as ChromaSettings
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

# 全局 ChromaDB 客户端
chroma_client = None


def init_chromadb():
    """
    初始化 ChromaDB 连接并检查连通性
    
    根据配置连接到自部署的 ChromaDB 服务器或本地持久化模式
    """
    global chroma_client
    
    try:
        chroma_host = getattr(settings, 'CHROMA_HOST', 'localhost')
        chroma_port = getattr(settings, 'CHROMA_PORT', 8000)
        use_http = getattr(settings, 'CHROMA_USE_HTTP', 'true').lower() in ('true', '1', 'yes')
        
        if use_http:
            # HTTP 客户端模式 - 连接到自部署的 ChromaDB 服务器
            chroma_client = chromadb.HttpClient(
                host=chroma_host,
                port=chroma_port,
                settings=ChromaSettings(
                    anonymized_telemetry=False
                )
            )
        else:
            # 持久化客户端模式 - 本地存储
            persist_directory = getattr(settings, 'CHROMA_PERSIST_DIRECTORY', './chroma_data')
            chroma_client = chromadb.PersistentClient(
                path=persist_directory,
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
        
        # 测试连接 - 尝试列出集合
        try:
            collections = chroma_client.list_collections()
            logger.info("✅ ChromaDB 启动成功")
        except Exception as test_error:
            raise ConnectionError(f"无法连接到 ChromaDB 服务: {test_error}")
            
    except ImportError as e:
        logger.error(f"❌ ChromaDB 模块未安装: {e}")
        chroma_client = None
        raise ImportError("ChromaDB 未安装，请先安装依赖")
    
    except ConnectionError as e:
        logger.error(f"❌ ChromaDB 连接错误: {e}")
        chroma_client = None
        raise
    
    except Exception as e:
        logger.error(f"❌ ChromaDB 初始化失败: {type(e).__name__}: {e}")
        chroma_client = None
        raise RuntimeError(f"ChromaDB 初始化失败: {e}")


def close_chromadb():
    """
    关闭 ChromaDB 连接
    
    注意: HttpClient 通常不需要显式关闭，但这里提供接口以保持一致性
    """
    global chroma_client
    if chroma_client:
        logger.info("ChromaDB 连接已关闭")
        chroma_client = None


def get_chromadb_client():
    """
    获取 ChromaDB 客户端实例
    
    Returns:
        chromadb.Client: ChromaDB 客户端实例
        
    Raises:
        RuntimeError: 如果客户端未初始化
    """
    if chroma_client is None:
        logger.error("ChromaDB 客户端未初始化")
        raise RuntimeError(
            "ChromaDB 客户端未初始化，请先调用 init_chromadb() 或检查服务是否启动"
        )
    return chroma_client