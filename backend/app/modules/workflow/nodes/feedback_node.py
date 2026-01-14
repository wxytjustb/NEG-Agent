# 用户反馈节点 - 获取用户近期反馈总结数据
import logging
from typing import Dict, Any
from app.modules.workflow.core.state import WorkflowState
from app.core.config import settings
from app.services.feedback_service import feedback_service

# 可选依赖
try:
    from lmnr import observe  # type: ignore
except ImportError:
    # 如果 lmnr 未安装，使用空装饰器
    def observe(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

logger = logging.getLogger(__name__)


async def fetch_user_feedback_summary(access_token: str, days: int | None = None) -> Dict[str, Any]:
    """从服务层获取近 days 天的用户反馈总结数据

    说明：
    - 改为调用 FeedbackService 的 get_feedback_summary(days, access_token)
    - 兼容两种返回结构：
      1) data 为列表（逐条反馈项），按旧逻辑计算统计数据
      2) data 为字典（已聚合），尽可能映射到统一的输出结构

    Args:
        access_token: 用户的访问令牌
        days: 查询近几天的数据，默认使用配置文件中的值

    Returns:
        反馈总结数据字典，包含总数、有用率、类型统计等
    """
    if not access_token:
        raise ValueError("access_token 不能为空")

    if days is None:
        days = getattr(settings, "FEEDBACK_TREND_DEFAULT_DAYS", 7)

    logger.info(f"正在查询用户反馈总结: days={days}")
    try:
        result = await feedback_service.get_feedback_summary(days=days, access_token=access_token)
        logger.debug(f"反馈总结服务返回: {result}")

        # 标准化响应
        data = result.get("data") if isinstance(result, dict) else None
        if not data:
            logger.info("暂无反馈数据")
            return {}

        # 情况一：data 是列表，推断为原始反馈项列表
        if isinstance(data, list):
            feedback_list = data
            total_count = len(feedback_list)
            useful_count = sum(1 for item in feedback_list if item.get("isUseful") is True)
            not_useful_count = total_count - useful_count
            useful_rate = useful_count / total_count if total_count > 0 else 0

            feedback_types: Dict[str, int] = {}
            for item in feedback_list:
                feedback_type = item.get("feedbackType")
                if feedback_type and feedback_type != "helpful":
                    feedback_types[feedback_type] = feedback_types.get(feedback_type, 0) + 1

            feedback_data = {
                "total_count": total_count,
                "useful_count": useful_count,
                "not_useful_count": not_useful_count,
                "useful_rate": useful_rate,
                "feedback_types": feedback_types,
                "feedback_list": feedback_list,
            }
            logger.info(
                f"✅ 反馈总结计算成功: 总数={total_count}, 有用数={useful_count}, 满意度={useful_rate*100:.1f}%"
            )
            return feedback_data

        # 情况二：data 是字典，推断为聚合后的统计
        if isinstance(data, dict):
            total_count = data.get("total_count") or data.get("total") or data.get("count") or 0
            useful_rate = data.get("useful_rate") or data.get("usefulRate") or data.get("satisfaction") or 0
            feedback_types = (
                data.get("feedback_types")
                or data.get("types")
                or data.get("typeStats")
                or data.get("unUsefulTagCounts")
                or {}
            )
            feedback_list = data.get("feedback_list") or data.get("list") or data.get("items") or []

            # 兼容直接提供有用数量的返回（例如字段名为 useful）
            provided_useful = data.get("useful_count")
            if provided_useful is None:
                provided_useful = data.get("useful")

            computed_useful = int(round(useful_rate * total_count)) if useful_rate and total_count else 0
            useful_count = provided_useful if isinstance(provided_useful, int) else computed_useful
            not_useful_count = total_count - useful_count

            feedback_data = {
                "total_count": total_count,
                "useful_count": useful_count,
                "not_useful_count": not_useful_count,
                "useful_rate": useful_rate or (useful_count / total_count if total_count else 0),
                "feedback_types": feedback_types,
                "feedback_list": feedback_list,
            }
            logger.info("✅ 反馈总结获取成功(聚合数据)")
            return feedback_data

        logger.warning("反馈总结数据格式未知")
        return {}
    except Exception as e:
        logger.error(f"获取反馈总结异常: {str(e)}")
        return {}


def format_feedback_summary(feedback_data: Dict[str, Any]) -> str:
    """将反馈数据格式化为可读的文本摘要（包含满意度和负面反馈类型）
    
    Args:
        feedback_data: 反馈趋势数据
        
    Returns:
        格式化后的文本摘要
    """
    if not feedback_data:
        return "用户暂无反馈记录"
    
    useful_rate = feedback_data.get("useful_rate", 0)
    feedback_types = feedback_data.get("feedback_types", {})
    
    # 构建摘要文本
    summary_parts = [
        f"用户满意度：{useful_rate * 100:.1f}%"
    ]
    
    # 添加负面反馈类型统计
    if feedback_types:
        summary_parts.append("主要问题类型：")
        for feedback_type, count in feedback_types.items():
            summary_parts.append(f"  · {feedback_type}：{count}次")
    else:
        summary_parts.append("暂无负面反馈")
    
    return "\n".join(summary_parts)


@observe(name="feedback_node", tags=["node", "feedback"])
async def async_feedback_node(state: WorkflowState) -> Dict[str, Any]:
    """用户反馈节点 - 异步版本（推荐在 LangGraph 中使用）
    
    职责：
    1. 从 state 中获取 user_id 和 access_token
    2. 调用服务层获取用户近期反馈总结
    3. 将反馈数据格式化为文本摘要
    4. 更新 state，添加 feedback_summary 字段
    
    Args:
        state: 工作流状态
        
    Returns:
        更新后的状态字典
    """
    logger.info("========== 用户反馈节点开始 ==========")
    
    try:
        # 从 state 中获取必要信息
        user_id = state.get("user_id", "unknown")
        access_token = state.get("access_token")
        
        # 检查必要参数
        if not access_token:
            logger.warning("access_token 不存在，跳过反馈数据获取")
            return {
                "feedback_summary": "用户暂无反馈记录",
                "feedback_data": {}
            }
        
        if user_id == "unknown":
            logger.warning("user_id 未知，跳过反馈数据获取")
            return {
                "feedback_summary": "用户暂无反馈记录",
                "feedback_data": {}
            }
        
        # 异步调用服务层获取反馈总结
        logger.info(f"开始获取用户 {user_id} 的反馈总结...")
        feedback_data = await fetch_user_feedback_summary(
            access_token=access_token
        )
        
        # 格式化反馈摘要
        feedback_summary = format_feedback_summary(feedback_data)
        
        logger.info(f"✅ 反馈节点执行成功")
        logger.info(f"反馈摘要:\n{feedback_summary}")
        
        # 返回更新的状态
        return {
            "feedback_summary": feedback_summary,
            "feedback_data": feedback_data
        }
        
    except Exception as e:
        error_msg = f"反馈节点执行失败: {str(e)}"
        logger.error(error_msg)
        # 返回默认值，不中断工作流
        return {
            "feedback_summary": "用户暂无反馈记录",
            "feedback_data": {},
            "error": error_msg
        }


def feedback_node(state: WorkflowState) -> Dict[str, Any]:
    """用户反馈节点 - 同步版本
    
    职责：
    1. 从 state 中获取 user_id 和 access_token
    2. 调用服务层获取用户近期反馈总结
    3. 将反馈数据格式化为文本摘要
    4. 更新 state，添加 feedback_summary 字段
    
    Args:
        state: 工作流状态
        
    Returns:
        更新后的状态字典
    """
    logger.info("========== 用户反馈节点开始 ==========")
    
    import asyncio
    import nest_asyncio  # type: ignore
    
    # 允许嵌套事件循环
    nest_asyncio.apply()
    
    try:
        # 从 state 中获取必要信息
        user_id = state.get("user_id", "unknown")
        access_token = state.get("access_token")
        
        # 检查必要参数
        if not access_token:
            logger.warning("access_token 不存在，跳过反馈数据获取")
            return {
                "feedback_summary": "用户暂无反馈记录",
                "feedback_data": {}
            }
        
        if user_id == "unknown":
            logger.warning("user_id 未知，跳过反馈数据获取")
            return {
                "feedback_summary": "用户暂无反馈记录",
                "feedback_data": {}
            }
        
        # 调用异步方法获取反馈数据
        logger.info(f"开始获取用户 {user_id} 的反馈总结...")
        
        try:
            loop = asyncio.get_running_loop()
            task = loop.create_task(fetch_user_feedback_summary(
                access_token=access_token
            ))
            feedback_data = loop.run_until_complete(task)
        except RuntimeError:
            feedback_data = asyncio.run(fetch_user_feedback_summary(
                access_token=access_token
            ))
        
        # 格式化反馈摘要
        feedback_summary = format_feedback_summary(feedback_data)
        
        logger.info(f"✅ 反馈节点执行成功")
        logger.info(f"反馈摘要:\n{feedback_summary}")
        
        # 返回更新的状态
        return {
            "feedback_summary": feedback_summary,
            "feedback_data": feedback_data
        }
        
    except Exception as e:
        error_msg = f"反馈节点执行失败: {str(e)}"
        logger.error(error_msg)
        # 返回默认值，不中断工作流
        return {
            "feedback_summary": "用户暂无反馈记录",
            "feedback_data": {},
            "error": error_msg
        }
