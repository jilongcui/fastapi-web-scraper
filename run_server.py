#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
优雅停止程序的示例启动脚本
Usage: python run_server.py
停止: 使用 Ctrl+C
"""

import asyncio
import signal
import sys
import os

# 添加应用路径到系统路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.main import app
import uvicorn


def main():
    """主函数：启动服务器并处理优雅停止"""
    
    print("=" * 50)
    print("FastAPI Web Scraper Server")  
    print("=" * 50)
    print("启动服务器... 使用 Ctrl+C 来停止")
    print("服务器地址: http://localhost:8000")
    print("API文档: http://localhost:8000/docs")
    print("=" * 50)
    
    # 配置服务器
    config = uvicorn.Config(
        app=app,
        host="0.0.0.0",
        port=8000,
        reload=False,  # 禁用热重载以支持信号处理
        access_log=True,
        log_level="info"
    )
    
    server = uvicorn.Server(config)
    
    def signal_handler(signum, frame):
        """信号处理函数"""
        print(f"\n收到信号 {signum}，正在优雅停止服务器...")
        asyncio.create_task(server.shutdown())
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # 终止信号
    
    try:
        # 启动服务器
        asyncio.run(server.serve())
    except KeyboardInterrupt:
        print("\n收到键盘中断信号，正在停止...")
    except Exception as e:
        print(f"服务器运行出错: {e}")
    finally:
        print("服务器已完全停止")


if __name__ == "__main__":
    main()