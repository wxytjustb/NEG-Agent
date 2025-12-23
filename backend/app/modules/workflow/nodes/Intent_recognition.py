# 意图识别模块 - 基于 ChromaDB Embedding 向量相似度匹配
from typing import Dict, Tuple, List, Any
from app.modules.chromadb.core.chromadb_core import ChromaDBCore
import logging

logger = logging.getLogger(__name__)

# 意图模板库（核心意图定义）
INTENT_TEMPLATES = {
    "法律咨询": (
        "我的工资被拖欠 公司不发工资 拖欠提成 老板欠薪 "
        "遭遇恶意差评 不公平的罚款 被扣钱 平台扣费 无故扣款 "
        "权益被侵犯 合法权益 劳动纠纷 用工合同 维权 法律帮助 咨询律师 "
        "交通事故 被撞了 责任认定 保险理赔 "
        "工伤 受伤 工作中受伤 工伤赔偿 "
        "加班费 加班不给钱 超时工作 没有加班费 "
        "被辞退 被解雇 被开除 不公平待遇 非法解除合同"
    ),
    "情感倾诉": (
        "我感到很委屈 很难过 心里不舒服 心里难受 "
        "焦虑 紧张 担心 害怕 恭惧 心有余惸 "
        "心情不好 心情糟糕 心情低落 心情沮丧 郁闷 "
        "压力很大 压力山大 承受不住 太累了 身心俱疲 "
        "想找人聊聊 想倾诉 想说说心里话 没人理解 "
        "感到无助 无力感 孤单 孤立无援 没人帮忙 "
        "想哭 想放弃 不想干了 坚持不下去 太难了 "
        "被误解 被冤柉 不公平 为什么总是我 凭什么"
    ),
    "日常对话": (
        "今天天气怎么样 天气好不好 会下雨吗 "
        "吃了什么 吃饭了吗 吃过了吗 晚饭吃什么 "
        "聊聊天 闲聊 随便聊聊 "
        "你好 早上好 晚上好 问候 打个招呼 "
        "日常交流 聊天儿 说说话 "
        "今天怎么样 这两天如何 最近好吗 "
        "忙吗 累不累 辛苦了 辛苦了一天 "
        "休息 下班 下班了 下单多吗 今天跑了多少单"
    )
}

# ChromaDB 集合名称
INTENT_COLLECTION_NAME = "intent_collection"

# 全局 ChromaDB 实例
_chromadb_client = None
_intent_collection = None
_is_initialized = False


def _get_chromadb_client() -> ChromaDBCore:
    """获取 ChromaDB 客户端实例
    
    Returns:
        ChromaDBCore 实例
    """
    global _chromadb_client
    
    if _chromadb_client is None:
        logger.info("正在初始化 ChromaDB 客户端...")
        _chromadb_client = ChromaDBCore()
        logger.info("✅ ChromaDB 客户端初始化完成")
    
    return _chromadb_client


def _initialize_intent_collection():
    """初始化意图模板集合（只执行一次）"""
    global _intent_collection, _is_initialized
    
    if _is_initialized:
        return
    
    try:
        chromadb_client = _get_chromadb_client()
        
        # 确保 ChromaDB 客户端已初始化
        chromadb_client._ensure_client()
        
        # 获取或创建意图模板集合
        logger.info(f"正在初始化意图模板集合: {INTENT_COLLECTION_NAME}")
        _intent_collection = chromadb_client.client.get_or_create_collection(
            name=INTENT_COLLECTION_NAME,
            metadata={
                "hnsw:space": "cosine",  # 使用余弦相似度
                "description": "意图识别模板库"
            }
        )
        
        # 检查是否已有数据
        existing_count = _intent_collection.count()
        
        if existing_count == 0:
            # 首次初始化，添加意图模板
            logger.info("首次初始化，添加意图模板到 ChromaDB...")
            _add_intent_templates_to_chromadb()
        else:
            logger.info(f"✅ 意图模板集合已存在，包含 {existing_count} 个模板")
        
        _is_initialized = True
        logger.info("✅ 意图模板集合初始化完成")
        
    except Exception as e:
        logger.error(f"初始化意图模板集合失败: {str(e)}")
        raise


def _add_intent_templates_to_chromadb():
    """将意图模板添加到 ChromaDB"""
    global _intent_collection
    
    documents = []
    metadatas = []
    ids = []
    
    for idx, (intent, template) in enumerate(INTENT_TEMPLATES.items(), start=1):
        documents.append(template)
        metadatas.append({"intent": intent})
        ids.append(f"intent_{idx}")
    
    _intent_collection.add(
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )
    
    logger.info(f"✅ 已添加 {len(INTENT_TEMPLATES)} 个意图模板到 ChromaDB")


