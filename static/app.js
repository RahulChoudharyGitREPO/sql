/**
 * SQL Studio — Beekeeper Studio Clone Frontend Engine
 * Handles Multi-tab CodeMirror, Query Execution, Grid Rendering, Free Import/Export, and Table Editing.
 */

let tabs = [];
let activeTabId = null;
let tabCounter = 1;
let currentTables = [];
let selectedImportFile = null;

// ===========================================================================
// INITIALIZATION
// ===========================================================================

document.addEventListener("DOMContentLoaded", () => {
  initUIEvents();
  loadDatabases();
  loadTables();
  loadSavedQueries();
  loadHistory();
  
  // Create first query tab
  createTab({
    type: 'query',
    title: 'Query 1',
    sql: `-- Write your SQL query here (Press Ctrl + Enter to run)
SELECT 
    store,
    sale_date,
    revenue,
    SUM(revenue) OVER (PARTITION BY store ORDER BY sale_date) AS running_total,
    ROUND(AVG(revenue) OVER (PARTITION BY store ORDER BY sale_date ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 0) AS moving_avg
FROM store_daily_sales
ORDER BY store, sale_date;`
  });

  // Check for updates against GitHub Releases
  setTimeout(checkForUpdates, 1500);
});

function initUIEvents() {
  // Sidebar navigation
  document.querySelectorAll(".sidebar-nav-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".sidebar-nav-btn").forEach(b => b.classList.remove("active"));
      document.querySelectorAll(".sidebar-section").forEach(s => s.classList.remove("active"));
      
      btn.classList.add("active");
      const targetView = btn.dataset.view;
      const targetSec = document.getElementById(`sidebar-${targetView}`);
      if (targetSec) targetSec.classList.add("active");
    });
  });

  // Table search filter
  document.getElementById("table-search").addEventListener("input", (e) => {
    const query = e.target.value.toLowerCase();
    document.querySelectorAll(".table-tree-item").forEach(item => {
      const name = item.dataset.tableName.toLowerCase();
      item.style.display = name.includes(query) ? "flex" : "none";
    });
  });

  // Refresh tables
  document.getElementById("btn-refresh-tables").addEventListener("click", () => {
    loadTables();
  });

  // Header buttons
  document.getElementById("btn-new-query").addEventListener("click", () => {
    createTab({ type: 'query', title: `Query ${++tabCounter}` });
  });
  document.getElementById("btn-add-tab").addEventListener("click", () => {
    createTab({ type: 'query', title: `Query ${++tabCounter}` });
  });

  // DB Switcher
  document.getElementById("btn-switch-db").addEventListener("click", () => {
    openModal("modal-db-switch");
    loadDatabases();
  });
  document.getElementById("active-db-name").addEventListener("click", () => {
    openModal("modal-db-switch");
    loadDatabases();
  });

  document.getElementById("btn-create-db").addEventListener("click", createNewDatabase);

  // Import modal & Dropzone
  document.getElementById("btn-open-import").addEventListener("click", () => {
    openModal("modal-import");
  });

  const dropzone = document.getElementById("import-dropzone");
  const fileInput = document.getElementById("import-file-input");

  dropzone.addEventListener("click", () => fileInput.click());
  dropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropzone.classList.add("dragover");
  });
  dropzone.addEventListener("dragleave", () => dropzone.classList.remove("dragover"));
  dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzone.classList.remove("dragover");
    if (e.dataTransfer.files.length) {
      handleImportFileSelected(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener("change", (e) => {
    if (e.target.files.length) {
      handleImportFileSelected(e.target.files[0]);
    }
  });

  document.getElementById("btn-remove-file").addEventListener("click", () => {
    selectedImportFile = null;
    document.getElementById("selected-file-info").style.display = "none";
    dropzone.style.display = "block";
    fileInput.value = "";
  });

  document.getElementById("btn-do-import").addEventListener("click", executeImport);

  // Save Query modal
  document.getElementById("btn-confirm-save-query").addEventListener("click", confirmSaveQuery);

  // Global Keyboard Shortcuts
  window.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      runActiveTabQuery();
    }
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "t") {
      e.preventDefault();
      createTab({ type: 'query', title: `Query ${++tabCounter}` });
    }
  });

  // Close dropdowns on outside click
  window.addEventListener("click", (e) => {
    if (!e.target.closest(".dropdown")) {
      document.querySelectorAll(".dropdown").forEach(d => d.classList.remove("open"));
    }
  });
}

// ===========================================================================
// DATABASE & TABLES LOADER
// ===========================================================================

