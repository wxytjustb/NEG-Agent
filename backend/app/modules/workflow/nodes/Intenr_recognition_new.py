# 意图识别模块 - 基于 ModelScope API 调用
from typing import Dict, Tuple, List, Optional, Any
from app.core.config import settings
import logging
import json
from openai import OpenAI

logger = logging.getLogger(__name__)

# 意图标签定义（从配置文件读取）
INTENT_LABELS = [label.strip() for label in settings.INTENT_LABELS.split(",") if label.strip()]

# ModelScope 客户端（懒加载）
_modelscope_client = None


def _get_modelscope_client() -> OpenAI:
    """获取 ModelScope 客户端实例（懒加载）
    
    Returns:
        OpenAI 客户端实例（兼容 ModelScope API）
    """
    global _modelscope_client
    
    if _modelscope_client is None:
        logger.info("正在初始化 ModelScope API 客户端...")
        _modelscope_client = OpenAI(
            base_url=settings.MODELSCOPE_API_BASE_URL,
            api_key=settings.MODELSCOPE_API_KEY
        )
        logger.info("✅ ModelScope API 客户端初始化完成")
    
    return _modelscope_client


def detect_intent(
    user_input: str,
    history_text: str = "",
    min_confidence: Optional[float] = None  # 默认使用配置文件中的值
) -> Tuple[str, float, Dict[str, float], List[Dict[str, Any]]]:
    """检测用户输入的意图（使用 ModelScope API）
    
    Args:
        user_input: 用户输入文本
        history_text: 历史对话文本（提供上下文）
        min_confidence: 最低置信度阈值（低于此值返回 "日常对话"），默认使用配置值
        
    Returns:
        Tuple[主意图, 主意图置信度, 所有意图得分字典, 所有意图列表]
        
    Example:
        >>> intent, confidence, all_scores, intents = detect_intent(
        ...     user_input="被差评了",
        ...     history_text="用户：今天工作怎么样\n安然：..."
        ... )
        >>> print(f"主意图: {intent}, 置信度: {confidence:.2f}")
        >>> print(f"所有意图: {intents}")
        主意图: 法律咨询, 置信度: 0.90
        所有意图: [{'intent': '法律咨询', 'confidence': 0.90}, {'intent': '情感倾诉', 'confidence': 0.75}]
    """
    # 使用配置文件中的默认值
    if min_confidence is None:
        min_confidence = settings.INTENT_MIN_CONFIDENCE
    
    if not user_input or not user_input.strip():
        logger.warning("用户输入为空，返回默认意图")
        return "日常对话", 0.0, {}, []
    
    try:
        # 使用 ModelScope API 进行意图识别
        client = _get_modelscope_client()
        
        # 从 prompt.py 中获取意图识别提示词
        from app.utils.prompt import get_intent_recognition_prompt
        system_prompt = get_intent_recognition_prompt().format(
            user_input=user_input,
            history_text=history_text
        )
        
        # 调用 ModelScope API（非流式）
        response = client.chat.completions.create(
            model=settings.MODELSCOPE_MODEL,
            messages=[
                {"role": "system", "content": system_prompt}
            ],
            temperature=0.1,  # 低温度保证稳定性
            max_tokens=100,
            stream=False  # 意图识别不需要流式输出
        )
        
        # 解析响应
        message_content = response.choices[0].message.content
        if message_content is None or not message_content.strip():
            logger.warning("ModelScope 返回内容为空，返回默认意图")
            return "日常对话", 0.0, {label: 0.0 for label in INTENT_LABELS}, []
        
        # 尝试解析 JSON（ModelScope 可能需要额外处理）
        try:
            # 尝试直接解析
            result = json.loads(message_content.strip())
        except json.JSONDecodeError:
            # 如果不是纯 JSON，尝试提取 JSON 部分
            import re
            json_match = re.search(r'\{.*"intents".*\}', message_content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(0))
            else:
                logger.warning(f"ModelScope 返回格式无法解析: {message_content[:100]}，返回默认意图")
                return "日常对话", 0.0, {label: 0.0 for label in INTENT_LABELS}, []
        
        # 获取 intents 数组（支持单一和混合意图）
        intents_list = result.get("intents", [])
        
        if not intents_list or len(intents_list) == 0:
            logger.warning("未检测到意图，返回默认值")
            return "日常对话", 0.0, {}, []
        
        # 主意图（置信度最高的）
        primary_intent = intents_list[0]
        detected_intent = primary_intent.get("intent", "日常对话")
        confidence = float(primary_intent.get("confidence", 0.0))
        
        # 验证意图是否在预定义列表中
        if detected_intent not in INTENT_LABELS:
            logger.warning(f"检测到未知意图: {detected_intent}，归为日常对话")
            detected_intent = "日常对话"
            confidence = 0.5
        
        # 如果置信度过低，归为日常对话
        if confidence < min_confidence:
            logger.info(
                f"置信度过低 ({confidence:.2f} < {min_confidence})，归为日常对话。"
                f"用户输入: {user_input[:30]}..."
            )
            detected_intent = "日常对话"
        
        # 过滤有效的意图（只保留在 INTENT_LABELS 中的）
        valid_intents = []
        for intent_item in intents_list:
            intent_name = intent_item.get("intent", "")
            intent_conf = float(intent_item.get("confidence", 0.0))
            if intent_name in INTENT_LABELS:
                valid_intents.append({
                    "intent": intent_name,
                    "confidence": intent_conf
                })
        
        # 记录所有检测到的意图（包括混合意图）
        all_detected_intents = []
        for intent_item in valid_intents:
            intent_name = intent_item["intent"]
            intent_conf = intent_item["confidence"]
            all_detected_intents.append(f"{intent_name}({intent_conf:.2f})")
        
        logger.info(
            f"✅ 意图识别完成 (ModelScope): {detected_intent} (置信度: {confidence:.2f}) | "
            f"所有意图: {', '.join(all_detected_intents)} | "
            f"用户输入: {user_input[:30]}..."
        )
        
        # 构建得分字典（包含所有检测到的意图）
        scores = {label: 0.0 for label in INTENT_LABELS}
        for intent_item in valid_intents:
            intent_name = intent_item["intent"]
            intent_conf = intent_item["confidence"]
            scores[intent_name] = intent_conf
        
        return detected_intent, confidence, scores, valid_intents
        
    except json.JSONDecodeError as e:
        logger.error(f"ModelScope 返回格式解析失败: {str(e)}，返回默认意图")
        return "日常对话", 0.0, {label: 0.0 for label in INTENT_LABELS}, []
    
    except Exception as e:
        logger.error(f"ModelScope API 调用失败: {str(e)}，返回默认意图")
        return "日常对话", 0.0, {label: 0.0 for label in INTENT_LABELS}, []


def get_all_intents() -> List[str]:
    """获取所有已定义的意图标签
    
    Returns:
        意图标签列表
    """
    return INTENT_LABELS.copy()


# 预加载（可选，在应用启动时调用）
def preload_classifier():
    """预加载意图识别客户端
    
    建议在应用启动时调用，初始化 ModelScope 客户端
    """
    logger.info("开始预加载 ModelScope 意图识别客户端...")
    try:
        _get_modelscope_client()
        logger.info("✅ ModelScope 客户端预加载完成")
    except Exception as e:
        logger.warning(f"⚠️ ModelScope 客户端预加载失败: {str(e)}，将在首次调用时初始化")
