"""
SQL Studio - Beekeeper Studio Clone
Fast, beautiful, lightweight SQL client with unlimited free import/export (CSV, Excel, JSON, SQL).
"""

import os
import sys
import time
import json
import sqlite3
import traceback
import io
from pathlib import Path
from typing import Optional, List, Dict, Any

import pandas as pd
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query, Response
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

if sys.stdout is None:
    sys.stdout = open(os.devnull, 'w')
if sys.stderr is None:
    sys.stderr = open(os.devnull, 'w')

# Path resolution for standalone EXE and source
if getattr(sys, 'frozen', False):
    EXE_DIR = Path(sys.executable).resolve().parent
    MEIPASS_DIR = Path(sys._MEIPASS).resolve()
    STATIC_DIR = MEIPASS_DIR / "static" if (MEIPASS_DIR / "static").exists() else EXE_DIR / "static"
    
    # Store persistent databases in user AppData (or fallback to local folder)
    appdata = os.environ.get("APPDATA")
    if appdata:
        DATA_DIR = Path(appdata) / "SQLStudio" / "data"
    else:
        DATA_DIR = Path.home() / ".sql_studio" / "data"
else:
    BASE_DIR = Path(__file__).resolve().parent
    STATIC_DIR = BASE_DIR / "static"
    DATA_DIR = BASE_DIR / "data"

DATA_DIR.mkdir(parents=True, exist_ok=True)
STATIC_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="SQL Studio - Beekeeper Clone", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Active Database State
CURRENT_DB_PATH = str(DATA_DIR / "workspace.db")
HISTORY_FILE = DATA_DIR / "query_history.json"
SAVED_QUERIES_FILE = DATA_DIR / "saved_queries.json"

def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    target = db_path or CURRENT_DB_PATH
    conn = sqlite3.connect(target, timeout=20.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_sample_data():
    """Seed sample tables for instant testing (E-Commerce & Store Revenue)."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Store Daily Sales
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS store_daily_sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        store TEXT NOT NULL,
        sale_date DATE NOT NULL,
        revenue REAL NOT NULL,
        orders_count INTEGER DEFAULT 0
    );
    """)
    cursor.execute("SELECT COUNT(*) FROM store_daily_sales;")
    if cursor.fetchone()[0] == 0:
        sample_sales = [
            ("Koramangala", "2026-09-01", 3200, 45),
            ("Koramangala", "2026-09-02", 2800, 39),
            ("Koramangala", "2026-09-03", 4100, 58),
            ("Koramangala", "2026-09-04", 3900, 52),
            ("Koramangala", "2026-09-05", 5200, 71),
            ("Indiranagar", "2026-09-01", 2900, 41),
            ("Indiranagar", "2026-09-02", 3100, 44),
            ("Indiranagar", "2026-09-03", 3400, 48),
            ("Indiranagar", "2026-09-04", 4300, 60),
            ("Indiranagar", "2026-09-05", 4800, 65),
            ("Whitefield", "2026-09-01", 1800, 25),
            ("Whitefield", "2026-09-02", 2100, 30),
            ("Whitefield", "2026-09-03", 2600, 36),
            ("Whitefield", "2026-09-04", 3100, 42),
            ("Whitefield", "2026-09-05", 3500, 49),
        ]
        cursor.executemany("INSERT INTO store_daily_sales (store, sale_date, revenue, orders_count) VALUES (?, ?, ?, ?);", sample_sales)

    # 2. Payment Gateway & Bank Settlements (Reconciliation Problem)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS gateway_txns (
        order_ref TEXT PRIMARY KEY,
        customer_name TEXT,
        amount REAL,
        status TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bank_settlements (
        settlement_id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_ref TEXT,
        amount REAL,
        bank_ref TEXT,
        settled_date DATE
    );
    """)
    cursor.execute("SELECT COUNT(*) FROM gateway_txns;")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO gateway_txns (order_ref, customer_name, amount, status) VALUES (?, ?, ?, ?);", [
            ("ORD-501", "Aarav Sharma", 4999.0, "Success"),
            ("ORD-502", "Priya Patel", 2999.0, "Success"),
            ("ORD-503", "Rohan Verma", 1250.0, "Failed"),
            ("ORD-504", "Sneha Iyer", 1500.0, "Success"),
            ("ORD-505", "Vikram Malhotra", 8990.0, "Success"),
        ])
        cursor.executemany("INSERT INTO bank_settlements (order_ref, amount, bank_ref, settled_date) VALUES (?, ?, ?, ?);", [
            ("ORD-501", 4999.0, "HDFC-TXN-9811", "2026-09-02"),
            ("ORD-502", 2899.0, "ICICI-TXN-4421", "2026-09-02"), # amount mismatch
            ("ORD-505", 8990.0, "HDFC-TXN-9812", "2026-09-03"),
            ("ORD-506", 750.0, "SBI-TXN-1109", "2026-09-04"),    # missing in gateway
        ])

    # 3. User Logins (Streaks & Retention)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_logins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        login_date DATE,
        ip_address TEXT,
        device TEXT
    );
    """)
    cursor.execute("SELECT COUNT(*) FROM user_logins;")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO user_logins (user_id, login_date, ip_address, device) VALUES (?, ?, ?, ?);", [
            (101, "2026-03-01", "192.168.1.1", "Mobile"),
            (101, "2026-03-02", "192.168.1.1", "Desktop"),
            (101, "2026-03-03", "192.168.1.1", "Mobile"),
            (101, "2026-03-05", "192.168.1.1", "Desktop"),
            (102, "2026-03-01", "10.0.0.5", "Desktop"),
            (102, "2026-03-03", "10.0.0.5", "Mobile"),
            (103, "2026-03-10", "172.16.0.2", "Mobile"),
            (103, "2026-03-11", "172.16.0.2", "Mobile"),
            (103, "2026-03-12", "172.16.0.2", "Desktop"),
            (103, "2026-03-13", "172.16.0.2", "Mobile"),
            (103, "2026-03-15", "172.16.0.2", "Desktop"),
        ])
    
    conn.commit()
    conn.close()

