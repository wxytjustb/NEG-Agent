import sys
import os
import asyncio
import time

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from main import app
from app.core.config import settings
import logging

# Configure logging to see startup messages
logging.basicConfig(level=logging.INFO, format='%(message)s')

def test_session_flow():
    """测试完整的会话流程"""
    # 从配置文件读取测试 token
    access_token = settings.TEST_ACCESS_TOKEN
    
    if not access_token:
        print("\n❌ 错误: TEST_ACCESS_TOKEN 未在 .env 文件中配置")
        print("请在 backend/.env 文件中添加:")
        print("TEST_ACCESS_TOKEN=your_token_here")
        return
    
    print(f"\n{'='*60}")
    print("[TEST] 测试两层 Token 认证机制")
    print(f"{'='*60}\n")
    
    with TestClient(app) as client:
        # Step 1: 初始化会话
        print("[Step 1] 使用 access_token 初始化会话...")
        init_response = client.post(
            f"/api/agent/init?access_token={access_token}",
        )
        
        print(f"  状态码: {init_response.status_code}")
        
        if init_response.status_code != 200:
            print(f"  ❌ 会话初始化失败: {init_response.text}")
            return
        
        init_data = init_response.json()
        print(f"  ✅ 会话初始化成功")
        print(f"  响应: {init_data}")
        
        session_token = init_data.get("data", {}).get("session_token")
        if not session_token:
            print("  ❌ 未获取到 session_token")
            return
        
        print(f"  Session Token: {session_token[:30]}...")
        print(f"  过期时间: {init_data.get('data', {}).get('expires_in')} 秒\n")
        
        # Step 2: 使用 session_token 进行对话 (第一次)
        print("[Step 2] 使用 session_token 进行第一次对话...")
        start_time = time.time()
        chat_response1 = client.post(
            f"/api/agent/chat?session_token={session_token}",
            json={
                "messages": [{"role": "user", "content": "hello"}],
                "provider": "ollama"
            }
        )
        duration1 = time.time() - start_time
        
        print(f"  状态码: {chat_response1.status_code}")
        print(f"  耗时: {duration1:.4f}s")
        
        if chat_response1.status_code == 200:
            print("  ✅ 第一次对话成功\n")
        else:
            print(f"  ❌ 第一次对话失败: {chat_response1.text}\n")
            return
        
        # Step 3: 使用相同的 session_token 再次对话 (测试会话刷新)
        print("[Step 3] 使用相同的 session_token 进行第二次对话...")
        start_time = time.time()
        chat_response2 = client.post(
            f"/api/agent/chat?session_token={session_token}",
            json={
                "messages": [{"role": "user", "content": "你好"}],
                "provider": "ollama"
            }
        )
        duration2 = time.time() - start_time
        
        print(f"  状态码: {chat_response2.status_code}")
        print(f"  耗时: {duration2:.4f}s")
        
        if chat_response2.status_code == 200:
            print("  ✅ 第二次对话成功 (会话已刷新)\n")
        else:
            print(f"  ❌ 第二次对话失败: {chat_response2.text}\n")
            return
        
        # Step 4: 使用无效的 session_token (测试验证)
        print("[Step 4] 使用无效的 session_token 测试验证...")
        invalid_token = "sess_invalid_token_12345"
        chat_response3 = client.post(
            f"/api/agent/chat?session_token={invalid_token}",
            json={
                "messages": [{"role": "user", "content": "test"}],
                "provider": "ollama"
            }
        )
        
        print(f"  状态码: {chat_response3.status_code}")
        
        if chat_response3.status_code == 401:
            print("  ✅ 正确拒绝了无效的 session_token\n")
        else:
            print(f"  ❌ 应该返回 401,但返回了 {chat_response3.status_code}\n")
        
        # Step 5: 尝试使用 access_token 直接调用 chat (应该失败)
        print("[Step 5] 尝试使用 access_token 直接调用 /api/agent/chat...")
        chat_response4 = client.post(
            f"/api/agent/chat?access_token={access_token}",
            json={
                "messages": [{"role": "user", "content": "test"}],
                "provider": "ollama"
            }
        )
        
        print(f"  状态码: {chat_response4.status_code}")
        
        if chat_response4.status_code == 401:
            print("  ✅ 正确拒绝了 access_token (需要 session_token)\n")
        else:
            print(f"  ⚠️  返回了 {chat_response4.status_code},可能接受了 access_token\n")
        
        print(f"{'='*60}")
        print("✅ 测试完成!")
        print(f"{'='*60}\n")

if __name__ == "__main__":
    test_session_flow()
