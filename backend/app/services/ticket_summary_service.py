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

logger = logging.getLogger(__name__)

# 工单总结提示词
TICKET_SUMMARY_PROMPT = """
你是一个专业的工单处理助手。请根据以下信息（对话历史、当前输入、用户画像、工单类别），提取关键信息并生成工单数据。

## 上下文信息
1. **当前用户输入**:
{current_input}

2. **对话历史**:
{history}

3. **用户画像**:
{user_profile}

4. **可选工单类别**:
{ticket_categories}

## 核心原则：绝对忠实于事实，严禁捏造，下面所罗列的东西都是举例不是事实，一切都要按照用户所说的实情来总结。
1. **仅依据对话内容**：你总结的所有信息必须能在用户提供的文本中找到明确依据。
2. **区分事实来源**：只有【用户】说的话才是案件事实。
3. **缺失即留空**：如果输入中未提及时间、金额、平台等具体信息，**绝对不要捏造或推测**，对应字段必须填 null。
4. **禁止脑补细节**：不要补充任何用户没说过的背景故事或细节。
5. **严禁抄袭示例**：下方的“返回示例”仅供格式参考，用户说了什么就总结什么。

## 提取字段要求
请提取以下字段并返回 JSON 格式：
1. **issueType**: 工单二级分类 (必须是【可选工单类别】中列出的名称。请仔细分析用户问题，必须属于提供的分类之一)
2. **platform**: 涉及平台 (如果没有明确提及则填 null)
3. **briefFacts**: 事实简述 (客观描述发生了什么，包含时间、地点、人物、起因、经过、结果。整合所有细节，保持客观)
4. **title**: 工单标题 (格式：核心问题摘要，10字以内，禁止包含平台名称)
5. **userRequest**: 用户诉求 (用户希望得到什么帮助或结果)
6. **peopleNeedingHelp**: 涉及人数 (如果是单人填1，多人填具体数字或描述)

## 返回示例 (仅作格式参考，内容请忽略)
{{
    "issueType": "示例分类",
    "platform": "示例平台",
    "briefFacts": "用户描述的实际情况...",
    "title": "示例标题",
    "userRequest": "用户的实际诉求...",
    "peopleNeedingHelp": 1
}}

## 极简输入处理
如果用户只说了“人工”、“投诉”、“帮帮我”等简短词汇，没有提供具体事实：
- briefFacts 填 null 或 "用户仅表达了诉求，未提供细节"
- issueType 尝试推断，无法推断填 null
- 其他字段按需填 null

请返回纯 JSON 格式，不要包含 Markdown 格式标记（如 ```json）。
如果没有相关信息，请对应字段填 null。
"""

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
        access_token: Optional[str] = None
    ) -> AppTicket:
        """
        根据文本总结生成工单预览
        :param text: 用户输入的文本 (可选)
        :param user_id: 用户ID
        :param conversation_id: 会话ID
        :param access_token: 用户 token (用于获取工单类别)
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

            # 构建 Prompt
            prompt = ChatPromptTemplate.from_template(TICKET_SUMMARY_PROMPT)
            chain = prompt | self.llm | JsonOutputParser()
            
            # 处理空文本情况
            input_text = text if text else "（无新输入，请根据对话历史总结）"
            
            # 打印 LLM 输入上下文
            print("\n" + "-"*30 + " [LLM INPUT CONTEXT] " + "-"*30)
            print(f"History Length: {len(history_text)}")
            print(f"Categories: {ticket_categories[:100]}...")
            print(f"User Profile: {user_profile}")
            print(f"Input Text: {input_text}")
            print("-" * 80 + "\n")

            result = await chain.ainvoke({
                "history": history_text,
                "current_input": input_text,
                "user_profile": user_profile,
                "ticket_categories": ticket_categories,
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