init_sample_data()

# ===========================================================================
# PYDANTIC SCHEMAS
# ===========================================================================

class QueryRequest(BaseModel):
    query: str
    db_path: Optional[str] = None
    limit: Optional[int] = 500
    offset: Optional[int] = 0

class SaveQueryRequest(BaseModel):
    title: str
    query: str

class SwitchDBRequest(BaseModel):
    db_path: str

class CreateTableRequest(BaseModel):
    table_name: str
    columns: List[Dict[str, str]] # [{"name": "id", "type": "INTEGER PRIMARY KEY"}, ...]

class UpdateCellRequest(BaseModel):
    table: str
    primary_key_col: str
    primary_key_val: Any
    column: str
    new_value: Any

class InsertRowRequest(BaseModel):
    table: str
    data: Dict[str, Any]

class DeleteRowRequest(BaseModel):
    table: str
    primary_key_col: str
    primary_key_val: Any

# ===========================================================================
# API ENDPOINTS
# ===========================================================================

@app.get("/api/databases")
def list_databases():
    """List available local database files."""
    db_files = []
    for ext in ["*.db", "*.sqlite", "*.sqlite3"]:
        for f in DATA_DIR.glob(ext):
            db_files.append({
                "name": f.name,
                "path": str(f.resolve()),
                "size_kb": round(f.stat().st_size / 1024, 2),
                "active": str(f.resolve()) == os.path.abspath(CURRENT_DB_PATH)
            })
    return {
        "current_db": CURRENT_DB_PATH,
        "databases": db_files
    }

@app.post("/api/databases/switch")
def switch_database(req: SwitchDBRequest):
    global CURRENT_DB_PATH
    path = req.db_path
    if not path.endswith((".db", ".sqlite", ".sqlite3")):
        path += ".db"
    full_path = os.path.abspath(path)
    CURRENT_DB_PATH = full_path
    # test connection
    conn = get_connection()
    conn.close()
    return {"status": "ok", "current_db": CURRENT_DB_PATH}

@app.post("/api/databases/new")
def create_new_database(name: str = Form(...)):
    global CURRENT_DB_PATH
    if not name.endswith(".db"):
        name += ".db"
    new_path = DATA_DIR / name
    conn = sqlite3.connect(str(new_path))
    conn.execute("CREATE TABLE IF NOT EXISTS _studio_init (id INTEGER PRIMARY KEY);")
    conn.commit()
    conn.close()
    CURRENT_DB_PATH = str(new_path.resolve())
    return {"status": "ok", "current_db": CURRENT_DB_PATH}

