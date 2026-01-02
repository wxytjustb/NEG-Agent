# 配置文件
from pydantic_settings import BaseSettings
from typing import Optional, List


class Settings(BaseSettings):
    """应用配置类"""
    
    # 应用基础配置
    APP_NAME: str = "Agent API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # 服务器配置
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    
    # 数据库配置
    DATABASE_URL: str = "sqlite:///./app.db"
    
    # JWT 配置
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS 配置
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"
    
    # LLM API 配置 (DeepSeek)
    LLM_API_KEY: Optional[str] = None
    LLM_API_BASE_URL: Optional[str] = None
    LLM_MODEL: str = "gpt-3.5-turbo"
    
    # Ollama 配置
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: Optional[str] = None
    OLLAMA_TEMPERATURE: float = 0.7
    OLLAMA_MAX_TOKENS: int = 2000
    
    # LLM 提供商选择: 'deepseek' 或 'ollama'
    LLM_PROVIDER: str = "ollama"

    # Golang Server Auth Configuration
    GOLANG_API_BASE_URL: str = "https://app-api.roky.work"
    GOLANG_VERIFY_ENDPOINT: str = "/open-api/auth/verify-app-user"

    # Redis Configuration
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    REDIS_TTL: int = 300  # 5 minutes
    
    # Session Token Configuration
    SESSION_TOKEN_EXPIRE_MINUTES: int = 60  # Session Token 过期时间（分钟）
    SESSION_REDIS_PREFIX: str = "session:"  # Redis key prefix for sessions
    USER_SESSION_PREFIX: str = "user_session:"  # Redis key prefix for user-to-session mapping
    
    # Test Access Token (for development/testing only)
    TEST_ACCESS_TOKEN: Optional[str] = None

    # Laminar 配置（LangChain 监控和可视化）
    LAMINAR_API_KEY: Optional[str] = None
    LAMINAR_BASE_URL: Optional[str] = None  # 自托管服务器地址
    LAMINAR_HTTP_PORT: int = 8080  # HTTP 端口
    LAMINAR_GRPC_PORT: int = 8081  # gRPC 端口
    LAMINAR_ENABLED: bool = True  # 是否启用
    LAMINAR_ENVIRONMENT: str = "development"  # 环境名称

    # ChromaDB 配置（向量数据库）
    CHROMA_HOST: str = "localhost"  # ChromaDB 服务器地址
    CHROMA_PORT: int = 8001  # ChromaDB 服务器端口（对应 docker-compose 中的主机端口）
    CHROMA_USE_HTTP: str = "True"  # 是否使用 HTTP 客户端（True=远程，False=本地）
    CHROMADB_COLLECTION: str = "memory"  # 对话记忆集合名称
    CHROMADB_DISTANCE_METRIC: str = "cosine"  # 距离度量方式: cosine/l2/ip
    
    # 历史记忆配置
    HISTORY_MESSAGE_LIMIT: int = 10  # 获取最近N条历史消息，默认10条

    # 意图识别配置（Intent Recognition）
    INTENT_LABELS: str = "日常对话,法律咨询,情感倾诉"  # 意图标签（逗号分隔）
    INTENT_MIN_CONFIDENCE: float = 0.3  # 意图置信度阈值（低于此值归为日常对话）

    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# 创建全局配置实例
settings = Settings()
