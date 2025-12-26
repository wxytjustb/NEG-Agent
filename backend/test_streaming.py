#!/usr/bin/env python3
"""测试 LangGraph 流式输出"""
import asyncio
from app.modules.workflow.workflows.workflow import run_chat_workflow_streaming

async def test():
    print("开始测试流式输出...")
    content_chunks = []
    
    async for chunk in run_chat_workflow_streaming(
        user_input='你好',
        session_id='test_session',
        user_id='test_user'
    ):
        content_chunks.append(chunk)
        print(f'收到chunk: [{chunk}]')
    
    print(f'\n总共收到 {len(content_chunks)} 个chunk')
    print(f'完整内容: {"".join(content_chunks)}')

if __name__ == "__main__":
    asyncio.run(test())
