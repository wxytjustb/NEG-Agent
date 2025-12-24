from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.api.agent import router as agent_router
from app.initialize.redis import init_redis, close_redis
from app.initialize.laminar import init_laminar
from app.initialize.chromadb import init_chromadb, close_chromadb
from app.core.config import settings
import uvicorn
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 关闭冗余日志
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('app.modules.workflow.core.graph').setLevel(logging.WARNING)
logging.getLogger('app.modules.workflow.workflows.workflow').setLevel(logging.WARNING)
logging.getLogger('app.modules.workflow.nodes.user_info').setLevel(logging.WARNING)
logging.getLogger('app.modules.workflow.nodes.Intent_recognition').setLevel(logging.WARNING)
logging.getLogger('app.modules.workflow.nodes.llm_answer').setLevel(logging.WARNING)
logging.getLogger('app.core.session_token').setLevel(logging.WARNING)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 正在启动 NEG-Agent 服务...")
    
    # 初始化 Laminar
    init_laminar()
    
    # 初始化 ChromaDB
    try:
        init_chromadb()
        print("✅ ChromaDB 连接成功")
    except Exception as e:
        print(f"⚠️  ChromaDB 连接失败: {e}")
    
    # 初始化 Redis
    await init_redis()
    
    print(f"✅ 服务启动成功: http://{settings.HOST}:{settings.PORT}")
    print(f"📝 API 文档: http://{settings.HOST}:{settings.PORT}/docs")
    
    yield
    
    # Shutdown
    close_chromadb()
    await close_redis()
    print("✅ 服务已关闭")

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
