# 用户反馈API - Feedback API
from fastapi import APIRouter, Depends, HTTPException, Query
from app.schemas.feedback_schema import (
    CreateFeedbackRequest,
    FeedbackSummaryRequest,
    GetConversationFeedbackRequest,
    ConversationFeedbackResponse,
)
from app.services.feedback_service import feedback_service
from app.core.security import get_current_session
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/feedback", tags=["Feedback"])


@router.post("/create", summary="创建用户反馈")
async def create_feedback(
    request: CreateFeedbackRequest,
    user: dict = Depends(get_current_session)
):
    """
    创建用户反馈
    
    参数:
    - conversation_id: 对话ID
    - is_useful: 是否有用
    - comment: 用户评语（可选）
    - user_message: 用户发送的信息
    - ai_response: AI回复的信息
    
    返回: Go后端响应
    """
    try:
        access_token = user.get("access_token")
        user_id = user.get("user_id")  # 新增：获取user_id
        
        if not access_token:
            raise HTTPException(status_code=401, detail="未找到认证信息")
        
        logger.info(f"💬 [反馈] 创建反馈: user_id={user_id}, conversation_id={request.conversation_id}, is_useful={request.is_useful}")
        
        result = await feedback_service.create_feedback(
            conversation_id=request.conversation_id,
            user_id=user_id,  # 新增：传递user_id
            is_useful=request.is_useful,
            feedback_type=request.feedback_type,  # 新增：传递feedback_type
            comment=request.comment,
            user_message=request.user_message,
            ai_response=request.ai_response,
            access_token=access_token
        )
        
        return result
    
    except Exception as e:
        logger.error(f"创建反馈失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"创建反馈失败: {str(e)}")




@router.post("/summary", summary="获取反馈总结")
async def get_feedback_summary(
    request: FeedbackSummaryRequest,
    user: dict = Depends(get_current_session)
):
    """
    获取近 days 天的反馈总结

    参数:
    - days: 近 days 天内的反馈总结

    返回: 反馈总结数据
    """
    try:
        access_token = user.get("access_token")
        if not access_token:
            raise HTTPException(status_code=401, detail="未找到认证信息")

        # 兼容未传入 days 的情况，默认从配置读取
        req_days = request.days if (request and request.days is not None) else None
        days = req_days if req_days is not None else getattr(settings, "FEEDBACK_TREND_DEFAULT_DAYS", 7)
        logger.info(
            f"🧾 [反馈] 查询反馈总结: using days={days} (requested={req_days}, default_from_config={settings.FEEDBACK_TREND_DEFAULT_DAYS})"
        )

        result = await feedback_service.get_feedback_summary(
            days=days,
            access_token=access_token,
        )

        return result

    except Exception as e:
        logger.error(f"查询反馈总结失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"查询反馈总结失败: {str(e)}")


@router.get("/by_conversation", summary="根据会话查询反馈")
async def get_feedback_by_conversation(
    conversation_id: str = Query(..., alias="conversationId"),
    user: dict = Depends(get_current_session)
):
    """
    根据会话ID获取反馈

    参数:
    - conversationId: 会话ID

    返回: 会话反馈数据
    数据结构示例:
    {
      "conversationId": "conv_xxx",
      "hasFeedback": true,
      "count": 1,
      "items": [
        { "userMessage": "用户消息", "aiResponse": "AI回复", "userInfo": { ... } }
      ]
    }
    """
    try:
        access_token = user.get("access_token")
        if not access_token:
            raise HTTPException(status_code=401, detail="未找到认证信息")

        logger.info(f"🧾 [反馈] 按会话查询反馈: conversationId={conversation_id}")

        result = await feedback_service.get_feedback_by_conversation(
            conversation_id=conversation_id,
            access_token=access_token,
        )

        return result

    except Exception as e:
        logger.error(f"按会话查询反馈失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"按会话查询反馈失败: {str(e)}")