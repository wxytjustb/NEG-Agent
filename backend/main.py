from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.agent import router as agent_router

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
