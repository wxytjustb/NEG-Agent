from langgraph.graph import END  # type: ignore
from app.modules.workflow.core.graph import WorkflowGraphBuilder
from app.modules.workflow.core.state import WorkflowState
from app.modules.workflow.nodes.Intent_recognition import detect_intent
from app.modules.workflow.nodes.llm_answer import async_llm_stream_answer_node
from app.modules.workflow.nodes.user_info import async_user_info_node  # 异步版本（支持 session 缓存）
from app.modules.workflow.nodes.chromadb_node import get_memory_node, save_memory_node  # ChromaDB 记忆节点
from typing import Dict, Any, Optional
from lmnr import observe, Laminar
import logging

logger = logging.getLogger(__name__)


@observe(name="intent_recognition_node", tags=["node", "intent"])
def intent_recognition_node(state: WorkflowState) -> Dict[str, Any]:
    """意图识别节点 - LangGraph 节点包装器"""
    logger.info("========== 意图识别节点开始 ===========")

    try:
        user_input = state.get("user_input", "")
        logger.info(f"用户输入: {user_input[:50]}...")

        # 调用意图识别
        intent, confidence, all_scores = detect_intent(user_input)

        logger.info(f"✅ 意图识别完成: {intent} (置信度: {confidence:.2f})")

        # 返回更新的状态
        return {
            "intent": intent,
            "intent_confidence": confidence,
            "intent_scores": all_scores
        }

    except Exception as e:
        error_msg = f"意图识别节点执行失败: {str(e)}"
        logger.error(error_msg)
        return {
            "intent": "日常对话",
            "intent_confidence": 0.0,
            "intent_scores": {},
            "error": error_msg
        }


def create_chat_workflow():
    """创建对话工作流"""
    logger.info("正在创建对话工作流...")

    # 1. 创建图构建器
    builder = WorkflowGraphBuilder(state_schema=WorkflowState)

    # 2. 添加节点（按执行顺序）
    builder.add_node("user_info", async_user_info_node)  # 第1步：获取用户画像
    builder.add_node("intent_recognition", intent_recognition_node)  # 第2步：意图识别
    builder.add_node("get_memory", get_memory_node)  # 第3步：获取历史记忆
    builder.add_node("llm_answer", async_llm_stream_answer_node)  # 第4步：LLM回答（异步流式）
    builder.add_node("save_memory", save_memory_node)  # 第5步：保存记忆

    # 3. 设置入口节点
    builder.set_entry_point("user_info")  # 从用户信息获取开始

    # 4. 添加边（连接节点）
    builder.add_edge("user_info", "intent_recognition")  # 用户信息 → 意图识别
    builder.add_edge("intent_recognition", "get_memory")  # 意图识别 → 获取记忆
    builder.add_edge("get_memory", "llm_answer")  # 获取记忆 → LLM回答
    builder.add_edge("llm_answer", "save_memory")  # LLM回答 → 保存记忆
    builder.add_edge("save_memory", END)  # 保存记忆 → 结束

    # 5. 验证图结构
    builder.validate()

    # 6. 编译图
    workflow = builder.compile()

    logger.info("✅ 对话工作流创建完成")
    logger.info("工作流结构: 用户信息 → 意图识别 → 获取记忆 → LLM回答 → 保存记忆 → 结束")

    return workflow


# 全局工作流实例（懒加载）
_chat_workflow = None


def get_chat_workflow():
    """获取对话工作流实例（单例模式）

    Returns:
        编译后的对话工作流
    """
    global _chat_workflow

    if _chat_workflow is None:
        logger.info("首次调用，创建工作流实例...")
        _chat_workflow = create_chat_workflow()

    return _chat_workflow


@observe(name="chat_workflow_stream", tags=["workflow", "chat", "streaming"])
async def run_chat_workflow_streaming(
        user_input: str,
        session_id: str,
        user_id: Optional[str] = None,
        username: Optional[str] = None
):
    """运行对话工作流（流式版本）"""
    initial_state: WorkflowState = {
        "user_input": user_input,
        "session_id": session_id,
        "is_streaming": True
    }

    if user_id:
        initial_state["user_id"] = user_id

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
                chunk = event.get("data", {}).get("chunk")
                if chunk and hasattr(chunk, "content"):
                    content = chunk.content
                    if content:
                        has_output = True
                        logger.debug(f"捕获到流式chunk ({event_type}): {content[:50]}...")
                        yield content

        logger.info(f"✅ 工作流完成: 事件数={event_count}, 流式输出={has_output}")

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