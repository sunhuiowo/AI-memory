#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工具函数
"""

import logging
import sys
import signal
from typing import Any, Optional

def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """设置日志配置"""
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('mem0_chat.log', encoding='utf-8')
        ]
    )
    return logging.getLogger(__name__)

def print_banner():
    """打印系统横幅"""
    banner = """
    🧠 记忆增强聊天系统
    ========================================
    功能特点:
    • 基于长期记忆的个性化回复
    • 多轮对话上下文保持  
    • 多用户记忆隔离
    • 自动记忆存储和检索
    • 多代理专家协同：项目大脑 + 专家大脑
    ========================================
    命令说明:
    • 直接输入消息开始聊天
    • 'stats' - 查看对话与上下文统计
    • 'clear' - 清空当前对话历史
    • 'user <用户ID>' - 切换用户
    • 'agent <代理ID>' - 切换任务代理
    • 'agents' - 查看所有可用代理
    • 'session <会话ID>' - 切换或创建新会话
    • 'exit' - 退出系统
    • Ctrl+C - 强制退出
    ========================================
    """
    print(banner)

def setup_signal_handlers():
    """设置信号处理器，确保Ctrl+C可以正常退出"""
    def signal_handler(signum, frame):
        print("\n\n接收到退出信号，正在退出系统...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)

def handle_user_input(prompt: str) -> Optional[str]:
    """处理用户输入，支持中文和Ctrl+C"""
    try:
        user_input = input(prompt).strip()
        return user_input
    except (KeyboardInterrupt, EOFError):
        print("\n\n接收到退出信号，正在退出系统...")
        sys.exit(0)
    except UnicodeDecodeError:
        print("\n❌ 输入编码错误，请重试")
        return None
    except Exception as e:
        logging.error(f"输入处理错误: {e}")
        return None