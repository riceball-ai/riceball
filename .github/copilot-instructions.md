# RiceBall AI Agent Instructions

You are an expert AI developer working on **RiceBall**, a Full-stack AI Agent & Knowledge Base Platform.

## 1. Project Context
- **Backend**: FastAPI (Python 3.13+), Async SQLAlchemy, LangChain, ChromaDB. Managed by `uv`.
- **Frontend**: Nuxt 4 (SPA mode), Shadcn Vue, Tailwind CSS v4. Managed by `pnpm`.
- **Goal**: Private RAG knowledge base, Agent engine (MCP support).

## 2. Environment & Commands
**CRITICAL**: Always use **absolute paths** for file arguments.
**Context**: The user may be running locally or via Docker. Check `justfile` for checking short aliases.

### Backend (`backend/`)
- **Package Manager**: `uv` (faster pip replacement).
- **Start Dev Server**: `uv run fastapi dev src/main.py`
- **Database Migrations**:
  - Create: `uv run alembic revision --autogenerate -m "message"`
  - Apply: `uv run alembic upgrade head`
- **Add Dependency**: `uv add <package>`

### Frontend (`frontend/`)
- **Package Manager**: `pnpm`.
- **Start Dev Server**: `pnpm dev`
- **Nuxt Commands**: `npx nuxt <command>` (e.g., `npx nuxt generate`)

## 3. Architecture & Key Paths

### Backend Structure (`backend/src/`)
- **Entry Point**: `main.py` (aggregates all routers).
- **Configuration**: `config.py` (Pydantic `Settings`).
- **Database**: `database.py` (Async sessions).
- **Modules**: Logic is partitioned by domain in `src/<module>/`:
  - `auth`, `users`, `chat`, `rag`, `agents`, `files`.
  - API Routes: `src/<module>/api/v1/` (Always register new routers in `main.py`).

### Frontend Structure (`frontend/app/`)
- **Framework**: Nuxt 4. Directory structure follows Nuxt conventions within `frontend/app/`.
- **SPA Mode**: `ssr: false` in `nuxt.config.ts`.
- **UI Components**: `components/ui/` (Shadcn), `components/` (Custom).
- **State**: `stores/` (Pinia).
- **Composables**: `composables/` (Shared logic).

## 4. Coding Conventions

### Python (Backend)
- **Async First**: Use `async def` for all I/O bound operations (DB, AI calls).
- **Type Safety**: Use Pydantic models for schemas and Python 3.13+ type hints.
- **Dependency Injection**: Use `Depends()` for services and auth (e.g., `current_active_user`).
- **Database**: Use `sqlalchemy.ext.asyncio`. NEVER use synchronous drivers.

### Vue/Nuxt (Frontend)
- **Script Setup**: Use `<script setup lang="ts">`.
- **Styling**: Tailwind CSS v4. Use utility classes over `<style>` blocks.
- **Icons**: `lucide-vue-next`.
- **Data Fetching (CRITICAL)**:
  - **Reactive**: Use `useAPI` composable (wrapper around `useFetch` with auth handling).
  - **Imperative**: Use `const { $api } = useNuxtApp()` for actions/events.
  - **Avoid**: Raw `$fetch` or `useFetch` for backend API calls (misses auth/refresh logic).
- **Forms**: Use `zod` schema validation with `vee-validate`.

## 5. Implementation Workflow
1.  **Backend First**: Define Pydantic models -> Create DB Migration -> Implement `crud` -> Add Router -> Register in `main.py`.
2.  **Frontend Second**: Update Types (`frontend/app/types/`) -> Create `useAPI` hook or store action -> Build UI with Shadcn.
