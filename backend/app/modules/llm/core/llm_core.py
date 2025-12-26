# LLM 核心客户端 - 负责创建 LLM 实例
from langchain_openai import ChatOpenAI
from typing import Optional
from app.core.config import settings
from pydantic import SecretStr
import logging

logger = logging.getLogger(__name__)


class LLMCore:
    """LLM 核心客户端 - 负责创建和管理 LLM 模型连接"""
    
    def __init__(self):
        """初始化 LLM 核心客户端"""
        # DeepSeek 配置
        self.deepseek_api_key = settings.LLM_API_KEY
        self.deepseek_api_base = settings.LLM_API_BASE_URL
        self.deepseek_model = settings.LLM_MODEL
        
        # 验证配置
        self._validate_config()
    
    def _validate_config(self):
        """验证配置是否正确"""
        if not self.deepseek_api_key:
            logger.warning("LLM_API_KEY 未设置，请在 .env 文件中配置")
        logger.info(f"LLM 核心: 使用 DeepSeek 模型 {self.deepseek_model}")
    
    def create_llm(
        self, 
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None,
        provider: Optional[str] = "deepseek"  # 保留参数以兼容前端，默认值为 deepseek
    ) -> ChatOpenAI:
        """创建 LLM 实例（DeepSeek）
        
        Args:
            temperature: 温度参数
            max_tokens: 最大token数
            model: 模型名称
            provider: 提供商名称（保留以兼容前端，目前仅支持 deepseek）
            
        Returns:
            ChatOpenAI 实例
        """
        # 忽略 provider 参数，始终创建 DeepSeek LLM
        return ChatOpenAI(
            model=model or self.deepseek_model,
            temperature=temperature or 0.7,
            max_tokens=max_tokens or 2000,
            api_key=SecretStr(self.deepseek_api_key) if self.deepseek_api_key else None,  # type: ignore
            base_url=self.deepseek_api_base,
            streaming=True,  # 🔥 启用流式输出
        )
    
    def get_default_model_name(self) -> str:
        """获取默认模型名称
        
        Returns:
            模型名称
        """
        return self.deepseek_model


# 创建全局实例
llm_core = LLMCore()
