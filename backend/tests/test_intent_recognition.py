#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
意图识别测试脚本 - 测试 Transformer 零样本分类模型

使用方法：
    python test_intent_recognition.py
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.modules.workflow.nodes.Intent_recognition import detect_intent, get_all_intents, preload_classifier
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_intent_recognition():
    """测试意图识别功能"""
    
    print("\n" + "="*70)
    print("🧪 意图识别测试脚本")
    print("="*70 + "\n")
    
    # 显示所有意图标签
    all_intents = get_all_intents()
    print(f"📋 支持的意图标签: {', '.join(all_intents)}\n")
    
    # 预加载模型（可选，但建议）
    print("⏳ 正在加载模型（首次运行会下载约 600MB 文件）...\n")
    try:
        preload_classifier()
        print("✅ 模型加载成功！\n")
    except Exception as e:
        print(f"❌ 模型加载失败: {e}\n")
        print("💡 提示：请确保已安装依赖：pip install transformers torch\n")
        return
    
    # 测试用例
    test_cases = [
        # 法律咨询类
        "我想咨询一下劳动仲裁怎么申请",
        "公司拖欠我三个月工资了",
        "老板违法解雇我，我能维权吗",
        "加班费不给结算怎么办",
        "在工作中受伤了，能申请工伤赔偿吗",
        
        # 情感倾诉类
        "今天被差评了，心里很难受",
        "我感觉压力好大，快承受不住了",
        "每天这么累，真的想放弃了",
        "没人理解我，我好孤单",
        "老板总是针对我，我很委屈",
        
        # 日常对话类
        "今天天气怎么样",
        "你好啊",
        "晚上吃什么",
        "下班了吗",
        "今天跑了多少单",
    ]
    
    print("-" * 70)
    print("开始测试...\n")
    print("-" * 70 + "\n")
    
    success_count = 0
    total_count = len(test_cases)
    
    for idx, test_input in enumerate(test_cases, 1):
        try:
            intent, confidence, scores = detect_intent(test_input)
            
            print(f"测试 {idx}/{total_count}:")
            print(f"  输入: {test_input}")
            print(f"  识别结果: {intent}")
            print(f"  置信度: {confidence:.2%}")
            
            # 显示所有意图的得分
            print(f"  所有得分:")
            for label, score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
                print(f"    - {label}: {score:.2%}")
            
            print()
            success_count += 1
            
        except Exception as e:
            print(f"❌ 测试 {idx} 失败: {e}\n")
    
    print("-" * 70)
    print(f"\n✅ 测试完成: {success_count}/{total_count} 成功")
    print("="*70 + "\n")


def test_custom_input():
    """交互式测试 - 用户自定义输入"""
    
    print("\n" + "="*70)
    print("🎯 交互式意图识别测试")
    print("="*70 + "\n")
    
    print("💡 输入 'exit' 或 'quit' 退出\n")
    
    try:
        preload_classifier()
    except Exception as e:
        print(f"❌ 模型加载失败: {e}")
        return
    
    while True:
        try:
            user_input = input("\n请输入测试文本: ").strip()
            
            if user_input.lower() in ['exit', 'quit', 'q', '退出']:
                print("\n👋 再见！\n")
                break
            
            if not user_input:
                print("⚠️ 输入不能为空")
                continue
            
            intent, confidence, scores = detect_intent(user_input)
            
            print(f"\n📊 识别结果:")
            print(f"  意图: {intent}")
            print(f"  置信度: {confidence:.2%}")
            print(f"\n  详细得分:")
            for label, score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
                bar = "█" * int(score * 20)
                print(f"    {label:8s} {score:.2%} {bar}")
            
        except KeyboardInterrupt:
            print("\n\n👋 再见！\n")
            break
        except Exception as e:
            print(f"\n❌ 错误: {e}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="意图识别测试脚本")
    parser.add_argument(
        "--mode",
        choices=["auto", "interactive"],
        default="auto",
        help="测试模式：auto=自动测试，interactive=交互式测试"
    )
    
    args = parser.parse_args()
    
    if args.mode == "auto":
        test_intent_recognition()
    else:
        test_custom_input()
