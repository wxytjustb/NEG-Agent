#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试从 Golang 后端服务获取用户信息
通过提供的 access_token 调用 Golang Server 验证接口
"""

import asyncio
import httpx
import logging
import sys
from pathlib import Path

# 确保从正确的路径导入模块
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.config import settings

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def verify_token_with_go_server(token: str) -> dict:
    """
    向 Golang Server 验证 Token 并获取用户信息
    
    Args:
        token: 用户的 access_token
        
    Returns:
        用户信息字典
        
    Raises:
        Exception: 验证失败时抛出异常
    """
    if not token:
        raise ValueError("Token 不能为空")
    
    # 构建验证 URL
    verify_url = f"{settings.GOLANG_API_BASE_URL}{settings.GOLANG_VERIFY_ENDPOINT}"
    
    logger.info("="*60)
    logger.info("开始验证 Token...")
    logger.info(f"验证 URL: {verify_url}")
    logger.info(f"Token 前10位: {token[:10]}...")
    
    try:
        async with httpx.AsyncClient() as client:
            payload = {"token": token}
            
            # 发送 POST 请求
            response = await client.post(verify_url, json=payload, timeout=10.0)
            
            logger.info(f"响应状态码: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"Golang server 返回错误状态码 {response.status_code}")
                logger.error(f"响应内容: {response.text}")
                raise Exception(f"Token 验证失败，状态码: {response.status_code}")
            
            # 解析响应
            resp_data = response.json()
            logger.info(f"响应数据: {resp_data}")
            
            # 检查响应码（兼容 code=0 或 code=200）
            code = resp_data.get("code")
            if code != 200 and code != 0:
                logger.error(f"验证失败: {resp_data}")
                raise Exception(f"Token 验证失败: {resp_data.get('msg', 'Unknown error')}")
            
            # 获取用户数据
            user_data = resp_data.get("data", {})
            
            # 检查 isValid 字段
            is_valid = user_data.get("isValid", False)
            if not is_valid:
                logger.error(f"Token 无效: {resp_data}")
                raise Exception(f"Token 无效或已过期: {resp_data.get('msg', 'Token invalid')}")
            
            logger.info("✅ Token 验证成功！")
            logger.info("="*60)
            return user_data
            
    except httpx.RequestError as e:
        logger.error(f"❌ 连接 Golang server 失败: {str(e)}")
        raise Exception(f"无法连接到认证服务: {str(e)}")


def print_user_info(user_data: dict):
    """格式化打印用户信息"""
    logger.info("\n" + "="*60)
    logger.info("📋 用户信息详情")
    logger.info("="*60)
    
    # 常见字段
    fields_to_display = [
        ("用户ID", "appUserId", "id", "userId", "user_id"),
        ("用户名", "username", "userName", "name"),
        ("邮箱", "email"),
        ("手机号", "phone", "mobile"),
        ("昵称", "nickname", "nickName"),
        ("头像", "avatar"),
        ("性别", "gender", "sex"),
        ("年龄", "age"),
        ("公司", "company", "organization"),
        ("是否有效", "isValid"),
        ("创建时间", "createdAt", "createTime", "created_at"),
        ("更新时间", "updatedAt", "updateTime", "updated_at"),
    ]
    
    for label, *keys in fields_to_display:
        for key in keys:
            if key in user_data:
                value = user_data[key]
                logger.info(f"{label:12s}: {value}")
                break
    
    # 显示所有其他字段
    displayed_keys = set()
    for _, *keys in fields_to_display:
        displayed_keys.update(keys)
    
    other_fields = {k: v for k, v in user_data.items() if k not in displayed_keys}
    if other_fields:
        logger.info("\n" + "-"*60)
        logger.info("其他字段:")
        logger.info("-"*60)
        for key, value in other_fields.items():
            logger.info(f"{key:20s}: {value}")
    
    logger.info("="*60 + "\n")


async def test_with_token(token: str):
    """测试指定 Token 的验证流程"""
    try:
        # 验证 Token 并获取用户信息
        user_data = await verify_token_with_go_server(token)
        
        # 打印用户信息
        print_user_info(user_data)
        
        return user_data
        
    except Exception as e:
        logger.error(f"❌ 测试失败: {str(e)}")
        return None


async def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("🚀 Golang 用户信息获取测试")
    print("="*60 + "\n")
    
    # 方式1: 从配置文件读取测试 Token
    if settings.TEST_ACCESS_TOKEN:
        logger.info("📌 使用配置文件中的 TEST_ACCESS_TOKEN")
        token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJJRCI6MzM0LCJPcGVuSUQiOiJvdEdjSTdFQXhsUUJQMWE1WlhLNVJ1cTloQ2UwIiwiQnVmZmVyVGltZSI6ODY0MDAsImlzcyI6InFtUGx1cyIsImF1ZCI6WyJBUFAiXSwiZXhwIjoxNzk4MDEwMDA5LCJuYmYiOjE3NjY0NzQwMDl9.t2psDpTgdk3x9XOIv3l4HJAkNEx4ycY8hylUqa6gf1U"
    else:
        # 方式2: 手动输入 Token
        logger.info("📌 请输入您的 access_token:")
        logger.info("（提示：可以在 .env 文件中配置 TEST_ACCESS_TOKEN 避免每次输入）\n")
        token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJJRCI6MzM0LCJPcGVuSUQiOiJvdEdjSTdFQXhsUUJQMWE1WlhLNVJ1cTloQ2UwIiwiQnVmZmVyVGltZSI6ODY0MDAsImlzcyI6InFtUGx1cyIsImF1ZCI6WyJBUFAiXSwiZXhwIjoxNzk4MDEwMDA5LCJuYmYiOjE3NjY0NzQwMDl9.t2psDpTgdk3x9XOIv3l4HJAkNEx4ycY8hylUqa6gf1U"
    
    if not token:
        logger.error("❌ Token 不能为空！")
        return
    
    # 执行测试
    user_data = await test_with_token(token)
    
    if user_data:
        logger.info("✅ 测试完成！用户信息获取成功！")
    else:
        logger.error("❌ 测试失败！")


if __name__ == "__main__":
    # 运行测试
    asyncio.run(main())
