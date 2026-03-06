const dashboard = document.getElementById("dashboard");
const layoutStatus = document.getElementById("layout-status");
const blockTimers = new Map();
let currentLayout = null;
let resizeRaf = null;

function setStatus(text) {
  if (layoutStatus) {
    layoutStatus.textContent = text;
  }
}

function getMaxRow(layout) {
  if (!layout || !Array.isArray(layout.blocks)) return 0;
  return layout.blocks.reduce((max, block) => {
    const endRow = block.position.row + block.position.row_span - 1;
    return Math.max(max, endRow);
  }, 0);
}

function computeAutoRowHeight(layout, grid) {
  const rows = getMaxRow(layout);
  if (!rows || !dashboard) return 120;
  const padding = Number(grid.padding) || 0;
  const gap = Number(grid.gap) || 0;
  const available = dashboard.clientHeight - padding * 2 - gap * (rows - 1);
  const height = Math.floor(available / rows);
  return Math.max(40, height);
}

function applyGrid(layout) {
  const grid = layout.grid || {};
  document.documentElement.style.setProperty("--columns", grid.columns);
  document.documentElement.style.setProperty("--grid-gap", `${grid.gap}px`);
  document.documentElement.style.setProperty("--page-padding", `${grid.padding}px`);
  let rowHeight = Number(grid.row_height);
  if (!Number.isFinite(rowHeight) || rowHeight <= 0) {
    rowHeight = computeAutoRowHeight(layout, grid);
  }
  document.documentElement.style.setProperty("--row-height", `${rowHeight}px`);
}

function createBlockElement(block) {
  const el = document.createElement("div");
  el.className = "block loading";
  el.dataset.blockId = block.id;
  el.style.gridColumn = `${block.position.col} / span ${block.position.col_span}`;
  el.style.gridRow = `${block.position.row} / span ${block.position.row_span}`;
  if (block.min_height) {
    el.style.minHeight = `${block.min_height}px`;
  }
  el.innerHTML = `<div class="block-body"><p>Cargando ${block.title}...</p></div>`;
  return el;
}

async function fetchJson(url) {
  const response = await fetch(url, { headers: { "Accept": "application/json" } });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return response.json();
}

function runBlockScripts(scripts, context) {
  if (!Array.isArray(scripts)) return;
  scripts.forEach((script, index) => {
    if (typeof script !== "string" || script.trim() === "") return;
    try {
      const runner = new Function("context", script);
      runner(context);
    } catch (error) {
      console.error(`Error en script del bloque ${context.blockId} (#${index})`, error);
    }
  });
}

function scheduleRefresh(blockId, seconds) {
  if (blockTimers.has(blockId)) {
    clearTimeout(blockTimers.get(blockId));
  }
  const delay = Number(seconds);
  if (!Number.isFinite(delay) || delay <= 0) {
    blockTimers.delete(blockId);
    return;
  }
  const timeout = window.setTimeout(() => {
    refreshBlock(blockId);
  }, delay * 1000);
  blockTimers.set(blockId, timeout);
}

async function refreshBlock(blockId) {
  const blockEl = dashboard.querySelector(`[data-block-id="${blockId}"]`);
  if (!blockEl) return;

  blockEl.classList.add("loading");
  try {
    const data = await fetchJson(`/api/blocks/${blockId}`);
    const context = { blockId, blockEl, data };
    runBlockScripts(data.scripts_before, context);
    blockEl.innerHTML = data.html;
    blockEl.classList.remove("loading");
    runBlockScripts(data.scripts_after, context);
    scheduleRefresh(blockId, data.refresh_seconds);
  } catch (error) {
    blockEl.innerHTML = `<div class="block-body"><p class="block-error">Error al actualizar. Reintentando...</p></div>`;
    scheduleRefresh(blockId, 10);
  }
}

async function loadLayout() {
  setStatus("Sincronizando…");
  try {
    const params = new URLSearchParams(window.location.search);
    const panel = params.get("panel");
    const layoutUrl = panel ? `/api/layout?panel=${encodeURIComponent(panel)}` : "/api/layout";
    const layout = await fetchJson(layoutUrl);
    currentLayout = layout;
    applyGrid(layout);
    dashboard.innerHTML = "";
    layout.blocks.forEach((block) => {
      dashboard.appendChild(createBlockElement(block));
    });
    const panelLabel = panel ? ` (${panel})` : "";
    setStatus(`Layout actualizado${panelLabel} · ${layout.blocks.length} bloques`);
    if (resizeRaf !== null) {
      cancelAnimationFrame(resizeRaf);
    }
    resizeRaf = requestAnimationFrame(() => applyGrid(layout));
    await Promise.all(layout.blocks.map((block) => refreshBlock(block.id)));
  } catch (error) {
    dashboard.innerHTML = `<div class="block"><div class="block-body"><p class="block-error">No se pudo cargar el layout. Revisa el backend.</p></div></div>`;
    setStatus("Error al cargar layout");
  }
}

loadLayout();

window.addEventListener("resize", () => {
  if (!currentLayout) return;
  if (resizeRaf !== null) {
    cancelAnimationFrame(resizeRaf);
  }
  resizeRaf = requestAnimationFrame(() => applyGrid(currentLayout));
});
