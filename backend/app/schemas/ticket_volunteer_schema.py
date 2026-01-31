from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Any

class GetVolunteersRequest(BaseModel):
    """获取志愿者请求"""
    ticket_id: Optional[int] = Field(None, alias="ticketId", description="工单ID")
    conversation_id: Optional[str] = Field(None, alias="conversationId", description="会话ID")
    
    model_config = ConfigDict(populate_by_name=True)

class VolunteerUser(BaseModel):
    """志愿者用户详情"""
    realname: Optional[str] = Field(None, description="真实姓名")
    nickname: Optional[str] = Field(None, description="昵称")
    volunteer_service_type: Optional[str] = Field(None, alias="volunteerServiceType", description="服务类型")
    
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

class VolunteerInfo(BaseModel):
    """志愿者信息记录"""
    id: Optional[int] = Field(None, alias="ID", description="记录ID")
    volunteer_user: Optional[VolunteerUser] = Field(None, alias="volunteerUser", description="志愿者用户详情")
    
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

class VolunteerListResponse(BaseModel):
    """志愿者列表响应"""
    list: List[VolunteerInfo] = Field(default_factory=list, description="志愿者列表")

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

