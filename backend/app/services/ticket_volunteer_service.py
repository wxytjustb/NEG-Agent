from typing import Dict, Any, Optional
import httpx
import logging
from app.core.config import settings
from app.schemas.ticket_volunteer_schema import GetVolunteersRequest

logger = logging.getLogger(__name__)

class TicketVolunteerService:
    """工单志愿者服务类 - 负责调用 Golang 后端接口"""
    
    def __init__(self):
        self.base_url = settings.GOLANG_API_BASE_URL
        self.timeout = 10.0

    async def get_volunteers_by_ticket_and_conversation(
        self, 
        request_data: GetVolunteersRequest, 
        access_token: str
    ) -> Dict[str, Any]:
        """根据工单ID和会话ID获取志愿者列表"""
        url = f"{self.base_url}/app/ticketVolunteer/getByTicketAndConversation"
        
        headers = {
            "Content-Type": "application/json",
            "x-token": access_token
        }
        
        try:
            payload = request_data.model_dump(exclude_none=True, by_alias=True)
            logger.info(f"Getting volunteers with payload: {payload}")
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload, headers=headers)
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Get volunteers failed with status {response.status_code}: {response.text}")
                    return {
                        "code": response.status_code, 
                        "msg": f"HTTP Error {response.status_code}", 
                        "data": None
                    }
                    
        except Exception as e:
            logger.error(f"Error getting volunteers: {e}", exc_info=True)
            return {"code": 500, "msg": str(e), "data": None}

ticket_volunteer_service = TicketVolunteerService()
