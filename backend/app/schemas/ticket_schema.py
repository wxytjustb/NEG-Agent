from pydantic import BaseModel, Field
from typing import Optional, List, Union, Any
from datetime import datetime

class AppTicket(BaseModel):
    """工单模型"""
    id: Optional[int] = Field(None, description="工单ID")
    title: Optional[str] = Field(None, alias="title", description="工单标题")
    app_user_id: Optional[int] = Field(None, alias="appUserId", description="用户ID")
    issue_type: Optional[str] = Field(None, alias="issueType", description="问题类型: 法律咨询/心理咨询/投诉建议")
    platform: Optional[str] = Field(None, alias="platform", description="涉及的平台或设施")
    brief_facts: Optional[str] = Field(None, alias="briefFacts", description="事实简要说明")
    user_request: Optional[str] = Field(None, alias="userRequest", description="用户诉求描述")
    people_needing_help: Optional[Union[bool, str, int]] = Field(None, alias="peopleNeedingHelp", description="需要帮助的人数(是否涉及多人)")
    conversation_id: Optional[str] = Field(None, alias="conversationId", description="关联的会话ID")
    status: str = Field("pending", alias="status", description="状态: pending, processing, closed, rejected")
    handler_id: Optional[int] = Field(None, alias="handlerId", description="处理人ID")
    handler_name: Optional[str] = Field(None, alias="handlerName", description="处理人姓名")
    
    created_at: Optional[datetime] = Field(None, alias="createdAt", description="创建时间")
    updated_at: Optional[datetime] = Field(None, alias="updatedAt", description="更新时间")

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class TicketListResponse(BaseModel):
    """工单列表响应"""
    total: int
    items: List[AppTicket]
    page: int
    page_size: int

class UpdateTicketStatusRequest(BaseModel):
    """更新工单状态请求"""
    id: int = Field(..., description="工单ID")
    status: str = Field(..., description="新状态")

class BaseResponse(BaseModel):
    """基础响应结构"""
    code: int = Field(..., description="状态码")
    msg: str = Field(..., description="消息")
    data: Optional[Any] = Field(None, description="数据")
