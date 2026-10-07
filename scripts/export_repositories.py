import os
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SCRATCH_DIR = BASE_DIR / "scratch"

API_EXPORT_DIR = SCRATCH_DIR / "nextrole-api"
UI_EXPORT_DIR = SCRATCH_DIR / "nextrole-ui"

# Ensure scratch exists
SCRATCH_DIR.mkdir(exist_ok=True)

# -------------------------------------------------------------
# 1. Export Backend: nextrole-api
# -------------------------------------------------------------
print("Preparing nextrole-api...")
if API_EXPORT_DIR.exists():
    shutil.rmtree(API_EXPORT_DIR)
API_EXPORT_DIR.mkdir(parents=True, exist_ok=True)

app_dir = BASE_DIR / "app"

# Items to copy from app/
for item in app_dir.iterdir():
    if item.name in ["__pycache__", ".pytest_cache", "data"]:
        continue
    dest = API_EXPORT_DIR / item.name
    if item.is_dir():
        shutil.copytree(item, dest, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache"))
    else:
        shutil.copy2(item, dest)

# Backend .gitignore
api_gitignore = """# Python Virtual Environments
env/
venv/
.venv/

# Byte-code & Cache
__pycache__/
*.py[cod]
*$py.class
.pytest_cache/

# Local cache
data/
*.cache.json

# OS files
.DS_Store
Thumbs.db
"""
with open(API_EXPORT_DIR / ".gitignore", "w", encoding="utf-8") as f:
    f.write(api_gitignore)

# Backend README.md
api_readme = """# NextRole Backend API

Production-ready REST API for NextRole Job Discovery Platform. Built with **FastAPI**, **SQLAlchemy**, and **PostgreSQL**.

## Deployment (Render)
- **Runtime**: Python 3
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn server:app --host 0.0.0.0 --port $PORT`

## Environment Variables
- `DATABASE_URL`: PostgreSQL connection string (e.g. Aiven Cloud)
- `JWT_SECRET`: Secret key for JWT access tokens
- `ADMIN_EMAIL`: Default administrator email
- `ADMIN_INITIAL_PASSWORD`: Administrator password
"""
with open(API_EXPORT_DIR / "README.md", "w", encoding="utf-8") as f:
    f.write(api_readme)

print(f"nextrole-api prepared at {API_EXPORT_DIR}")

# -------------------------------------------------------------
# 2. Export Frontend: nextrole-ui
# -------------------------------------------------------------
print("Preparing nextrole-ui...")
if UI_EXPORT_DIR.exists():
    shutil.rmtree(UI_EXPORT_DIR)
UI_EXPORT_DIR.mkdir(parents=True, exist_ok=True)

frontend_dir = BASE_DIR / "frontend"

# Items to copy from frontend/
for item in frontend_dir.iterdir():
    if item.name in ["node_modules", "dist", ".git", ".next", ".turbo"]:
        continue
    dest = UI_EXPORT_DIR / item.name
    if item.is_dir():
        shutil.copytree(item, dest, ignore=shutil.ignore_patterns("node_modules", "dist", ".cache"))
    else:
        shutil.copy2(item, dest)

# Frontend .gitignore
ui_gitignore = """# Dependencies
node_modules/
.pnp
.pnp.js

# Build Outputs
dist/
dist-ssr/
build/

# Local environment
.env.local
.env.development.local
.env.test.local
.env.production.local

# Editor & OS
.vscode/
.idea/
.DS_Store
Thumbs.db
"""
with open(UI_EXPORT_DIR / ".gitignore", "w", encoding="utf-8") as f:
    f.write(ui_gitignore)

# Frontend README.md
ui_readme = """# NextRole Frontend UI

Modern, responsive web application for NextRole Job Discovery Platform. Built with **React 19**, **Vite**, **TypeScript**, and **Tailwind CSS**.

## Deployment (Vercel / Render Static Site)
- **Build Command**: `npm run build`
- **Publish Directory**: `dist`
"""
with open(UI_EXPORT_DIR / "README.md", "w", encoding="utf-8") as f:
    f.write(ui_readme)

print(f"nextrole-ui prepared at {UI_EXPORT_DIR}")
print("All exports prepared successfully.")