def detect_intent(
    user_input: str,
    min_confidence: float = 0.3
) -> Tuple[str, float, Dict[str, float]]:
    """检测用户输入的意图（使用 ChromaDB 的 Embedding 模型）
    
    Args:
        user_input: 用户输入文本
        min_confidence: 最低置信度阈值（低于此值返回 "日常对话"）
        
    Returns:
        Tuple[意图名称, 置信度, 所有意图的得分字典]
        
    Example:
        >>> intent, confidence, all_scores = detect_intent("我今天被差评了")
        >>> print(f"意图: {intent}, 置信度: {confidence:.2f}")
        意图: 情感倾诉, 置信度: 0.78
    """
    if not user_input or not user_input.strip():
        logger.warning("用户输入为空，返回默认意图")
        return "日常对话", 0.0, {}
    
    try:
        # 确保集合已初始化
        _initialize_intent_collection()
        
        # 使用 ChromaDB 查询最相似的意图模板
        results = _intent_collection.query(
            query_texts=[user_input],
            n_results=len(INTENT_TEMPLATES)  # 返回所有意图的相似度
        )
        
        # 解析结果
        if not results['metadatas'] or not results['metadatas'][0]:
            logger.warning("ChromaDB 查询无结果，返回默认意图")
            return "日常对话", 0.0, {}
        
        # 构建得分字典（距离转换为相似度）
        scores = {}
        for metadata, distance in zip(results['metadatas'][0], results['distances'][0]):
            intent = metadata['intent']
            # ChromaDB 返回的是距离，需要转换为相似度（1 - distance）
            # 余弦距离范围 [0, 2]，相似度范围 [0, 1]
            similarity = 1 - (distance / 2)
            scores[intent] = similarity
        
        # 选择最高分的意图
        detected_intent = max(scores.items(), key=lambda x: x[1])[0]
        confidence = scores[detected_intent]
        
        # 如果置信度过低，归为日常对话
        if confidence < min_confidence:
            logger.info(
                f"置信度过低 ({confidence:.2f} < {min_confidence})，归为日常对话。"
                f"用户输入: {user_input[:30]}..."
            )
            detected_intent = "日常对话"
        
        logger.info(
            f"✅ 意图识别完成: {detected_intent} (置信度: {confidence:.2f}) | "
            f"用户输入: {user_input[:30]}..."
        )
        
        return detected_intent, confidence, scores
        
    except Exception as e:
        logger.error(f"意图识别失败: {str(e)}，返回默认意图")
        return "日常对话", 0.0, {}


def add_intent_template(intent_name: str, template: str) -> bool:
    """动态添加新的意图模板（运行时扩展）
    
    Args:
        intent_name: 意图名称
        template: 意图模板文本
        
    Returns:
        是否添加成功
    """
    try:
        # 确保集合已初始化
        _initialize_intent_collection()
        
        # 更新本地模板库
        INTENT_TEMPLATES[intent_name] = template
        
        # 添加到 ChromaDB
        _intent_collection.add(
            documents=[template],
            metadatas=[{"intent": intent_name}],
            ids=[f"intent_{intent_name}_{len(INTENT_TEMPLATES)}"]
        )
        
        logger.info(f"✅ 新增意图模板: {intent_name}")
        return True
        
    except Exception as e:
        logger.error(f"添加意图模板失败: {str(e)}")
        return False


def get_all_intents() -> Dict[str, str]:
    """获取所有已定义的意图模板
    
    Returns:
        意图名称到模板的映射
    """
    return INTENT_TEMPLATES.copy()


def reset_intent_collection():
    """重置意图模板集合（清空并重新初始化）
    
    警告：此操作会删除所有意图模板数据！
    """
    global _is_initialized
    
    try:
        chromadb_client = _get_chromadb_client()
        
        # 删除旧集合
        chromadb_client.client.delete_collection(name=INTENT_COLLECTION_NAME)
        logger.info(f"已删除意图模板集合: {INTENT_COLLECTION_NAME}")
        
        # 重置初始化标志
        _is_initialized = False
        
        # 重新初始化
        _initialize_intent_collection()
        logger.info("✅ 意图模板集合已重置")
        
    except Exception as e:
        logger.error(f"重置意图模板集合失败: {str(e)}")


# 预加载（可选，在应用启动时调用）
def preload_intent_collection():
    """预加载意图模板集合
    
    建议在应用启动时调用，避免首次请求时初始化延迟
    """
    logger.info("开始预加载意图模板集合...")
    _initialize_intent_collection()
    logger.info("✅ 意图模板集合预加载完成")