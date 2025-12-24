# Pydantic JSON 规范 - Agent 相关数据模型
from pydantic import BaseModel, Field
from typing import List, Optional


class ChatMessage(BaseModel):
    """聊天消息模型"""
    role: str = Field(..., description="消息角色: system/user/assistant")
    content: str = Field(..., description="消息内容")


class AgentChatRequest(BaseModel):
    """Agent 对话请求"""
    messages: List[ChatMessage] = Field(..., description="对话消息列表")
    provider: Optional[str] = Field("ollama", description="LLM 提供商: 'deepseek' 或 'ollama'")
    temperature: Optional[float] = Field(0.7, description="温度参数", ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(2000, description="最大生成token数", gt=0)
    model: Optional[str] = Field(None, description="指定模型名称")
    stream: Optional[bool] = Field(False, description="是否以SSE流式输出")
    use_history: Optional[bool] = Field(True, description="是否使用Redis中的对话历史")


class WorkflowChatRequest(BaseModel):
    """Workflow 对话请求（基于 LangGraph）"""
    user_input: str = Field(..., description="用户输入内容")
