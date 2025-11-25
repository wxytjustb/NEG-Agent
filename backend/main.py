from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.agent import router as agent_router
import uvicorn

app = FastAPI(title="Agent API", version="1.0.0")

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
    uvicorn.run("main:app", host="0.0.0.0", port=8000, log_level="info")

    # 注意: 一旦调用 uvicorn.run()，它会阻塞程序直到服务器停止。


if __name__ == "__main__":
    start_server()
