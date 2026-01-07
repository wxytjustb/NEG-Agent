from langgraph.graph import END  # type: ignore
from app.modules.workflow.core.graph import WorkflowGraphBuilder
from app.modules.workflow.core.state import WorkflowState
from app.modules.workflow.nodes.Intent_recognition import detect_intent
from app.modules.workflow.nodes.llm_answer import async_llm_stream_answer_node
# 工单功能已移除，代码保留但不在工作流中使用
# from app.modules.workflow.nodes.ticket_analysis import async_ticket_analysis_node, async_ask_user_confirmation_node
from app.modules.workflow.nodes.user_info import async_user_info_node  # 异步版本（支持 session 缓存）
from app.modules.workflow.nodes.chromadb_node import get_memory_node, save_memory_node  # ChromaDB 记忆节点
from app.modules.workflow.nodes.database_node import save_database_node  # MySQL 数据库节点
from app.modules.workflow.nodes.working_memory import working_memory  # Working Memory 短期记忆节点
# from app.utils.greeting import check_and_respond_greeting, stream_greeting_response  # 问候语检测和回复（暂时禁用）
# 删除：不再需要创建工单节点，前端直接调用 Golang 接口
from typing import Dict, Any, Optional
from lmnr import observe, Laminar
import logging

logger = logging.getLogger(__name__)


@observe(name="intent_recognition_node", tags=["node", "intent"])
def intent_recognition_node(state: WorkflowState) -> Dict[str, Any]:
    """意图识别节点 - 基于用户输入分析意图"""
    logger.info("========== 意图识别节点开始 ===========")
    
    try:
        user_input = state.get("user_input", "")
        history_text = state.get("history_text", "")
        
        logger.info(f"用户输入: {user_input[:50]}...")
        logger.info(f"历史上下文: {len(history_text)} 字符")
        
        # 调用意图识别（只使用 user_input 和 history_text）
        intent, confidence, all_scores, intents = detect_intent(
            user_input=user_input,
            history_text=history_text
        )
        
        logger.info(f"✅ 意图识别完成: {intent} (置信度: {confidence:.2f})")
        if len(intents) > 1:
            logger.info(f"🔀 检测到混合意图: {intents}")
        
        # 返回更新的状态
        return {
            "intent": intent,
            "intent_confidence": confidence,
            "intent_scores": all_scores,
            "intents": intents
        }
        
    except Exception as e:
        error_msg = f"意图识别节点执行失败: {str(e)}"
        logger.error(error_msg)
        return {
            "intent": "日常对话",
            "intent_confidence": 0.0,
            "intent_scores": {},
            "intents": [],
            "error": error_msg
        }


@observe(name="get_working_memory_node", tags=["node", "memory", "redis"])
async def get_working_memory_node(state: WorkflowState) -> Dict[str, Any]:
    """获取 Working Memory 节点 - 从 Redis 获取最近10轮对话"""
    try:
        conversation_id = state.get("conversation_id")  # 改为使用 conversation_id
        if not conversation_id:
            return {"working_memory_text": "", "working_memory_count": 0}
        
        # 获取最近10轮对话（20条消息）
        messages = await working_memory.get_messages(conversation_id)  # 使用 conversation_id
        
        if not messages:
            return {"working_memory_text": "", "working_memory_count": 0}
        
        # 格式化为文本
        memory_lines = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            role_name = "用户" if role == "user" else "安然" if role == "assistant" else role
            memory_lines.append(f"{role_name}：{content}")
        
        memory_text = "\n".join(memory_lines)
        logger.info(f"✅ Working Memory 获取完成，共 {len(messages)} 条消息（conversation_id={conversation_id[:20]}...）")
        
        return {
            "working_memory_text": memory_text,
            "working_memory_count": len(messages)
        }
    except Exception as e:
        logger.error(f"获取 Working Memory 失败: {e}", exc_info=True)
        return {"working_memory_text": "", "working_memory_count": 0}


@observe(name="save_working_memory_node", tags=["node", "memory", "redis", "storage"])
async def save_to_working_memory_node(state: WorkflowState) -> Dict[str, Any]:
    """保存到 Working Memory 节点 - 将对话保存到 Redis"""
    try:
        conversation_id = state.get("conversation_id")  # 改为使用 conversation_id
        user_input = state.get("user_input", "")
        llm_response = state.get("llm_response", "")
        
        if not conversation_id:
            return {"working_memory_saved": False}
        
        # 保存用户消息
        if user_input:
            await working_memory.save_message(
                session_token=conversation_id,  # 使用 conversation_id
                role="user",
                content=user_input
            )
        
        # 保存助手消息
        if llm_response:
            await working_memory.save_message(
                session_token=conversation_id,  # 使用 conversation_id
                role="assistant",
                content=llm_response
            )
        
        logger.info(f"✅ Working Memory 保存完成（conversation_id={conversation_id[:20]}...）")
        return {"working_memory_saved": True}
    except Exception as e:
        logger.error(f"保存到 Working Memory 失败: {e}", exc_info=True)
        return {"working_memory_saved": False}