@app.get("/api/tables")
def get_tables():
    """Get tables, views, column details, and row counts."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    SELECT name, type 
    FROM sqlite_master 
    WHERE type IN ('table', 'view') AND name NOT LIKE 'sqlite_%' AND name NOT LIKE '_studio_%'
    ORDER BY name ASC;
    """)
    tables_meta = cursor.fetchall()
    
    result = []
    for row in tables_meta:
        t_name = row["name"]
        t_type = row["type"]
        
        # Row count
        try:
            cursor.execute(f'SELECT COUNT(*) FROM "{t_name}";')
            cnt = cursor.fetchone()[0]
        except Exception:
            cnt = 0
            
        # Columns
        cursor.execute(f'PRAGMA table_info("{t_name}");')
        cols = []
        for c in cursor.fetchall():
            cols.append({
                "cid": c[0],
                "name": c[1],
                "type": c[2] or "TEXT",
                "notnull": bool(c[3]),
                "dflt_value": c[4],
                "pk": bool(c[5])
            })
            
        result.append({
            "name": t_name,
            "type": t_type,
            "row_count": cnt,
            "columns": cols
        })
        
    conn.close()
    return {"tables": result, "database": os.path.basename(CURRENT_DB_PATH)}

@app.post("/api/query")
def execute_query(req: QueryRequest):
    """Execute arbitrary SQL query with execution timing and safety."""
    start_time = time.perf_counter()
    sql = req.query.strip()
    if not sql:
        return {"columns": [], "rows": [], "execution_time_ms": 0, "row_count": 0, "status": "empty"}
    
    # Save to history
    save_history(sql)
    
    conn = get_connection(req.db_path)
    cursor = conn.cursor()
    
    # Split multiple statements if any
    statements = [s.strip() for s in sql.split(";") if s.strip()]
    last_columns = []
    last_rows = []
    affected_rows = 0
    
    try:
        for idx, stmt in enumerate(statements):
            is_last = (idx == len(statements) - 1)
            cursor.execute(stmt)
            if stmt.strip().upper().startswith(("INSERT", "UPDATE", "DELETE", "REPLACE", "CREATE", "DROP", "ALTER")):
                affected_rows += cursor.rowcount if cursor.rowcount > 0 else 0
                conn.commit()
            
            if is_last and cursor.description:
                last_columns = [desc[0] for desc in cursor.description]
                raw_rows = cursor.fetchmany(req.limit) if req.limit else cursor.fetchall()
                last_rows = [list(r) for r in raw_rows]
                
        execution_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return {
            "status": "success",
            "columns": last_columns,
            "rows": last_rows,
            "row_count": len(last_rows),
            "affected_rows": affected_rows,
            "execution_time_ms": execution_time_ms,
            "has_more": len(last_rows) == req.limit if req.limit else False
        }
    except Exception as e:
        conn.rollback()
        execution_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "error": str(e),
                "traceback": traceback.format_exc(),
                "execution_time_ms": execution_time_ms
            }
        )
    finally:
        conn.close()

@app.get("/api/table/{table_name}/data")
def get_table_data(
    table_name: str,
    limit: int = 100,
    offset: int = 0,
    sort_by: Optional[str] = None,
    sort_dir: Optional[str] = "ASC",
    search: Optional[str] = None
):
    """Fetch paginated data for table viewer."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get columns
    cursor.execute(f'PRAGMA table_info("{table_name}");')
    cols_info = cursor.fetchall()
    columns = [c[1] for c in cols_info]
    pk_col = next((c[1] for c in cols_info if c[5]), columns[0] if columns else "rowid")
    
    where_clause = ""
    params = []
    if search and search.strip():
        search_terms = []
        for col in columns:
            search_terms.append(f'CAST("{col}" AS TEXT) LIKE ?')
            params.append(f"%{search.strip()}%")
        where_clause = "WHERE " + " OR ".join(search_terms)
        
    order_clause = ""
    if sort_by and sort_by in columns:
        dir_clean = "DESC" if sort_dir.upper() == "DESC" else "ASC"
        order_clause = f'ORDER BY "{sort_by}" {dir_clean}'
        
    # Total count
    cursor.execute(f'SELECT COUNT(*) FROM "{table_name}" {where_clause};', params)
    total_rows = cursor.fetchone()[0]
    
    # Rows
    query = f'SELECT * FROM "{table_name}" {where_clause} {order_clause} LIMIT ? OFFSET ?;'
    cursor.execute(query, params + [limit, offset])
    raw_rows = cursor.fetchall()
    rows = [list(r) for r in raw_rows]
    
    conn.close()
    return {
        "table": table_name,
        "columns": columns,
        "pk_col": pk_col,
        "rows": rows,
        "total_rows": total_rows,
        "limit": limit,
        "offset": offset
    }

@app.post("/api/table/cell/update")
def update_cell(req: UpdateCellRequest):
    """Inline cell editor."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        query = f'UPDATE "{req.table}" SET "{req.column}" = ? WHERE "{req.primary_key_col}" = ?;'
        cursor.execute(query, (req.new_value, req.primary_key_val))
        conn.commit()
        return {"status": "ok", "affected": cursor.rowcount}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()

