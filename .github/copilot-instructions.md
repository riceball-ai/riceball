# RiceBall AI Agent Instructions

You are an expert AI developer working on **RiceBall**, an open-source AI Agent & Knowledge Base Platform.

## 1. Project Overview
- **Stack**: Full-stack application with **FastAPI** (Python) backend and **Nuxt 4** (Vue.js) frontend.
- **Core Tech**: LangChain, ChromaDB, Docker, PostgreSQL/SQLite.
- **Goal**: Private RAG knowledge base, Agent engine (MCP support), and multi-model aggregation.

## 2. Architecture & Structure

### Backend (`backend/`)
- **Framework**: FastAPI with Async SQLAlchemy & Alembic.
- **Package Manager**: `uv`.
- **Structure**: Modularized by domain in `src/`.
  - `src/main.py`: Application entry point & router aggregation.
  - `src/config.py`: Pydantic-based configuration (`Settings`).
  - `src/database.py`: Async DB session & engine setup.
  - **Modules**: `auth`, `users`, `ai_models`, `assistants`, `files`, `rag`, `chat`, `agents`.
  - **API**: Versioned routes (e.g., `api/v1/user_router`).

### Frontend (`frontend/`)
- **Framework**: Nuxt 4 (SPA mode: `ssr: false`).
- **Package Manager**: `pnpm`.
- **UI**: **Shadcn Vue** (via `shadcn-nuxt` & `reka-ui`), Tailwind CSS v4.
- **State**: Pinia.
- **Structure**:
  - `app/`: Main application source (Nuxt 4 directory structure).
  - `app/components/`: UI components (Shadcn components in `ui/`).
  - `app/stores/`: Pinia stores.
  - `app/composables/`: Shared logic.

## 3. Development Workflow & Commands

**ALWAYS** use `just` or `docker compose` for running commands. Do not run `uv` or `pnpm` directly on the host unless specified.

- **Root Commands** (`justfile`):
  - `just dev`: Start the full stack (backend + frontend) via Docker Compose.
  - `just backend <cmd>`: Run command in backend container.
  - `just frontend <cmd>`: Run command in frontend container.

- **Backend Specific**:
  - `just uv add <package>`: Add Python dependency.
  - `just migrate`: Run Alembic migrations (`upgrade head`).
  - `just alembic revision --autogenerate -m "message"`: Create migration.

- **Frontend Specific**:
  - `pnpm add <package>`: Add Node dependency.
  - `nuxt <cmd>`: Run Nuxt commands.

## 4. Coding Conventions

### Python (Backend)
- **Async/Await**: Use `async def` for all route handlers and DB operations.
- **Typing**: Strong typing with Pydantic models and Python 3.13+ type hints.
- **Dependency Injection**: Use FastAPI's `Depends` for services and auth (e.g., `current_active_user`).
- **Database**: Use `sqlalchemy.ext.asyncio`.
- **Configuration**: Access settings via `src.config.settings`.

### Vue/Nuxt (Frontend)
- **Composition API**: Always use `<script setup lang="ts">`.
- **Styling**: Use Tailwind CSS utility classes. Avoid custom CSS files where possible.
- **Components**: Prefer Shadcn Vue components.
- **Data Fetching**: Use `useFetch` or `$fetch` for API calls.
- **Validation**: Use `zod` and `vee-validate` for forms.
- **Icons**: Use `lucide-vue-next`.

## 5. Key Integration Points
- **Auth**: `fastapi-users` handles user management and OAuth.
- **AI**: `langchain` integrates with OpenAI, Anthropic, etc.
- **Vector DB**: `chromadb` for RAG storage.
- **API Communication**: Frontend communicates with backend via `/api/v1` endpoints.

## 6. Common Tasks
- **New API Endpoint**:
  1. Define Pydantic schemas.
  2. Create router in appropriate module (e.g., `src/chat/api/v1/`).
  3. Register router in `src/main.py`.
- **New UI Page**:
  1. Create page in `frontend/app/pages/`.
  2. Use `definePageMeta` for layout/middleware.
  3. Fetch data using composables.
