import logging
from fastapi import FastAPI, APIRouter, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi_pagination import add_pagination
from pathlib import Path

from .config import settings, StorageType
from .auth import current_active_user, current_superuser
from .auth.api.v1.user_router import router as auth_user_router
from .auth.api.v1.refresh_router import router as auth_refresh_router
from .auth.api.v1.oauth_user_router import router as oauth_user_router
from .auth.api.v1.oauth_admin_router import router as oauth_admin_router_v1
from .system_config.api.v1.user_router import router as configs_user_router_v1
from .system_config.api.v1.admin_router import router as configs_admin_router_v1
from .system_config.api.v1.manifest_router import router as manifest_router
from .users.api.v1.user_router import router as users_user_router_v1
from .users.api.v1.admin_router import router as users_admin_router_v1
from .ai_models.api.v1.admin_router import router as models_admin_router_v1
from .ai_models.api.v1.user_router import router as models_user_router_v1
from .assistants.api.v1.admin_router import router as assistants_admin_router_v1
from .assistants.api.v1.user_router import router as assistants_user_router_v1
from .files.api.v1.user_router import router as files_user_router_v1
from .files.api.v1.admin_router import router as files_admin_router_v1
from .rag.api.v1.admin_router import router as rag_admin_router_v1
from .chat.api.v1.user_router import router as chat_user_router_v1
from .chat.api.v1.admin_router import router as chat_admin_router_v1
from .chat.api.v1.share_router import router as chat_share_router_v1
from .agents.api.v1.admin_router import router as agents_admin_router_v1

logging.basicConfig(level=settings.LOG_LEVEL)

async def require_active_user(current_active_user = Depends(current_active_user)):
    if not current_active_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Active user required"
        )
    return current_active_user


async def require_admin(current_superuser = Depends(current_superuser)):
    if not current_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_superuser


app_config = {
    "title": settings.APP_NAME
}

if settings.ENVIRONMENT not in settings.SHOW_DOCS_ENVIRONMENT:
    app_config["openapi_url"] = None

app = FastAPI(**app_config)

app.include_router(configs_user_router_v1, prefix="/api/v1", tags=["Public Configs"])
app.include_router(manifest_router, prefix="/api/v1/config", tags=["Public Configs"])

app.include_router(auth_user_router, prefix="/api/v1", tags=["Auth"])
app.include_router(auth_refresh_router, prefix="/api/v1", tags=["Auth"])
app.include_router(oauth_user_router, prefix="/api/v1", tags=["OAuth"])

# Assistants (public endpoints)
app.include_router(assistants_user_router_v1, prefix="/api/v1", tags=["Assistants"])
app.include_router(chat_share_router_v1, prefix="/api/v1", tags=["Chat Shares"])


# User routes
user_route_v1 = APIRouter(
    prefix="/api/v1",
    dependencies=[Depends(require_active_user)]
)

user_route_v1.include_router(users_user_router_v1, tags=["Users"])

user_route_v1.include_router(models_user_router_v1, tags=["AI Models"])

user_route_v1.include_router(files_user_router_v1, tags=["Files"])

user_route_v1.include_router(chat_user_router_v1, tags=["Chat"])

app.include_router(user_route_v1)


# Admin routes
admin_router_v1 = APIRouter(
    prefix="/api/v1/admin",
    dependencies=[Depends(require_admin)]
)

admin_router_v1.include_router(assistants_admin_router_v1, tags=["Admin - Assistants"])

admin_router_v1.include_router(models_admin_router_v1, tags=["Admin - AI Models"])

admin_router_v1.include_router(files_admin_router_v1, tags=["Admin - Files"])

admin_router_v1.include_router(rag_admin_router_v1, prefix="/rag", tags=["Admin - RAG"])

admin_router_v1.include_router(chat_admin_router_v1, tags=["Admin - Chat"])

admin_router_v1.include_router(agents_admin_router_v1, tags=["Admin - Agent Tools & MCP"])

# OAuth Admin routes
admin_router_v1.include_router(oauth_admin_router_v1, tags=["Admin - OAuth"])

# Users Admin routes
admin_router_v1.include_router(users_admin_router_v1, tags=["Admin - Users"])
admin_router_v1.include_router(configs_admin_router_v1, tags=["Admin - System Config"])

app.include_router(admin_router_v1)

# Add pagination support
add_pagination(app)

# Static Files & SPA Serving
# 1. Mount Local File Storage (if enabled)
if settings.STORAGE_TYPE == StorageType.LOCAL:
    local_storage_path = settings.LOCAL_STORAGE_PATH or (settings.STORAGE_DIR / "files")
    local_storage_path.mkdir(parents=True, exist_ok=True)
    # Mount at /api/v1/files/static to match the URL generation in storage.py
    app.mount("/api/v1/files/static", StaticFiles(directory=local_storage_path), name="local_files")

# 2. Serve Frontend Static Files (SPA)
# We assume the frontend build is copied to /app/static in the container
static_dir = Path("/app/static")

if static_dir.exists():
    # Mount Nuxt assets
    if (static_dir / "_nuxt").exists():
        app.mount("/_nuxt", StaticFiles(directory=static_dir / "_nuxt"), name="nuxt_assets")
    
    # Catch-all route for SPA
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        # Check if file exists in static dir (e.g. favicon.ico, robots.txt)
        file_path = static_dir / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        
        # Otherwise return index.html for client-side routing
        index_path = static_dir / "index.html"
        if index_path.exists():
            return FileResponse(index_path)
            
        # If index.html is missing, return 404
        raise HTTPException(status_code=404, detail="Frontend not found")