"""
用户反馈服务 - 调用 Golang 后端的反馈接口
更新：
- 创建反馈改为调用 `/app/ai_feedback/create`，并按后端 CreateAiFeedbackRequest 字段发送：
  conversationId, feedbackType, isUseful, comment, userMessage, aiResponse（始终上传 feedbackType/comment，允许空字符串）。
- 会话反馈 `by_conversation` 返回结构更新：items 内包含 userMessage 与 aiResponse（可选 userInfo），不再返回 createdAt。
"""
import httpx
import logging
import json
from typing import Optional, Dict, Any, List
from app.core.config import settings

logger = logging.getLogger(__name__)


class FeedbackService:
    """反馈服务客户端"""

    def __init__(self):
        # 读取现有的 Golang 后端地址配置，不新增 BASE_URL
        # 若未配置则回退到本地默认地址
        self.base_url = getattr(settings, "GOLANG_API_BASE_URL", "http://localhost:8888")
        self.timeout = 10.0

    def _parse_response(self, response: httpx.Response) -> Dict[str, Any]:
        """解析后端响应，容忍非标准 JSON 文本。"""
        try:
            return response.json()
        except Exception:
            text = response.text
            logger.error(f"⚠️ 后端返回非标准JSON，原始响应: {text}")
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                try:
                    return json.loads(text[start : end + 1])
                except Exception:
                    return {"code": response.status_code, "msg": "非JSON响应", "raw": text}
            return {"code": response.status_code, "msg": "非JSON响应", "raw": text}

    async def create_feedback(
        self,
        conversation_id: str,
        user_id: Optional[str],
        is_useful: bool,
        feedback_type: Optional[List[str]],
        comment: Optional[str],
        user_message: str,
        ai_response: str,
        access_token: str,
    ) -> Dict[str, Any]:
        """
        创建用户反馈

        Args:
            conversation_id: 对话ID
            user_id: 用户ID（可选）
            is_useful: 是否有用
            feedback_type: 反馈类型（可选）
            comment: 用户评语（可选）
            user_message: 用户发送的信息
            ai_response: AI回复的信息
            access_token: 用户认证Token

        Returns:
            Dict: Golang 后端响应
        """
        try:
            # 新接口路径与字段
            url = f"{self.base_url}/app/ai_feedback/create"

            # 基础字段按 CreateAiFeedbackRequest 要求（feedbackType 为字符串数组）
            payload: Dict[str, Any] = {
                "conversationId": conversation_id,
                "isUseful": is_useful,
                "comment": comment or "",
                "userMessage": user_message,
                "aiResponse": ai_response,
                "feedbackType": feedback_type or [],
            }


            headers = {
                "x-token": access_token,
                "Content-Type": "application/json",
                "Accept": "application/json",
            }

            # 以原始 JSON 字符串发送，避免任何中间层改写或编码差异
            payload_json = json.dumps(payload, ensure_ascii=False)

            logger.info(
                f"📤 [反馈服务] 调用Go后端: url={url}, conversationId={conversation_id}, isUseful={is_useful}"
            )
            logger.debug(f"📦 发送JSON: {payload_json}")

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, content=payload_json, headers=headers)
                result = self._parse_response(response)

                if response.status_code == 200:
                    logger.info(
                        f"✅ 反馈创建成功 | conversation_id={conversation_id}, user_id={user_id}"
                    )
                else:
                    logger.error(f"❌ 反馈创建失败: {result}")
                return result

        except Exception as e:
            logger.error(f"❌ 反馈创建异常: {str(e)}", exc_info=True)
            return {"code": 500, "msg": f"创建失败: {str(e)}", "data": None}

    


    async def get_feedback_summary(self, days: int, access_token: str) -> Dict[str, Any]:
        """
        获取近 days 天的反馈总结（GET）

        Args:
            days: 需要查询的天数
            access_token: 用户认证Token

        Returns:
            Dict: 反馈总结数据
        """
        try:
            url = f"{self.base_url}/app/ai_feedback/summary"

            params = {"days": days}

            headers = {
                "x-token": access_token,
                "Accept": "application/json",
            }

            logger.info(f"🧾 [反馈服务] 查询反馈总结(GET): days={days}")

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params, headers=headers)
                result = self._parse_response(response)

                if response.status_code == 200:
                    logger.info("✅ 反馈总结查询成功")
                else:
                    logger.error(f"❌ 反馈总结查询失败: {result}")
                return result

        except Exception as e:
            logger.error(f"❌ 反馈总结查询异常: {str(e)}", exc_info=True)
            return {"code": 500, "msg": f"查询失败: {str(e)}", "data": None}


    async def get_feedback_by_conversation(self, conversation_id: str, access_token: str) -> Dict[str, Any]:
        """
        根据会话ID获取反馈（GET）

        Args:
            conversation_id: 会话ID
            access_token: 用户认证Token

        Returns:
            Dict: 会话反馈数据（示例）
            {
              "code": 0,
              "data": {
                "conversationId": "conv_xxx",
                "hasFeedback": true,
                "count": 1,
                "items": [
                  { "userMessage": "...", "aiResponse": "...", "userInfo": { ... } }
                ]
              }
            }
        """
        try:
            url = f"{self.base_url}/app/ai_feedback/by_conversation"

            params = {"conversationId": conversation_id}

            headers = {
                "x-token": access_token,
                "Accept": "application/json",
            }

            logger.info(
                f"🧾 [反馈服务] 按会话查询反馈(GET): conversationId={conversation_id}"
            )

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params, headers=headers)
                result = self._parse_response(response)

                if response.status_code == 200:
                    logger.info("✅ 会话反馈查询成功")
                else:
                    logger.error(f"❌ 会话反馈查询失败: {result}")
                return result

        except Exception as e:
            logger.error(f"❌ 会话反馈查询异常: {str(e)}", exc_info=True)
            return {"code": 500, "msg": f"查询失败: {str(e)}", "data": None}


# 全局反馈服务实例
feedback_service = FeedbackService()
