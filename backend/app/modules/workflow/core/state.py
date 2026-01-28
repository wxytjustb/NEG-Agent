# LangGraph 工作流状态定义
from typing import TypedDict, Optional, List, Dict, Any


class WorkflowState(TypedDict, total=False):
    """工作流状态定义
    
    LangGraph 会在各个节点之间传递这个状态对象
    每个节点可以读取和更新状态中的字段
    """
    
    # ========== 核心标识 ==========
    user_input: str  # 用户的原始输入
    user_id: str  # 用户ID
    session_id: str  # 会话ID（单次对话）
    conversation_id: str  # 对话ID（跨多轮对话保持一致）
    access_token: str  # 用户认证Token（用于调用 Golang API）
    
    # ========== 用户画像 ==========
    company: str  # 用户公司
    age: str  # 用户年龄
    gender: str  # 用户性别
    
    # ========== 意图识别 ==========
    intent: str  # 主意图（置信度最高的）
    intent_confidence: float  # 主意图的置信度
    intents: List[Dict[str, Any]]  # 所有检测到的意图列表（包括混合意图）
    
    # ========== 记忆上下文 ==========
    working_memory_text: str  # Working Memory 文本（Redis 中最近10轮对话）
    working_memory_count: int  # Working Memory 消息数量
    similar_messages: str  # 相似度较高的消息文本（ChromaDB 语义检索）
    similar_message_count: int  # 相似消息数量
    feedback_summary: str  # 用户反馈趋势摘要（近七天）
    feedback_data: Dict[str, Any]  # 用户反馈原始数据
    
    # ========== LLM 输出 ==========
    llm_response: str  # LLM 生成的回答
    
    # ========== 工单相关 ==========
    need_create_ticket: bool  # 是否需要创建工单
    ticket_reason: str  # 工单判断理由
    confirmation_message: str  # 工单确认消息
    user_confirmed_ticket: bool  # 用户是否确认创建工单
    
    # ========== 记忆保存状态 ==========
    memory_saved: bool  # ChromaDB 记忆是否保存成功
    working_memory_saved: bool  # Working Memory 是否保存成功
    
    # ========== 流式输出控制 ==========
    is_streaming: bool  # 是否使用流式输出
    
    # ========== 错误处理 ==========
    error: Optional[str]  # 错误信息（如果有）
