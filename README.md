# 🐝 SQL Studio — 

> Fast, beautiful, lightweight SQL client with **100% Free & Unlimited Import/Export** (CSV, Excel, JSON, SQL Dumps) and built-in Auto-Updates.

---

## ✨ Features

- 🎨 **Beekeeper Studio Dark Palette**: Dracula syntax highlighting, table tree, schema viewer, and tabbed query workspace.
- ⚡ **Unlimited Data Import**: Direct import of CSV, Excel (`.xlsx`, `.xls`), JSON, and raw SQL script dumps.
- 🚀 **Unlimited Data Export**: Direct export of query results and table dumps in CSV, Excel, JSON, SQL `INSERT` statements, and Markdown tables.
- 🔄 **Over-the-Air (OTA) Auto-Updater**: Checks for updates on startup via GitHub Releases. When an update is published, users get an instant update modal and 1-click upgrade without reinstalling.
- 💾 **Safe Local Persistence**: Stores databases and query history in `%APPDATA%/SQLStudio/data`.
- 🪟 **Zero Console / Sub-second Launch**: Single standalone `.exe` compiled with PyInstaller windowed mode.

---

## 🛠️ How to Run from Source

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run application
python run_studio.py
```

---

## 📦 How to Build Standalone Windows EXE

```bash
python build_exe.py
```
This produces `SQLStudio.exe` (~52 MB) with custom icons and embedded static assets.

---

## 🚀 How to Publish Updates to All Users

1. Make your changes and update `APP_VERSION` in `app.py`.
2. Commit and tag a release:
```bash
git add .
git commit -m "Add new features"
git tag v1.0.1
git push origin main --tags
```
3. GitHub Actions will automatically compile `SQLStudio.exe` and publish the release. All running instances will notify users with a 1-click update popup!
