"""
Pydantic JSON 规范 - 用户反馈相关数据模型
与 Golang 接口字段保持一致（使用 camelCase 别名）。
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict


class CreateFeedbackRequest(BaseModel):
    """创建用户反馈请求（AI反馈）"""
    model_config = ConfigDict(populate_by_name=True)

    conversation_id: str = Field(..., alias="conversationId", description="对话ID")
    is_useful: bool = Field(..., alias="isUseful", description="是否有用")
    feedback_type: Optional[str] = Field(
        None, alias="feedbackType", description="反馈类型（标签，允许空字符串）"
    )
    comment: Optional[str] = Field(
        None, alias="comment", description="用户评语（允许空字符串）"
    )
    user_message: str = Field(..., alias="userMessage", description="用户发送的信息")
    ai_response: str = Field(..., alias="aiResponse", description="AI回复的信息")


class UpdateFeedbackRequest(BaseModel):
    """更新用户反馈请求"""
    model_config = ConfigDict(populate_by_name=True)

    is_useful: Optional[bool] = Field(None, alias="isUseful", description="是否有用")
    comment: Optional[str] = Field(None, alias="comment", description="用户评语")
    user_message: Optional[str] = Field(
        None, alias="userMessage", description="用户发送的信息"
    )
    ai_response: Optional[str] = Field(None, alias="aiResponse", description="AI回复的信息")


class FeedbackListRequest(BaseModel):
    """反馈列表查询请求"""
    model_config = ConfigDict(populate_by_name=True)

    user_id: Optional[str] = Field(None, alias="userId", description="用户ID筛选")
    conversation_id: Optional[str] = Field(
        None, alias="conversationId", description="对话ID筛选"
    )
    page: int = Field(1, ge=1, alias="page", description="页码")
    page_size: int = Field(10, ge=1, le=100, alias="pageSize", description="每页数量")


class FeedbackSummaryRequest(BaseModel):
    """反馈总结查询请求（近 days 天）"""
    model_config = ConfigDict(populate_by_name=True)
    # 改为可选：不传则由接口从配置 FEEDBACK_TREND_DEFAULT_DAYS 读取
    days: Optional[int] = Field(
        None, ge=1, alias="days", description="近 days 天的反馈总结（可选，不传则用配置默认值）"
    )


class GetConversationFeedbackRequest(BaseModel):
    """根据会话ID获取反馈请求"""
    model_config = ConfigDict(populate_by_name=True)

    conversation_id: str = Field(
        ..., alias="conversationId", description="会话ID"
    )


class ConversationFeedbackResponse(BaseModel):
    """根据会话ID获取反馈的响应"""
    model_config = ConfigDict(populate_by_name=True)

    conversation_id: str = Field(
        ..., alias="conversationId", description="会话ID"
    )
    has_feedback: bool = Field(
        ..., alias="hasFeedback", description="是否已有反馈"
    )
    count: int = Field(
        ..., alias="count", description="反馈条数"
    )
    # 新结构：每条反馈包含用户消息与 AI 回复；可选用户信息
    class ConversationFeedbackItem(BaseModel):
        model_config = ConfigDict(populate_by_name=True)
        user_message: str = Field(..., alias="userMessage", description="该轮用户发言")
        ai_response: str = Field(..., alias="aiResponse", description="该轮 AI 回复")
        user_info: Optional[Dict] = Field(None, alias="userInfo", description="用户信息(结构由后端定义)")

    items: List[ConversationFeedbackItem] = Field(
        default_factory=list, alias="items", description="反馈项列表（含用户消息与AI回复）"
    )
    # 兼容旧字段：若仅返回 AI 文本列表，仍可解析
    ai_responses: Optional[List[str]] = Field(
        default=None, alias="aiResponses", description="兼容旧字段：仅 AI 回复文本列表"
    )
