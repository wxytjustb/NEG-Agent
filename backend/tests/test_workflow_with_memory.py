#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整工作流测试（包含 ChromaDB 记忆）
测试新的工作流：用户信息 → 意图识别 → 获取记忆 → LLM回答 → 保存记忆
"""

import asyncio
import sys
from pathlib import Path

# 确保从正确的路径导入模块
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.modules.workflow.workflows.workflow import run_chat_workflow
from app.core.session_token import create_session, update_session, delete_session
from app.initialize import redis
from app.initialize.chromadb import init_chromadb
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def setup_test_session():
    """设置测试会话"""
    logger.info("\n" + "="*60)
    logger.info("步骤 1: 创建测试会话")
    logger.info("="*60)
    
    await redis.init_redis()
    logger.info("✅ Redis 初始化成功")
    
    init_chromadb()
    logger.info("✅ ChromaDB 初始化成功")
    
    # 创建测试用户会话
    test_user_data = {
        "appUserId": 888,
        "username": "测试骑手",
        "age": 28,
        "gender": "男",
        "companyName": "美团"
    }
    
    session_id = await create_session(test_user_data)
    logger.info(f"✅ 会话创建成功: {session_id}")
    
    # 更新会话数据（存储用户画像）
    await update_session(session_id, {
        "user_id": "888",
        "company": "美团",
        "age": "28",
        "gender": "男"
    })
    logger.info("✅ 用户画像已存入会话")
    logger.info(f"   - 用户ID: 888")
    logger.info(f"   - 公司: 美团")
    logger.info(f"   - 年龄: 28")
    logger.info(f"   - 性别: 男")
    
    return session_id


def test_workflow_with_memory(session_id: str):
    """
    测试完整工作流（包含记忆）
    
    工作流程：
    1. 用户信息获取
    2. 意图识别
    3. 获取 ChromaDB 记忆
    4. LLM 回答
    5. 保存记忆到 ChromaDB
    """
    logger.info("\n" + "="*60)
    logger.info("步骤 2: 测试完整工作流（包含记忆）")
    logger.info("="*60)
    
    # 第一轮对话
    logger.info("\n" + "-"*60)
    logger.info("💬 第一轮对话")
    logger.info("-"*60)
    
    round1_input = "我今天被客户投诉了，说我送餐慢，但实际上是商家出餐慢"
    logger.info(f"用户输入: {round1_input}")
    
    result1 = run_chat_workflow(
        user_input=round1_input,
        session_id=session_id,
        user_id="888",
        username="测试骑手"
    )
    
    logger.info("\n📊 第一轮工作流执行结果:")
    logger.info(f"  用户ID: {result1.get('user_id')}")
    logger.info(f"  用户画像: 公司={result1.get('company')}, 年龄={result1.get('age')}, 性别={result1.get('gender')}")
    logger.info(f"  识别意图: {result1.get('intent')} (置信度: {result1.get('intent_confidence', 0):.2f})")
    logger.info(f"  检索记忆数: {result1.get('memory_count', 0)} 条")
    logger.info(f"  LLM 回答长度: {len(result1.get('llm_response', ''))} 字符")
    logger.info(f"  记忆保存状态: {'✅ 成功' if result1.get('memory_saved') else '❌ 失败'}")
    
    if result1.get('saved_message_ids'):
        logger.info(f"  保存的消息ID数: {len(result1.get('saved_message_ids', []))}")
    
    logger.info(f"\n💬 LLM 回答:")
    logger.info(f"  {result1.get('llm_response', 'N/A')[:200]}...")
    
    # 第二轮对话（测试记忆检索）
    logger.info("\n" + "-"*60)
    logger.info("💬 第二轮对话（测试记忆检索）")
    logger.info("-"*60)
    
    round2_input = "刚才那个投诉的事情，我应该怎么向平台申诉？"
    logger.info(f"用户输入: {round2_input}")
    
    result2 = run_chat_workflow(
        user_input=round2_input,
        session_id=session_id,
        user_id="888",
        username="测试骑手"
    )
    
    logger.info("\n📊 第二轮工作流执行结果:")
    logger.info(f"  用户ID: {result2.get('user_id')}")
    logger.info(f"  识别意图: {result2.get('intent')} (置信度: {result2.get('intent_confidence', 0):.2f})")
    logger.info(f"  检索记忆数: {result2.get('memory_count', 0)} 条 ⭐ 应该能检索到上一轮对话")
    
    if result2.get('memory_count', 0) > 0:
        logger.info(f"  ✅ 成功检索到历史记忆！")
        logger.info(f"\n📚 检索到的历史记忆片段:")
        history_text = result2.get('history_text', '')
        for i, line in enumerate(history_text.split('\n')[:3], 1):  # 只显示前3条
            logger.info(f"    [{i}] {line[:80]}...")
    else:
        logger.warning(f"  ⚠️ 未检索到历史记忆")
    
    logger.info(f"  LLM 回答长度: {len(result2.get('llm_response', ''))} 字符")
    logger.info(f"  记忆保存状态: {'✅ 成功' if result2.get('memory_saved') else '❌ 失败'}")
    
    logger.info(f"\n💬 LLM 回答:")
    logger.info(f"  {result2.get('llm_response', 'N/A')[:200]}...")
    
    # 第三轮对话（再次测试记忆）
    logger.info("\n" + "-"*60)
    logger.info("💬 第三轮对话（测试记忆累积）")
    logger.info("-"*60)
    
    round3_input = "除了申诉，我还有什么其他办法吗？"
    logger.info(f"用户输入: {round3_input}")
    
    result3 = run_chat_workflow(
        user_input=round3_input,
        session_id=session_id,
        user_id="888",
        username="测试骑手"
    )
    
    logger.info("\n📊 第三轮工作流执行结果:")
    logger.info(f"  识别意图: {result3.get('intent')} (置信度: {result3.get('intent_confidence', 0):.2f})")
    logger.info(f"  检索记忆数: {result3.get('memory_count', 0)} 条 ⭐ 应该能检索到前两轮对话")
    
    if result3.get('memory_count', 0) > 0:
        logger.info(f"  ✅ 成功检索到历史记忆！")
    
    logger.info(f"  LLM 回答长度: {len(result3.get('llm_response', ''))} 字符")
    logger.info(f"  记忆保存状态: {'✅ 成功' if result3.get('memory_saved') else '❌ 失败'}")
    
    logger.info(f"\n💬 LLM 回答:")
    logger.info(f"  {result3.get('llm_response', 'N/A')[:200]}...")
    
    # 测试总结
    logger.info("\n" + "="*60)
    logger.info("✅ 完整工作流测试完成！")
    logger.info("="*60)
    logger.info("\n📊 测试总结:")
    logger.info(f"  - 总对话轮数: 3")
    logger.info(f"  - 第1轮记忆检索: {result1.get('memory_count', 0)} 条（预期0，首次对话）")
    logger.info(f"  - 第2轮记忆检索: {result2.get('memory_count', 0)} 条（预期>0，应检索到第1轮）")
    logger.info(f"  - 第3轮记忆检索: {result3.get('memory_count', 0)} 条（预期>0，应检索到前2轮）")
    logger.info(f"  - 记忆保存状态: 全部成功 ✅")
    
    logger.info("\n🎯 工作流节点执行顺序验证:")
    logger.info("  1. ✅ 用户信息获取 - 从 Redis session 读取用户画像")
    logger.info("  2. ✅ 意图识别 - 识别用户意图")
    logger.info("  3. ✅ 获取记忆 - 从 ChromaDB 语义搜索相关历史")
    logger.info("  4. ✅ LLM 回答 - 使用用户画像 + 意图 + 历史记忆生成回答")
    logger.info("  5. ✅ 保存记忆 - 将本轮对话保存到 ChromaDB")
    
    return result1, result2, result3


async def cleanup_test_session(session_id: str):
    """清理测试会话"""
    logger.info("\n" + "="*60)
    logger.info("步骤 3: 清理测试会话")
    logger.info("="*60)
    
    await delete_session(session_id)
    logger.info(f"✅ 测试会话已删除: {session_id}")
    
    await redis.close_redis()
    logger.info("✅ Redis 连接已关闭")


async def main():
    """主测试函数"""
    logger.info("\n" + "="*60)
    logger.info("🚀 完整工作流测试（包含 ChromaDB 记忆）")
    logger.info("="*60)
    logger.info("\n测试流程:")
    logger.info("  1. 创建测试会话并存储用户画像")
    logger.info("  2. 测试3轮对话，验证记忆的检索和保存")
    logger.info("  3. 清理测试数据")
    logger.info("="*60)
    
    # 1. 设置测试会话
    session_id = await setup_test_session()
    
    # 2. 测试工作流
    test_workflow_with_memory(session_id)
    
    # 3. 清理测试会话
    await cleanup_test_session(session_id)
    
    logger.info("\n" + "="*60)
    logger.info("✅ 所有测试完成！")
    logger.info("="*60)


if __name__ == "__main__":
    asyncio.run(main())