async function loadDatabases() {
  try {
    const res = await fetch("/api/databases");
    const data = await res.json();
    
    const activeName = data.current_db ? data.current_db.split(/[\\/]/).pop() : "workspace.db";
    document.getElementById("active-db-name").textContent = activeName;
    document.getElementById("sb-db-info").innerHTML = `<i class="fa-solid fa-server"></i> ${activeName}`;

    const modalList = document.getElementById("db-list-modal");
    modalList.innerHTML = "";
    data.databases.forEach(db => {
      const row = document.createElement("div");
      row.className = `db-item-row ${db.active ? 'active' : ''}`;
      row.innerHTML = `
        <div style="display: flex; align-items: center; gap: 8px;">
          <i class="fa-solid fa-database" style="color: ${db.active ? '#fbbf24' : '#64748b'};"></i>
          <div>
            <div style="font-weight: 600; font-size: 0.85rem;">${db.name}</div>
            <div style="font-size: 0.7rem; color: #64748b;">${db.size_kb} KB</div>
          </div>
        </div>
        ${db.active ? '<span style="font-size: 0.72rem; color: #10b981; font-weight: bold;">ACTIVE</span>' : '<button class="btn btn-secondary" style="padding: 3px 8px; font-size: 0.72rem;">Switch</button>'}
      `;
      row.addEventListener("click", () => switchDatabase(db.path));
      modalList.appendChild(row);
    });
  } catch (err) {
    console.error("Failed to load databases:", err);
  }
}

async function switchDatabase(dbPath) {
  try {
    const res = await fetch("/api/databases/switch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ db_path: dbPath })
    });
    const data = await res.json();
    if (data.status === "ok") {
      closeModal("modal-db-switch");
      loadDatabases();
      loadTables();
    }
  } catch (err) {
    alert("Failed to switch database: " + err);
  }
}

async function createNewDatabase() {
  const nameInput = document.getElementById("new-db-input");
  const name = nameInput.value.trim();
  if (!name) return alert("Please enter a database name");
  
  const formData = new FormData();
  formData.append("name", name);
  
  try {
    const res = await fetch("/api/databases/new", {
      method: "POST",
      body: formData
    });
    const data = await res.json();
    if (data.status === "ok") {
      nameInput.value = "";
      closeModal("modal-db-switch");
      loadDatabases();
      loadTables();
    }
  } catch (err) {
    alert("Failed to create database: " + err);
  }
}

async function loadTables() {
  const listEl = document.getElementById("tables-list");
  listEl.innerHTML = '<div class="loading-spinner"><i class="fa-solid fa-circle-notch fa-spin"></i> Loading...</div>';
  
  try {
    const res = await fetch("/api/tables");
    const data = await res.json();
    currentTables = data.tables || [];

    document.getElementById("sb-tables-count").textContent = `${currentTables.length} Tables`;

    if (currentTables.length === 0) {
      listEl.innerHTML = '<div style="padding: 16px; text-align: center; color: #64748b; font-size: 0.8rem;">No tables found.<br>Use Import to add data.</div>';
      return;
    }

    listEl.innerHTML = "";
    currentTables.forEach(t => {
      const item = document.createElement("div");
      item.className = "table-tree-item";
      item.dataset.tableName = t.name;
      item.innerHTML = `
        <div class="table-tree-left">
          <i class="${t.type === 'view' ? 'fa-solid fa-eye' : 'fa-solid fa-table'}"></i>
          <span>${t.name}</span>
        </div>
        <span class="table-badge-cnt">${t.row_count}</span>
      `;
      
      item.addEventListener("click", () => {
        openTableViewerTab(t.name);
      });
      
      listEl.appendChild(item);
    });
  } catch (err) {
    listEl.innerHTML = `<div style="padding: 12px; color: #ef4444; font-size: 0.8rem;">Error: ${err.message}</div>`;
  }
}

// ===========================================================================
// TABS MANAGER
// ===========================================================================

