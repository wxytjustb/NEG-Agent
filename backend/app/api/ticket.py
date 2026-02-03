from fastapi import APIRouter, Depends, HTTPException, Query, Body
from app.schemas.ticket_schema import AppTicket, TicketListResponse, UpdateTicketStatusRequest, BaseResponse
from app.services.ticket_service import ticket_service
from app.core.security import get_current_session
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ticket", tags=["Ticket"])

@router.post("/createTicket", response_model=BaseResponse)
async def create_ticket(
    ticket: AppTicket,
    user: dict = Depends(get_current_session)
):
    """
    创建工单
    Body: AppTicket 结构
    """
    try:
        access_token = user.get("access_token")
        user_id = user.get("user_id")
        
        if not access_token:
            raise HTTPException(status_code=401, detail="未找到认证信息")
        
        logger.info(f"🎫 [工单] 创建工单: user_id={user_id}, issue_type={ticket.issue_type}")
    
        result = await ticket_service.create_ticket(ticket, access_token)
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建工单失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"创建工单失败: {str(e)}")

@router.get("/getTicketList", response_model=BaseResponse)
async def get_ticket_list(
    page: int = Query(1, ge=1, description="页码"),
    pageSize: int = Query(10, ge=1, le=100, description="每页数量"),
    conversationId: Optional[str] = Query(None, description="会话ID过滤"),
    user: dict = Depends(get_current_session)
):
    """
    获取工单列表
    Query: page, pageSize, conversationId
    """
    try:
        access_token = user.get("access_token")
        user_id = user.get("user_id")
        
        if not access_token:
            raise HTTPException(status_code=401, detail="未找到认证信息")
            
        logger.info(f"🎫 [工单] 获取列表: user_id={user_id}, page={page}")
        
        result = await ticket_service.get_ticket_list(
            access_token=access_token,
            page=page,
            page_size=pageSize,
            conversation_id=conversationId
        )
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取工单列表失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取工单列表失败: {str(e)}")

@router.get("/getTicketDetail", response_model=AppTicket)
async def get_ticket_detail(
    id: int = Query(..., description="工单ID"),
    user: dict = Depends(get_current_session)
):
    """
    获取工单详情
    Query: id
    """
    try:
        access_token = user.get("access_token")
        user_id = user.get("user_id")
        
        if not access_token:
            raise HTTPException(status_code=401, detail="未找到认证信息")
            
        logger.info(f"🎫 [工单] 获取详情: user_id={user_id}, ticket_id={id}")
        
        ticket = await ticket_service.get_ticket_detail(id, access_token)
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
            
        return ticket
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取工单详情失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取工单详情失败: {str(e)}")

@router.get("/getVolunteerServiceCategories", response_model=BaseResponse)
async def get_volunteer_service_categories(
    user: dict = Depends(get_current_session)
):
    """
    获取志愿者服务分类列表
    """
    try:
        access_token = user.get("access_token")
        
        if not access_token:
            raise HTTPException(status_code=401, detail="未找到认证信息")
            
        result = await ticket_service.get_volunteer_service_categories(access_token)
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取服务分类失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取服务分类失败: {str(e)}")


@router.get("/getVolunteerServiceCategories", response_model=BaseResponse)
async def get_volunteer_service_categories(
    user: dict = Depends(get_current_session)
):
    """
    获取志愿者服务类型列表
    """
    try:
        access_token = user.get("access_token")
        
        if not access_token:
            raise HTTPException(status_code=401, detail="未找到认证信息")
            
        result = await ticket_service.get_volunteer_service_categories(access_token)
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取服务类型列表失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取服务类型列表失败: {str(e)}")


@router.get("/getServiceCategories", response_model=BaseResponse)
async def get_service_categories(
    user: dict = Depends(get_current_session)
):
    """
    获取服务分类列表
    """
    try:
        access_token = user.get("access_token")
        
        if not access_token:
            raise HTTPException(status_code=401, detail="未找到认证信息")
            
        result = await ticket_service.get_service_categories(access_token)
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取服务分类列表失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取服务分类列表失败: {str(e)}")


@router.post("/updateTicketStatus")
async def update_ticket_status(
    request: UpdateTicketStatusRequest,
    user: dict = Depends(get_current_session)
):
    """
    更新工单状态
    Body: {id: "...", status: "..."}
    """
    try:
        access_token = user.get("access_token")
        user_id = user.get("user_id")
        
        if not access_token:
            raise HTTPException(status_code=401, detail="未找到认证信息")

        logger.info(f"🎫 [工单] 更新状态: user_id={user_id}, ticket_id={request.id}, status={request.status}")

        success = await ticket_service.update_ticket_status(request.id, request.status, access_token)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update status")
            
        return {"code": 200, "message": "Success", "data": {"status": request.status}}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新工单状态失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"更新工单状态失败: {str(e)}")
