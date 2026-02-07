from fastapi import APIRouter, Depends, HTTPException, Body
from app.schemas.ticket_schema import AppTicket, BaseResponse
from app.services.ticket_summary_service import ticket_summary_service
from app.core.security import get_current_session
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ticket_summary", tags=["Ticket Summary"])

@router.post("/summarize", response_model=AppTicket)
async def summarize_ticket(
    payload: Dict[str, Any] = Body(..., example={"conversationId": "uuid", "text": "可选描述"}),
    user: dict = Depends(get_current_session)
):
    """
    工单总结预览接口
    输入: {"conversationId": "可选，用于获取历史记录", "text": "可选，补充描述"}
    输出: 填充好的 AppTicket 对象
    """
    try:
        user_id = user.get("user_id")
        access_token = user.get("access_token")
        
        text = payload.get("text")
        conversation_id = payload.get("conversationId")
        
        # 移除 text 必填校验，支持仅通过 conversationId 总结
            
        logger.info(f"Generating ticket summary for user {user_id}")
        
        # 调用总结服务 (内部处理上下文获取)
        ticket = await ticket_summary_service.summarize_ticket(
            text=text,
            user_id=user_id,
            conversation_id=conversation_id,
            access_token=access_token
        )
        return ticket
        
    except Exception as e:
        logger.error(f"Error in summarize_ticket: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
