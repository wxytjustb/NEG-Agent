import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

def init_laminar():
    """初始化 Laminar 自动追踪"""
    if not settings.LAMINAR_ENABLED:
        logger.info("⚠️ Laminar 追踪已禁用")
        return
    
    if not settings.LAMINAR_API_KEY:
        logger.warning("⚠️ LAMINAR_API_KEY 未设置，追踪功能已禁用")
        return
    
    try:
        from lmnr import Laminar
        Laminar.initialize(
            project_api_key=settings.LAMINAR_API_KEY,
            base_url=settings.LAMINAR_BASE_URL,
            http_port=settings.LAMINAR_HTTP_PORT,  
            grpc_port=settings.LAMINAR_GRPC_PORT,  
        )
        logger.info(f"✅ Laminar 已启用")
        logger.info(f"   服务器: {settings.LAMINAR_BASE_URL}")
        logger.info(f"   HTTP Port: {settings.LAMINAR_HTTP_PORT}")
        logger.info(f"   gRPC Port: {settings.LAMINAR_GRPC_PORT}")
        logger.info(f"   环境: {settings.LAMINAR_ENVIRONMENT}")
        logger.info("   ✨ LangChain/LangGraph 将自动被追踪")
    except ImportError:
        logger.warning("⚠️ Laminar SDK (lmnr) 未安装，请执行: pip install lmnr")
    except Exception as e:
        logger.error(f"❌ Laminar 初始化失败: {str(e)}")
 