# 🧠 mem0 Demo · AI 项目大脑多代理系统

基于 [mem0](https://github.com/mem0ai/mem0) 打造的命令行演示，聚焦“项目大脑 + 专家大脑”的多代理协作。系统会在每轮用户交互前自动拼装：

- 用户长期记忆（mem0 向量库，跨代理共享）
- 各专家大脑的私有记忆与结论
- 近期对话速记、会话状态以及外部提示

从而输出结构化、可执行的项目规划建议。

---

## ✨ 功能亮点

- **AI 项目管理多代理**：项目大脑统筹，产品/算法/解决方案专家协作产出。
- **用户/代理记忆分离**：用户特征只写入用户空间，专家总结写入各自记忆，避免互相污染。
- **上下文编排器**：`ContextOrchestrator` 将记忆、对话摘要、额外上下文拼成稳定的系统提示。
- **可配置 Persona**：`Config.AGENT_PROFILES` 描述角色、风格、关键词、协作链路，可随业务扩展。
- **多会话管理**：`session <id>` 切换不同项目线程，缓存与记忆也随之隔离。
- **友好的 CLI / Web 输出**：CLI 提示 + 响应式 Web 控制台，实时展示摘要、专家反馈与记忆命中。

---

## 🧠 Multi-Agent 项目流

1. **项目大脑** 接收用户输入，生成项目摘要 / 风险 / 需要协调的专家领域。
2. **专家大脑（产品、算法、方案）** 在各自记忆的基础上给出结论、行动项、依赖关系。
3. **项目大脑二次整合**，输出面向用户的最终建议（总体策略、里程碑、角色分工、风险&待澄清问题）。
4. 全流程中，每位代理都会把有价值的信息写回 mem0，便于下次检索。

专家选择采用关键词匹配，可在 `Config.MULTI_AGENT_PIPELINE` 中设置最大专家数与后备列表。

---

## 📦 目录结构

```
core/
  ├─ agent_controller.py   # Multi-Agent 编排（项目大脑 + 专家大脑）
  ├─ chat_engine.py        # 调用 LLM，存储记忆
  ├─ context_engine.py     # 系统提示/上下文构建器
  └─ memory_manager.py     # mem0 封装，支持用户/代理多维记忆
config/settings.py         # 所有配置与 persona 定义
models/data_models.py      # 对话/上下文/多代理数据模型
utils/helpers.py           # CLI 辅助方法（日志、banner、输入处理）
main.py                    # 命令行入口
```

---

## ⚙️ 安装与运行

1. **安装依赖**
   ```bash
   pip install -r requirements.txt  # 或使用 uv / poetry 等工具
   ```
2. **配置 mem0 & LLM**
   - `config/settings.py` 中填入 API Key、LLM 服务、向量库信息。
   - 启动 mem0 所依赖的向量数据库（示例使用 Qdrant）。
3. **启动 CLI**
   ```bash
   python main.py
   ```
4. **启动 Web 控制台（可选）**
   ```bash
   uvicorn web.server:app --reload
   ```
   打开浏览器访问 `http://127.0.0.1:8000`，即可使用动态、可自适应的项目大脑操作台。

---

## 🔧 配置说明（节选）

| 配置项 | 说明 |
| --- | --- |
| `VECTOR_STORE_CONFIG` | mem0 使用的向量库信息（host、collection、embedding 维度等） |
| `EMBEDDER_CONFIG` / `LLM_CONFIG` | 嵌入模型与推理模型连接信息 |
| `CONVERSATION_CACHE_SIZE` | CLI 侧缓存历史的窗口大小 |
| `AGENT_PROFILES` | 描述项目大脑与专家大脑的 persona、风格、关键词、协作链路 |
| `CONTEXT_PIPELINE` | 控制历史窗口、是否生成摘要、协作记忆拼接策略 |
| `MULTI_AGENT_PIPELINE` | 专家选择策略（最大专家数、后备列表等） |
| `ENABLE_MULTI_AGENT` | 是否启用多代理流程（默认开启） |

---

## 🧑‍💼 自定义专家大脑
- **Web 控制台**：`web/server.py` + `templates/index.html`，通过 FastAPI + Jinja + 原生 JS，即时刷新项目摘要、专家列表、记忆命中。

1. 在 `AGENT_PROFILES` 新增角色（如 `biz_owner`、`qa_lead`）。
2. 配置 `type: "specialist"`、`expertise_keywords`、`instructions`。
3. 将 agent id 加入 `project_brain` 的 `collaborators` 或 `MULTI_AGENT_PIPELINE.fallback_specialists`。
4. 重新运行 CLI，项目大脑会自动路由到新的专家并生成记忆。

---

## 🕹️ CLI 命令速查

| 命令 | 作用 |
| --- | --- |
| `<任意文本>` | 触发多代理项目分析流程 |
| `stats` | 查看当前用户缓存、代理、会话信息 |
| `clear` | 清空当前用户的短期缓存 |
| `user <user_id>` | 切换用户记忆空间 |
| `agent <agent_id>` | 覆盖默认项目大脑（调试用） |
| `agents` | 查看所有已配置的代理 persona |
| `session <session_id>` | 切换/创建新会话（将清理缓存） |
| `exit` | 退出程序 |

---

## 🧪 开发 & 调试建议

- **多代理流水线**：可在 `MultiAgentController` 中扩展更复杂的调度（如任务依赖图、LLM 反馈驱动的 agent picking）。
- **记忆落盘**：`MemoryManager` 默认同时写入“用户级记忆 + 指定代理记忆”，如需额外维度可扩展 metadata。
- **提示优化**：`ContextOrchestrator` 支持 `extra_context`，可将项目大脑输出、工单描述等作为附加提示。
- **日志观测**：`mem0_chat.log` 会记录每次记忆读写与 LLM 调用，可据此调优。

---

## 📚 参考

- [mem0 官方仓库](https://github.com/mem0ai/mem0)
- [Qdrant 文档](https://qdrant.tech/documentation/)
- 自行部署的 LLM 服务（示例使用 vLLM HTTP 接口）

欢迎基于此 Demo 扩展属于你的 AI 项目管理助理 🚀
