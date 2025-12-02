#!/usr/bin/env python3
"""Create a new app module skeleton inside src/.

Usage:
    python scripts/new_app.py newapp

This will create:
    src/newapp/
        __init__.py
        models.py
        api/__init__.py
        api/router.py
        api/v1/__init__.py
        api/v1/router.py
        api/v1/schemas.py

If the target already exists, the script aborts (unless --force provided).
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"

ROUTER_TEMPLATE = """from fastapi import APIRouter

from .v1.router import router as v1_router

router = APIRouter()
router.include_router(v1_router, prefix="/v1/{name}", tags=["{class_name}"])
"""

V1_ROUTER_TEMPLATE = """from fastapi import APIRouter

router = APIRouter()

@router.get("/ping", summary="Health check")
async def ping():
    return {{"status": "ok", "service": "{name}"}}
"""

SCHEMAS_TEMPLATE = """from pydantic import BaseModel
"""

MODELS_TEMPLATE = """from src.model import Base  # SQLAlchemy declarative Base
from sqlalchemy.orm import Mapped, mapped_column
"""

ROOT_ROUTER_IMPORT_HINT = """
# To enable this module's routes, add the following line in src/main.py:
# from .{name}.api.router import router as {name}_router
# app.include_router({name}_router, prefix="/api")
"""

def pascal(name: str) -> str:
    return ''.join(part.capitalize() for part in name.replace('-', '_').split('_'))

def create_module(name: str, force: bool = False) -> None:
    target = SRC / name
    if target.exists() and not force:
        print(f"[ERROR] {target} already exists. Use --force to overwrite (will not delete existing files).", file=sys.stderr)
        sys.exit(1)

    # Ensure directories
    (target / "api" / "v1").mkdir(parents=True, exist_ok=True)

    class_name = pascal(name)

    files: dict[Path, str] = {
        target / "__init__.py": "",
        target / "models.py": MODELS_TEMPLATE.format(class_name=class_name, name=name),
        target / "api" / "__init__.py": "",
        target / "api" / "router.py": ROUTER_TEMPLATE.format(name=name, class_name=class_name),
        target / "api" / "v1" / "__init__.py": "",
        target / "api" / "v1" / "router.py": V1_ROUTER_TEMPLATE.format(name=name),
        target / "api" / "v1" / "schemas.py": SCHEMAS_TEMPLATE.format(class_name=class_name),
    }

    for path, content in files.items():
        if path.exists() and not force:
            print(f"[SKIP] {path} exists.")
            continue
        path.write_text(content, encoding="utf-8")
        print(f"[WRITE] {path.relative_to(ROOT)}")

    print(ROOT_ROUTER_IMPORT_HINT.format(name=name))


def main():
    parser = argparse.ArgumentParser(description="Create a new application module skeleton")
    parser.add_argument("name", help="New module (package) name under src/")
    parser.add_argument("--force", action="store_true", help="Overwrite existing files if they exist")
    args = parser.parse_args()

    if not SRC.exists():
        print("[ERROR] src directory not found", file=sys.stderr)
        sys.exit(2)

    create_module(args.name, force=args.force)

if __name__ == "__main__":
    main()
