# LLM 服务层 - 负责模型连接（DeepSeek / Ollama）
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from typing import Optional, Union
from app.core.config import settings
from pydantic import SecretStr
import logging

logger = logging.getLogger(__name__)


class LLMService:
    """LLM 服务类 - 只负责创建和管理 LLM 模型连接"""
    
    def __init__(self):
        """初始化 LLM 服务"""
        self.provider = settings.LLM_PROVIDER.lower()
        
        # DeepSeek 配置
        self.deepseek_api_key = settings.LLM_API_KEY
        self.deepseek_api_base = settings.LLM_API_BASE_URL
        self.deepseek_model = settings.LLM_MODEL
        
        # Ollama 配置
        self.ollama_base_url = settings.OLLAMA_BASE_URL
        self.ollama_model = settings.OLLAMA_MODEL
        self.ollama_temperature = settings.OLLAMA_TEMPERATURE
        self.ollama_max_tokens = settings.OLLAMA_MAX_TOKENS
        
        # 验证配置
        self._validate_config()
    
    def _validate_config(self):
        """验证配置是否正确"""
        if self.provider == "deepseek":
            if not self.deepseek_api_key:
                logger.warning("使用 DeepSeek 但 LLM_API_KEY 未设置，请在 .env 文件中配置")
            logger.info(f"LLM 服务初始化: 使用 DeepSeek 模型 {self.deepseek_model}")
        elif self.provider == "ollama":
            if not self.ollama_model:
                logger.warning("使用 Ollama 但 OLLAMA_MODEL 未设置，请在 .env 文件中配置")
            logger.info(f"LLM 服务初始化: 使用 Ollama 模型 {self.ollama_model} @ {self.ollama_base_url}")
        else:
            logger.error(f"不支持的 LLM_PROVIDER: {self.provider}，请使用 'deepseek' 或 'ollama'")
    
    def create_llm(
        self, 
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None,
        provider: Optional[str] = None
    ) -> Union[ChatOpenAI, ChatOllama]:
        """创建 LLM 实例
        
        Args:
            temperature: 温度参数
            max_tokens: 最大token数
            model: 模型名称
            provider: 指定使用的提供商 ('deepseek' 或 'ollama')，不指定则使用默认配置
            
        Returns:
            ChatOpenAI 或 ChatOllama 实例
        """
        use_provider = (provider or self.provider).lower()
        
        if use_provider == "deepseek":
            return self._create_deepseek_llm(temperature, max_tokens, model)
        elif use_provider == "ollama":
            return self._create_ollama_llm(temperature, max_tokens, model)
        else:
            raise ValueError(f"不支持的 provider: {use_provider}，请使用 'deepseek' 或 'ollama'")
    
    def _create_deepseek_llm(
        self, 
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None
    ) -> ChatOpenAI:
        """创建 DeepSeek LLM 实例（使用 OpenAI 兼容接口）
        
        Args:
            temperature: 温度参数
            max_tokens: 最大token数
            model: 模型名称
            
        Returns:
            ChatOpenAI 实例
        """
        return ChatOpenAI(
            model=model or self.deepseek_model,
            temperature=temperature or 0.7,
            max_completion_tokens=max_tokens or 2000,
            api_key=SecretStr(self.deepseek_api_key) if self.deepseek_api_key else None,  # type: ignore
            base_url=self.deepseek_api_base,
        )
    
    def _create_ollama_llm(
        self,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None
    ) -> ChatOllama:
        """创建 Ollama LLM 实例
        
        Args:
            temperature: 温度参数
            max_tokens: 最大token数
            model: 模型名称
            
        Returns:
            ChatOllama 实例
        """
        ollama_model = model or self.ollama_model or "llama2"
        return ChatOllama(
            model=ollama_model,
            base_url=self.ollama_base_url,
            temperature=temperature or self.ollama_temperature,
        )
    
    def get_default_model_name(self, provider: Optional[str] = None) -> str:
        """获取默认模型名称
        
        Args:
            provider: 提供商名称
            
        Returns:
            模型名称
        """
        use_provider = (provider or self.provider).lower()
        
        if use_provider == "deepseek":
            return self.deepseek_model
        elif use_provider == "ollama":
            return self.ollama_model or "llama2"
        else:
            raise ValueError(f"不支持的 provider: {use_provider}")


# 创建全局服务实例
llm_service = LLMService()