def create_chat_workflow():
    """创建对话工作流"""
    logger.info("正在创建对话工作流...")
    
    # 1. 创建图构建器
    builder = WorkflowGraphBuilder(state_schema=WorkflowState)
    
    # 2. 添加节点（按执行顺序）
    builder.add_node("user_info", async_user_info_node)                    # 第1步：获取用户画像
    builder.add_node("get_working_memory", get_working_memory_node)        # 第2步：获取 Working Memory（Redis 10轮对话）
    builder.add_node("get_memory", get_memory_node)                        # 第3步：获取 ChromaDB 历史记忆（相似度检索）
    builder.add_node("intent_recognition", intent_recognition_node)        # 第4步：意图识别
    builder.add_node("llm_answer", async_llm_stream_answer_node)          # 第5步：LLM回答（异步流式）
    builder.add_node("save_working_memory", save_to_working_memory_node)  # 第6步：保存到 Working Memory
    builder.add_node("save_memory", save_memory_node)                     # 第7步：保存到 ChromaDB
    builder.add_node("save_database", save_database_node)                 # 第8步：保存到 MySQL
    
    # 工单节点已移除（前端直接调用 Golang 接口）
    # builder.add_node("ticket_analysis", async_ticket_analysis_node)
    # builder.add_node("ask_user_confirmation", async_ask_user_confirmation_node)
    
    # 3. 设置入口节点
    builder.set_entry_point("user_info")  # 从用户信息获取开始
    
    # 4. 添加边（连接节点）
    # 并行流程：用户信息 → (Working Memory + ChromaDB记忆 并行) → 意图识别 → LLM对话 → 保存Working Memory → (ChromaDB + MySQL 并行保存) → 结束
    builder.add_edge("user_info", "get_working_memory")           # 用户信息 → Working Memory
    builder.add_edge("user_info", "get_memory")                   # 用户信息 → ChromaDB（并行）
    builder.add_edge("get_working_memory", "intent_recognition")  # Working Memory → 意图识别
    builder.add_edge("get_memory", "intent_recognition")          # ChromaDB → 意图识别（两路汇聚）
    builder.add_edge("intent_recognition", "llm_answer")          # 意图识别 → LLM对话
    builder.add_edge("llm_answer", "save_working_memory")         # LLM对话 → 保存到 Working Memory
    builder.add_edge("save_working_memory", "save_memory")        # Working Memory → 保存到 ChromaDB
    builder.add_edge("save_working_memory", "save_database")      # Working Memory → 保存到 MySQL（并行）
    builder.add_edge("save_memory", END)                           # ChromaDB保存 → 结束
    builder.add_edge("save_database", END)                         # MySQL保存 → 结束
    
    # 5. 验证图结构
    builder.validate()
    
    # 6. 编译图
    workflow = builder.compile()
    
    logger.info("✅ 对话工作流创建完成")
    logger.info("工作流结构：用户信息 → [Working Memory + ChromaDB 并行] → 意图识别 → LLM对话 → 保存Working Memory → [ChromaDB + MySQL 并行保存] → 结束")
    
    return workflow


# 全局工作流实例（懒加载）
_chat_workflow = None


def get_chat_workflow():
    """获取对话工作流实例（单例模式）
    
    Returns:
        编译后的对话工作流
    """
    global _chat_workflow
    
    # 临时强制重新创建（调试用）
    logger.info("🔄 [调试] 强制重新创建 Workflow...")
    _chat_workflow = create_chat_workflow()
    
    return _chat_workflow