function createTab(options = {}) {
  const id = 'tab-' + Math.random().toString(36).substr(2, 9);
  const type = options.type || 'query'; // 'query' | 'table'
  const title = options.title || (type === 'query' ? `Query ${tabCounter}` : options.tableName);
  
  const tabData = {
    id,
    type,
    title,
    tableName: options.tableName || null,
    cmEditor: null,
    lastResult: null
  };

  tabs.push(tabData);

  // Render Tab Header Button
  const tabsBar = document.getElementById("tabs-bar");
  const addBtn = document.getElementById("btn-add-tab");
  
  const tabBtn = document.createElement("div");
  tabBtn.className = "tab-btn";
  tabBtn.id = `btn-${id}`;
  tabBtn.innerHTML = `
    <i class="${type === 'query' ? 'fa-solid fa-terminal tab-icon' : 'fa-solid fa-table tab-icon'}"></i>
    <span>${title}</span>
    <button class="tab-close" title="Close Tab">&times;</button>
  `;

  tabBtn.addEventListener("click", (e) => {
    if (!e.target.classList.contains("tab-close")) {
      switchTab(id);
    }
  });

  tabBtn.querySelector(".tab-close").addEventListener("click", (e) => {
    e.stopPropagation();
    closeTab(id);
  });

  tabsBar.insertBefore(tabBtn, addBtn);

  // Render Tab Content Pane
  const contentArea = document.getElementById("tab-content-area");
  const pane = document.createElement("div");
  pane.className = "tab-pane";
  pane.id = `pane-${id}`;

  if (type === 'query') {
    pane.innerHTML = `
      <div class="query-toolbar">
        <div class="query-toolbar-left">
          <button class="btn-run" onclick="runQueryForTab('${id}')">
            <i class="fa-solid fa-play"></i> Run (Ctrl+Enter)
          </button>
          <button class="btn-tool" onclick="formatSQLForTab('${id}')">
            <i class="fa-solid fa-wand-magic-sparkles"></i> Format
          </button>
          <button class="btn-tool" onclick="openSaveQueryModal('${id}')">
            <i class="fa-solid fa-bookmark"></i> Save
          </button>
          <button class="btn-tool" onclick="clearEditorForTab('${id}')">
            <i class="fa-solid fa-eraser"></i> Clear
          </button>
        </div>
        <div class="query-toolbar-right">
          <div class="dropdown" id="export-dropdown-${id}">
            <button class="btn-tool" onclick="toggleDropdown('export-dropdown-${id}')">
              <i class="fa-solid fa-file-export"></i> Export Result <i class="fa-solid fa-chevron-down" style="font-size: 0.7rem;"></i>
            </button>
            <div class="dropdown-menu">
              <div class="dropdown-item" onclick="exportTabResult('${id}', 'csv')"><i class="fa-solid fa-file-csv"></i> Export as CSV</div>
              <div class="dropdown-item" onclick="exportTabResult('${id}', 'excel')"><i class="fa-solid fa-file-excel"></i> Export as Excel (.xlsx)</div>
              <div class="dropdown-item" onclick="exportTabResult('${id}', 'json')"><i class="fa-solid fa-file-code"></i> Export as JSON</div>
              <div class="dropdown-item" onclick="exportTabResult('${id}', 'sql')"><i class="fa-solid fa-database"></i> Export as SQL Inserts</div>
              <div class="dropdown-item" onclick="exportTabResult('${id}', 'markdown')"><i class="fa-solid fa-table"></i> Export as Markdown</div>
            </div>
          </div>
        </div>
      </div>
      <div class="editor-container" id="editor-${id}"></div>
      <div class="results-container">
        <div class="results-header">
          <div class="results-stats" id="stats-${id}">
            <span><i class="fa-solid fa-circle-info"></i> Ready to execute query</span>
          </div>
          <div class="results-filter">
            <input type="text" placeholder="Filter result rows..." oninput="filterGridRows('${id}', this.value)">
          </div>
        </div>
        <div class="results-grid-wrapper" id="grid-${id}">
          <div class="empty-state">
            <i class="fa-solid fa-bolt"></i>
            <span>Press <strong>Run</strong> or <strong>Ctrl+Enter</strong> to execute SQL</span>
          </div>
        </div>
      </div>
    `;
  } else {
    // Table Data Viewer Pane
    pane.innerHTML = `
      <div class="query-toolbar">
        <div class="query-toolbar-left">
          <button class="btn-tool" onclick="refreshTableData('${id}', '${options.tableName}')">
            <i class="fa-solid fa-rotate"></i> Refresh
          </button>
          <button class="btn-tool" onclick="openInsertRowModal('${options.tableName}')">
            <i class="fa-solid fa-plus"></i> Add Row
          </button>
        </div>
        <div class="query-toolbar-right">
          <div class="dropdown" id="export-table-dropdown-${id}">
            <button class="btn-tool" onclick="toggleDropdown('export-table-dropdown-${id}')">
              <i class="fa-solid fa-file-export"></i> Export Table <i class="fa-solid fa-chevron-down" style="font-size: 0.7rem;"></i>
            </button>
            <div class="dropdown-menu">
              <div class="dropdown-item" onclick="exportFullTable('${options.tableName}', 'csv')"><i class="fa-solid fa-file-csv"></i> Export as CSV</div>
              <div class="dropdown-item" onclick="exportFullTable('${options.tableName}', 'excel')"><i class="fa-solid fa-file-excel"></i> Export as Excel (.xlsx)</div>
              <div class="dropdown-item" onclick="exportFullTable('${options.tableName}', 'json')"><i class="fa-solid fa-file-code"></i> Export as JSON</div>
              <div class="dropdown-item" onclick="exportFullTable('${options.tableName}', 'sql')"><i class="fa-solid fa-database"></i> Export as SQL Inserts</div>
              <div class="dropdown-item" onclick="exportFullTable('${options.tableName}', 'markdown')"><i class="fa-solid fa-table"></i> Export as Markdown</div>
            </div>
          </div>
        </div>
      </div>
      <div class="results-container" style="height: 100%;">
        <div class="results-header">
          <div class="results-stats" id="stats-${id}">
            <span>Table: <strong>${options.tableName}</strong></span>
          </div>
          <div class="results-filter">
            <input type="text" placeholder="Search in table..." oninput="searchTableRows('${id}', '${options.tableName}', this.value)">
          </div>
        </div>
        <div class="results-grid-wrapper" id="grid-${id}">
          <div class="loading-spinner"><i class="fa-solid fa-circle-notch fa-spin"></i> Loading table records...</div>
        </div>
      </div>
    `;
  }

  contentArea.appendChild(pane);

  // Initialize CodeMirror if query tab
  if (type === 'query') {
    const editorEl = pane.querySelector(`#editor-${id}`);
    const cm = CodeMirror(editorEl, {
      value: options.sql || "SELECT * FROM store_daily_sales LIMIT 50;",
      mode: "text/x-sql",
      theme: "dracula",
      lineNumbers: true,
      matchBrackets: true,
      autoCloseBrackets: true,
      extraKeys: {
        "Ctrl-Space": "autocomplete",
        "Ctrl-Enter": () => runQueryForTab(id),
        "Cmd-Enter": () => runQueryForTab(id)
      }
    });
    tabData.cmEditor = cm;
  }

  switchTab(id);

  if (type === 'table') {
    loadTableDataForTab(id, options.tableName);
  }

  return tabData;
}

