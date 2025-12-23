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
    intent: str  # 识别出的意图（法律咨询/情感倾诉/日常对话）
    intent_confidence: float  # 意图识别的置信度
    intent_scores: Dict[str, float]  # 所有意图的得分
    
    # 安全检测结果
    is_safe: bool  # 输入是否安全
    safety_response: Optional[str]  # 如果不安全，这里是预设的回应
    
    # 对话历史
    history_text: str  # 格式化的对话历史文本
    history_messages: List[Dict[str, str]]  # 原始消息列表
    
    # 记忆检索
    long_term_memory: str  # 从向量数据库检索的长期记忆
    
    # Prompt 构建
    full_prompt: str  # 构建完成的完整 Prompt
    
    # LLM 调用
    llm_response: str  # LLM 生成的回答
    
    # 流式输出控制
    is_streaming: bool  # 是否使用流式输出
    
    # 错误处理
    error: Optional[str]  # 错误信息（如果有）
