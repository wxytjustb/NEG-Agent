import sys
import os
import asyncio
import time

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from main import app
import logging

# Configure logging to see startup messages
logging.basicConfig(level=logging.INFO, format='%(message)s')

# TestClient with lifespan support (default in newer FastAPI)
# Using 'with TestClient(app) as client:' ensures lifespan events are triggered

def test_redis_caching():
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJJRCI6MzM0LCJPcGVuSUQiOiJvdEdjSTdFQXhsUUJQMWE1WlhLNVJ1cTloQ2UwIiwiQnVmZmVyVGltZSI6ODY0MDAsImlzcyI6InFtUGx1cyIsImF1ZCI6WyJBUFAiXSwiZXhwIjoxNzY0NTk3NTM3LCJuYmYiOjE3NjM5OTI3Mzd9.aOGj3aCwxi7ZvpgSuXxuj-b9eHx4OGnFSV9wqCo-98w"
    
    print(f"\n[TEST] Testing Redis Caching with token: {token[:20]}...")
    
    with TestClient(app) as client:
        # 1. First Request - Should hit upstream (and cache it)
        start_time = time.time()
        response1 = client.post(
            f"/api/agent/chat?access_token={token}",
            json={
                "messages": [{"role": "user", "content": "hello"}],
                "provider": "ollama"
            }
        )
        duration1 = time.time() - start_time
        print(f"Request 1 (Upstream): Status {response1.status_code}, Duration {duration1:.4f}s")
        
        if response1.status_code != 200:
            print("❌ Request 1 failed, cannot proceed with cache test.")
            return

        # 2. Second Request - Should hit Redis cache (faster)
        start_time = time.time()
        response2 = client.post(
            f"/api/agent/chat?access_token={token}",
            json={
                "messages": [{"role": "user", "content": "hello"}],
                "provider": "ollama"
            }
        )
        duration2 = time.time() - start_time
        print(f"Request 2 (Cache):    Status {response2.status_code}, Duration {duration2:.4f}s")

        if response2.status_code == 200:
            print("✅ Request 2 succeeded.")
        else:
            print("❌ Request 2 failed.")

if __name__ == "__main__":
    test_redis_caching()
