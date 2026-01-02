# LangGraph 工作流状态定义
from typing import TypedDict, Optional, List, Dict, Any


class WorkflowState(TypedDict, total=False):
    """工作流状态定义
    
    LangGraph 会在各个节点之间传递这个状态对象
    每个节点可以读取和更新状态中的字段
    """
    
    # 用户输入
    user_input: str  # 用户的原始输入
    user_id: str  # 用户ID
    session_id: str  # 会话ID
    access_token: str  # 用户的 access_token（用于获取用户画像）
    
    # 用户画像信息
    company: str  # 用户公司
    age: str  # 用户年龄
    gender: str  # 用户性别
    
    # 意图识别结果
    intent: str  # 主意图（置信度最高的）
    intent_confidence: float  # 主意图的置信度
    intent_scores: Dict[str, float]  # 所有意图的得分
    intents: List[Dict[str, Any]]  # 所有检测到的意图列表（包括混合意图）
    
    # 安全检测结果
    is_safe: bool  # 输入是否安全
    safety_response: Optional[str]  # 如果不安全，这里是预设的回应
    
    # 对话历史
    history_text: str  # 最近5条对话历史文本
    history_messages: List[Dict[str, str]]  # 原始消息列表
    similar_messages: str  # 相似度较高的消息文本
    recent_message_count: int  # 最近消息数量
    similar_message_count: int  # 相似消息数量
    
    # 记忆检索
    long_term_memory: str  # 从向量数据库检索的长期记忆
    
    # Prompt 构建
    full_prompt: str  # 构建完成的完整 Prompt
    
    # LLM 调用
    llm_response: str  # LLM 生成的回答
    
    # 工单管理
    need_create_ticket: bool  # 是否需要创建工单
    ticket_reason: str  # 工单判断理由
    user_confirmed_ticket: bool  # 用户是否确认创建工单（用户点击确认后设为 True）
    ticket_created: bool  # 工单是否已创建
    
    # 流式输出控制
    is_streaming: bool  # 是否使用流式输出
    
    # 错误处理
    error: Optional[str]  # 错误信息（如果有）
