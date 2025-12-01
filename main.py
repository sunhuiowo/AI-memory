#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主程序入口
"""
# pylint: disable=broad-except

import sys

from config.settings import Config
from core.memory_manager import MemoryManager
from core.chat_engine import ChatEngine
from core.agent_controller import MultiAgentController
from models.data_models import MultiAgentResult
from utils.helpers import setup_logging, print_banner, handle_user_input, setup_signal_handlers

logger = setup_logging()

class ChatApplication:
    """聊天应用程序"""
    
    def __init__(self):
        try:
            self.memory_manager = MemoryManager()
            self.chat_engine = ChatEngine(self.memory_manager)
            self.current_user = Config.DEFAULT_USER_ID
            self.current_agent = Config.DEFAULT_AGENT_ID
            self.current_session = Config.DEFAULT_SESSION_ID
            self.multi_agent_enabled = Config.ENABLE_MULTI_AGENT
            self.agent_controller = (
                MultiAgentController(self.chat_engine)
                if self.multi_agent_enabled else None
            )
            logger.info("聊天应用程序初始化完成")
        except Exception as exc:  # noqa: BLE001
            logger.critical("应用程序初始化失败: %s", exc)
            print("❌ 系统启动失败，请检查配置")
            sys.exit(1)
    
    def run(self):
        """运行主循环"""
        print_banner()
        setup_signal_handlers()
        
        print("系统已就绪，请输入命令或消息...")
        
        while True:
            try:
                # 获取用户输入
                prompt = f"\n👤 用户[{self.current_user}]｜代理[{self.current_agent}]> "
                user_input = handle_user_input(prompt)
                
                if user_input is None:
                    continue
                
                # 处理命令
                if self._handle_commands(user_input):
                    if user_input.lower() == 'exit':
                        break
                    continue
                
                # 处理聊天
                self._handle_chat(user_input)
                
            except SystemExit:
                # 正常退出
                break
            except Exception as exc:  # noqa: BLE001
                logger.error("主循环错误: %s", exc)
                print("❌ 系统出现错误，请重试")
    
    def _handle_commands(self, user_input: str) -> bool:
        """处理特殊命令，返回是否已处理"""
        if not user_input:
            return True
            
        user_input_lower = user_input.lower()
        
        if user_input_lower == 'exit':
            self._handle_exit()
            return True
            
        elif user_input_lower == 'stats':
            self._show_stats()
            return True
            
        elif user_input_lower == 'clear':
            self._clear_history()
            return True
        
        elif user_input_lower == 'agents':
            self._list_agents()
            return True
            
        elif user_input.startswith('user '):
            self._switch_user(user_input)
            return True
        
        elif user_input.startswith('agent '):
            self._switch_agent(user_input)
            return True
        
        elif user_input.startswith('session '):
            self._switch_session(user_input)
            return True
            
        return False
    
    def _handle_chat(self, message: str):
        """处理聊天消息"""
        if not message.strip():
            return
            
        print("🤔 思考中...", end="", flush=True)
        
        try:
            multi_agent_details = None
            if self.multi_agent_enabled and self.agent_controller:
                ma_result = self.agent_controller.process_user_message(
                    message,
                    self.current_user,
                    self.current_session
                )
                response = ma_result.final_response
                multi_agent_details = ma_result
            else:
                response = self.chat_engine.generate_response(
                    message,
                    self.current_user,
                    self.current_agent,
                    self.current_session
                )
            
            print("\r" + " " * 20 + "\r", end="")  # 清除"思考中"提示
            
            if response.error:
                print(f"❌ 错误: {response.content}")
            else:
                if multi_agent_details:
                    self._print_multi_agent_details(multi_agent_details)
                print(f"🤖 助手: {response.content}")
                
                # 显示记忆使用信息
                if response.memory_used:
                    print(f"💡 参考了 {response.memories_count} 条记忆（协作代理: {', '.join(response.collaborators) or '无'}）")
                    
        except Exception as exc:  # noqa: BLE001
            print("\r" + " " * 20 + "\r", end="")  # 清除"思考中"提示
            print(f"❌ 生成回复时出错: {exc}")
    
    def _show_stats(self):
        """显示统计信息"""
        try:
            stats = self.chat_engine.get_conversation_stats(self.current_user)
            print("📊 对话统计:")
            print(f"  用户ID: {stats['user_id']}")
            print(f"  缓存对话数: {stats['cached_conversations']}/{stats['cache_max_size']}")
            print(f"  当前代理: {self.current_agent}")
            print(f"  当前会话: {self.current_session}")
        except Exception as exc:  # noqa: BLE001
            print(f"❌ 获取统计信息失败: {exc}")
    
    def _clear_history(self):
        """清空对话历史"""
        try:
            self.chat_engine.clear_conversation_cache(self.current_user)
            print("✅ 对话历史已清空")
        except Exception as exc:  # noqa: BLE001
            print(f"❌ 清空历史失败: {exc}")
    
    def _switch_user(self, user_input: str):
        """切换用户"""
        try:
            new_user = user_input[5:].strip()
            if new_user:
                self.current_user = new_user
                print(f"✅ 已切换到用户: {self.current_user}")
            else:
                print("❌ 请输入有效的用户ID")
        except Exception as exc:  # noqa: BLE001
            print(f"❌ 切换用户失败: {exc}")
    
    def _switch_agent(self, user_input: str):
        """切换当前代理"""
        try:
            new_agent = user_input[6:].strip()
            if new_agent in Config.AGENT_PROFILES:
                self.current_agent = new_agent
                print(f"✅ 已切换到代理: {self.current_agent}")
            else:
                print("❌ 未找到该代理，请先使用 'agents' 查看列表")
        except Exception as exc:  # noqa: BLE001
            print(f"❌ 切换代理失败: {exc}")
    
    def _switch_session(self, user_input: str):
        """切换会话ID，便于隔离任务上下文"""
        try:
            new_session = user_input[8:].strip()
            if new_session:
                self.current_session = new_session
                self.chat_engine.clear_conversation_cache(self.current_user)
                print(f"✅ 已切换到会话: {self.current_session}（历史缓存已清理）")
            else:
                print("❌ 请输入有效的会话ID")
        except Exception as exc:  # noqa: BLE001
            print(f"❌ 切换会话失败: {exc}")
    
    def _list_agents(self):
        """列出可用代理，展示各自擅长领域"""
        print("🧑‍🤝‍🧑 可用代理列表：")
        for agent_id, profile in Config.AGENT_PROFILES.items():
            collaborators = ", ".join(profile.get("collaborators", [])) or "无"
            print(f"- {agent_id}: {profile.get('description', '')}")
            print(f"  协作代理: {collaborators}")
            print(f"  表达风格: {profile.get('style', '未设置')}")
    
    def _print_multi_agent_details(self, ma_result: MultiAgentResult):
        """输出项目大脑与专家大脑的协作过程。"""
        print("🧠 项目大脑摘要:")
        print(f"  {ma_result.project_summary}")
        if ma_result.specialist_outputs:
            print("👥 专家大脑反馈:")
            for specialist in ma_result.specialist_outputs:
                profile = Config.AGENT_PROFILES.get(specialist.agent_id, {})
                name = profile.get("name", specialist.agent_id)
                print(f"  - {name}: {specialist.content}")
    
    def _handle_exit(self):
        """处理退出"""
        print("感谢使用，再见！👋")
        logger.info("用户退出系统")

def main():
    """主函数"""
    try:
        app = ChatApplication()
        app.run()
    except SystemExit:
        # 正常退出
        pass
    except Exception as exc:  # noqa: BLE001
        logger.critical("应用程序启动失败: %s", exc)
        print("❌ 系统启动失败，请检查配置")
        return 1
    
    print("系统已安全退出")
    return 0

if __name__ == "__main__":
    exit(main())