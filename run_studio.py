import os
import sys
import time
import subprocess
import webbrowser
import threading
import multiprocessing
import traceback
from pathlib import Path

# Always initialize multiprocessing freeze support first for Windows PyInstaller
multiprocessing.freeze_support()

# Setup log directory in AppData or Temp
try:
    appdata = os.environ.get("APPDATA")
    if appdata:
        LOG_DIR = Path(appdata) / "SQLStudio"
    else:
        LOG_DIR = Path.home() / ".sql_studio"
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    LOG_FILE = LOG_DIR / "sql_studio_launcher.log"
except Exception:
    LOG_FILE = Path(os.environ.get("TEMP", ".")) / "sql_studio_launcher.log"

def log(msg):
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
    except Exception:
        pass

log(f"SQL Studio Launcher starting... sys.frozen={getattr(sys, 'frozen', False)}, executable={sys.executable}")

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

if sys.stdout is None:
    sys.stdout = open(os.devnull, 'w', encoding='utf-8')
if sys.stderr is None:
    sys.stderr = open(os.devnull, 'w', encoding='utf-8')

import socket

def find_free_port(start_port=5050, max_attempts=50):
    for p in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                if s.connect_ex(('127.0.0.1', p)) != 0:
                    return p
        except Exception:
            return p
    return start_port

def launch_browser(port):
    time.sleep(1.0)
    url = f"http://localhost:{port}"
    log(f"Attempting to launch browser window for {url}")
    
    # Try launching Chrome in app mode for native desktop feel
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
    ]
    
    launched = False
    for cp in chrome_paths:
        if os.path.exists(cp):
            try:
                subprocess.Popen([cp, f"--app={url}", "--window-size=1280,820", "--window-position=100,80"])
                launched = True
                log(f"Launched in native desktop window via {os.path.basename(cp)}")
                break
            except Exception as e:
                log(f"Failed to launch {cp}: {e}")
                
    if not launched:
        try:
            webbrowser.open(url)
            log(f"Opened in default browser: {url}")
        except Exception as e:
            log(f"Failed to open default browser: {e}")

if __name__ == "__main__":
    try:
        port = find_free_port(5050)
        log(f"Selected port: {port}")
        
        # Start browser launcher in background thread
        threading.Thread(target=launch_browser, args=(port,), daemon=True).start()
        
        # Start FastAPI server
        import uvicorn
        from app import app
        
        log("Imported app successfully. Starting uvicorn...")
        # Note: In PyInstaller frozen exe, uvicorn must run the app object directly, not string "app:app"
        config = uvicorn.Config(app=app, host="127.0.0.1", port=port, log_level="warning", access_log=False)
        server = uvicorn.Server(config)
        server.run()
        log("Uvicorn server exited cleanly.")
    except Exception as e:
        log(f"CRITICAL ERROR in __main__: {traceback.format_exc()}")