function switchTab(id) {
  activeTabId = id;
  document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
  document.querySelectorAll(".tab-pane").forEach(p => p.classList.remove("active"));

  const btn = document.getElementById(`btn-${id}`);
  const pane = document.getElementById(`pane-${id}`);
  if (btn) btn.classList.add("active");
  if (pane) pane.classList.add("active");

  const tab = tabs.find(t => t.id === id);
  if (tab && tab.cmEditor) {
    setTimeout(() => tab.cmEditor.refresh(), 10);
  }
}

function closeTab(id) {
  const idx = tabs.findIndex(t => t.id === id);
  if (idx === -1) return;

  document.getElementById(`btn-${id}`)?.remove();
  document.getElementById(`pane-${id}`)?.remove();
  tabs.splice(idx, 1);

  if (activeTabId === id) {
    if (tabs.length > 0) {
      const nextTab = tabs[Math.max(0, idx - 1)];
      switchTab(nextTab.id);
    } else {
      createTab({ type: 'query', title: `Query ${++tabCounter}` });
    }
  }
}

function openTableViewerTab(tableName) {
  // check if already open
  const existing = tabs.find(t => t.type === 'table' && t.tableName === tableName);
  if (existing) {
    switchTab(existing.id);
  } else {
    createTab({ type: 'table', title: tableName, tableName });
  }
}

// ===========================================================================
// QUERY EXECUTION & RESULTS RENDERING
// ===========================================================================

function runActiveTabQuery() {
  if (activeTabId) {
    runQueryForTab(activeTabId);
  }
}

async function runQueryForTab(tabId) {
  const tab = tabs.find(t => t.id === tabId);
  if (!tab || !tab.cmEditor) return;

  let query = tab.cmEditor.getSelection();
  if (!query || !query.trim()) {
    query = tab.cmEditor.getValue();
  }
  query = query.trim();
  if (!query) return;

  const gridEl = document.getElementById(`grid-${tabId}`);
  const statsEl = document.getElementById(`stats-${tabId}`);

  gridEl.innerHTML = '<div class="loading-spinner"><i class="fa-solid fa-circle-notch fa-spin"></i> Executing query...</div>';
  statsEl.innerHTML = '<span>Executing...</span>';

  try {
    const res = await fetch("/api/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query })
    });
    const data = await res.json();

    if (!res.ok || data.status === "error") {
      gridEl.innerHTML = `<div class="error-banner"><strong>SQL Error:</strong>\n${escapeHtml(data.error || 'Unknown error')}</div>`;
      statsEl.innerHTML = `<span style="color: #ef4444;"><i class="fa-solid fa-triangle-exclamation"></i> Error (${data.execution_time_ms} ms)</span>`;
      return;
    }

    tab.lastResult = data;
    renderGrid(tabId, data);
    document.getElementById("sb-time-info").innerHTML = `<i class="fa-solid fa-bolt"></i> ${data.execution_time_ms} ms`;
    loadHistory();
    loadTables(); // in case CREATE/DROP/INSERT was run
  } catch (err) {
    gridEl.innerHTML = `<div class="error-banner"><strong>Network Error:</strong>\n${escapeHtml(err.message)}</div>`;
  }
}

