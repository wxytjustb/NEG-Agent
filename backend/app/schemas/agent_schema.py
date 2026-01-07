# Pydantic JSON 规范 - Agent 相关数据模型
from pydantic import BaseModel, Field
from typing import Optional, List


class WorkflowChatRequest(BaseModel):
    """Workflow 对话请求（基于 LangGraph）"""
    user_input: str = Field(..., description="用户输入内容")
    conversation_id: str = Field(..., description="对话ID（用于存储和检索对话历史）")
    user_confirmed_ticket: Optional[bool] = Field(default=None, description="用户是否确认创建工单")


class HistoryResponse(BaseModel):
    """历史对话响应模型"""
    user_id: str = Field(..., description="用户ID")
    session_id: str = Field(..., description="会话ID")
    total_count: int = Field(..., description="消息总数")
    messages: List[dict] = Field(..., description="消息列表")
