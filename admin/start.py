#!/usr/bin/env python
"""Django 服务启动脚本 - 从环境变量读取配置"""
import os
import sys
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

if __name__ == '__main__':
    # 设置 Django settings 模块
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'admin.settings')
    
    # 获取服务器配置
    host = os.getenv('SERVER_HOST', '0.0.0.0')
    port = os.getenv('SERVER_PORT', '8000')
    
    # 构建 runserver 命令参数
    sys.argv = ['manage.py', 'runserver', f'{host}:{port}']
    
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    
    print(f"启动 Django 服务器: http://{host}:{port}/")
    execute_from_command_line(sys.argv)
