from fastapi import APIRouter, Depends, HTTPException
from app.schemas.ticket_schema import BaseResponse
from app.schemas.ticket_volunteer_schema import GetVolunteersRequest, VolunteerListResponse, VolunteerInfo
from app.services.ticket_volunteer_service import ticket_volunteer_service
from app.core.security import get_current_session
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ticketVolunteer", tags=["TicketVolunteer"])

@router.post("/getByTicketAndConversation", response_model=BaseResponse)
async def get_volunteers_by_ticket_and_conversation(
    request: GetVolunteersRequest,
    user: dict = Depends(get_current_session)
):
    """
    根据工单ID和会话ID获取志愿者列表
    """
    try:
        access_token = user.get("access_token")
        user_id = user.get("user_id")
        
        if not access_token:
            raise HTTPException(status_code=401, detail="未找到认证信息")
            
        logger.info(f"🎫 [志愿者] 获取列表: user_id={user_id}, ticket_id={request.ticket_id}")
        
        result = await ticket_volunteer_service.get_volunteers_by_ticket_and_conversation(
            request_data=request,
            access_token=access_token
        )
        
        # 过滤多余字段，只返回前端需要的数据
        if result.get("code") in [0, 200] and result.get("data"):
            try:
                raw_data = result["data"]
                
                # Manual filtering to ensure robustness
                if isinstance(raw_data, dict) and "list" in raw_data and isinstance(raw_data["list"], list):
                    new_list = []
                    for item in raw_data["list"]:
                        new_item = {}
                        # Keep ID
                        if "ID" in item:
                            new_item["ID"] = item["ID"]
                        elif "id" in item:
                            new_item["ID"] = item["id"]
                            
                        # Keep volunteerUser (filtered)
                        if "volunteerUser" in item and isinstance(item["volunteerUser"], dict):
                            vu = item["volunteerUser"]
                            new_vu = {}
                            if "realname" in vu:
                                new_vu["realname"] = vu["realname"]
                            if "nickname" in vu:
                                new_vu["nickname"] = vu["nickname"]
                            if "volunteerServiceType" in vu:
                                new_vu["volunteerServiceType"] = vu["volunteerServiceType"]
                            new_item["volunteerUser"] = new_vu
                        
                        new_list.append(new_item)
                    
                    result["data"] = {"list": new_list}
                    logger.info(f"已手动过滤志愿者数据: {len(new_list)} 条记录")
                    
                # 处理直接返回数组的情况 (兼容性)
                elif isinstance(raw_data, list):
                    new_list = []
                    for item in raw_data:
                        new_item = {}
                        if "ID" in item: new_item["ID"] = item["ID"]
                        if "volunteerUser" in item and isinstance(item["volunteerUser"], dict):
                            vu = item["volunteerUser"]
                            new_vu = {}
                            if "realname" in vu: new_vu["realname"] = vu["realname"]
                            if "volunteerServiceType" in vu: new_vu["volunteerServiceType"] = vu["volunteerServiceType"]
                            new_item["volunteerUser"] = new_vu
                        new_list.append(new_item)
                    result["data"] = {"list": new_list}

            except Exception as e:
                logger.warning(f"过滤志愿者数据失败，将返回原始数据: {e}")
                
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取志愿者列表失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取志愿者列表失败: {str(e)}")
