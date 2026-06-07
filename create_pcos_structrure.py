#!/usr/bin/env python3
"""Create the complete PCOS project structure with stub files."""

import os
from pathlib import Path

# Get current directory (where script is run)
ROOT = Path.cwd()
print(f"Creating PCOS project structure in {ROOT}")

# ============================================================
# 1. Create directory tree
# ============================================================
dirs = [
    "src/pcos/api/routers",
    "src/pcos/api/schemas",
    "src/pcos/core",
    "src/pcos/infrastructure/win32",
    "src/pcos/workers",
    "src/pcos/ui",
    "src/pcos/tests/unit",
    "src/pcos/tests/integration",
    "data",
    "logs",
    "scripts",
]

for d in dirs:
    (ROOT / d).mkdir(parents=True, exist_ok=True)
    print(f"  Created: {d}")

# ============================================================
# 2. Create __init__.py files
# ============================================================
init_files = [
    "src/pcos/__init__.py",
    "src/pcos/api/__init__.py",
    "src/pcos/api/routers/__init__.py",
    "src/pcos/api/schemas/__init__.py",
    "src/pcos/core/__init__.py",
    "src/pcos/infrastructure/__init__.py",
    "src/pcos/infrastructure/win32/__init__.py",
    "src/pcos/workers/__init__.py",
    "src/pcos/ui/__init__.py",
    "src/pcos/tests/__init__.py",
    "src/pcos/tests/unit/__init__.py",
    "src/pcos/tests/integration/__init__.py",
]

for f in init_files:
    (ROOT / f).touch()
    print(f"  Created: {f}")

# ============================================================
# 3. Write all source files
# ============================================================

# infrastructure/settings.py
(ROOT / "src/pcos/infrastructure/settings.py").write_text('''
import os
from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    API_HOST: str = "127.0.0.1"
    API_PORT: int = 8765
    LOG_LEVEL: str = "INFO"
    PCOS_DATA_DIR: Path = Path(os.environ.get("PCOS_DATA_DIR", "E:/pcos_data"))
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
'''.strip())



# Create empty worker files
for worker in ["state_monitor.py", "push_worker.py", "embedding_worker.py"]:
    (ROOT / f"src/pcos/workers/{worker}").write_text("# Stub for future implementation")

# Create empty router files
for router in ["capture.py", "notes.py", "state.py", "tasks.py", "feedback.py", "divergence.py", "convergence.py"]:
    (ROOT / f"src/pcos/api/routers/{router}").write_text("# Stub for future implementation")

# Create empty schema files
for schema in ["capture.py", "note.py", "task.py", "state.py"]:
    (ROOT / f"src/pcos/api/schemas/{schema}").write_text("# Stub for future implementation")

# Create empty core service files
for service in ["capture_service.py", "state_service.py", "memory_service.py", 
                "push_service.py", "feedback_service.py", "divergence_service.py",
                "convergence_service.py", "reflection_service.py"]:
    (ROOT / f"src/pcos/core/{service}").write_text("# Stub for future implementation")

# Create empty win32 stub files
(ROOT / "src/pcos/infrastructure/win32/state_detector.py").write_text("# Stub for future implementation")
(ROOT / "src/pcos/infrastructure/win32/notifier.py").write_text("# Stub for future implementation")

# ============================================================
# 4. Create requirements.txt
# ============================================================
(ROOT / "requirements.txt").write_text('''
fastapi==0.110.0
uvicorn==0.27.1
PyQt6==6.6.1
pynput==1.7.6
pywin32==306
loguru==0.7.2
psutil==5.9.8
pydantic-settings==2.2.1
'''.strip())

# ============================================================
# 5. Create .env template
# ============================================================
(ROOT / ".env").write_text('''
# PCOS configuration – set your preferred data directory
PCOS_DATA_DIR=E:/pcos_data
API_HOST=127.0.0.1
API_PORT=8765
LOG_LEVEL=INFO
'''.strip())

# ============================================================
# 6. Create README.md
# ============================================================
(ROOT / "README.md").write_text('''
# PCOS – Personal Cognitive Operating System

## Setup
1. `python -m venv venv`
2. `venv\\Scripts\\activate` (Windows) or `source venv/bin/activate` (Linux/Mac)
3. `pip install -r requirements.txt`
4. Edit `.env` to set your data directory (default E:/pcos_data)
5. `python -m src.pcos.main`

## Project structure
See architecture reference. Data directory configurable via PCOS_DATA_DIR env or .env file.
'''.strip())

# ============================================================
# 7. Create run script
# ============================================================
(ROOT / "run.ps1").write_text('''
# PowerShell run script
.\\venv\\Scripts\\Activate.ps1
python -m src.pcos.main
'''.strip())

(ROOT / "run.bat").write_text('''
@echo off
call venv\\Scripts\\activate.bat
python -m src.pcos.main
'''.strip())

# ============================================================
# 8. Create .gitignore
# ============================================================
(ROOT / ".gitignore").write_text('''
venv/
__pycache__/
*.pyc
.pytest_cache/
*.log
data/
logs/
.pcos_data/
'''.strip())

print("\n" + "="*50)
print("✅ PCOS project structure created successfully!")
print("="*50)
print("\nNext steps:")
print(f"  1. cd {ROOT}")
print("  2. python -m venv venv")
print("  3. venv\\Scripts\\activate (Windows) or source venv/bin/activate (Unix)")
print("  4. pip install -r requirements.txt")
print("  5. python -m src.pcos.main")
print("  6. Test API: curl http://localhost:8765/health")