@app.post("/api/table/row/insert")
def insert_row(req: InsertRowRequest):
    """Insert a new row into table."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cols = list(req.data.keys())
        placeholders = ["?"] * len(cols)
        col_str = ", ".join([f'"{c}"' for c in cols])
        val_str = ", ".join(placeholders)
        query = f'INSERT INTO "{req.table}" ({col_str}) VALUES ({val_str});'
        cursor.execute(query, list(req.data.values()))
        conn.commit()
        return {"status": "ok", "lastrowid": cursor.lastrowid}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()

@app.post("/api/table/row/delete")
def delete_row(req: DeleteRowRequest):
    """Delete a row from table."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        query = f'DELETE FROM "{req.table}" WHERE "{req.primary_key_col}" = ?;'
        cursor.execute(query, (req.primary_key_val,))
        conn.commit()
        return {"status": "ok", "affected": cursor.rowcount}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()

# ===========================================================================
# UNLIMITED 100% FREE IMPORT (CSV, EXCEL, JSON, SQL)
# ===========================================================================

@app.post("/api/import/file")
async def import_file(
    file: UploadFile = File(...),
    table_name: Optional[str] = Form(None),
    if_exists: Optional[str] = Form("replace") # 'replace', 'append', 'fail'
):
    """Free unlimited import from CSV, XLSX, XLS, JSON, or SQL dump."""
    filename = file.filename
    ext = os.path.splitext(filename)[1].lower()
    
    inferred_table = table_name or Path(filename).stem
    inferred_table = "".join(c if c.isalnum() or c == "_" else "_" for c in inferred_table).strip("_")
    if not inferred_table:
        inferred_table = "imported_table"
        
    contents = await file.read()
    conn = get_connection()
    
    try:
        if ext in [".csv", ".tsv", ".txt"]:
            sep = "\t" if ext == ".tsv" else ","
            df = pd.read_csv(io.BytesIO(contents), sep=sep)
            df.to_sql(inferred_table, conn, if_exists=if_exists, index=False)
            row_count = len(df)
            
        elif ext in [".xlsx", ".xls"]:
            excel_file = pd.ExcelFile(io.BytesIO(contents))
            sheet_names = excel_file.sheet_names
            total_imported = 0
            # If multiple sheets, import each as table_name_sheet
            for s_name in sheet_names:
                df = pd.read_excel(excel_file, sheet_name=s_name)
                t_target = inferred_table if len(sheet_names) == 1 else f"{inferred_table}_{s_name}"
                t_target = "".join(c if c.isalnum() or c == "_" else "_" for c in t_target)
                df.to_sql(t_target, conn, if_exists=if_exists, index=False)
                total_imported += len(df)
            row_count = total_imported
            
        elif ext == ".json":
            df = pd.read_json(io.BytesIO(contents))
            df.to_sql(inferred_table, conn, if_exists=if_exists, index=False)
            row_count = len(df)
            
        elif ext == ".sql":
            sql_text = contents.decode("utf-8", errors="replace")
            cursor = conn.cursor()
            cursor.executescript(sql_text)
            conn.commit()
            row_count = "SQL Script Executed"
            
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported format: {ext}. Supported formats: CSV, Excel (.xlsx/.xls), JSON, SQL.")
            
        return {
            "status": "success",
            "table": inferred_table,
            "rows_imported": row_count,
            "filename": filename
        }
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"Import failed: {str(e)}")
    finally:
        conn.close()

# ===========================================================================
# UNLIMITED 100% FREE EXPORT (CSV, EXCEL, JSON, SQL, MARKDOWN)
# ===========================================================================

