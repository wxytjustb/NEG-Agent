from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.api.agent import router as agent_router
from app.initialize.redis import init_redis, close_redis
from app.core.config import settings
import uvicorn
import logging

logger = logging.getLogger(__name__)

# 初始化 Laminar（在应用启动时自动 Hook LangChain）
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

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_laminar()  # 初始化 Laminar
    await init_redis()
    yield
    # Shutdown
    await close_redis()

app = FastAPI(title="Agent API", version="1.0.0", lifespan=lifespan)

# 解决跨域问题
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(agent_router)

@app.get("/")
def root():
    return {"message": "FastAPI is running!", "status": "ok"}

@app.get("/ping")
def ping():
    return {"message": "Hello from FastAPI!"}



def start_server():
    """
    启动 Uvicorn 服务器来运行 FastAPI 应用
    """
    print("--- 正在启动 FastAPI 服务器 ---")

    # uvicorn.run() 接受以下关键参数:
    # - "main:app": 指定要运行的模块和应用对象 (格式: <module_name>:<app_object>)
    # - host: 服务器监听的 IP 地址
    # - port: 服务器监听的端口
    # - reload: (可选) 开启热重载，方便开发
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="debug")

    # 注意: 一旦调用 uvicorn.run()，它会阻塞程序直到服务器停止。


if __name__ == "__main__":
    start_server()
