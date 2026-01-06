# 意图识别模块 - 使用向量引擎 qwen3-0.6b
from typing import Dict, Tuple, List, Optional, Any
from app.core.config import settings
from app.initialize.vectorengine import get_vectorengine_client
import logging
import json

logger = logging.getLogger(__name__)

INTENT_LABELS = [label.strip() for label in settings.INTENT_LABELS.split(",") if label.strip()]


def detect_intent(
    user_input: str,
    history_text: str = "",
    min_confidence: Optional[float] = None
) -> Tuple[str, float, Dict[str, float], List[Dict[str, Any]]]:
    """检测用户输入的意图（使用向量引擎 API）
    
    Args:
        user_input: 用户输入文本
        history_text: 历史对话文本（提供上下文）
        min_confidence: 最低置信度阈值，默认使用配置值
        
    Returns:
        Tuple[主意图, 主意图置信度, 所有意图得分字典, 所有意图列表]
    """
    if min_confidence is None:
        min_confidence = settings.INTENT_MIN_CONFIDENCE
    
    if not user_input or not user_input.strip():
        logger.warning("用户输入为空，返回默认意图")
        return "日常对话", 0.0, {}, []
    
    try:
        client = get_vectorengine_client()
        
        from app.utils.prompt import get_intent_recognition_prompt
        system_prompt = get_intent_recognition_prompt().format(
            user_input=user_input,
            history_text=history_text
        )
        
        response = client.chat.completions.create(
            model=settings.VECTORENGINE_EMBEDDING_MODEL,
            messages=[{"role": "system", "content": system_prompt}],
            temperature=0.1,
            max_tokens=100
        )
        
        # 兼容多种返回格式
        if hasattr(response, 'choices'):
            message_content = response.choices[0].message.content
        elif isinstance(response, str):
            message_content = response
        else:
            message_content = str(response)
        
        logger.info(f"向量引擎返回内容: {message_content[:200]}...")
        
        if message_content is None or not message_content.strip():
            logger.warning("向量引擎返回内容为空，返回默认意图")
            return "日常对话", 0.0, {label: 0.0 for label in INTENT_LABELS}, []
        
        # 清理 markdown 代码块
        message_content = message_content.strip()
        if message_content.startswith('```json'):
            message_content = message_content[7:]  # 移除 ```json
        if message_content.startswith('```'):
            message_content = message_content[3:]  # 移除 ```
        if message_content.endswith('```'):
            message_content = message_content[:-3]  # 移除结尾 ```
        message_content = message_content.strip()
        
        result = json.loads(message_content)
        
        # 获取 intents 数组
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
        
        # 过滤有效的意图
        valid_intents = []
        for intent_item in intents_list:
            intent_name = intent_item.get("intent", "")
            intent_conf = float(intent_item.get("confidence", 0.0))
            if intent_name in INTENT_LABELS:
                valid_intents.append({
                    "intent": intent_name,
                    "confidence": intent_conf
                })
        
        logger.info(
            f"✅ 意图识别完成: {detected_intent} (置信度: {confidence:.2f}) | "
            f"用户输入: {user_input[:30]}..."
        )
        
        # 构建得分字典
        scores = {label: 0.0 for label in INTENT_LABELS}
        for intent_item in valid_intents:
            scores[intent_item["intent"]] = intent_item["confidence"]
        
        return detected_intent, confidence, scores, valid_intents
        
    except json.JSONDecodeError as e:
        logger.error(f"向量引擎返回格式解析失败: {str(e)}，内容: {message_content}，返回默认意图")
        return "日常对话", 0.0, {label: 0.0 for label in INTENT_LABELS}, []
    
    except Exception as e:
        logger.error(f"向量引擎 API 调用失败: {str(e)}，返回默认意图")
        return "日常对话", 0.0, {label: 0.0 for label in INTENT_LABELS}, []


def get_all_intents() -> List[str]:
    """获取所有已定义的意图标签
    
    Returns:
        意图标签列表
    """
    return INTENT_LABELS.copy()


def preload_classifier():
    logger.info("开始预加载向量引擎 qwen3-0.6b...")
    try:
        get_vectorengine_client()
        logger.info("✅ qwen3-0.6b 预加载完成")
    except Exception as e:
        logger.warning(f"⚠️ qwen3-0.6b 预加载失败: {str(e)}")