function renderGrid(tabId, data) {
  const gridEl = document.getElementById(`grid-${tabId}`);
  const statsEl = document.getElementById(`stats-${tabId}`);

  if (data.affected_rows > 0 && (!data.rows || data.rows.length === 0)) {
    gridEl.innerHTML = `
      <div class="empty-state">
        <i class="fa-solid fa-circle-check" style="color: #10b981;"></i>
        <span>Query executed successfully. <strong>${data.affected_rows} rows affected</strong> in ${data.execution_time_ms} ms.</span>
      </div>
    `;
    statsEl.innerHTML = `<span class="stat-badge"><i class="fa-solid fa-check"></i> ${data.affected_rows} rows affected</span> <span>in ${data.execution_time_ms} ms</span>`;
    return;
  }

  if (!data.columns || data.columns.length === 0) {
    gridEl.innerHTML = `
      <div class="empty-state">
        <i class="fa-solid fa-circle-check" style="color: #10b981;"></i>
        <span>Query executed successfully in ${data.execution_time_ms} ms (no output rows).</span>
      </div>
    `;
    statsEl.innerHTML = `<span>Completed in ${data.execution_time_ms} ms</span>`;
    return;
  }

  statsEl.innerHTML = `
    <span class="stat-badge"><i class="fa-solid fa-check"></i> ${data.row_count} rows returned</span>
    <span>in ${data.execution_time_ms} ms</span>
  `;

  let tableHtml = '<table class="data-table"><thead><tr>';
  tableHtml += '<th style="width: 40px; text-align: center;">#</th>';
  data.columns.forEach(col => {
    tableHtml += `<th>${escapeHtml(col)}</th>`;
  });
  tableHtml += '</tr></thead><tbody>';

  data.rows.forEach((row, rIdx) => {
    tableHtml += `<tr><td style="text-align: center; color: #64748b;">${rIdx + 1}</td>`;
    row.forEach(cell => {
      if (cell === null || cell === undefined) {
        tableHtml += '<td class="null-val">NULL</td>';
      } else {
        tableHtml += `<td title="${escapeHtml(String(cell))}">${escapeHtml(String(cell))}</td>`;
      }
    });
    tableHtml += '</tr>';
  });

  tableHtml += '</tbody></table>';
  gridEl.innerHTML = tableHtml;
}

function filterGridRows(tabId, query) {
  const tab = tabs.find(t => t.id === tabId);
  if (!tab || !tab.lastResult || !tab.lastResult.rows) return;

  const q = query.toLowerCase().trim();
  const filteredRows = tab.lastResult.rows.filter(r => 
    r.some(cell => String(cell).toLowerCase().includes(q))
  );

  renderGrid(tabId, {
    columns: tab.lastResult.columns,
    rows: filteredRows,
    row_count: filteredRows.length,
    execution_time_ms: tab.lastResult.execution_time_ms
  });
}

// ===========================================================================
// TABLE VIEWER DATA & INLINE CELL EDITING
// ===========================================================================

async function loadTableDataForTab(tabId, tableName, search = "") {
  const gridEl = document.getElementById(`grid-${tabId}`);
  const statsEl = document.getElementById(`stats-${tabId}`);

  try {
    const url = `/api/table/${encodeURIComponent(tableName)}/data?limit=100&search=${encodeURIComponent(search)}`;
    const res = await fetch(url);
    const data = await res.json();

    statsEl.innerHTML = `<span>Table: <strong>${tableName}</strong> (${data.total_rows} total records)</span>`;

    let html = '<table class="data-table"><thead><tr>';
    html += '<th style="width: 40px; text-align: center;">#</th>';
    data.columns.forEach(col => {
      const isPk = col === data.pk_col;
      html += `<th>${isPk ? '<i class="fa-solid fa-key" style="color: #fbbf24; font-size: 0.7rem;"></i> ' : ''}${escapeHtml(col)}</th>`;
    });
    html += '<th style="width: 60px; text-align: center;">Actions</th></tr></thead><tbody>';

    data.rows.forEach((row, rIdx) => {
      const pkVal = row[data.columns.indexOf(data.pk_col)];
      html += `<tr><td style="text-align: center; color: #64748b;">${rIdx + 1}</td>`;
      
      data.columns.forEach((col, cIdx) => {
        const cell = row[cIdx];
        const isNull = cell === null || cell === undefined;
        html += `
          <td class="${isNull ? 'null-val' : ''}" 
              ondblclick="makeCellEditable(this, '${tableName}', '${data.pk_col}', '${escapeQuotes(pkVal)}', '${col}')"
              title="Double click to edit">
            ${isNull ? 'NULL' : escapeHtml(String(cell))}
          </td>
        `;
      });

      html += `
        <td style="text-align: center;">
          <button class="btn-icon" style="color: #ef4444;" onclick="deleteTableRow('${tabId}', '${tableName}', '${data.pk_col}', '${escapeQuotes(pkVal)}')">
            <i class="fa-solid fa-trash-can"></i>
          </button>
        </td>
      </tr>`;
    });

    html += '</tbody></table>';
    gridEl.innerHTML = html;
  } catch (err) {
    gridEl.innerHTML = `<div class="error-banner">Error loading table: ${err.message}</div>`;
  }
}

