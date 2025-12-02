# RiceBall - 为团队和企业打造的私有化 AI 知识库与智能体（Agent）平台

[English Documentation](../README.md)

## 🍚 RiceBall 是什么？

RiceBall 是一个开源的、全栈式的 **AI 智能体与知识库平台**。它旨在帮助团队和企业在私有环境中快速构建和部署基于大语言模型（LLM）的智能应用。

核心能力：

- **私有化 RAG 知识库**：支持文档上传、自动切片与向量化，让 AI 基于你的私有数据回答问题。
- **智能体 (Agent) 引擎**：基于 LangChain ，支持工具调用和 **MCP (Model Context Protocol)** (🚧 实现中)，让 AI 具备执行任务的能力。
- **多模型聚合**：支持 OpenAI、Anthropic 等主流接口协议，拒绝供应商锁定。
- **现代化全栈架构**：后端采用 FastAPI (Python)，前端采用 Nuxt 3 (Vue)，内置 OAuth 认证。

## 💡 为什么选择 RiceBall？

在 AI 落地过程中，企业往往面临数据安全与灵活性的平衡难题。RiceBall 提供了最佳实践：

1. **数据完全掌控**：支持本地部署（Docker），所有数据（知识库、对话记录）均存储在你的私有服务器上。
2. **业务深度集成**：通过工具调用和 MCP 协议（🚧 实现中），RiceBall 可以连接你的数据库、API 和内部工具，成为真正的业务助手。
3. **灵活的模型策略**：根据场景选择模型——用高性能模型处理复杂推理，用高性价比模型处理日常对话，优化成本。
4. **开发者友好**：提供清晰的模块化架构和完善的 API，方便进行二次开发和定制。

## 👥 适用人群

- **企业与团队**：构建内部知识库助手、智能客服、研发效能工具。
- **全栈开发者**：寻找成熟的 RAG + Agent 架构作为起点的开发者。
- **系统集成商**：为客户交付私有化 AI 解决方案的服务商。

## 🐹 关于名字

RiceBall （饭团）的名字来源于我养的一只仓鼠。它每次在小食盆里吃饭的时候团起来跟一个饭团似的，所以我给它起名叫饭团。

## 🚀 快速开始

```bash
git clone ...

cp backend/.env.example backend/.env

docker-compose up -d
```

## ❤️ 致谢

RiceBall 的诞生离不开开源社区的贡献，特别感谢以下优秀的开源项目：

- [FastAPI](https://fastapi.tiangolo.com/)
- [FastAPI Users](https://frankie567.github.io/fastapi-users/)
- [Nuxt](https://nuxt.com/)
- [LangChain](https://www.langchain.com/)
- [ChromaDB](https://www.trychroma.com/)
- [Shadcn Vue](https://www.shadcn-vue.com/)
- ...

## 📄 协议

本项目基于 [MIT 协议](LICENSE) 开源。
