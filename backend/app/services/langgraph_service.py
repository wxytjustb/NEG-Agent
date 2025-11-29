# LangGraph 服务层 - 工作流编排
from typing import List, Dict, Any, Optional, TypedDict
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage, SystemMessage
from app.core.config import settings
from app.services.llm_service import llm_service
from app.services.redis_service import redis_service
from app.prompts.prompts import RIGHTS_PROTECTION_SYSTEM_PROMPT
import logging

logger = logging.getLogger(__name__)


class LangGraphService:
    """LangGraph 服务类 - 负责工作流编排"""
    
    def __init__(self):
        """初始化 LangGraph 服务"""
        self.settings = settings
        logger.info("LangGraph 服务已初始化")
    
    def create_chat_and_save_graph(self):
        """创建 LLM 对话并存储到 Redis 的工作流
        
        工作流步骤：
        1. 接收用户消息
        2. 调用 LLM 生成回复
        3. 保存对话到 Redis
        
        Returns:
            编译后的工作流图
        """
        # 定义工作流状态
        class ChatState(TypedDict):
            session_data: Dict[str, Any]  # 会话数据（包含 user_id, session_token 等）
            user_message: str  # 用户消息
            user_intent: str  # 用户意图（通过 AI 分析）
            ai_response: str  # AI回复
            messages: List[BaseMessage]  # 完整消息列表
            error: Optional[str]  # 错误信息
        
        # 创建状态图
        workflow = StateGraph(ChatState)
        
        # 节点 1: 分析用户意图
        async def analyze_intent(state: ChatState) -> ChatState:
            """分析用户意图"""
            try:
                logger.info(f"分析用户意图: {state['user_message'][:50]}...")
                
                # 创建专门用于意图识别的 LLM
                llm = llm_service.create_llm(
                    temperature=0.3,
                    max_tokens=100,
                    provider='ollama'
                )
                
                # 意图识别提示词
                intent_prompt = f"""请简短分析下面用户消息的意图，用一句话概括（不超过20字）。

用户消息：{state['user_message']}

意图分析："""
                 
                messages = [HumanMessage(content=intent_prompt)]
                response = await llm.ainvoke(messages)
                user_intent = response.content if hasattr(response, 'content') else str(response)
                
                # 清理意图文本
                if not isinstance(user_intent, str):
                    user_intent = str(user_intent)
                
                user_intent = user_intent.strip()
                if len(user_intent) > 50:
                    user_intent = user_intent[:50] + "..."
                
                state['user_intent'] = user_intent
                logger.info(f"意图识别完成: {user_intent}")
                return state
                
            except Exception as e:
                logger.error(f"意图识别失败: {str(e)}")
                state['user_intent'] = "未知意图"
                return state
        
        # 节点 2: 调用 LLM 生成回复（使用流式）
        async def call_llm(state: ChatState) -> ChatState:
            """调用 LLM 生成回复（流式，但在节点内累积完整响应）"""
            try:
                # 创建 LLM 实例
                llm = llm_service.create_llm(
                    temperature=0.7,
                    max_tokens=2000,
                    provider='ollama'
                )
                
                # 构建消息列表：系统提示词 + 历史消息 + 当前消息
                messages = []
                messages.append(SystemMessage(content=RIGHTS_PROTECTION_SYSTEM_PROMPT))
                
                # 加载历史消息
                session_data = state.get('session_data', {})
                user_id = session_data.get('user_id')
                if user_id:
                    try:
                        history = await redis_service.get_chat_history(user_id)
                        if history:
                            for msg in history:
                                role = msg.get('role')
                                content = msg.get('content', '')
                                if role == 'user':
                                    messages.append(HumanMessage(content=content))
                                elif role == 'assistant':
                                    messages.append(AIMessage(content=content))
                    except Exception as e:
                        logger.warning(f"加载历史消息失败: {str(e)}")
                
                # 添加当前用户消息
                messages.append(HumanMessage(content=state['user_message']))
                
                # 使用 astream 流式调用，LangGraph 会自动发送 on_chat_model_stream 事件
                # 同时在节点内累积完整响应用于保存到 Redis
                full_response = ""
                async for chunk in llm.astream(messages):
                    content = chunk.content if hasattr(chunk, 'content') else str(chunk)
                    if content and isinstance(content, str):
                        full_response += content
                
                # 更新状态
                state['ai_response'] = full_response
                state['messages'] = messages + [AIMessage(content=full_response)]
                
                logger.info(f"LLM 回复生成成功，长度: {len(full_response)}")
                return state
                
            except Exception as e:
                logger.error(f"LLM 调用失败: {str(e)}")
                state['error'] = f"LLM 调用失败: {str(e)}"
                state['ai_response'] = "抱歉，我遇到了一些问题。"
                return state
        
        # 节点 3: 保存到 Redis
        async def save_to_redis(state: ChatState) -> ChatState:
            """保存对话到 Redis"""
            try:
                session_data = state.get('session_data', {})
                user_id = session_data.get('user_id')
                
                if not user_id:
                    logger.warning("user_id 为空，跳过保存")
                    return state
                
                # 保存用户消息
                await redis_service.append_message(
                    user_id=user_id,
                    session_id="",
                    role="user",
                    content=state['user_message']
                )
                
                # 保存 AI 回复
                await redis_service.append_message(
                    user_id=user_id,
                    session_id="",
                    role="assistant",
                    content=state['ai_response']
                )
                
                logger.info(f"对话已保存到 Redis: user_id={user_id}")
                return state
                
            except Exception as e:
                logger.error(f"Redis 保存失败: {str(e)}", exc_info=True)
                state['error'] = f"Redis 保存失败: {str(e)}"
                return state
        
        # 添加节点
        workflow.add_node("analyze_intent", analyze_intent)
        workflow.add_node("call_llm", call_llm)
        workflow.add_node("save_to_redis", save_to_redis)
        
        # 设置流程：入口 -> 意图识别 -> LLM -> Redis -> 结束
        workflow.set_entry_point("analyze_intent")
        workflow.add_edge("analyze_intent", "call_llm")
        workflow.add_edge("call_llm", "save_to_redis")
        workflow.add_edge("save_to_redis", END)
        
        # 编译图
        app = workflow.compile()
        return app
    
    async def run_chat_workflow(self, session_data: Dict[str, Any], user_message: str) -> Dict[str, Any]:
        """运行对话工作流
        
        Args:
            session_data: 会话数据（包含 user_id, session_token, username 等）
            user_message: 用户消息
            
        Returns:
            工作流执行结果
        """
        try:
            # 创建工作流
            graph = self.create_chat_and_save_graph()
            
            # 初始状态
            initial_state = {
                "session_data": session_data,  # 传入完整的 session_data
                "user_message": user_message,
                "user_intent": "",  # 意图将由 analyze_intent 节点填充
                "ai_response": "",
                "messages": [],
                "error": None
            }
            
            # 执行工作流
            result = await graph.ainvoke(initial_state)
            return result
            
        except Exception as e:
            logger.error(f"工作流执行失败: {str(e)}")
            raise
    
    async def run_chat_workflow_stream(self, session_data: Dict[str, Any], user_message: str):
        """运行对话工作流（使用 LangGraph 原生流式输出）
        
        使用 astream_events (v2) 实现真正的流式输出：
        - 监听 on_chat_model_stream 事件获取 LLM token 流
        - 监听节点完成事件获取意图等信息
        - 完全在 LangGraph 上下文中，Laminar 自动追踪
        
        Args:
            session_data: 会话数据
            user_message: 用户消息
            
        Yields:
            - intent:<意图文本>
            - <LLM token 流>
        """
        try:
            # 创建工作流图
            graph = self.create_chat_and_save_graph()
            
            # 初始状态
            initial_state = {
                "session_data": session_data,
                "user_message": user_message,
                "user_intent": "",
                "ai_response": "",
                "messages": [],
                "error": None
            }
            
            user_intent_sent = False
            intent_node_completed = False
            
            # 使用 astream_events (v2) - LangGraph 原生流式 API
            async for event in graph.astream_events(initial_state, version="v2"):
                event_type = event.get("event")
                event_name = event.get("name", "")
                
                # 1. 监听意图识别节点完成
                if event_type == "on_chain_end" and event_name == "analyze_intent" and not user_intent_sent:
                    output = event.get("data", {}).get("output", {})
                    user_intent = output.get("user_intent", "未知意图")
                    yield f"intent:{user_intent}"
                    user_intent_sent = True
                    intent_node_completed = True
                
                # 2. 监听 LLM 流式输出 token（关键！）
                # on_chat_model_stream: LangChain ChatModel 的流式事件
                if event_type == "on_chat_model_stream":
                    # 只在意图识别完成后才开始发送 LLM token
                    if intent_node_completed:
                        chunk = event.get("data", {}).get("chunk", {})
                        # 提取 content
                        if hasattr(chunk, 'content'):
                            content = chunk.content
                        else:
                            content = chunk.get('content', '')
                        
                        if content:
                            yield content
            
        except Exception as e:
            logger.error(f"工作流流式执行失败: {str(e)}", exc_info=True)
            yield f"[ERROR] {str(e)}"

# 创建全局服务实例
langgraph_service = LangGraphService()
