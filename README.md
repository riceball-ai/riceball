# RiceBall - Private AI Knowledge Base & Agent Platform Built for Teams and Enterprises

[Documentation](https://riceball-ai.github.io/riceball/) | [文档](https://riceball-ai.github.io/riceball/zh/)

## 🍚 What is RiceBall?

RiceBall is an open-source, full-stack **AI Agent & Knowledge Base Platform**. It aims to help teams and enterprises quickly build and deploy LLM-based intelligent applications in a private environment.

![Client Interface](docs/.vuepress/public/client.png)
![Dashboard Interface](docs/.vuepress/public/dashboard.png)

**Core Capabilities:**

- **Private RAG Knowledge Base**: Supports document upload, automatic chunking, and vectorization, enabling AI to answer questions based on your private data.
- **Agent Engine**: Based on LangChain, supports tool calling and **MCP (Model Context Protocol)** (🚧 In Progress), empowering AI to execute tasks.
- **Multi-Model Aggregation**: Supports mainstream interface protocols like OpenAI and Anthropic, avoiding vendor lock-in.
- **Modern Full-Stack Architecture**: Backend uses FastAPI (Python), frontend uses Nuxt 3 (Vue), with built-in OAuth authentication.

## 💡 Why Choose RiceBall?

In the process of AI adoption, enterprises often face the dilemma of balancing data security and flexibility. RiceBall provides best practices:

1. **Complete Data Control**: Supports local deployment (Docker); all data (knowledge base, chat history) is stored on your private server.
2. **Deep Business Integration**: Through tool calling and the MCP protocol (🚧 In Progress), RiceBall can connect to your databases, APIs, and internal tools, becoming a true business assistant.
3. **Flexible Model Strategy**: Choose models based on scenarios—use high-performance models for complex reasoning, and cost-effective models for daily conversation to optimize costs.
4. **Developer Friendly**: Provides a clear modular architecture and comprehensive APIs, facilitating secondary development and customization.

## 👥 Target Audience

- **Enterprises & Teams**: Building internal knowledge base assistants, intelligent customer service, and R&D efficiency tools.
- **Full-Stack Developers**: Developers looking for a mature RAG + Agent architecture as a starting point.
- **System Integrators**: Service providers delivering private AI solutions to clients.

## 🐹 About the Name

The name RiceBall comes from a hamster I own. Every time it eats in its little food bowl, it curls up like a rice ball, so I named it RiceBall.

## 🚀 Quick Start

> **Note**: This setup is for **preview and testing purposes only**. Please use with caution in production environments.

Run RiceBall with a single command using our All-in-One Docker image (includes SQLite & Local Storage):

```bash
docker run -d \
  -p 8000:8000 \
  -e SUPERUSER_EMAIL=admin@admin.com \
  -e SUPERUSER_PASSWORD=admin123456 \
  -v riceball_storage:/app/storage \
  --name riceball \
  ghcr.io/riceball-ai/riceball:all-in-one-latest
```

Visit http://localhost:8000 to start using RiceBall. You can configure the initial superuser credentials via the `SUPERUSER_EMAIL` and `SUPERUSER_PASSWORD` environment variables.

## 🛠️ Production Deployment (Source Code)

For production environments requiring PostgreSQL and S3, you can deploy from source:

```bash
git clone https://github.com/riceball-ai/riceball.git
cd riceball

docker compose -f docker-compose.prod.yml up -d

```

## ❤️ Acknowledgements

RiceBall wouldn't exist without the contributions of the open-source community. Special thanks to the following excellent open-source projects:

- [FastAPI](https://fastapi.tiangolo.com/)
- [FastAPI Users](https://frankie567.github.io/fastapi-users/)
- [Vue.js](https://vuejs.org/)
- [Nuxt](https://nuxt.com/)
- [LangChain](https://www.langchain.com/)
- [ChromaDB](https://www.trychroma.com/)
- [Shadcn Vue](https://www.shadcn-vue.com/)
- ...

It is impossible to list all projects. If your project is used but not listed here, please contact us to add it.

## 📄 License

This project is open source under the [MIT License](LICENSE).
