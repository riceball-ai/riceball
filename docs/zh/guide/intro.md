# 介绍

## 🍚 RiceBall 是什么？

RiceBall 是一个开源的、全栈式的 **AI 智能体与知识库平台**。它旨在帮助团队和企业在私有环境中快速构建和部署基于大语言模型（LLM）的智能应用。

核心能力：

- **🔐 私有化 RAG 知识库**：
  - 安全上传文档（PDF, DOCX, XLSX, PPTX, Markdown）。
  - 基于 **ChromaDB** 自动进行切片和向量化。
  - 支持引用追踪。
- **🤖 智能体 (Agent) 引擎**：
  - 基于 **LangChain** 构建，利用强大的 **工具调用 (Tool Calling)** 能力执行任务。
  - **通用 MCP 支持 (Universal MCP)**：完整实现 Model Context Protocol。
    - **Stdio**：连接本地命令行工具。
    - **SSE**：连接远程或 Docker 容器中的工具。
    - **Presets**：常用工具一键安装。
- **🔌 多模型支持**：
  - **拒绝厂商锁定**：在 OpenAI, Anthropic, Google Gemini, XAI (Grok) 以及任何兼容 OpenAI 接口的供应商之间切换。
  - **成本优化**：简单问题路由到低成本模型，复杂推理交给高性能模型。
- **🚀 OpenAI 兼容 API**：
  - 将配置好的助手作为标准 OpenAI API 端点暴露。
  - 轻松集成现有工具（如 VS Code 插件或第三方客户端）。

## 🛠️ 技术栈

- **前端**: [Nuxt 4](https://nuxt.com/) (Vue 3), [Shadcn Vue](https://www.shadcn-vue.com/), [TailwindCSS v4](https://tailwindcss.com/), [Pinia](https://pinia.vuejs.org/)
- **后端**: [FastAPI](https://fastapi.tiangolo.com/), [SQLAlchemy](https://www.sqlalchemy.org/) (Async), [Alembic](https://alembic.sqlalchemy.org/)
- **AI & 数据**: [LangChain](https://www.langchain.com/), [ChromaDB](https://www.trychroma.com/), [Pydantic](https://docs.pydantic.dev/)
- **存储**: PostgreSQL / SQLite, Redis, S3 (MinIO/AWS)

## 💡 为什么选择 RiceBall？

1. **安全优先**：私有化部署方案确保数据和 IP 保留在你自己的基础设施上。
2. **业务原生**：通过 **工具调用 (Tool Calling)** 和 **通用 MCP 支持**，RiceBall 不仅仅是一个聊天机器人，它是能够与处于任何环境（本地/远程）的业务系统（文件、数据库、API）进行交互的操作员。
3. **开发者就绪**：清晰的模块化架构（前后端分离），是构建定制化 AI 解决方案的绝佳起点。

## 🔗 通用 MCP 主机 (Universal MCP Host)

RiceBall 实现了完整的 **Model Context Protocol (MCP)** 规范，作为通用主机（Universal Host）可以连接任何 MCP 服务器。

### 核心特性
- **🔌 全传输协议支持**:
  - **Stdio**: 无缝连接本地进程（如 `git`、本地 Python 脚本）。非常适合本地开发和调试。
  - **HTTP (Simple & SSE)**: 完整支持 HTTP 传输协议。使用 HTTP POST 发送消息，可选 Server-Sent Events (SSE) 进行流式传输。完美支持 Docker "Sidecar" 模式部署。
- **📦 智能预设 (Smart Presets)**: 内置常用工具配置（如本地文件系统、Brave 搜索 API 等），无需手动配置，一键安装即可使用。
- **📄 无限扩展**: 通过管理后台添加自定义的 MCP 服务器连接信息，无限扩展你的助手能力。

## 👥 适用人群

- **企业与团队**：构建内部知识库助手、智能客服、研发效能工具。
- **全栈开发者**：寻找成熟的 RAG + Agent 架构作为起点的开发者。
- **系统集成商**：为客户交付私有化 AI 解决方案的服务商。

## 🐹 关于名字

RiceBall （饭团）的名字来源于我养的一只仓鼠。它每次在小食盆里吃饭的时候团起来跟一个饭团似的，所以我给它起名叫饭团。
