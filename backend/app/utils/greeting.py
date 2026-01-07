"""
问候语自动回复工具
检测用户是否只是打招呼，并返回预设的友好回复
"""
import re
import random
from typing import Optional, Tuple


# 问候语关键词列表（严格匹配）
GREETING_PATTERNS = [
    # 基础问候
    "你好", "您好", "你好啊", "您好啊",
    "hi", "hello", "hey",
    "嗨", "哈喽", "哎",
    
    # 时间问候
    "早", "早上好", "上午好", "中午好", "下午好", "晚上好", "晚安",
    "早安", "午安",
    
    # 在线询问
    "在吗", "在不在", "在么", "在嘛",
    "有人吗", "有人在吗",
    "在线吗", "在不",
    
    # 自我介绍询问
    "你是谁", "你是", "你叫什么", "你叫啥",
    "介绍一下", "介绍下自己",
    
    # 称呼
    "安然",
]

# 预设的问候回复语句库（随机选择）
GREETING_RESPONSES = [
    "你好呀，我是安然，很高兴见到你。有什么想聊的吗？",
    "嗨，我在呢。今天过得怎么样？",
    "你好，我一直都在。有什么想说的就跟我讲吧。",
    "在的在的，有什么我能帮你的吗？",
    "你好，我是安然。累了的话可以随时跟我聊聊天。",
    "嗨，看到你真好。最近还好吗？",
    "你好呀，想聊点什么都可以跟我说。",
    "在的，随时可以找我聊天。今天还顺利吗？"
]


def is_pure_greeting(user_input: str) -> bool:
    """
    判断用户输入是否为纯问候语（严格模式）
    
    规则：
    1. 去除空格、标点后的文本必须完全匹配问候语模式
    2. 不允许有任何额外内容
    
    Args:
        user_input: 用户输入文本
        
    Returns:
        bool: True 表示是纯问候语
    """
    if not user_input or len(user_input.strip()) == 0:
        return False
    
    # 清理文本：去除空格、标点符号
    import string
    text = user_input.strip().lower()
    # 移除标点和空格
    punctuation = string.punctuation + ' 　！？。，、；："\'（）【】《》'
    text_cleaned = text.translate(str.maketrans('', '', punctuation)).strip()
    
    # 严格匹配：清理后的文本必须完全等于某个问候语模式
    for pattern in GREETING_PATTERNS:
        pattern_cleaned = pattern.lower().replace(' ', '')
        if text_cleaned == pattern_cleaned:
            return True
    
    return False


def get_greeting_response() -> str:
    """
    随机获取一条问候回复语句
    
    Returns:
        str: 随机选择的问候回复
    """
    return random.choice(GREETING_RESPONSES)


def check_and_respond_greeting(user_input: str) -> Tuple[bool, Optional[str]]:
    """
    检查是否为问候语，并返回对应回复
    
    Args:
        user_input: 用户输入文本
        
    Returns:
        Tuple[bool, Optional[str]]: 
            - bool: 是否为纯问候语
            - str: 如果是问候语，返回随机回复；否则返回 None
    """
    if is_pure_greeting(user_input):
        return True, get_greeting_response()
    return False, None


async def stream_greeting_response(response: str):
    """
    将问候回复以流式方式输出（逐字输出）
    
    Args:
        response: 要输出的问候回复文本
        
    Yields:
        str: 逐字输出的字符
    """
    for char in response:
        yield char
