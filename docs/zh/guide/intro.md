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
  - **Model Context Protocol (MCP)** 支持正在积极开发中 (🚧)，旨在连接你的生态系统。
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
2. **业务原生**：通过 **工具调用 (Tool Calling)**（以及即将到来的 **MCP** 支持），RiceBall 不仅仅是一个聊天机器人，它是一个能够与业务系统交互的操作员。
3. **开发者就绪**：清晰的模块化架构（前后端分离），是构建定制化 AI 解决方案的绝佳起点。

## 👥 适用人群

- **企业与团队**：构建内部知识库助手、智能客服、研发效能工具。
- **全栈开发者**：寻找成熟的 RAG + Agent 架构作为起点的开发者。
- **系统集成商**：为客户交付私有化 AI 解决方案的服务商。

## 🐹 关于名字

RiceBall （饭团）的名字来源于我养的一只仓鼠。它每次在小食盆里吃饭的时候团起来跟一个饭团似的，所以我给它起名叫饭团。