function refreshTableData(tabId, tableName) {
  loadTableDataForTab(tabId, tableName);
}

function searchTableRows(tabId, tableName, query) {
  loadTableDataForTab(tabId, tableName, query);
}

function makeCellEditable(tdEl, table, pkCol, pkVal, colName) {
  if (tdEl.querySelector("input")) return;
  const currentVal = tdEl.classList.contains("null-val") ? "" : tdEl.textContent.trim();
  
  const input = document.createElement("input");
  input.type = "text";
  input.value = currentVal;
  input.className = "form-input";
  input.style.padding = "2px 4px";
  input.style.fontSize = "0.8rem";

  tdEl.textContent = "";
  tdEl.appendChild(input);
  input.focus();

  input.addEventListener("keydown", async (e) => {
    if (e.key === "Enter") {
      const newVal = input.value;
      try {
        await fetch("/api/table/cell/update", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            table,
            primary_key_col: pkCol,
            primary_key_val: pkVal,
            column: colName,
            new_value: newVal === "" ? null : newVal
          })
        });
        tdEl.textContent = newVal === "" ? "NULL" : newVal;
        if (newVal === "") tdEl.classList.add("null-val"); else tdEl.classList.remove("null-val");
      } catch (err) {
        alert("Failed to update cell: " + err);
        tdEl.textContent = currentVal;
      }
    }
    if (e.key === "Escape") {
      tdEl.textContent = currentVal;
    }
  });

  input.addEventListener("blur", () => {
    tdEl.textContent = currentVal;
  });
}

async function deleteTableRow(tabId, table, pkCol, pkVal) {
  if (!confirm(`Are you sure you want to delete this row where ${pkCol} = ${pkVal}?`)) return;
  try {
    await fetch("/api/table/row/delete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        table,
        primary_key_col: pkCol,
        primary_key_val: pkVal
      })
    });
    loadTableDataForTab(tabId, table);
    loadTables();
  } catch (err) {
    alert("Delete failed: " + err);
  }
}

// ===========================================================================
// FREE UNLIMITED IMPORT (CSV, EXCEL, JSON, SQL)
// ===========================================================================

function handleImportFileSelected(file) {
  selectedImportFile = file;
  document.getElementById("import-file-name").textContent = file.name;
  document.getElementById("import-file-size").textContent = `${Math.round(file.size / 1024)} KB`;
  
  const ext = file.name.split('.').pop().toLowerCase();
  const icon = document.querySelector(".selected-file-info .file-icon");
  if (ext.includes("xls")) icon.className = "fa-solid fa-file-excel file-icon";
  else if (ext === "json") icon.className = "fa-solid fa-file-code file-icon";
  else if (ext === "sql") icon.className = "fa-solid fa-database file-icon";
  else icon.className = "fa-solid fa-file-csv file-icon";

  document.getElementById("import-dropzone").style.display = "none";
  document.getElementById("selected-file-info").style.display = "flex";

  const autoName = file.name.split('.')[0].replace(/[^a-zA-Z0-9_]/g, '_');
  document.getElementById("import-table-name").value = autoName;
}

async function executeImport() {
  if (!selectedImportFile) {
    return alert("Please select a file to import");
  }

  const btn = document.getElementById("btn-do-import");
  btn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Importing...';
  btn.disabled = true;

  const formData = new FormData();
  formData.append("file", selectedImportFile);
  formData.append("table_name", document.getElementById("import-table-name").value.trim());
  formData.append("if_exists", document.getElementById("import-if-exists").value);

  try {
    const res = await fetch("/api/import/file", {
      method: "POST",
      body: formData
    });
    const data = await res.json();

    if (!res.ok) {
      alert("Import Failed: " + (data.detail || 'Unknown error'));
      return;
    }

    alert(`✓ Successfully imported ${data.rows_imported} rows into table '${data.table}'!`);
    closeModal("modal-import");
    loadTables();
    openTableViewerTab(data.table);
  } catch (err) {
    alert("Network error importing file: " + err.message);
  } finally {
    btn.innerHTML = '<i class="fa-solid fa-upload"></i> Start Import';
    btn.disabled = false;
  }
}

