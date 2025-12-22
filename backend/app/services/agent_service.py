# Agent 服务层 - 负责流式对话业务逻辑
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from typing import List, Dict, Optional, AsyncGenerator
from lmnr import observe, Laminar
from app.modules.llm.core import llm_core
from app.services.redis_service import redis_service
from app.core.config import settings
from app.core.session_token import get_session
from app.utils.prompt import ANRAN_SYSTEM_PROMPT  # 使用完整版 Prompt
import logging

logger = logging.getLogger(__name__)


class AgentService:
    """Agent 服务类 - 负责对话相关业务逻辑"""
    
    def __init__(self):
        """初始化 Agent 服务"""
        self.llm_core = llm_core
        # 默认系统提示词（使用"安然"角色）
        self.default_system_prompt = ANRAN_SYSTEM_PROMPT
    
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
            prompt_to_use = self.default_system_prompt or system_prompt or ""
            if prompt_to_use:  # 只在有提示词时添加
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
    
    @observe(name="agent_chat_stream", tags=["agent", "chat", "streaming"])
    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        system_prompt: Optional[str] = None,
        auto_inject_prompt: bool = True,
        session_token: Optional[str] = None,
        save_history: bool = True,
        user_id: Optional[str] = None,  # 新增：允许直接传入 user_id
        username: Optional[str] = None   # 新增：用于 Laminar 追踪
    ) -> AsyncGenerator[str, None]:
        """执行流式对话生成
        
        Args:
            messages: 对话消息列表，格式 [{"role": "user", "content": "..."}]
            temperature: 温度参数
            max_tokens: 最大token数
            model: 模型名称
            provider: 指定使用的提供商（目前仅支持 'deepseek'）
            system_prompt: 自定义系统提示词
            auto_inject_prompt: 是否自动注入系统提示词（默认 False）
            session_token: 会话 token（用于获取 user_id 并存储历史）
            save_history: 是否保存对话历史到 Redis（默认 True）
            user_id: 直接传入的用户ID（可选）
            username: 用户名（用于 Laminar 追踪）
            
        Yields:
            生成的文本块
        """
        # 初始化变量
        new_user_message = None  # 记录本次新的用户消息（在加载历史之前提取）
        
        # 设置 Laminar 追踪
        if user_id:
            Laminar.set_trace_user_id(str(user_id))
        if session_token:
            Laminar.set_trace_session_id(session_token)
        
        # 设置元数据
        if user_id or username:
            # 提取第一条用户消息作为预览
            message_preview = ""
            for msg in messages:
                if msg.get("role") == "user":
                    content = msg.get("content", "")
                    message_preview = content[:50] + "..." if len(content) > 50 else content
                    break
            
            Laminar.set_trace_metadata({
                "username": username or "Unknown",
                "user_id": str(user_id) if user_id else None,
                "session_token": session_token[:20] + "..." if session_token else None,
                "message_preview": message_preview,
                "provider": provider or "deepseek",
                "model": model or "default"
            })
        
        # 从 session_token 获取 user_id 和 username
        actual_session_token = session_token
        if session_token and save_history and not user_id:
            try:
                session_data = await get_session(session_token)
                if session_data:
                    user_id = session_data.get("user_id")
                    if user_id:  # 确保 user_id 存在
                        logger.info(f"从 session 获取到 user_id: {user_id}")
                        
                        # ⚠️ 关键：在加载历史之前，先提取本次新的用户消息
                        for msg in reversed(messages):
                            if msg.get("role") == "user":
                                new_user_message = msg.get("content", "")
                                logger.info(f"提取新用户消息: {new_user_message[:50]}...")
                                break
                        
                        # 加载对话历史
                        history = await redis_service.get_chat_history(user_id)
                        if history:
                            logger.info(f"加载历史对话 {len(history)} 条消息")
                            # 合并历史消息和当前消息（去重当前请求中的历史部分）
                            if messages and messages[0].get("role") != "system":
                                # 如果当前消息没有 system，将历史消息插入
                                messages = history + messages
                            else:
                                # 保留 system 消息，其他历史消息追加
                                messages = [messages[0]] + history + messages[1:]
                else:
                    logger.warning(f"session_token 无效或已过期: {session_token[:20]}...")
            except Exception as e:
                logger.error(f"获取 session 或历史失败: {str(e)}")
        try:
            # 创建 LLM 实例
            llm = self.llm_core.create_llm(
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
            
            # 收集 AI 回复内容（用于保存历史）
            ai_response = ""
            
            # 流式调用模型
            async for chunk in llm.astream(langchain_messages):
                if hasattr(chunk, 'content') and chunk.content:
                    # 确保输出为字符串
                    content = chunk.content
                    if isinstance(content, str):
                        ai_response += content
                        yield content
                    elif isinstance(content, list):
                        # 处理列表类型的内容
                        for item in content:
                            if isinstance(item, str):
                                ai_response += item
                                yield item
                            elif isinstance(item, dict):
                                text = str(item.get('text', ''))
                                ai_response += text
                                yield text
            
            # 保存对话历史到 Redis（只保存本次新对话）
            if save_history and user_id and ai_response and new_user_message:
                try:
                    # 使用之前提取的新用户消息（避免提取到历史消息）
                    logger.info(f"保存新对话: user={new_user_message[:30]}..., ai={ai_response[:30]}...")
                    
                    # 追加用户消息和 AI 回复，传入真实的 session_token
                    await redis_service.append_message(user_id, actual_session_token or "", "user", new_user_message)
                    await redis_service.append_message(user_id, actual_session_token or "", "assistant", ai_response)
                    logger.info(f"✅ 对话历史已保存: user_id={user_id}, session_token={actual_session_token}, 用户消息长度={len(new_user_message)}, AI回复长度={len(ai_response)}")
                except Exception as e:
                    logger.error(f"保存对话历史失败: {str(e)}")
                    
        except Exception as e:
            logger.error(f"流式对话失败: {str(e)}")
            raise Exception(f"流式对话失败: {str(e)}")
    
# 创建全局服务实例
agent_service = AgentService()