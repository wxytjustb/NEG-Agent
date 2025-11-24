# Agent 服务层 - 负责流式对话业务逻辑
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from typing import List, Dict, Optional, AsyncGenerator
from app.services.llm_service import llm_service
from app.prompts.prompts import RIGHTS_PROTECTION_SYSTEM_PROMPT, GENERAL_CHAT_SYSTEM_PROMPT
import logging

logger = logging.getLogger(__name__)


class AgentService:
    """Agent 服务类 - 负责对话相关业务逻辑"""
    
    def __init__(self):
        """初始化 Agent 服务"""
        self.llm_service = llm_service
        # 默认系统提示词
        self.default_system_prompt = RIGHTS_PROTECTION_SYSTEM_PROMPT
    
    def _convert_messages(
        self, 
        messages: List[Dict[str, str]], 
        system_prompt: Optional[str] = None,
        auto_inject_prompt: bool = True
    ) -> List:
        """将消息字典转换为 LangChain 消息对象
        
        Args:
            messages: 消息列表，格式 [{"role": "user", "content": "..."}]
            system_prompt: 系统提示词（如果提供）
            auto_inject_prompt: 是否自动注入系统提示词（如果消息中没有 system 角色）
            
        Returns:
            LangChain 消息对象列表
        """
        langchain_messages = []
        
        # 检查是否已有 system 消息
        has_system = any(msg.get("role") == "system" for msg in messages)
        
        # 如果需要自动注入系统提示词且没有 system 消息
        if auto_inject_prompt and not has_system:
            prompt_to_use = self.default_system_prompt  or system_prompt
            langchain_messages.append(SystemMessage(content=prompt_to_use))
        
        # 转换用户消息
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "system":
                langchain_messages.append(SystemMessage(content=content))
            elif role == "assistant":
                langchain_messages.append(AIMessage(content=content))
            else:  # user
                langchain_messages.append(HumanMessage(content=content))
        
        return langchain_messages
    
    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        system_prompt: Optional[str] = None,
        auto_inject_prompt: bool = True
    ) -> AsyncGenerator[str, None]:
        """执行流式对话生成
        
        Args:
            messages: 对话消息列表，格式 [{"role": "user", "content": "..."}]
            temperature: 温度参数
            max_tokens: 最大token数
            model: 模型名称
            provider: 指定使用的提供商 ('deepseek' 或 'ollama')
            system_prompt: 自定义系统提示词
            auto_inject_prompt: 是否自动注入系统提示词（默认 False）
            
        Yields:
            生成的文本块
        """
        try:
            # 创建 LLM 实例
            llm = self.llm_service.create_llm(
                temperature=temperature,
                max_tokens=max_tokens,
                model=model,
                provider=provider
            )
            
            # 转换消息格式（支持自动注入提示词）
            langchain_messages = self._convert_messages(
                messages, 
                system_prompt=system_prompt,
                auto_inject_prompt=auto_inject_prompt
            )
            
            # 流式调用模型
            async for chunk in llm.astream(langchain_messages):
                if hasattr(chunk, 'content') and chunk.content:
                    # 确保输出为字符串
                    content = chunk.content
                    if isinstance(content, str):
                        yield content
                    elif isinstance(content, list):
                        # 处理列表类型的内容
                        for item in content:
                            if isinstance(item, str):
                                yield item
                            elif isinstance(item, dict):
                                yield str(item.get('text', ''))
                    
        except Exception as e:
            logger.error(f"流式对话失败: {str(e)}")
            raise Exception(f"流式对话失败: {str(e)}")
    
    async def simple_chat_stream(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        provider: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """简单流式对话（单轮）
        
        Args:
            prompt: 用户提示词
            system_message: 系统提示词
            temperature: 温度参数
            max_tokens: 最大token数
            provider: 指定使用的提供商
            
        Yields:
            生成的文本块
        """
        messages = []
        
        if system_message:
            messages.append({"role": "system", "content": system_message})
        
        messages.append({"role": "user", "content": prompt})
        
        async for chunk in self.chat_stream(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            provider=provider
        ):
            yield chunk
    
    async def rights_protection_chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = 0.7,
        max_tokens: Optional[int] = 2000,
        provider: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """权益保障智能体对话（自动注入权益保障提示词）
        
        Args:
            messages: 对话消息列表
            temperature: 温度参数（默认0.7，保证专业性）
            max_tokens: 最大token数
            provider: LLM提供商
            
        Yields:
            生成的文本块
        """
        async for chunk in self.chat_stream(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            provider=provider,
            system_prompt=RIGHTS_PROTECTION_SYSTEM_PROMPT,
            auto_inject_prompt=True  # 自动注入权益保障提示词
        ):
            yield chunk


# 创建全局服务实例
agent_service = AgentService()
