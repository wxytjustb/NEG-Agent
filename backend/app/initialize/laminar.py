import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

def init_laminar():
    """初始化 Laminar 自动追踪"""
    if not settings.LAMINAR_ENABLED:
        return
    
    if not settings.LAMINAR_API_KEY:
        logger.warning("⚠️  Laminar API Key 未设置")
        return
    
    try:
        from lmnr import Laminar
        Laminar.initialize(
            project_api_key=settings.LAMINAR_API_KEY,
            base_url=settings.LAMINAR_BASE_URL,
            http_port=settings.LAMINAR_HTTP_PORT,  
            grpc_port=settings.LAMINAR_GRPC_PORT,  
        )
        logger.info("✅ Laminar 启动成功")
    except ImportError:
        logger.warning("⚠️  Laminar SDK 未安装")
    except Exception as e:
        logger.error(f"❌ Laminar 启动失败: {str(e)}")
 