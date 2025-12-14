from typing import List, Dict, Any, Optional, TypedDict
from lmnr import observe, Laminar
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage, SystemMessage
from app.core.config import settings
from app.services.llm_service import llm_service
from app.services.redis_service import redis_service
from app.prompts.prompts import RIGHTS_PROTECTION_SYSTEM_PROMPT
import logging

logger = logging.getLogger(__name__)

class LangGraphService:
    """LangGraph 服务类 - 负责工作流编排 (Laminar 集成增强版)"""
    
    def __init__(self):
        self.settings = settings
        logger.info("LangGraph 服务已初始化")
        # 建议：确保环境变量 LAMINAR_API_KEY 已设置

    def create_chat_and_save_graph(self):
        """创建 LLM 对话并存储到 Redis 的工作流"""
        
        # --- 1. 定义状态 ---
        class ChatState(TypedDict):
            session_data: Dict[str, Any]
            user_message: str
            user_intent: str
            ai_response: str
            messages: List[BaseMessage]
            error: Optional[str]
        
        workflow = StateGraph(ChatState)
        
        # --- 2. 节点定义 ---
        
        # [节点 1] 意图识别
        @observe(name="analyze_intent_node", tags=["node", "intent"])
        async def analyze_intent(state: ChatState) -> ChatState:
            try:
                # 使用手动 Span 包装 LLM 调用，确保 Input/Output 干净清晰
                with Laminar.start_as_current_span(
                    name="intent_llm_call",
                    input={"user_message": state['user_message']}, # 只记录关键输入
                    span_type="LLM" # 强制标记为 LLM 类型以获得 Token 统计界面
                ) as span:
                    
                    llm = llm_service.create_llm(temperature=0.3, max_tokens=100, provider='ollama')
                    intent_prompt = f"请简短分析下面用户消息的意图，用一句话概括（不超过20字）。\n\n用户消息：{state['user_message']}\n\n意图分析："
                    
                    # 调用 LLM
                    response = await llm.ainvoke([HumanMessage(content=intent_prompt)])
                    user_intent = response.content.strip() if hasattr(response, 'content') else str(response)
                    
                    # 记录输出和 Token
                    Laminar.set_span_output(user_intent)
                    if hasattr(response, 'usage_metadata') and response.usage_metadata:
                         Laminar.set_span_attributes({
                             "llm.usage.input_tokens": response.usage_metadata.get('input_tokens', 0),
                             "llm.usage.output_tokens": response.usage_metadata.get('output_tokens', 0)
                         })
                
                state['user_intent'] = user_intent
                return state
            except Exception as e:
                logger.error(f"意图识别失败: {e}")
                state['user_intent'] = "常规对话"
                return state

        # [节点 2] 核心回复生成
        @observe(name="call_llm_node", tags=["node", "generation"])
        async def call_llm(state: ChatState) -> ChatState:
            """调用 LLM 生成回复（流式，但在节点内累积完整响应）"""
            try:
                # 准备上下文消息
                messages = [SystemMessage(content=RIGHTS_PROTECTION_SYSTEM_PROMPT)]
                
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
                
                llm = llm_service.create_llm(temperature=0.7, max_tokens=2000, provider='ollama')
                
                full_response = ""
                
                # 手动 Span：为了在 Trace 中看到漂亮的 Prompt 和 Response，而不是 State 字典
                with Laminar.start_as_current_span(
                    name="chat_generation_llm",
                    input=[{"role": m.type, "content": m.content} for m in messages], # 格式化消息列表
                    span_type="LLM"
                ) as span:
                    # 注意：在节点内部我们聚合流式结果，以便存入 State
                    # 真正的流式推送给前端是在 run_chat_workflow_stream 中处理的
                    async for chunk in llm.astream(messages):
                        content = chunk.content
                        if content:
                            full_response += content
                    
                    Laminar.set_span_output(full_response)
                    # 注意：这里可能拿不到 usage，因为是简单的 astream
                    # Usage 的精确统计将在最外层的 run_chat_workflow_stream 处理
                
                state['ai_response'] = full_response
                state['messages'] = messages + [AIMessage(content=full_response)]
                return state
                
            except Exception as e:
                logger.error(f"LLM 生成失败: {e}")
                state['error'] = str(e)
                state['ai_response'] = "抱歉，我遇到了一些问题。"
                return state

        # [节点 3] 保存到 Redis
        @observe(name="save_redis_node", tags=["node", "storage"])
        async def save_to_redis(state: ChatState) -> ChatState:
            """保存对话到 Redis"""
            try:
                session_data = state.get('session_data', {})
                user_id = session_data.get('user_id')
                session_token = session_data.get('session_token')  # 提取真实的 session_token
                
                if not user_id:
                    logger.warning("user_id 为空，跳过保存")
                    return state
                
                # 保存用户消息，传入真实的 session_token
                await redis_service.append_message(
                    user_id=user_id,
                    session_id=session_token or "",  # 使用真实的 session_token
                    role="user",
                    content=state['user_message']
                )
                
                # 保存 AI 回复，传入真实的 session_token
                await redis_service.append_message(
                    user_id=user_id,
                    session_id=session_token or "",  # 使用真实的 session_token
                    role="assistant",
                    content=state['ai_response']
                )
                
                logger.info(f"对话已保存到 Redis: user_id={user_id}, session_token={session_token}")
                return state
                
            except Exception as e:
                logger.error(f"Redis 保存失败: {str(e)}", exc_info=True)
                state['error'] = f"Redis 保存失败: {str(e)}"
                return state

        # --- 3. 构建图 ---
        workflow.add_node("analyze_intent", analyze_intent)
        workflow.add_node("call_llm", call_llm)
        workflow.add_node("save_to_redis", save_to_redis)

        workflow.set_entry_point("analyze_intent")
        workflow.add_edge("analyze_intent", "call_llm")
        workflow.add_edge("call_llm", "save_to_redis")
        workflow.add_edge("save_to_redis", END)
        
        return workflow.compile()

    @observe(name="workflow_stream", tags=["workflow", "chat"]) 
    async def run_chat_workflow_stream(self, session_data: Dict[str, Any], user_message: str):
        """
        运行流式工作流
        修复点：监听 'on_chat_model_end' 事件以捕获 Token Usage 并上报给 Laminar
        """
        # 提取用户信息
        user_id = session_data.get("user_id")
        session_token = session_data.get("session_token")
        username = session_data.get("username", "Unknown")
        
        # 设置 Laminar 追踪的用户ID和会话ID
        if user_id:
            Laminar.set_trace_user_id(str(user_id))
        if session_token:
            Laminar.set_trace_session_id(session_token)
        
        # 设置元数据
        Laminar.set_trace_metadata({
            "username": username,
            "user_id": str(user_id) if user_id else None,
            "session_token": session_token[:20] + "..." if session_token else None,
            "message_preview": user_message[:50] + "..." if len(user_message) > 50 else user_message
        })

        graph = self.create_chat_and_save_graph()
        initial_state = {
            "session_data": session_data,
            "user_message": user_message,
            "user_intent": "", "ai_response": "", "messages": [], "error": None
        }

        # 用于累加整个工作流的 Token 消耗
        total_input_tokens = 0
        total_output_tokens = 0

        try:
            # 使用 v2 版本事件流
            async for event in graph.astream_events(initial_state, version="v2"):
                event_type = event.get("event")
                event_name = event.get("name", "")

                # --- 1. 意图发送逻辑 ---
                if event_type == "on_chain_end" and event_name == "analyze_intent":
                    data = event.get("data", {}).get("output", {})
                    if data:
                        intent = data.get("user_intent", "")
                        yield f"intent:{intent}"

                # --- 2. 关键修复：Token 统计逻辑 ---
                # 当任何 LLM 模型完成调用时（包括意图识别和正文生成）
                if event_type == "on_chat_model_end":
                    output = event.get("data", {}).get("output")
                    if output and hasattr(output, 'usage_metadata') and output.usage_metadata:
                        usage = output.usage_metadata
                        # 累加 Token
                        total_input_tokens += usage.get('input_tokens', 0)
                        total_output_tokens += usage.get('output_tokens', 0)
                        
                        # 【重要】实时更新当前 Span (workflow_stream) 的统计信息
                        # 使用 set_span_attributes 记录 token 消耗
                        Laminar.set_span_attributes({
                            "llm.usage.input_tokens": total_input_tokens,
                            "llm.usage.output_tokens": total_output_tokens,
                            "llm.usage.total_tokens": total_input_tokens + total_output_tokens
                        })

                # --- 3. 流式内容推送逻辑 ---
                if event_type == "on_chat_model_stream":
                    # 过滤掉意图识别节点的流（如果意图识别也用了流式），只保留主回复的流
                    # 这里可以通过 event_name 或者 metadata 判断，或者简单地全部透传
                    chunk = event.get("data", {}).get("chunk")
                    if hasattr(chunk, 'content'):
                        content = chunk.content
                        if content:
                            yield content

        except Exception as e:
            logger.error(f"工作流异常: {e}", exc_info=True)
            yield f"[ERROR] {str(e)}"
            # 记录错误到元数据
            Laminar.set_span_attributes({
                "error.type": type(e).__name__,
                "error.message": str(e)
            })

# 初始化
langgraph_service = LangGraphService()