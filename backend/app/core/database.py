"""
Golang Backend Database Client - 调用 Golang 后端的 MySQL 数据库接口
提供消息存储和查询功能
"""
import httpx
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.core.config import settings

logger = logging.getLogger(__name__)


class GolangDatabaseClient:
    """Golang 后端数据库客户端"""
    
    def __init__(self):
        self.base_url = settings.GOLANG_API_BASE_URL
        self.timeout = 10.0  # 10秒超时
    
    async def save_message(
        self,
        conversation_id: str,
        message_content: str,
        role: str,
        message_id: str,
        access_token: Optional[str] = None  # 新增：认证Token
    ) -> bool:
        """
        保存消息到 Golang 后端 MySQL
        
        Args:
            conversation_id: 对话ID
            message_content: 消息内容
            role: 角色 (user/assistant)
            message_id: 消息ID
            access_token: 用户认证Token（可选）
            
        Returns:
            bool: 保存成功返回 True
        """
        try:
            url = f"{self.base_url}/app/conversation/createMessage"
            
            payload = {
                "conversationId": conversation_id,
                "messageContent": message_content,
                "role": role,
                "messageId": message_id
            }
            
            # 构建请求头，使用 x-token 认证
            headers = {
                "Content-Type": "application/json"
            }
            if access_token:
                headers["x-token"] = access_token  # Golang 后端使用 x-token
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload, headers=headers)
                
                if response.status_code == 200:
                    logger.info(
                        f"✅ 消息保存成功 | conversation_id={conversation_id[:20]}... | "
                        f"role={role} | message_id={message_id[:20]}..."
                    )
                    return True
                else:
                    logger.error(
                        f"❌ 消息保存失败 | status={response.status_code} | "
                        f"response={response.text}"
                    )
                    return False
                    
        except Exception as e:
            logger.error(f"❌ 调用 Golang API 失败: {e}", exc_info=True)
            return False
    
    async def get_conversation_history(
        self,
        conversation_id: str,
        access_token: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        从 Golang 后端获取对话历史
        
        Args:
            conversation_id: 对话ID
            access_token: 用户认证Token（可选）
            
        Returns:
            List[Dict]: 消息列表，每条消息包含 role, content, timestamp 等字段
        """
        try:
            url = f"{self.base_url}/app/conversation/{conversation_id}/history"
            
            # 构建请求头
            headers = {}
            if access_token:
                headers["x-token"] = access_token
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    result = response.json()
                    # Golang 后端返回格式: {"code": 0, "data": {...}, "msg": "success"}
                    if result.get("code") == 0:  # 修正：Golang 返回 code: 0 表示成功
                        data = result.get("data", {})
                        messages = data.get("messages", [])
                        logger.info(
                            f"✅ 获取对话历史成功 | conversation_id={conversation_id[:20]}... | "
                            f"消息数={len(messages)}"
                        )
                        return messages
                    else:
                        logger.error(
                            f"❌ Golang API 返回错误 | code={result.get('code')} | "
                            f"msg={result.get('msg')}"
                        )
                        return []
                else:
                    logger.error(
                        f"❌ 获取对话历史失败 | status={response.status_code} | "
                        f"response={response.text}"
                    )
                    return []
                    
        except Exception as e:
            logger.error(f"❌ 调用 Golang API 失败: {e}", exc_info=True)
            return []
    
    async def get_user_conversations(
        self,
        access_token: str
    ) -> List[Dict[str, Any]]:
        """
        获取用户的所有会话列表（基于 user_id）
        
        Args:
            access_token: 用户认证Token
            
        Returns:
            List[Dict]: 会话列表，每个会话包含 conversation_id, 消息数量等信息
        """
        try:
            url = f"{self.base_url}/app/conversation/list"
            
            # 构建请求头
            headers = {}
            if access_token:
                headers["x-token"] = access_token
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    result = response.json()
                    # Golang 后端返回格式: {"code": 0, "data": {"conversations": [...], "total": N}, "msg": "success"}
                    if result.get("code") == 0:  # 修正：Golang 返回 code: 0 表示成功
                        data = result.get("data", {})
                        # 提取嵌套的 conversations 数组
                        if isinstance(data, dict):
                            conversations = data.get("conversations", [])
                        else:
                            # 兼容旧版本，data 直接是数组
                            conversations = data if isinstance(data, list) else []
                        
                        logger.info(
                            f"✅ 获取用户会话列表成功 | "
                            f"会话数={len(conversations)}"
                        )
                        return conversations
                    else:
                        logger.error(
                            f"❌ Golang API 返回错误 | code={result.get('code')} | "
                            f"msg={result.get('msg')}"
                        )
                        return []
                else:
                    logger.error(
                        f"❌ 获取会话列表失败 | status={response.status_code} | "
                        f"response={response.text}"
                    )
                    return []
                    
        except Exception as e:
            logger.error(f"❌ 调用 Golang API 失败: {e}", exc_info=True)
            return []


# 全局实例
golang_db_client = GolangDatabaseClient()
