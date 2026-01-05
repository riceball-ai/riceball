from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from src.database import get_async_session
from src.system_config.service import config_service

router = APIRouter()

@router.get("/manifest.json")
async def get_manifest(
    session: AsyncSession = Depends(get_async_session)
):
    """
    Generate dynamic PWA manifest based on system configuration.
    """
    configs = await config_service.get_public_configs(session)
    
    # Check if PWA is enabled
    if not configs.get("pwa_enabled", True):
        return Response(status_code=status.HTTP_404_NOT_FOUND)
    
    # Get values with defaults
    name = configs.get("site_title", "RiceBall")
    short_name = configs.get("pwa_short_name", name)
    description = configs.get("pwa_description", "RiceBall AI Agent Platform")
    theme_color = configs.get("pwa_theme_color", "#ffffff")
    background_color = configs.get("pwa_background_color", "#ffffff")
    display = configs.get("pwa_display", "standalone")
    
    # Handle icons
    icons = []
    pwa_icon = configs.get("pwa_icon")
    site_logo = configs.get("site_logo")
    site_favicon = configs.get("site_favicon")
    
    # Use pwa_icon if available, otherwise site_logo, otherwise site_favicon
    icon_url = pwa_icon or site_logo or site_favicon
    
    if icon_url:
        # If we have an icon, we define it for multiple sizes to satisfy PWA requirements
        # In a real scenario, we might want to generate resized versions, 
        # but for now we point to the same file.
        icons = [
            {
                "src": icon_url,
                "sizes": "192x192",
                "type": "image/png"
            },
            {
                "src": icon_url,
                "sizes": "512x512",
                "type": "image/png"
            }
        ]
    else:
        # Fallback to default favicon if no custom icon is set
        icons = [
            {
                "src": "/favicon.ico",
                "sizes": "64x64 32x32 24x24 16x16",
                "type": "image/x-icon"
            }
        ]

    manifest = {
        "name": name,
        "short_name": short_name,
        "description": description,
        "theme_color": theme_color,
        "background_color": background_color,
        "display": display,
        "start_url": "/",
        "scope": "/",
        "icons": icons
    }
    
    return manifest