@app.post("/api/export/data")
def export_data(
    table: Optional[str] = Form(default=None),
    query: Optional[str] = Form(default=None),
    format: str = Form(default="csv") # 'csv', 'excel', 'json', 'sql', 'markdown'
):
    """Free unlimited export of any table or query result to CSV, Excel, JSON, SQL, or Markdown."""
    conn = get_connection()
    
    try:
        t_clean = table if isinstance(table, str) and table.strip() else None
        q_clean = query if isinstance(query, str) and query.strip() else None
        fmt_clean = format if isinstance(format, str) else "csv"
        
        sql = q_clean if q_clean else f'SELECT * FROM "{t_clean}";'
        df = pd.read_sql_query(sql, conn)
        base_name = t_clean or "query_export"
        
        if fmt_clean == "csv":
            stream = io.StringIO()
            df.to_csv(stream, index=False)
            response = Response(content=stream.getvalue(), media_type="text/csv")
            response.headers["Content-Disposition"] = f'attachment; filename="{base_name}.csv"'
            return response
            
        elif format == "excel":
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df.to_excel(writer, sheet_name=base_name[:30], index=False)
            output.seek(0)
            response = Response(content=output.getvalue(), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            response.headers["Content-Disposition"] = f'attachment; filename="{base_name}.xlsx"'
            return response
            
        elif format == "json":
            json_str = df.to_json(orient="records", indent=2)
            response = Response(content=json_str, media_type="application/json")
            response.headers["Content-Disposition"] = f'attachment; filename="{base_name}.json"'
            return response
            
        elif format == "markdown":
            md_str = df.to_markdown(index=False)
            response = Response(content=md_str, media_type="text/markdown")
            response.headers["Content-Disposition"] = f'attachment; filename="{base_name}.md"'
            return response
            
        elif format == "sql":
            # Generate INSERT statements
            lines = [f"-- Export of {base_name} ({len(df)} rows)", ""]
            target_tbl = base_name or "exported_table"
            for _, row in df.iterrows():
                cols = ", ".join([f'"{c}"' for c in df.columns])
                vals = []
                for val in row.values:
                    if pd.isna(val):
                        vals.append("NULL")
                    elif isinstance(val, (int, float)):
                        vals.append(str(val))
                    else:
                        escaped = str(val).replace("'", "''")
                        vals.append(f"'{escaped}'")
                lines.append(f'INSERT INTO "{target_tbl}" ({cols}) VALUES ({", ".join(vals)});')
            sql_dump = "\n".join(lines)
            response = Response(content=sql_dump, media_type="application/sql")
            response.headers["Content-Disposition"] = f'attachment; filename="{base_name}_inserts.sql"'
            return response
            
        else:
            raise HTTPException(status_code=400, detail="Invalid format. Use csv, excel, json, sql, or markdown.")
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Export error: {str(e)}")
    finally:
        conn.close()

# ===========================================================================
# QUERY HISTORY & SAVED QUERIES
# ===========================================================================

def save_history(query_str: str):
    try:
        history = []
        if HISTORY_FILE.exists():
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
        history.insert(0, {
            "query": query_str,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        })
        history = history[:100] # keep last 100
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)
    except Exception:
        pass

@app.get("/api/history")
def get_history():
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

@app.get("/api/saved_queries")
def get_saved_queries():
    if SAVED_QUERIES_FILE.exists():
        with open(SAVED_QUERIES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

@app.post("/api/saved_queries")
def save_query(req: SaveQueryRequest):
    saved = []
    if SAVED_QUERIES_FILE.exists():
        with open(SAVED_QUERIES_FILE, "r", encoding="utf-8") as f:
            saved = json.load(f)
    saved.insert(0, {
        "id": int(time.time()),
        "title": req.title,
        "query": req.query,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    })
    with open(SAVED_QUERIES_FILE, "w", encoding="utf-8") as f:
        json.dump(saved, f, indent=2)
    return {"status": "ok", "saved": saved}

# ===========================================================================
# AUTO-UPDATER SYSTEM (GitHub Releases Integration)
# ===========================================================================

APP_VERSION = "1.0.0"
GITHUB_REPO = "RahulChoudharyGitREPO/sql"

def parse_version(v_str: str):
    v = v_str.lstrip("v").strip()
    parts = []
    for p in v.split("."):
        try:
            parts.append(int(p))
        except ValueError:
            parts.append(0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])

