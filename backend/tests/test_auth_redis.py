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

def test_golang_token_verification():
    """测试 FastAPI Server 向 Golang Server 验证 Token"""
    # 从配置文件读取测试 token
    access_token = settings.TEST_ACCESS_TOKEN
    
    if not access_token:
        print("\n❌ 错误: TEST_ACCESS_TOKEN 未在 .env 文件中配置")
        print("请在 backend/.env 文件中添加:")
        print("TEST_ACCESS_TOKEN=your_token_here")
        return
    
    print(f"\n{'='*60}")
    print("[TEST] 测试 FastAPI Server 向 Golang Server 验证 Token")
    print(f"{'='*60}\n")
    
    with TestClient(app) as client:
        # Test 1: 使用有效的 access_token 调用 /api/agent/init
        print("[Test 1] 使用有效的 access_token 验证...")
        print(f"  Token: {access_token[:30]}...")
        
        start_time = time.time()
        response = client.post(
            f"/api/agent/init?access_token={access_token}",
        )
        duration = time.time() - start_time
        
        print(f"  状态码: {response.status_code}")
        print(f"  耗时: {duration:.4f}s")
        
        if response.status_code == 200:
            data = response.json()
            print(f"  ✅ Token 验证成功")
            print(f"  用户信息: {data.get('data', {}).get('user', {})}")
            print(f"  Session Token: {data.get('data', {}).get('session_token', '')[:30]}...\n")
        else:
            print(f"  ❌ Token 验证失败: {response.text}\n")
            return


if __name__ == "__main__":
    test_golang_token_verification()
