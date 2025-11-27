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
    
    # LLM API 配置 (DeepSeek 或其他 OpenAI 兼容接口)
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
    SESSION_TOKEN_EXPIRE_MINUTES: int = 30  # 30 minutes
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

    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# 创建全局配置实例
settings = Settings()
