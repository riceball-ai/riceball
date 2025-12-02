#!/usr/bin/env python3
"""
Create superuser script

Usage:
    python scripts/create_superuser.py
    
Or with environment variables:
    SUPERUSER_EMAIL=admin@example.com SUPERUSER_PASSWORD=password python scripts/create_superuser.py
"""

import asyncio
import os
import sys
from getpass import getpass
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Project imports need to be after path setup (ignore lint warnings)
from sqlalchemy import select  # noqa: E402

from src.database import async_session_maker  # noqa: E402
from src.users.models import User  # noqa: E402
from src.auth.manager import get_user_manager  # noqa: E402

# Import all models to ensure proper relationship resolution
from src.assistants.models import Assistant, Conversation, Message  # noqa: E402, F401
from src.ai_models.models import Model, ModelProvider  # noqa: E402, F401
from src.auth.refresh_token_models import RefreshToken  # noqa: E402, F401
from src.agents.models import AgentExecution, MCPServerConfig  # noqa: E402, F401


def get_email_input() -> str:
    """Get email address input"""
    email = os.getenv("SUPERUSER_EMAIL")
    if email:
        print(f"Using email from environment variable: {email}")
        return email
    
    while True:
        email = input("Enter superuser email address: ").strip()
        if email and "@" in email:
            return email
        print("Please enter a valid email address")


def get_password_input() -> str:
    """Get password input"""
    password = os.getenv("SUPERUSER_PASSWORD")
    if password:
        print("Using password from environment variable")
        return password
    
    while True:
        password = getpass("Enter password: ")
        if len(password) >= 8:
            confirm_password = getpass("Confirm password: ")
            if password == confirm_password:
                return password
            else:
                print("Passwords do not match, please try again")
        else:
            print("Password must be at least 8 characters long")


async def create_superuser():
    """Create superuser"""
    print("=== Creating Superuser ===")
    
    # Get input
    email = get_email_input()
    password = get_password_input()
    
    try:
        async with async_session_maker() as session:
            # Initialize user database with session
            from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
            user_db = SQLAlchemyUserDatabase(session, User)
            
            # Get user manager
            user_manager_gen = get_user_manager(user_db)
            user_manager = await user_manager_gen.__anext__()
            
            # Check if user already exists
            existing_user = await user_db.get_by_email(email)
            if existing_user:
                print(f"ℹ️  User {email} already exists, skipping creation")
                return
            
            # Create user directly without UserCreate schema
            hashed_password = user_manager.password_helper.hash(password)
            
            user = User(
                email=email,
                hashed_password=hashed_password,
                is_superuser=True,
                is_verified=True,
                is_active=True
            )
            
            session.add(user)
            await session.commit()
            await session.refresh(user)
            
            print("✅ Superuser created successfully!")
            print(f"   Email: {user.email}")
            print(f"   ID: {user.id}")
            print(f"   Is superuser: {user.is_superuser}")
            print(f"   Is verified: {user.is_verified}")
                
    except Exception as e:
        print(f"❌ Error: {e}")


async def list_superusers():
    """List all superusers"""
    print("\n=== Current Superuser List ===")
    
    try:
        async with async_session_maker() as session:
            # Query superusers directly
            stmt = select(User).where(User.is_superuser)
            result = await session.execute(stmt)
            superusers = result.scalars().all()
            
            if superusers:
                for user in superusers:
                    status = "✅ Active" if user.is_active else "❌ Inactive"
                    verified = "✅ Verified" if user.is_verified else "❌ Unverified"
                    print(f"  • {user.email} (ID: {user.id})")
                    print(f"    Status: {status}, Verification: {verified}")
                    print(f"    Created: {user.created_at}")
                    print()
            else:
                print("  No superusers found")
                
    except Exception as e:
        print(f"❌ Error querying superusers: {e}")


async def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Superuser management script")
    parser.add_argument("--list", action="store_true", help="List all superusers")
    
    args = parser.parse_args()
    
    if args.list:
        await list_superusers()
    else:
        await create_superuser()
        await list_superusers()


if __name__ == "__main__":
    asyncio.run(main())