@observe(name="chat_workflow_stream", tags=["workflow", "chat", "streaming"])
async def run_chat_workflow_streaming(
    user_input: str,
    conversation_id: str,  # 新增：对话ID
    session_id: str,
    user_id: Optional[str] = None,
    username: Optional[str] = None,
    access_token: Optional[str] = None,  # 新增：Access Token
    user_confirmed_ticket: Optional[bool] = None  # 用户确认创建工单
):
    """运行对话工作流（流式版本）
    
    Returns:
        生成器，yield 流式内容和最终的 trace_id
    """
    # ✅ 问候语检测逻辑已暂时禁用，后续再添加
    # is_greeting, greeting_response = check_and_respond_greeting(user_input)
    # if is_greeting:
    #     logger.info(f"👋 检测到纯问候语，直接返回预设回复: {greeting_response}")
    #     async for char in stream_greeting_response(greeting_response):
    #         yield char
    #     await working_memory.save_message(session_token=session_id, role="user", content=user_input)
    #     await working_memory.save_message(session_token=session_id, role="assistant", content=greeting_response)
    #     return
    
    initial_state: WorkflowState = {
        "user_input": user_input,
        "conversation_id": conversation_id,  # 新增：传入 conversation_id
        "session_id": session_id,
        "is_streaming": True,
        # 意图识别初始为空（对话后才进行意图分析）
        "intent": "",
        "intent_confidence": 0.0,
        "intent_scores": {},
        "intents": []
    }
    
    if user_id:
        initial_state["user_id"] = user_id
    
    if access_token:
        initial_state["access_token"] = access_token  # 新增：传入 access_token

    # 如果用户确认了工单，设置 state
    if user_confirmed_ticket is not None:
        initial_state["user_confirmed_ticket"] = user_confirmed_ticket
        logger.info(f"📩 收到用户确认: user_confirmed_ticket={user_confirmed_ticket}")

    # 设置 Laminar 追踪元数据
    if user_id:
        Laminar.set_trace_user_id(str(user_id))
    if session_id:
        Laminar.set_trace_session_id(session_id)
    
    Laminar.set_trace_metadata({
        "username": username or "Unknown",
        "user_id": str(user_id) if user_id else None,
        "session_id": session_id[:20] + "..." if len(session_id) > 20 else session_id,
        "message_preview": user_input[:50] + "..." if len(user_input) > 50 else user_input
    })
    
    config = {
        "metadata": {
            "workflow": "chat_workflow",
            "message": user_input[:50] + "..." if len(user_input) > 50 else user_input,
            "session_id": session_id,
            "user_id": str(user_id) if user_id else None,
            "username": username or "Unknown"
        }
    }
    
    has_output = False
    total_input_tokens = 0
    total_output_tokens = 0
    event_count = 0  # 调试：统计事件数量
    final_state = None  # 存储最终状态

    try:
        async for event in get_chat_workflow().astream_events(initial_state, config=config, version="v2"):
            event_type = event.get("event")
            event_count += 1
            
            # 每10个事件记录一次（避免日志过多）
            if event_count % 10 == 0:
                logger.debug(f"已处理 {event_count} 个事件，当前类型: {event_type}")
            
            # 监听 LLM Token 使用情况
            if event_type == "on_chat_model_end":
                output = event.get("data", {}).get("output")
                if output and hasattr(output, 'usage_metadata') and output.usage_metadata:
                    usage = output.usage_metadata
                    total_input_tokens += usage.get('input_tokens', 0)
                    total_output_tokens += usage.get('output_tokens', 0)
                    
                    # 更新 Laminar Span 的 Token 统计
                    Laminar.set_span_attributes({
                        "llm.usage.input_tokens": total_input_tokens,
                        "llm.usage.output_tokens": total_output_tokens,
                        "llm.usage.total_tokens": total_input_tokens + total_output_tokens
                    })
            
            # 尝试监听多种流式事件类型
            if event_type in ["on_chat_model_stream", "on_llm_stream", "on_chain_stream"]:
                # 检查事件信息
                event_name = event.get("name", "")
                event_tags = event.get("tags", [])

                # 调试：打印事件信息
                # logger.info(f"🔍 流式事件: name={event_name}, tags={event_tags}")

                # 直接输出所有流式事件（因为 ticket_analysis 使用同步调用，不会产生流式事件）
                chunk = event.get("data", {}).get("chunk")
                if chunk and hasattr(chunk, "content"):
                    content = chunk.content
                    if content:
                        has_output = True
                        yield content

            # 监听工作流结束事件，获取最终状态
            if event_type == "on_chain_end" and event.get("name") == "LangGraph":
                final_state = event.get("data", {}).get("output")
                logger.info("✅ 捕获到工作流最终状态")

        logger.info(f"✅ 工作流完成: 事件数={event_count}, 流式输出={has_output}")

        # 工单功能已移除，不再返回工单相关 state
        # 前端直接调用 Golang 接口创建工单

        # 兜底逻辑：仅在完全没有输出时触发
        if not has_output:
            logger.warning("⚠️ 未捕获到流式输出，使用兜底逻辑（不会重新执行工作流）")

        # ❌ 不要重新执行工作流！只从已完成的状态中获取结果
        # 这里的问题是：astream_events 已经执行完了工作流，只是没有 yield 出来
        # 我们应该从最终状态获取结果，而不是再次 invoke

        # 由于 astream_events 不返回最终状态，我们只能提示错误
            yield "[提示] 流式输出异常，请重试"

    except Exception as e:
        logger.error(f"流式工作流执行失败: {str(e)}", exc_info=True)
        yield f"[错误] {str(e)}"