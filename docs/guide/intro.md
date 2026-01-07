# Introduction

## 🍚 What is RiceBall?

RiceBall is an open-source, full-stack **AI Agent & Knowledge Base Platform**. It aims to help teams and enterprises quickly build and deploy LLM-based intelligent applications in a private environment.

**Core Capabilities:**

- **🔐 Private RAG Knowledge Base**: 
  - Upload documents (PDF, DOCX, XLSX, PPTX, Markdown) securely.
  - Automatic chunking and vectorization using **ChromaDB**.
  - Citations and reference tracking.
- **🤖 Agent Engine**: 
  - Built on **LangChain**, utilizing robust **Tool Calling** capabilities to execute tasks.
  - **Model Context Protocol (MCP)** support is in active development (🚧), aiming to provide standardized connections to your ecosystem.
- **🔌 Multi-Model Support**: 
  - **Vendor Agnostic**: Switch between OpenAI, Anthropic, Google Gemini, XAI (Grok), and any OpenAI-compatible provider.
  - **Cost Optimization**: Route simple queries to cheaper models and complex reasoning to high-performance models.
- **🚀 OpenAI Compatible API**: 
  - Expose your configured Assistant as a standard OpenAI API endpoint.
  - Integrate easily with existing tools like VS Code extensions or third-party wrappers.

## 🛠️ Tech Stack

- **Frontend**: [Nuxt 4](https://nuxt.com/) (Vue 3), [Shadcn Vue](https://www.shadcn-vue.com/), [TailwindCSS v4](https://tailwindcss.com/), [Pinia](https://pinia.vuejs.org/)
- **Backend**: [FastAPI](https://fastapi.tiangolo.com/), [SQLAlchemy](https://www.sqlalchemy.org/) (Async), [Alembic](https://alembic.sqlalchemy.org/)
- **AI & Data**: [LangChain](https://www.langchain.com/), [ChromaDB](https://www.trychroma.com/), [Pydantic](https://docs.pydantic.dev/)
- **Storage**: PostgreSQL / SQLite, Redis, S3 (MinIO/AWS)

## 💡 Why Choose RiceBall?

1. **Security First**: Self-hosted solution ensures your IP and user data remain on your infrastructure.
2. **Business Native**: Through **Tool Calling** (with upcoming **MCP** support), RiceBall isn't just a chatbot—it's an operator that can interact with your business systems.
3. **Developer Ready**: Clean, modular architecture (Frontend/Backend separation) makes it an excellent starter kit for custom AI solutions.

## 👥 Target Audience

- **Enterprises & Teams**: Building internal knowledge base assistants, intelligent customer service, and R&D efficiency tools.
- **Full-Stack Developers**: Developers looking for a mature RAG + Agent architecture as a starting point.
- **System Integrators**: Service providers delivering private AI solutions to clients.

## 🐹 About the Name

The name RiceBall comes from a hamster I own. Every time it eats in its little food bowl, it curls up like a rice ball, so I named it RiceBall.
