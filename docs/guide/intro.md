# Introduction

## 🍚 What is RiceBall?

RiceBall is an open-source, full-stack **AI Agent & Knowledge Base Platform**. It aims to help teams and enterprises quickly build and deploy LLM-based intelligent applications in a private environment.

**Core Capabilities:**

- **🔐 Private RAG Knowledge Base**: 
  - Upload documents (PDF, DOCX, XLSX, PPTX, Markdown) securely.
  - **Web Reader**: Extract clean content from any webpage URL to your knowledge base.
  - Automatic chunking and vectorization using **ChromaDB**.
  - Citations and reference tracking.
- **🤖 Agent Engine**: 
  - Built on **LangChain**, utilizing robust **Tool Calling** capabilities to execute tasks.
  - **Universal MCP Support**: Full implementation of Model Context Protocol.
    - **Stdio**: Connect to local tools.
    - **SSE**: Connect to remote/Dockerized tools.
    - **Presets**: One-click install for common tools.
- **🔌 Multi-Model Support**: 
  - **Vendor Agnostic**: Switch between OpenAI, Anthropic, Google Gemini, XAI (Grok).
  - **Ollama Integration**: One-click scan & import for local models (DeepSeek, Llama3, etc.).
  - **OpenAI Compatible**: Support any provider via standard protocol (e.g. DashScope).
  - **Cost Optimization**: Route simple queries to cheaper models and complex reasoning to high-performance models.
- **�️ Enterprise SSO & Auth**:
  - Full **OAuth 2.0** support (Google, GitHub, Keycloak, Auth0).
  - Native integration with **WeCom (Enterprise WeChat)** for seamless employee login.
- **�🚀 OpenAI Compatible API**: 
  - Expose your configured Assistant as a standard OpenAI API endpoint.
  - Integrate easily with existing tools like VS Code extensions or third-party wrappers.

## 🛠️ Tech Stack

- **Frontend**: [Nuxt 4](https://nuxt.com/) (Vue 3), [Shadcn Vue](https://www.shadcn-vue.com/), [TailwindCSS v4](https://tailwindcss.com/), [Pinia](https://pinia.vuejs.org/)
- **Backend**: [FastAPI](https://fastapi.tiangolo.com/), [SQLAlchemy](https://www.sqlalchemy.org/) (Async), [Alembic](https://alembic.sqlalchemy.org/)
- **AI & Data**: [LangChain](https://www.langchain.com/), [ChromaDB](https://www.trychroma.com/), [Pydantic](https://docs.pydantic.dev/)
- **Storage**: PostgreSQL / SQLite, Redis, S3 (MinIO/AWS)

## 💡 Why Choose RiceBall?

1. **Security First**: Self-hosted solution ensures your IP and user data remain on your infrastructure.
2. **Business Native**: Through **Tool Calling** and **Universal MCP Support**, RiceBall isn't just a chatbot—it's an operator that can interact with your business systems (Filesystem, Databases, APIs) regardless of where they are hosted.
3. **Developer Ready**: Clean, modular architecture (Frontend/Backend separation) makes it an excellent starter kit for custom AI solutions.

## 🔗 Universal MCP Host

RiceBall implements the full **Model Context Protocol (MCP)** specification, acting as a Universal Host that can connect to any MCP Server.

### Key Features
- **🔌 Any Transport Protocol**:
  - **Stdio**: Seamlessly connect to local processes (e.g., `git`, local scripts). Ideal for local development.
  - **HTTP (Simple & SSE)**: Full support for HTTP transport. Uses HTTP POST for client-to-server messages with optional Server-Sent Events (SSE) for streaming. Perfect for Docker "Sidecar" patterns.
- **📦 Smart Presets**: Built-in configurations for popular tools (Filesystem, Brave Search, etc.) enabling one-click setup without manual configuration.
- **📄 Extensible**: Add your own custom MCP servers via the Admin Panel to expand your Assistant's capabilities endlessly.

## 👥 Target Audience

- **Enterprises & Teams**: Building internal knowledge base assistants, intelligent customer service, and R&D efficiency tools.
- **Full-Stack Developers**: Developers looking for a mature RAG + Agent architecture as a starting point.
- **System Integrators**: Service providers delivering private AI solutions to clients.

## 🐹 About the Name

The name RiceBall comes from a hamster I own. Every time it eats in its little food bowl, it curls up like a rice ball, so I named it RiceBall.
