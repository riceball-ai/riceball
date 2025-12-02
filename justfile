dev command *args:
    docker compose {{command}} {{args}}

backend command *args:
    docker compose exec backend {{command}} {{args}}

uv *args:
    docker compose exec backend uv {{args}}

alembic *args:
    docker compose exec backend uv run alembic {{args}}

migrate:
    docker compose exec backend uv run alembic upgrade head

frontend command *args:
    docker compose exec frontend {{command}} {{args}}

pnpm *args:
    docker compose exec frontend pnpm {{args}}

nuxt *args:
    docker compose exec frontend npx nuxt {{args}}