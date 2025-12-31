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
from src.system_config.api.v1.schemas import ConfigCreate


# Default configuration items
DEFAULT_CONFIGS = [
    {
        "key": "registration_enabled",
        "value": True,
        "description": "Whether user registration is enabled",
        "is_public": True,
        "is_enabled": True
    },
    {
        "key": "conversation_title_model_id",
        "value": '',
        "description": "Model ID for generating conversation titles, uses conversation assistant model if empty",
        "is_public": False,
        "is_enabled": True
    },
    {
        "key": "allow_user_create_assistants",
        "value": False,
        "description": "Whether to allow users to create assistants",
        "is_public": True,
        "is_enabled": True
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
            
            for config_data in DEFAULT_CONFIGS:
                try:
                    # Check if configuration item already exists
                    existing_config = await config_service.get_config(session, config_data["key"])
                    
                    if existing_config:
                        print(f"Configuration item '{config_data['key']}' already exists, skipping")
                        skipped_count += 1
                        continue
                    
                    # Create new configuration item
                    config_create = ConfigCreate(**config_data)
                    created_config = await config_service.create_config(session, config_create)
                    print(f"Created configuration item '{created_config.key}': {created_config.get_value()}")
                    created_count += 1
                    
                except Exception as e:
                    print(f"Error creating configuration item '{config_data['key']}': {e}")
                    continue
            
            print("\nInitialization completed!")
            print(f"Created {created_count} new configuration items")
            print(f"Skipped {skipped_count} existing configuration items")
            
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