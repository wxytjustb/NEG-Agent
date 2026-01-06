# 向量引擎初始化模块 - 用于意图识别
from openai import OpenAI
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# 全局客户端实例（懒加载）
_vectorengine_client = None


def get_vectorengine_client() -> OpenAI:
    """获取向量引擎客户端实例（懒加载）
    
    Returns:
        OpenAI 兼容的向量引擎客户端
    """
    global _vectorengine_client
    
    if _vectorengine_client is None:
        logger.info("正在初始化向量引擎客户端...")
        
        if not settings.VECTORENGINE_API_TOKEN:
            raise ValueError("VECTORENGINE_API_TOKEN 未配置，请在 .env 文件中设置")
        
        _vectorengine_client = OpenAI(
            api_key=settings.VECTORENGINE_API_TOKEN,
            base_url=settings.VECTORENGINE_API_BASE_URL
        )
        logger.info("✅ 向量引擎客户端初始化完成")
    
    return _vectorengine_client


def test_connection() -> bool:
    """测试向量引擎连接
    
    Returns:
        连接成功返回 True，失败返回 False
    """
    try:
        logger.info("🔍 开始测试向量引擎连接...")
        
        client = get_vectorengine_client()
        
        # 测试调用 Chat API
        response = client.chat.completions.create(
            model=settings.VECTORENGINE_EMBEDDING_MODEL,
            messages=[{"role": "user", "content": "测试连接"}],
            max_tokens=10
        )
        
        # 检查响应类型（向量引擎可能返回字典或字符串）
        if isinstance(response, str):
            logger.info(f"✅ 向量引擎连接测试成功（返回字符串）")
            logger.info(f"   - API Base URL: {settings.VECTORENGINE_API_BASE_URL}")
            logger.info(f"   - 模型: {settings.VECTORENGINE_EMBEDDING_MODEL}")
            logger.info(f"   - 响应: {response[:100]}...")
            return True
        elif hasattr(response, 'choices') and response.choices:
            logger.info(f"✅ 向量引擎连接测试成功（标准格式）")
            logger.info(f"   - API Base URL: {settings.VECTORENGINE_API_BASE_URL}")
            logger.info(f"   - 模型: {settings.VECTORENGINE_EMBEDDING_MODEL}")
            return True
        elif response:
            logger.info(f"✅ 向量引擎连接测试成功（非标准格式）")
            logger.info(f"   - API Base URL: {settings.VECTORENGINE_API_BASE_URL}")
            logger.info(f"   - 模型: {settings.VECTORENGINE_EMBEDDING_MODEL}")
            logger.info(f"   - 响应类型: {type(response)}")
            return True
        else:
            logger.error("❌ 向量引擎返回空结果")
            return False
            
    except Exception as e:
        logger.error(f"❌ 向量引擎连接测试失败: {str(e)}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
        return False


def warmup_vectorengine():
    """预热向量引擎服务（应用启动时调用）
    
    通过发送测试请求来唤醒可能处于冷启动状态的向量引擎服务，
    避免用户首次请求时遇到 425 错误
    """
    import time
    
    logger.info("=" * 60)
    logger.info("🚀 开始预热向量引擎服务...")
    logger.info("=" * 60)
    
    max_attempts = 5
    retry_delay = 3  # 秒
    
    for attempt in range(1, max_attempts + 1):
        try:
            logger.info(f"第 {attempt}/{max_attempts} 次尝试预热...")
            
            client = get_vectorengine_client()
            
            # 发送预热请求
            response = client.chat.completions.create(
                model=settings.VECTORENGINE_EMBEDDING_MODEL,
                messages=[{"role": "user", "content": "预热服务"}],
                max_tokens=5
            )
            
            # 成功则退出
            logger.info("✅ 向量引擎服务预热成功！")
            logger.info(f"   - API Base URL: {settings.VECTORENGINE_API_BASE_URL}")
            logger.info(f"   - 模型: {settings.VECTORENGINE_EMBEDDING_MODEL}")
            logger.info("=" * 60)
            return True
            
        except Exception as e:
            error_str = str(e)
            
            # 检查是否是 425 错误（服务唤醒中）
            if "425" in error_str or "waking up" in error_str.lower():
                if attempt < max_attempts:
                    logger.warning(
                        f"⚠️ 向量引擎服务正在唤醒中，{retry_delay}秒后重试... "
                        f"(第 {attempt}/{max_attempts} 次)"
                    )
                    time.sleep(retry_delay)
                    continue
                else:
                    logger.error("❌ 向量引擎服务预热失败：达到最大重试次数")
                    logger.warning("⚠️ 服务将在后台继续唤醒，首次用户请求可能会稍慢")
                    logger.info("=" * 60)
                    return False
            else:
                # 其他错误
                logger.error(f"❌ 向量引擎预热失败: {error_str}")
                if attempt < max_attempts:
                    logger.info(f"{retry_delay}秒后重试...")
                    time.sleep(retry_delay)
                    continue
                else:
                    logger.warning("⚠️ 预热失败，但服务可能仍可正常使用")
                    logger.info("=" * 60)
                    return False
    
    logger.info("=" * 60)
    return False