// ===========================================================================
// FREE UNLIMITED EXPORT (CSV, EXCEL, JSON, SQL, MARKDOWN)
// ===========================================================================

function exportTabResult(tabId, format) {
  const tab = tabs.find(t => t.id === tabId);
  if (!tab || !tab.cmEditor) return;

  const query = tab.cmEditor.getSelection() || tab.cmEditor.getValue();
  if (!query.trim()) return alert("No SQL query to export");

  triggerExportDownload({ query, format });
}

function exportFullTable(tableName, format) {
  triggerExportDownload({ table: tableName, format });
}

function triggerExportDownload({ table, query, format }) {
  const form = document.createElement("form");
  form.method = "POST";
  form.action = "/api/export/data";
  form.target = "_blank";

  if (table) {
    const tInput = document.createElement("input");
    tInput.type = "hidden";
    tInput.name = "table";
    tInput.value = table;
    form.appendChild(tInput);
  }

  if (query) {
    const qInput = document.createElement("input");
    qInput.type = "hidden";
    qInput.name = "query";
    qInput.value = query;
    form.appendChild(qInput);
  }

  const fInput = document.createElement("input");
  fInput.type = "hidden";
  fInput.name = "format";
  fInput.value = format;
  form.appendChild(fInput);

  document.body.appendChild(form);
  form.submit();
  form.remove();
}

// ===========================================================================
// SAVED QUERIES & HISTORY
// ===========================================================================

async function loadSavedQueries() {
  const listEl = document.getElementById("saved-queries-list");
  try {
    const res = await fetch("/api/saved_queries");
    const saved = await res.json();
    if (saved.length === 0) {
      listEl.innerHTML = '<div style="padding: 12px; font-size: 0.75rem; color: #64748b;">No saved queries yet.</div>';
      return;
    }
    listEl.innerHTML = "";
    saved.forEach(sq => {
      const item = document.createElement("div");
      item.className = "saved-item";
      item.innerHTML = `
        <div class="saved-title">${escapeHtml(sq.title)}</div>
        <div class="saved-sql-preview">${escapeHtml(sq.query)}</div>
      `;
      item.addEventListener("click", () => {
        createTab({ type: 'query', title: sq.title, sql: sq.query });
      });
      listEl.appendChild(item);
    });
  } catch (err) {
    console.error("Failed to load saved queries:", err);
  }
}

async function loadHistory() {
  const listEl = document.getElementById("history-queries-list");
  try {
    const res = await fetch("/api/history");
    const history = await res.json();
    if (history.length === 0) {
      listEl.innerHTML = '<div style="padding: 12px; font-size: 0.75rem; color: #64748b;">No recent queries.</div>';
      return;
    }
    listEl.innerHTML = "";
    history.slice(0, 30).forEach(h => {
      const item = document.createElement("div");
      item.className = "history-item";
      item.innerHTML = `
        <div class="history-sql-preview">${escapeHtml(h.query)}</div>
        <div class="history-time">${h.timestamp}</div>
      `;
      item.addEventListener("click", () => {
        createTab({ type: 'query', title: 'History Query', sql: h.query });
      });
      listEl.appendChild(item);
    });
  } catch (err) {
    console.error("Failed to load history:", err);
  }
}

function openSaveQueryModal(tabId) {
  window._saveQueryTabId = tabId;
  openModal("modal-save-query");
}

async function confirmSaveQuery() {
  const title = document.getElementById("save-query-title").value.trim();
  if (!title) return alert("Please enter a title");

  const tab = tabs.find(t => t.id === window._saveQueryTabId);
  if (!tab || !tab.cmEditor) return;

  const query = tab.cmEditor.getValue();

  try {
    await fetch("/api/saved_queries", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title, query })
    });
    closeModal("modal-save-query");
    document.getElementById("save-query-title").value = "";
    loadSavedQueries();
  } catch (err) {
    alert("Failed to save query: " + err);
  }
}

function formatSQLForTab(tabId) {
  const tab = tabs.find(t => t.id === tabId);
  if (!tab || !tab.cmEditor) return;

  let sql = tab.cmEditor.getValue();
  const keywords = ["SELECT", "FROM", "WHERE", "GROUP BY", "HAVING", "ORDER BY", "LEFT JOIN", "RIGHT JOIN", "INNER JOIN", "FULL OUTER JOIN", "UNION", "WITH", "LIMIT", "OFFSET"];
  keywords.forEach(kw => {
    const reg = new RegExp(`\\b${kw}\\b`, 'gi');
    sql = sql.replace(reg, `\n${kw}`);
  });
  tab.cmEditor.setValue(sql.trim());
}

function clearEditorForTab(tabId) {
  const tab = tabs.find(t => t.id === tabId);
  if (tab && tab.cmEditor) tab.cmEditor.setValue("");
}

