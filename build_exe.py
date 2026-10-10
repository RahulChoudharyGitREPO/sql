"""
Build script for SQL Studio Standalone Windows EXE
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
if hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent

def build():
    print("=" * 60)
    print("[Build] Compiling SQL Studio into standalone Windows .EXE...")
    print("=" * 60)
    
    os.chdir(str(BASE_DIR))
    
    static_dir = BASE_DIR / "static"
    ico_path = BASE_DIR / "app_icon.ico"
    
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=SQLStudio",
        "--onefile",
        "--noconsole",
        "--windowed",
        "--clean",
        "--noconfirm",
        f"--icon={ico_path}",
        f"--add-data={static_dir};static",
        "--hidden-import=uvicorn.logging",
        "--hidden-import=uvicorn.loops",
        "--hidden-import=uvicorn.loops.auto",
        "--hidden-import=uvicorn.protocols",
        "--hidden-import=uvicorn.protocols.http",
        "--hidden-import=uvicorn.protocols.http.auto",
        "--hidden-import=uvicorn.protocols.websockets",
        "--hidden-import=uvicorn.protocols.websockets.auto",
        "--hidden-import=uvicorn.lifespans",
        "--hidden-import=uvicorn.lifespans.on",
        "--hidden-import=pandas",
        "--hidden-import=openpyxl",
        "--hidden-import=sqlite3",
        # EXCLUDE UNRELATED HEAVY PACKAGES TO PREVENT UNZIP LAG
        "--exclude-module=torch",
        "--exclude-module=torchvision",
        "--exclude-module=scipy",
        "--exclude-module=matplotlib",
        "--exclude-module=sympy",
        "--exclude-module=IPython",
        "--exclude-module=cv2",
        "--exclude-module=tensorboard",
        "--exclude-module=pytest",
        "run_studio.py"
    ]
    
    print("Running command:", " ".join(cmd))
    res = subprocess.run(cmd)
    
    if res.returncode == 0:
        dist_exe = BASE_DIR / "dist" / "SQLStudio.exe"
        if dist_exe.exists():
            # Kill running instances before copying
            subprocess.run(["taskkill", "/F", "/IM", "SQLStudio.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            import time
            time.sleep(0.5)
            # Copy to sql_studio root for convenient access
            dest_exe = BASE_DIR / "SQLStudio.exe"
            shutil.copy2(dist_exe, dest_exe)
            print("=" * 60)
            print("[SUCCESS] Build SUCCESSFUL!")
            print(f"[SUCCESS] EXE Path: {dest_exe}")
            print(f"[SUCCESS] Size: {round(dest_exe.stat().st_size / (1024*1024), 2)} MB")
            print("=" * 60)
    else:
        print("[ERROR] Build failed with exit code:", res.returncode)

if __name__ == "__main__":
    build()
