from typing import Dict, Any, Optional
import json
import logging
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from app.core.config import settings
from pydantic import SecretStr
from app.schemas.ticket_schema import AppTicket
from app.services.ticket_service import ticket_service
from app.services.redis_service import redis_service
from app.utils.prompt import get_ticket_summary_prompt

logger = logging.getLogger(__name__)

class TicketSummaryService:
    """工单总结与创建服务"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.ALIYUN_MODEL,
            api_key=SecretStr(settings.ALIYUN_API_KEY) if settings.ALIYUN_API_KEY else None,
            base_url=settings.ALIYUN_API_BASE_URL,
            temperature=0.1,  # 低温度保证稳定输出
            max_tokens=500,
            extra_body={"enable_thinking": False}  # 显式禁用 thinking，通过 extra_body 传递
        )
        self.base_url = settings.GOLANG_API_BASE_URL
        self.timeout = 10.0

    async def get_volunteer_service_categories(self, access_token: str) -> Dict[str, Any]:
        """获取志愿者服务类型列表 (从后端接口获取)"""
        url = f"{self.base_url}/app/volunteer/getServiceCategories"
        headers = {"x-token": access_token}
        
        try:
            import httpx
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=headers)
                
                # 打印原始响应到控制台
                print("\n" + "="*50)
                print("🏷️ [CATEGORIES API DEBUG]")
                print(f"URL: {url}")
                print(f"Status Code: {response.status_code}")
                try:
                    resp_json = response.json()
                    print(f"Response: {json.dumps(resp_json, ensure_ascii=False, indent=2)}")
                except:
                    print(f"Raw Response: {response.text}")
                print("="*50 + "\n")

                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Get categories failed with status {response.status_code}: {response.text}")
                    return {"code": response.status_code, "msg": f"HTTP Error {response.status_code}", "data": None}
                    
        except Exception as e:
            logger.error(f"Error getting categories: {e}", exc_info=True)
            print(f"❌ [CATEGORIES API ERROR]: {str(e)}")
            return {"code": 500, "msg": str(e), "data": None}

    async def summarize_ticket(
        self, 
        text: Optional[str] = None, 
        user_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        access_token: Optional[str] = None,
        intent_info: Optional[str] = None
    ) -> AppTicket:
        """
        根据文本总结生成工单预览
        :param text: 用户输入的文本 (可选)
        :param user_id: 用户ID
        :param conversation_id: 会话ID
        :param access_token: 用户 token (用于获取工单类别)
        :param intent_info: 意图识别结果信息
        :return: AppTicket 对象 (仅包含总结字段)
        """
        print(f"\n🤖 [Ticket Summary Service] Start summarizing... Text: {text[:20] if text else 'None'}...")
        
        try:
            # 1. 获取对话历史 (从 Golang 后端 MySQL)
            history_text = "无"
            if conversation_id and access_token:
                try:
                    from app.core.database import golang_db_client
                    # 使用 golang_db_client 从后端接口获取历史
                    history_messages = await golang_db_client.get_conversation_history(conversation_id, access_token)
                    
                    if history_messages:
                        formatted_history = []
                        # 取最近 20 条消息作为上下文
                        for msg in history_messages[-20:]: 
                            role = msg.get("role", "unknown")
                            content = msg.get("content", "")
                            # 过滤掉空的或无效的消息
                            if content:
                                formatted_history.append(f"{role}: {content}")
                        
                        if formatted_history:
                            history_text = "\n".join(formatted_history)
                            logger.info(f"Loaded {len(formatted_history)} history messages from Golang API for summary.")
                        else:
                            logger.info(f"No valid content in chat history for conversation {conversation_id}")
                    else:
                         logger.info(f"No chat history found from Golang API for conversation {conversation_id}")
                except Exception as e:
                    logger.warning(f"Failed to fetch chat history from Golang API: {e}")
            else:
                logger.info("Missing conversation_id or access_token, skipping history fetch.")
            
            # 2. 获取工单类别
            ticket_categories = ""
            category_map = {} # 建立 子分类 -> 父分类 的映射
            
            if access_token:
                 try:
                    # 尝试从后端服务获取 (使用本类中的方法)
                    categories_resp = await self.get_volunteer_service_categories(access_token)
                    if categories_resp and isinstance(categories_resp, dict):
                        data = categories_resp.get("data")
                        if isinstance(data, list):
                            formatted_categories = []
                            for item in data:
                                if not isinstance(item, dict):
                                    continue
                                    
                                parent_name = item.get("name", "未知分类")
                                children = item.get("children", [])
                                
                                if children and isinstance(children, list):
                                    # 提取子分类名称
                                    for child in children:
                                        if isinstance(child, dict) and child.get("name"):
                                            child_name = child.get("name")
                                            # 记录映射关系
                                            category_map[child_name] = parent_name
                                            # 列表中仅添加子分类名称
                                            formatted_categories.append(child_name)
                                    
                            if formatted_categories:
                                ticket_categories = ", ".join(formatted_categories)
                 except Exception as e:
                     logger.warning(f"Failed to fetch ticket categories inside summarize_ticket: {e}")
            
            if not ticket_categories:
                logger.warning("No ticket categories found, using empty string.")
            
            # 3. 获取用户画像 (当前仅使用 ID，后续可扩展)
            user_profile = f"用户ID: {user_id}" if user_id else "未知用户"

            # 处理意图信息
            current_intent_info = intent_info if intent_info else "未提供意图信息"

            # 构建 Prompt
            prompt = ChatPromptTemplate.from_template(get_ticket_summary_prompt())
            chain = prompt | self.llm | JsonOutputParser()
            
            # 处理空文本情况
            input_text = text if text else "（无新输入，请根据对话历史总结）"
            
            # 打印 LLM 输入上下文
            print("\n" + "-"*30 + " [LLM INPUT CONTEXT] " + "-"*30)
            print(f"History Length: {len(history_text)}")
            print(f"Categories: {ticket_categories[:100]}...")
            print(f"User Profile: {user_profile}")
            print(f"Intent Info: {current_intent_info}")
            print(f"Input Text: {input_text}")
            print("-" * 80 + "\n")

            result = await chain.ainvoke({
                "history": history_text,
                "current_input": input_text,
                "user_profile": user_profile,
                "ticket_categories": ticket_categories,
                "intent_info": current_intent_info,
            })
            
            # 打印 LLM 原始输出
            print("\n" + "-"*30 + " [LLM RAW OUTPUT] " + "-"*30)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            print("-" * 80 + "\n")
            
            return AppTicket(**result)
            
        except Exception as e:
            logger.error(f"Error summarizing ticket: {e}", exc_info=True)
            return AppTicket(title="工单自动生成失败，请手动填写")

    async def create_ticket(self, ticket: AppTicket, access_token: str) -> Dict[str, Any]:
        """
        创建工单 (代理调用 TicketService)
        :param ticket: 工单对象
        :param access_token: 用户 token
        :return: 创建结果
        """
        return await ticket_service.create_ticket(ticket, access_token)

ticket_summary_service = TicketSummaryService()
