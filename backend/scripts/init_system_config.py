#!/usr/bin/env python3
"""
System Configuration Initialization Script

This script is used to initialize some default system configuration items,
such as registration switch, email verification, etc.
"""

import asyncio
import sys
import os

# Add project root directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import get_async_session
from src.system_config.service import config_service
from src.system_config.api.v1.schemas import ConfigCreate, ConfigUpdate
from src.config import settings


# Default configuration items
DEFAULT_CONFIGS = [
    {
        "key": "site_title",
        "value": settings.APP_NAME,
        "description": "Site Title",
        "is_public": True,
        "is_enabled": True,
        "config_type": "text",
        "config_group": "branding",
        "label": "Site Title"
    },
    {
        "key": "site_slogan",
        "value": "Boost your productivity with AI",
        "description": "Site Slogan",
        "is_public": True,
        "is_enabled": True,
        "config_type": "text",
        "config_group": "branding",
        "label": "Site Slogan"
    },
    {
        "key": "site_logo",
        "value": settings.APP_LOGO or "",
        "description": "Site Logo URL",
        "is_public": True,
        "is_enabled": True,
        "config_type": "image",
        "config_group": "branding",
        "label": "Site Logo"
    },
    {
        "key": "site_favicon",
        "value": settings.APP_FAVICON or "",
        "description": "Site Favicon URL",
        "is_public": True,
        "is_enabled": True,
        "config_type": "image",
        "config_group": "branding",
        "label": "Site Favicon"
    },
    # PWA Configuration
    {
        "key": "pwa_enabled",
        "value": False,
        "description": "Enable PWA features",
        "is_public": True,
        "is_enabled": True,
        "config_type": "boolean",
        "config_group": "pwa",
        "label": "Enable PWA"
    },
    {
        "key": "pwa_short_name",
        "value": settings.APP_NAME,
        "description": "PWA Short Name",
        "is_public": True,
        "is_enabled": True,
        "config_type": "text",
        "config_group": "pwa",
        "label": "Short Name"
    },
    {
        "key": "pwa_description",
        "value": "RiceBall AI Agent Platform",
        "description": "PWA Description",
        "is_public": True,
        "is_enabled": True,
        "config_type": "text",
        "config_group": "pwa",
        "label": "Description"
    },
    {
        "key": "pwa_theme_color",
        "value": "#ffffff",
        "description": "PWA Theme Color",
        "is_public": True,
        "is_enabled": True,
        "config_type": "text",
        "config_group": "pwa",
        "label": "Theme Color"
    },
    {
        "key": "pwa_background_color",
        "value": "#ffffff",
        "description": "PWA Background Color",
        "is_public": True,
        "is_enabled": True,
        "config_type": "text",
        "config_group": "pwa",
        "label": "Background Color"
    },
    {
        "key": "pwa_icon",
        "value": "",
        "description": "PWA Icon URL (512x512 recommended)",
        "is_public": True,
        "is_enabled": True,
        "config_type": "image",
        "config_group": "pwa",
        "label": "App Icon"
    },
    {
        "key": "pwa_display",
        "value": "standalone",
        "description": "PWA Display Mode",
        "is_public": True,
        "is_enabled": True,
        "config_type": "select",
        "config_group": "pwa",
        "label": "Display Mode",
        "options": [
            {"label": "Standalone", "value": "standalone"},
            {"label": "Minimal UI", "value": "minimal-ui"},
            {"label": "Browser", "value": "browser"},
            {"label": "Fullscreen", "value": "fullscreen"}
        ]
    },
    {
        "key": "registration_enabled",
        "value": True,
        "description": "Whether user registration is enabled",
        "is_public": True,
        "is_enabled": True,
        "config_type": "boolean",
        "config_group": "security",
        "label": "Enable Registration"
    },
    {
        "key": "conversation_title_model_id",
        "value": '',
        "description": "Model ID for generating conversation titles, uses conversation assistant model if empty",
        "is_public": False,
        "is_enabled": True,
        "config_type": "text",
        "config_group": "ai",
        "label": "Title Generation Model"
    },
    {
        "key": "allow_user_create_assistants",
        "value": False,
        "description": "Whether to allow users to create assistants",
        "is_public": True,
        "is_enabled": True,
        "config_type": "boolean",
        "config_group": "security",
        "label": "Allow User Create Assistants"
    }
]


async def init_default_configs():
    """Initialize default configurations"""
    print("Starting to initialize system configurations...")
    
    # Get database session
    async for session in get_async_session():
        try:
            created_count = 0
            skipped_count = 0
            updated_count = 0
            
            for config_data in DEFAULT_CONFIGS:
                try:
                    # Check if configuration item already exists
                    existing_config = await config_service.get_config(session, config_data["key"])
                    
                    if existing_config:
                        # Check if metadata needs update
                        needs_update = False
                        update_data = {}
                        
                        if existing_config.config_type != config_data.get("config_type", "text"):
                            update_data["config_type"] = config_data.get("config_type", "text")
                            needs_update = True
                            
                        if existing_config.config_group != config_data.get("config_group", "general"):
                            update_data["config_group"] = config_data.get("config_group", "general")
                            needs_update = True
                            
                        if existing_config.label != config_data.get("label"):
                            update_data["label"] = config_data.get("label")
                            needs_update = True

                        if needs_update:
                            config_update = ConfigUpdate(**update_data)
                            await config_service.update_config(session, config_data["key"], config_update)
                            print(f"Updated metadata for '{config_data['key']}'")
                            updated_count += 1
                        else:
                            print(f"Configuration item '{config_data['key']}' already exists and up to date, skipping")
                            skipped_count += 1
                        continue
                    
                    # Create new configuration item
                    config_create = ConfigCreate(**config_data)
                    created_config = await config_service.create_config(session, config_create)
                    print(f"Created configuration item '{created_config.key}': {created_config.get_value()}")
                    created_count += 1
                    
                except Exception as e:
                    print(f"Error processing configuration item '{config_data['key']}': {e}")
                    continue
            
            print("\nInitialization completed!")
            print(f"Created {created_count} new items, Updated {updated_count} items, Skipped {skipped_count} items")
            
        except Exception as e:
            print(f"Error initializing configurations: {e}")
            return False
        
        finally:
            await session.close()
    
    return True


async def list_current_configs():
    """List all current configurations"""
    print("\nCurrent system configurations:")
    print("-" * 80)
    
    async for session in get_async_session():
        try:
            configs = await config_service.get_all_configs(session)
            
            if not configs:
                print("No configuration items found")
                return
            
            for config in configs:
                print(f"Key: {config.key}")
                print(f"Value: {config.get_value()}")
                print(f"Description: {config.description}")
                print(f"Public: {'Yes' if config.is_public else 'No'}")
                print(f"Enabled: {'Yes' if config.is_enabled else 'No'}")
                print("-" * 40)
                
        except Exception as e:
            print(f"Error getting configuration list: {e}")
        
        finally:
            await session.close()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--list":
        # List current configurations
        asyncio.run(list_current_configs())
    else:
        # Initialize default configurations
        success = asyncio.run(init_default_configs())
        
        if success:
            print("\nYou can use --list parameter to view all current configurations")
        else:
            sys.exit(1)