# 对话工作流 - 使用 LangGraph 编排完整对话流程
from langgraph.graph import END  # type: ignore
from app.modules.workflow.core.graph import WorkflowGraphBuilder
from app.modules.workflow.core.state import WorkflowState
from app.modules.workflow.nodes.Intent_recognition import detect_intent
from app.modules.workflow.nodes.llm_answer import llm_answer_node
from app.modules.workflow.nodes.user_info import async_user_info_node  # 异步版本（支持 session 缓存）
from app.modules.workflow.nodes.chromadb_node import get_memory_node, save_memory_node  # ChromaDB 记忆节点
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# Laminar 可观测性追踪
try:
    from lmnr import observe, Laminar
    LAMINAR_AVAILABLE = True
except ImportError:
    LAMINAR_AVAILABLE = False
    # 定义空装饰器，避免报错
    def observe(**kwargs):
        def decorator(func):
            return func
        return decorator


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
    builder.add_node("user_info", async_user_info_node)           # 第1步：获取用户画像
    builder.add_node("intent_recognition", intent_recognition_node) # 第2步：意图识别
    builder.add_node("get_memory", get_memory_node)         # 第3步：获取历史记忆
    builder.add_node("llm_answer", llm_answer_node)                # 第4步：LLM回答
    builder.add_node("save_memory", save_memory_node)       # 第5步：保存记忆
    
    # 3. 设置入口节点
    builder.set_entry_point("user_info")  # 从用户信息获取开始
    
    # 4. 添加边（连接节点）
    builder.add_edge("user_info", "intent_recognition")      # 用户信息 → 意图识别
    builder.add_edge("intent_recognition", "get_memory")     # 意图识别 → 获取记忆
    builder.add_edge("get_memory", "llm_answer")             # 获取记忆 → LLM回答
    builder.add_edge("llm_answer", "save_memory")            # LLM回答 → 保存记忆
    builder.add_edge("save_memory", END)                     # 保存记忆 → 结束
    
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


@observe(name="run_chat_workflow", tags=["workflow", "chat", "langgraph"])
def run_chat_workflow(
    user_input: str,
    session_id: str,
    history_text: str = "",
    long_term_memory: str = "",
    user_id: Optional[str] = None,
    username: Optional[str] = None
) -> Dict[str, Any]:
    """运行对话工作流（使用 session_id 版本 + Laminar 追踪）
    
    Args:
        user_input: 用户输入
        session_id: 会话ID（会自动从 session 中获取用户信息）
        history_text: 对话历史
        long_term_memory: 长期记忆
        user_id: 用户ID（用于 Laminar 追踪）
        username: 用户名（用于 Laminar 追踪）
        
    Returns:
        包含 LLM 回答的结果字典
        
    Example:
        >>> # 首次请求：需要先通过 /api/agent/init 初始化会话
        >>> # 初始化时会使用 access_token 获取用户信息并缓存到 session
        >>> 
        >>> # 后续请求：直接使用 session_id
        >>> result = run_chat_workflow(
        ...     user_input="我今天被差评了",
        ...     session_id="sess_abc123...",
        ...     user_id="334",
        ...     username="张三"
        ... )
        >>> print(result["llm_response"])
        >>> print(f"用户公司: {result['company']}, 年龄: {result['age']}")
    """
    logger.info("========== 开始运行对话工作流 ==========")
    logger.info(f"会话ID: {session_id}")
    logger.info(f"用户输入: {user_input[:50]}...")
    
    # 设置 Laminar 追踪信息
    if LAMINAR_AVAILABLE:
        if user_id:
            Laminar.set_trace_user_id(str(user_id))
        if session_id:
            Laminar.set_trace_session_id(session_id)
        
        # 设置元数据
        Laminar.set_trace_metadata({
            "username": username or "Unknown",
            "user_id": str(user_id) if user_id else None,
            "session_id": session_id[:20] + "..." if session_id else None,
            "message_preview": user_input[:50] + "..." if len(user_input) > 50 else user_input,
            "workflow_type": "langgraph_chat"
        })
    
    # 1. 准备初始状态（只需 session_id，用户信息会自动从 session 中获取）
    initial_state: WorkflowState = {
        "user_input": user_input,
        "session_id": session_id,
        "history_text": history_text,
        "long_term_memory": long_term_memory,
        "is_streaming": False
    }
    
    # 2. 获取工作流
    workflow = get_chat_workflow()
    
    # 3. 执行工作流
    result = workflow.invoke(initial_state)
    
    logger.info("========== 对话工作流执行完成 ==========")
    logger.info(f"用户ID: {result.get('user_id', 'N/A')}")
    logger.info(f"用户画像: 公司={result.get('company')}, 年龄={result.get('age')}, 性别={result.get('gender')}")
    logger.info(f"识别意图: {result.get('intent', 'N/A')} (置信度: {result.get('intent_confidence', 0):.2f})")
    logger.info(f"回答长度: {len(result.get('llm_response', ''))} 字符")
    
    return result
