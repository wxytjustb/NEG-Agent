"""
ID 生成器工具
用于生成唯一的 conversation_id、session_id 等标识符
"""
import uuid
import time
from typing import Optional


def generate_conversation_id(prefix: str = "conv") -> str:
    """
    生成唯一的对话 ID
    
    格式：{prefix}_{uuid}_{timestamp}
    示例：conv_a1b2c3d4e5f6_1704614400123
    
    特点：
    - 全局唯一（基于 UUID4）
    - 包含时间戳（毫秒级）
    - 可排序（按时间）
    - 长度约 40-45 个字符
    
    Args:
        prefix: ID 前缀，默认为 "conv"
        
    Returns:
        str: 唯一的对话 ID
    """
    # 生成 UUID（去除横杠）
    unique_id = uuid.uuid4().hex[:12]  # 取前12位
    
    # 获取当前时间戳（毫秒）
    timestamp = int(time.time() * 1000)
    
    # 组合生成最终 ID
    conversation_id = f"{prefix}_{unique_id}_{timestamp}"
    
    return conversation_id


def generate_short_conversation_id(prefix: str = "conv") -> str:
    """
    生成较短的唯一对话 ID
    
    格式：{prefix}_{timestamp}_{random}
    示例：conv_1704614400_a1b2c3
    
    特点：
    - 全局唯一概率高
    - 较短（约 25-30 个字符）
    - 可排序（按时间）
    
    Args:
        prefix: ID 前缀，默认为 "conv"
        
    Returns:
        str: 较短的唯一对话 ID
    """
    # 获取当前时间戳（秒）
    timestamp = int(time.time())
    
    # 生成随机字符串（6位）
    random_str = uuid.uuid4().hex[:6]
    
    # 组合生成最终 ID
    conversation_id = f"{prefix}_{timestamp}_{random_str}"
    
    return conversation_id


def generate_uuid_conversation_id(prefix: str = "conv") -> str:
    """
    生成基于完整 UUID 的对话 ID
    
    格式：{prefix}_{uuid}
    示例：conv_a1b2c3d4e5f6g7h8i9j0k1l2
    
    特点：
    - 全局唯一（标准 UUID4）
    - 较长（约 36-40 个字符）
    - 无时间信息
    
    Args:
        prefix: ID 前缀，默认为 "conv"
        
    Returns:
        str: 基于 UUID 的对话 ID
    """
    # 生成完整 UUID（去除横杠）
    unique_id = uuid.uuid4().hex
    
    # 组合生成最终 ID
    conversation_id = f"{prefix}_{unique_id}"
    
    return conversation_id


def generate_snowflake_like_id(worker_id: int = 1, datacenter_id: int = 1) -> int:
    """
    生成类雪花算法的 ID（纯数字）
    
    格式：64位整数
    示例：1704614400123456789
    
    特点：
    - 纯数字 ID
    - 趋势递增
    - 包含时间戳
    - 适合数据库主键
    
    结构：
    - 41位时间戳（毫秒）
    - 5位数据中心 ID
    - 5位机器 ID
    - 12位序列号（单毫秒内）
    
    Args:
        worker_id: 机器 ID（0-31）
        datacenter_id: 数据中心 ID（0-31）
        
    Returns:
        int: 雪花 ID（64位整数）
    """
    # 获取当前时间戳（毫秒）
    timestamp = int(time.time() * 1000)
    
    # 简化版：时间戳 + worker_id + datacenter_id + 随机序列
    # （完整雪花算法需要维护序列号状态，这里简化处理）
    sequence = int(time.time() * 1000000) % 4096  # 12位序列号（0-4095）
    
    # 组合各部分
    snowflake_id = (
        (timestamp << 22) |  # 时间戳左移22位
        (datacenter_id << 17) |  # 数据中心ID左移17位
        (worker_id << 12) |  # 机器ID左移12位
        sequence  # 序列号
    )
    
    return snowflake_id


def extract_timestamp_from_id(conversation_id: str) -> Optional[int]:
    """
    从 conversation_id 中提取时间戳
    
    支持的格式：
    - conv_{uuid}_{timestamp}
    - conv_{timestamp}_{random}
    
    Args:
        conversation_id: 对话 ID
        
    Returns:
        Optional[int]: 时间戳（毫秒或秒），如果无法提取则返回 None
    """
    try:
        parts = conversation_id.split("_")
        if len(parts) >= 3:
            # 尝试最后一部分（格式1：conv_{uuid}_{timestamp}）
            try:
                timestamp = int(parts[-1])
                return timestamp
            except ValueError:
                pass
            
            # 尝试第二部分（格式2：conv_{timestamp}_{random}）
            try:
                timestamp = int(parts[1])
                return timestamp
            except ValueError:
                pass
        
        return None
    except Exception:
        return None


def is_valid_conversation_id(conversation_id: str, prefix: str = "conv") -> bool:
    """
    验证 conversation_id 是否有效
    
    检查：
    - 是否包含指定前缀
    - 是否包含足够的部分
    - 格式是否正确
    
    Args:
        conversation_id: 对话 ID
        prefix: 期望的前缀
        
    Returns:
        bool: 是否有效
    """
    if not conversation_id or not isinstance(conversation_id, str):
        return False
    
    if not conversation_id.startswith(f"{prefix}_"):
        return False
    
    parts = conversation_id.split("_")
    if len(parts) < 2:
        return False
    
    return True


# 默认使用的生成器（推荐）
generate_id = generate_conversation_id
