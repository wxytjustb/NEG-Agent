from typing import List, Optional, Dict, Any
import httpx
import logging
from app.core.config import settings
from app.schemas.ticket_schema import AppTicket

logger = logging.getLogger(__name__)

class TicketService:
    """工单服务类 - 负责调用 Golang 后端工单接口"""
    
    def __init__(self):
        self.base_url = settings.GOLANG_API_BASE_URL
        self.timeout = 10.0

    async def create_ticket(self, ticket_data: AppTicket, access_token: str) -> Dict[str, Any]:
        """创建工单"""
        url = f"{self.base_url}/app/ticket/createTicket"
        
        headers = {
            "Content-Type": "application/json",
            "x-token": access_token
        }
        
        try:
            # 转换 Pydantic 模型为 dict，排除 None 值，使用 alias 作为 key
            payload = ticket_data.dict(exclude_none=True, by_alias=True)
            logger.info(f"Creating ticket with payload: {payload}")
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload, headers=headers)
                
                if response.status_code == 200:
                    resp_json = response.json()
                    logger.info(f"Create ticket response: {resp_json}")
                    return resp_json
                else:
                    logger.error(f"Create ticket failed with status {response.status_code}: {response.text}")
                    
        except Exception as e:
            logger.error(f"Error creating ticket: {e}", exc_info=True)
            
        return {"code": -1, "msg": "Internal Error", "data": {}}

    async def get_ticket_list(
        self, 
        access_token: str,
        page: int = 1, 
        page_size: int = 10, 
        conversation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取工单列表"""
        url = f"{self.base_url}/app/ticket/getTicketList"
        
        headers = {
            "x-token": access_token
        }
        
        params = {
            "page": page,
            "pageSize": page_size
        }
        if conversation_id:
            params["conversationId"] = conversation_id
            
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params, headers=headers)
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Get ticket list failed with status {response.status_code}: {response.text}")
                    return {"code": response.status_code, "msg": f"HTTP Error {response.status_code}", "data": None}
                    
        except Exception as e:
            logger.error(f"Error getting ticket list: {e}", exc_info=True)
            return {"code": 500, "msg": str(e), "data": None}

    async def get_ticket_detail(self, ticket_id: int, access_token: str) -> Optional[AppTicket]:
        """获取工单详情"""
        url = f"{self.base_url}/app/ticket/getTicketDetail"
        
        headers = {
            "x-token": access_token
        }
        
        params = {"id": ticket_id}
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params, headers=headers)
                
                if response.status_code == 200:
                    resp_json = response.json()
                    if resp_json.get("code") == 200 or resp_json.get("code") == 0:
                        data = resp_json.get("data")
                        if data:
                            return AppTicket(**data)
                    logger.error(f"Get ticket detail failed: {resp_json}")
                else:
                    logger.error(f"Get ticket detail failed with status {response.status_code}: {response.text}")
                    
        except Exception as e:
            logger.error(f"Error getting ticket detail: {e}", exc_info=True)
            
        return None

    async def update_ticket_status(self, ticket_id: int, status: str, access_token: str) -> bool:
        """更新工单状态"""
        url = f"{self.base_url}/app/ticket/updateTicketStatus"
        
        headers = {
            "Content-Type": "application/json",
            "x-token": access_token
        }
        
        payload = {
            "id": ticket_id,
            "status": status
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload, headers=headers)
                
                if response.status_code == 200:
                    resp_json = response.json()
                    if resp_json.get("code") == 200 or resp_json.get("code") == 0:
                        return True
                    logger.error(f"Update ticket status failed: {resp_json}")
                else:
                    logger.error(f"Update ticket status failed with status {response.status_code}: {response.text}")
                    
        except Exception as e:
            logger.error(f"Error updating ticket status: {e}", exc_info=True)
            
        return False

ticket_service = TicketService()