// ===========================================================================
// UTILITIES
// ===========================================================================

function openModal(id) {
  document.getElementById(id)?.classList.add("open");
}

function closeModal(id) {
  document.getElementById(id)?.classList.remove("open");
}

function toggleDropdown(id) {
  const el = document.getElementById(id);
  if (el) el.classList.toggle("open");
}

function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function escapeQuotes(str) {
  if (str === null || str === undefined) return "";
  return String(str).replace(/'/g, "\\'");
}

// ===========================================================================
// AUTO-UPDATER SYSTEM (Client-side)
// ===========================================================================

let cachedUpdateData = null;

async function checkForUpdates(manual = false) {
  try {
    const res = await fetch("/api/check_update");
    const data = await res.json();
    
    if (data.has_update) {
      cachedUpdateData = data;
      const badge = document.getElementById("update-badge");
      if (badge) {
        badge.style.display = "inline-flex";
        badge.innerHTML = `<i class="fa-solid fa-sparkles"></i> Update to ${data.latest_version}!`;
      }
      
      // Auto-popup update modal when new release is detected
      openUpdateModal();
    } else if (manual) {
      alert(`SQL Studio is up to date! (Version: ${data.current_version})`);
    }
  } catch (err) {
    console.warn("Update check skipped/offline:", err);
    if (manual) alert("Could not check for updates right now. Please check your internet connection.");
  }
}

function openUpdateModal() {
  if (!cachedUpdateData) return;
  
  const titleEl = document.getElementById("update-modal-title");
  const subEl = document.getElementById("update-version-tag");
  const badgeEl = document.getElementById("update-badge-pill");
  const dateEl = document.getElementById("update-release-date");
  const notesEl = document.getElementById("update-release-notes");
  const btnPerform = document.getElementById("btn-perform-update");
  
  if (titleEl) titleEl.textContent = `New Update: ${cachedUpdateData.release_name || cachedUpdateData.latest_version}`;
  if (subEl) subEl.textContent = `Version ${cachedUpdateData.latest_version} (Current: ${cachedUpdateData.current_version})`;
  if (badgeEl) badgeEl.textContent = cachedUpdateData.latest_version;
  if (dateEl) {
    const pubDate = cachedUpdateData.published_at ? new Date(cachedUpdateData.published_at).toLocaleDateString() : "Latest";
    dateEl.textContent = `Released: ${pubDate}`;
  }
  if (notesEl) notesEl.textContent = cachedUpdateData.release_notes || "Includes bug fixes and performance improvements.";
  
  // Wire update action button
  if (btnPerform) {
    btnPerform.onclick = performAppUpdate;
  }
  
  openModal("modal-update");
}

async function performAppUpdate() {
  if (!cachedUpdateData || !cachedUpdateData.download_url) {
    alert("No binary download asset found in the latest release.");
    return;
  }
  
  const btnPerform = document.getElementById("btn-perform-update");
  const btnLater = document.getElementById("btn-update-later");
  const progressContainer = document.getElementById("update-progress-container");
  const progressLabel = document.getElementById("update-progress-label");
  
  if (btnPerform) {
    btnPerform.disabled = true;
    btnPerform.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Updating...`;
  }
  if (btnLater) btnLater.style.display = "none";
  if (progressContainer) progressContainer.style.display = "block";
  if (progressLabel) progressLabel.textContent = "Downloading update package from GitHub Releases...";
  
  try {
    const res = await fetch("/api/perform_update", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ download_url: cachedUpdateData.download_url })
    });
    
    const result = await res.json();
    if (!res.ok) throw new Error(result.detail || "Update failed");
    
    if (progressLabel) {
      progressLabel.textContent = "Applying update and restarting SQL Studio...";
    }
    
    // UI indicator while app restarts
    setTimeout(() => {
      document.body.innerHTML = `
        <div style="height:100vh; display:flex; flex-direction:column; align-items:center; justify-content:center; background:#13141f; color:#f8fafc; font-family:'Inter',sans-serif; text-align:center;">
          <img src="app_icon.png" style="width:64px; height:64px; margin-bottom:20px; border-radius:12px;">
          <h2 style="margin:0 0 10px 0; color:#fbbf24;">Restarting SQL Studio...</h2>
          <p style="color:#94a3b8; font-size:0.9rem;">Applying latest updates and launching new version.</p>
        </div>
      `;
    }, 1200);
    
  } catch (err) {
    alert("Update Error: " + err.message);
    if (btnPerform) {
      btnPerform.disabled = false;
      btnPerform.innerHTML = `<i class="fa-solid fa-rotate-right"></i> Retry Update`;
    }
    if (btnLater) btnLater.style.display = "inline-block";
    if (progressContainer) progressContainer.style.display = "none";
  }
}