@app.get("/api/version")
def get_version():
    return {
        "version": APP_VERSION,
        "repo": GITHUB_REPO,
        "is_frozen": getattr(sys, 'frozen', False),
        "data_dir": str(DATA_DIR)
    }

@app.get("/api/check_update")
def check_update():
    import urllib.request
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "SQLStudio-App",
                "Accept": "application/vnd.github.v3+json"
            }
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            
        latest_tag = data.get("tag_name", "1.0.0")
        latest_ver = parse_version(latest_tag)
        current_ver = parse_version(APP_VERSION)
        
        has_update = latest_ver > current_ver
        
        # Look for SQLStudio.exe asset or binary asset
        download_url = None
        for asset in data.get("assets", []):
            name = asset.get("name", "").lower()
            if name.endswith(".exe"):
                download_url = asset.get("browser_download_url")
                break
                
        if not download_url:
            download_url = data.get("html_url")
            
        return {
            "has_update": has_update,
            "current_version": APP_VERSION,
            "latest_version": latest_tag,
            "release_name": data.get("name") or latest_tag,
            "release_notes": data.get("body", "Bug fixes and improvements."),
            "download_url": download_url,
            "published_at": data.get("published_at"),
            "html_url": data.get("html_url")
        }
    except Exception as e:
        # If no releases exist yet or offline, report current version safely
        return {
            "has_update": False,
            "current_version": APP_VERSION,
            "latest_version": APP_VERSION,
            "release_name": f"Version {APP_VERSION}",
            "release_notes": "Up to date.",
            "download_url": None,
            "error": str(e)
        }

class PerformUpdateRequest(BaseModel):
    download_url: str

@app.post("/api/perform_update")
def perform_update(req: PerformUpdateRequest):
    import urllib.request
    import subprocess
    import threading
    try:
        url = req.download_url
        if not url:
            raise HTTPException(status_code=400, detail="Missing update download URL")
            
        updates_dir = DATA_DIR.parent / "updates"
        updates_dir.mkdir(parents=True, exist_ok=True)
        new_exe_path = updates_dir / "SQLStudio_latest.exe"
        
        # Download new binary
        req_obj = urllib.request.Request(url, headers={"User-Agent": "SQLStudio-Updater"})
        with urllib.request.urlopen(req_obj, timeout=120) as response, open(new_exe_path, "wb") as out_file:
            while True:
                chunk = response.read(65536)
                if not chunk:
                    break
                out_file.write(chunk)
                
        # Determine target exe path
        if getattr(sys, 'frozen', False):
            target_exe = sys.executable
        else:
            target_exe = str(BASE_DIR / "SQLStudio.exe")
            
        batch_script = updates_dir / "apply_update.bat"
        pid = os.getpid()
        
        script_content = f"""@echo off
setlocal
echo ========================================================
echo Updating SQL Studio...
echo Waiting for existing instance to stop...
echo ========================================================
timeout /t 2 /nobreak >nul
:wait_loop
tasklist /fi "PID eq {pid}" | findstr "{pid}" >nul
if %ERRORLEVEL% == 0 (
    timeout /t 1 /nobreak >nul
    goto wait_loop
)
echo Replacing binary...
copy /y "{new_exe_path}" "{target_exe}"
echo Starting updated SQL Studio...
start "" "{target_exe}"
del "%~f0"
"""
        with open(batch_script, "w", encoding="utf-8") as f:
            f.write(script_content)
            
        CREATE_NO_WINDOW = 0x08000000
        subprocess.Popen(["cmd.exe", "/c", str(batch_script)], creationflags=CREATE_NO_WINDOW)
        
        def exit_process():
            time.sleep(1.2)
            os._exit(0)
            
        threading.Thread(target=exit_process, daemon=True).start()
        
        return {"status": "ok", "message": "Update downloaded successfully! Restarting application..."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}")

# Mount static frontend
app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")

if __name__ == "__main__":
    port = 5050
    print("============================================================")
    print(f"[SQL Studio] Server starting on http://localhost:{port}")
    print(f"[SQL Studio] Active DB: {CURRENT_DB_PATH}")
    print("[SQL Studio] Unlimited Free Import/Export: CSV, Excel, JSON, SQL")
    print("============================================================")
    uvicorn.run("app:app", host="127.0.0.1", port=port, reload=True)

