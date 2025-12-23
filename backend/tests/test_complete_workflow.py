#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整工作流测试
测试从 session_id 到 LLM 回答的完整流程
"""

import asyncio
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# 确保从正确的路径导入模块
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.modules.workflow.workflows.workflow import run_chat_workflow
from app.core.session_token import create_session, update_session
from app.initialize import redis
from app.initialize.chromadb import init_chromadb
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 是否使用 Mock LLM（设为 True 可以避免调用真实 API）
USE_MOCK_LLM = False  # ⚠️ 设为 False 调用真实 LLM（会产生费用）


async def setup_test_session():
    """
    设置测试会话（模拟用户初始化）
    
    Returns:
        session_id: 创建的会话ID
    """
    logger.info("="*60)
    logger.info("步骤 1: 创建测试会话")
    logger.info("="*60)
    
    # 初始化 Redis 连接
    await redis.init_redis()
    
    # 初始化 ChromaDB 客户端（用于意图识别）
    init_chromadb()
    logger.info("✅ ChromaDB 初始化成功")
    
    # 模拟从 Golang Server 获取的用户数据
    test_user_data = {
        "appUserId": 334,
        "username": "test_user",
        "age": 25,
        "gender": "男",
        "companyName": "饿了么"
    }
    
    # 创建会话
    session_id = await create_session(test_user_data)
    logger.info(f"✅ 会话创建成功: {session_id}")
    
    # 将用户画像信息添加到会话中
    await update_session(session_id, {
        "user_id": str(test_user_data["appUserId"]),
        "company": test_user_data["companyName"],
        "age": str(test_user_data["age"]),
        "gender": test_user_data["gender"]
    })
    logger.info(f"✅ 用户画像已存入会话")
    logger.info(f"   - 用户ID: {test_user_data['appUserId']}")
    logger.info(f"   - 公司: {test_user_data['companyName']}")
    logger.info(f"   - 年龄: {test_user_data['age']}")
    logger.info(f"   - 性别: {test_user_data['gender']}")
    
    return session_id


def test_workflow_with_different_intents(session_id: str):
    """
    测试不同意图的工作流
    
    Args:
        session_id: 会话ID
    """
    logger.info("\n" + "="*60)
    logger.info("步骤 2: 测试不同意图的工作流")
    logger.info("="*60)
    
    # 测试用例列表
    test_cases = [
        {
            "name": "情感倾诉场景",
            "input": "我今天被差评了，公司要扣我钱，心里很委屈",
            "expected_intent": "情感倾诉"
        },
        {
            "name": "法律咨询场景",
            "input": "我的工资被拖欠了一个月，应该怎么维权？",
            "expected_intent": "法律咨询"
        },
        {
            "name": "日常对话场景",
            "input": "今天天气怎么样？",
            "expected_intent": "日常对话"
        }
    ]
    
    results = []
    
    # Mock LLM 回答（根据意图返回不同的模拟回答）
    def mock_llm_invoke(prompt):
        """Mock LLM 调用，根据 Prompt 内容返回不同的回答"""
        mock_response = MagicMock()
        
        # 根据 Prompt 中的关键词返回不同的模拟回答
        if "差评" in prompt or "委屈" in prompt:
            mock_response.content = "[模拟回答] 听得出来你现在既愤怒又无奈，明明不是你的错却要承担损失，真的太委屈了。法律上讲，你有权通过平台申诉通道提交证据进行申辩。"
        elif "工资" in prompt or "维权" in prompt:
            mock_response.content = "[模拟回答] 辛苦挣来的钱被拖欠，这种焦虑和不安我特别能理解。法律上你有权要求公司按时足额支付工资。建议您先整理好证据，然后拨戒12333劳动保障监察热线咨询。"
        elif "天气" in prompt:
            mock_response.content = "[模拟回答] 今天天气还不错呢，阳光挺暖和的。不过你们在外面跑单，风吹日晒的，记得多留意天气变化，带好雨具或防晒呀。"
        else:
            mock_response.content = "[模拟回答] 我会一直在这里陈着你面对的。"
        
        return mock_response
    
    for i, test_case in enumerate(test_cases, 1):
        logger.info(f"\n{'─'*60}")
        logger.info(f"测试用例 {i}: {test_case['name']}")
        logger.info(f"{'─'*60}")
        logger.info(f"用户输入: {test_case['input']}")
        
        try:
            # 根据配置决定是否使用 Mock
            if USE_MOCK_LLM:
                logger.info("✅ 使用 Mock LLM（不调用真实 API）")
                # Mock LLM 调用
                with patch('app.modules.workflow.nodes.llm_answer.llm_core.create_llm') as mock_create_llm:
                    mock_llm = MagicMock()
                    mock_llm.invoke = mock_llm_invoke
                    mock_create_llm.return_value = mock_llm
                    
                    # 运行工作流
                    result = run_chat_workflow(
                        user_input=test_case['input'],
                        session_id=session_id,
                        user_id="334",  # 测试用户ID
                        username="测试用户"  # 测试用户名
                    )
            else:
                logger.info("⚠️  使用真实 LLM API（会产生费用）")
                # 运行工作流
                result = run_chat_workflow(
                    user_input=test_case['input'],
                    session_id=session_id,
                    user_id="334",  # 测试用户ID
                    username="测试用户"  # 测试用户名
                )
            
            # 提取结果
            detected_intent = result.get('intent', 'N/A')
            intent_confidence = result.get('intent_confidence', 0)
            llm_response = result.get('llm_response', '')
            user_id = result.get('user_id', 'N/A')
            company = result.get('company', 'N/A')
            age = result.get('age', 'N/A')
            gender = result.get('gender', 'N/A')
            
            # 打印结果
            logger.info(f"\n📊 工作流执行结果:")
            logger.info(f"   用户ID: {user_id}")
            logger.info(f"   用户画像: 公司={company}, 年龄={age}, 性别={gender}")
            logger.info(f"   识别意图: {detected_intent}")
            logger.info(f"   置信度: {intent_confidence:.2f}")
            logger.info(f"   期望意图: {test_case['expected_intent']}")
            
            # 验证意图
            if detected_intent == test_case['expected_intent']:
                logger.info(f"   ✅ 意图识别正确")
            else:
                logger.warning(f"   ⚠️ 意图识别可能不准确（期望: {test_case['expected_intent']}, 实际: {detected_intent}）")
            
            logger.info(f"\n💬 LLM 回答 ({len(llm_response)} 字符):")
            logger.info(f"   {llm_response[:200]}..." if len(llm_response) > 200 else f"   {llm_response}")
            
            # 保存结果
            results.append({
                "test_case": test_case['name'],
                "input": test_case['input'],
                "expected_intent": test_case['expected_intent'],
                "detected_intent": detected_intent,
                "confidence": intent_confidence,
                "user_profile": {
                    "user_id": user_id,
                    "company": company,
                    "age": age,
                    "gender": gender
                },
                "llm_response": llm_response,
                "success": detected_intent == test_case['expected_intent']
            })
            
            logger.info(f"\n✅ 测试用例 {i} 执行完成")
            
        except Exception as e:
            logger.error(f"\n❌ 测试用例 {i} 执行失败: {str(e)}", exc_info=True)
            results.append({
                "test_case": test_case['name'],
                "success": False,
                "error": str(e)
            })
    
    return results


def print_test_summary(results):
    """打印测试总结"""
    logger.info("\n" + "="*60)
    logger.info("测试总结")
    logger.info("="*60)
    
    total = len(results)
    success = sum(1 for r in results if r.get('success', False))
    failed = total - success
    
    logger.info(f"\n📊 测试统计:")
    logger.info(f"   总测试数: {total}")
    logger.info(f"   成功: {success} ✅")
    logger.info(f"   失败: {failed} ❌")
    logger.info(f"   成功率: {(success/total*100):.1f}%")
    
    logger.info(f"\n📋 详细结果:")
    for i, result in enumerate(results, 1):
        status = "✅" if result.get('success', False) else "❌"
        logger.info(f"   {i}. {result['test_case']}: {status}")
        if result.get('success', False):
            logger.info(f"      期望意图: {result['expected_intent']}")
            logger.info(f"      识别意图: {result['detected_intent']} (置信度: {result['confidence']:.2f})")
            logger.info(f"      用户画像: {result['user_profile']}")
        else:
            logger.info(f"      错误: {result.get('error', 'Unknown')}")


async def cleanup_test_session(session_id: str):
    """清理测试会话"""
    logger.info("\n" + "="*60)
    logger.info("步骤 3: 清理测试会话")
    logger.info("="*60)
    
    from app.core.session_token import delete_session
    
    await delete_session(session_id)
    logger.info(f"✅ 测试会话已删除: {session_id}")
    
    # 关闭 Redis 连接
    await redis.close_redis()
    logger.info(f"✅ Redis 连接已关闭")


async def main():
    """主测试函数"""
    logger.info("\n" + "="*60)
    logger.info("🚀 完整工作流测试")
    logger.info("="*60)
    logger.info("\n测试流程:")
    logger.info("  1. 创建测试会话并存储用户画像")
    logger.info("  2. 测试不同意图的完整工作流")
    logger.info("  3. 清理测试数据")
    
    session_id = None
    
    try:
        # 步骤 1: 设置测试会话
        session_id = await setup_test_session()
        
        # 步骤 2: 测试工作流
        results = test_workflow_with_different_intents(session_id)
        
        # 打印总结
        print_test_summary(results)
        
        logger.info("\n✅ 所有测试完成！")
        
    except Exception as e:
        logger.error(f"\n❌ 测试过程中发生错误: {str(e)}", exc_info=True)
    
    finally:
        # 步骤 3: 清理
        if session_id:
            await cleanup_test_session(session_id)


if __name__ == "__main__":
    # 运行测试
    asyncio.run(main())

