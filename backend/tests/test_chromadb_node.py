#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ChromaDB 节点功能测试
测试获取记忆和保存记忆的完整流程
"""

import sys
from pathlib import Path

# 确保从正确的路径导入模块
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.modules.workflow.nodes.chromadb_node import (
    get_memory_node,
    save_memory_node,
    get_all_messages_node
)
from app.initialize.chromadb import init_chromadb
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_save_and_get_memory():
    """
    测试保存和获取记忆的完整流程
    """
    logger.info("\n" + "="*60)
    logger.info("🧪 ChromaDB 节点功能测试")
    logger.info("="*60)
    
    # 初始化 ChromaDB
    logger.info("\n步骤 1: 初始化 ChromaDB")
    init_chromadb()
    logger.info("✅ ChromaDB 初始化成功")
    
    # 测试用户和会话信息
    test_user_id = "test_user_123"
    test_session_id = "test_session_456"
    
    # ========== 测试 1: 保存记忆 ==========
    logger.info("\n" + "="*60)
    logger.info("测试 1: 保存对话记忆到 ChromaDB")
    logger.info("="*60)
    
    # 模拟第一轮对话
    state_round1 = {
        "user_id": test_user_id,
        "session_id": test_session_id,
        "user_input": "我今天被差评了，公司要扣我钱，心里很委屈",
        "llm_response": "听得出来你现在既愤怒又无奈，明明不是你的错却要承担损失，真的太委屈了。法律上讲，你有权通过平台申诉通道提交证据进行申辩。"
    }
    
    logger.info("💬 第一轮对话:")
    logger.info(f"  用户: {state_round1['user_input']}")
    logger.info(f"  助手: {state_round1['llm_response'][:50]}...")
    
    result1 = save_memory_node(state_round1)
    
    if result1.get("memory_saved"):
        logger.info(f"✅ 第一轮对话已保存")
        logger.info(f"  保存的消息ID: {result1.get('saved_message_ids')}")
    else:
        logger.error("❌ 第一轮对话保存失败")
        return
    
    # 模拟第二轮对话
    state_round2 = {
        "user_id": test_user_id,
        "session_id": test_session_id,
        "user_input": "我应该怎么申诉？需要准备什么证据？",
        "llm_response": "申诉时建议准备：1. 配送时的GPS轨迹截图 2. 与客户的沟通记录 3. 送达时的照片。登录骑手端APP，找到该订单，点击申诉按钮。"
    }
    
    logger.info("\n💬 第二轮对话:")
    logger.info(f"  用户: {state_round2['user_input']}")
    logger.info(f"  助手: {state_round2['llm_response'][:50]}...")
    
    result2 = save_memory_node(state_round2)
    
    if result2.get("memory_saved"):
        logger.info(f"✅ 第二轮对话已保存")
        logger.info(f"  保存的消息ID: {result2.get('saved_message_ids')}")
    else:
        logger.error("❌ 第二轮对话保存失败")
        return
    
    # ========== 测试 2: 获取相关记忆（语义搜索）==========
    logger.info("\n" + "="*60)
    logger.info("测试 2: 基于语义搜索获取相关记忆")
    logger.info("="*60)
    
    # 测试查询 1: 与差评相关的问题
    query_state1 = {
        "user_id": test_user_id,
        "session_id": test_session_id,
        "user_input": "上次那个差评的事情怎么处理？"
    }
    
    logger.info(f"\n🔍 查询 1: {query_state1['user_input']}")
    memory_result1 = get_memory_node(query_state1)
    
    if memory_result1.get("memory_count", 0) > 0:
        logger.info(f"✅ 检索到 {memory_result1['memory_count']} 条相关记忆")
        logger.info("📚 相关记忆内容:")
        for line in memory_result1.get("history_text", "").split("\n"):
            logger.info(f"  - {line[:80]}...")
    else:
        logger.warning("⚠️ 未检索到相关记忆")
    
    # 测试查询 2: 与申诉相关的问题
    query_state2 = {
        "user_id": test_user_id,
        "session_id": test_session_id,
        "user_input": "申诉需要什么材料？"
    }
    
    logger.info(f"\n🔍 查询 2: {query_state2['user_input']}")
    memory_result2 = get_memory_node(query_state2)
    
    if memory_result2.get("memory_count", 0) > 0:
        logger.info(f"✅ 检索到 {memory_result2['memory_count']} 条相关记忆")
        logger.info("📚 相关记忆内容:")
        for line in memory_result2.get("history_text", "").split("\n"):
            logger.info(f"  - {line[:80]}...")
    else:
        logger.warning("⚠️ 未检索到相关记忆")
    
    # ========== 测试 3: 获取所有历史消息 ==========
    logger.info("\n" + "="*60)
    logger.info("测试 3: 获取所有历史消息（按时间顺序）")
    logger.info("="*60)
    
    all_messages_state = {
        "user_id": test_user_id,
        "session_id": test_session_id
    }
    
    all_messages_result = get_all_messages_node(all_messages_state)
    
    if all_messages_result.get("message_count", 0) > 0:
        logger.info(f"✅ 获取到 {all_messages_result['message_count']} 条历史消息")
        logger.info("📚 完整对话历史:")
        for i, msg in enumerate(all_messages_result.get("messages", []), 1):
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            timestamp = msg.get("timestamp", "")[:19]
            logger.info(f"  [{i}] {timestamp} - {role}: {content[:60]}...")
    else:
        logger.warning("⚠️ 未获取到历史消息")
    
    # ========== 测试总结 ==========
    logger.info("\n" + "="*60)
    logger.info("✅ 所有测试完成！")
    logger.info("="*60)
    logger.info("\n📊 测试结果汇总:")
    logger.info(f"  - 保存对话轮数: 2")
    logger.info(f"  - 第一轮保存状态: {'成功' if result1.get('memory_saved') else '失败'}")
    logger.info(f"  - 第二轮保存状态: {'成功' if result2.get('memory_saved') else '失败'}")
    logger.info(f"  - 语义搜索 1 结果数: {memory_result1.get('memory_count', 0)}")
    logger.info(f"  - 语义搜索 2 结果数: {memory_result2.get('memory_count', 0)}")
    logger.info(f"  - 历史消息总数: {all_messages_result.get('message_count', 0)}")
    
    logger.info("\n💡 提示: 可以通过以下方式集成到工作流中:")
    logger.info("  1. 在对话开始前调用 get_memory_node 获取相关记忆")
    logger.info("  2. 在对话结束后调用 save_memory_node 保存本轮对话")
    logger.info("  3. 使用 get_all_messages_node 获取完整对话历史")


if __name__ == "__main__":
    test_save_and_get_memory()
