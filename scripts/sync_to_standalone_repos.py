import os
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
APP_DIR = BASE_DIR / "app"
FRONTEND_DIR = BASE_DIR / "frontend"
API_EXPORT = BASE_DIR / "scratch" / "nextrole-api"
UI_EXPORT = BASE_DIR / "scratch" / "nextrole-ui"

def copy_tree_contents(src: Path, dst: Path, ignore_names: set):
    """Copies all items from src into dst, preserving dst/.git and updating files."""
    dst.mkdir(parents=True, exist_ok=True)
    
    # 1. Clean existing files/folders in dst that are not in ignore_names
    for item in dst.iterdir():
        if item.name == ".git":
            continue
        if item.name not in [x.name for x in src.iterdir()]:
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()

    # 2. Copy items from src to dst
    for item in src.iterdir():
        if item.name in ignore_names:
            continue
        target = dst / item.name
        if item.is_dir():
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(
                item,
                target,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache", "node_modules", "dist", ".cache")
            )
        else:
            shutil.copy2(item, target)

def sync_repos():
    print("Syncing backend to scratch/nextrole-api...")
    copy_tree_contents(APP_DIR, API_EXPORT, ignore_names={"__pycache__", ".pytest_cache", "data", ".env", ".git"})
    
    print("Syncing frontend to scratch/nextrole-ui...")
    copy_tree_contents(FRONTEND_DIR, UI_EXPORT, ignore_names={"node_modules", "dist", ".git", ".cache"})
    
    print("Sync completed successfully.")

if __name__ == "__main__":
    sync_repos()
