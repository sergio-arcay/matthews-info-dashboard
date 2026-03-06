from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from mid.blocks.registry import BlockRegistry
from mid.layout.engine import build_layout, default_grid
from mid.layout.panels import build_panel
from mid.layout.schemas import BlockResponse, LayoutResponse

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "frontend"

app = FastAPI(title="Matthews Info Dashboard")
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

registry = BlockRegistry()
registry.load()


@app.get("/", response_class=FileResponse)
def root() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/api/layout", response_model=LayoutResponse)
def get_layout(panel: str | None = None) -> LayoutResponse:
    if panel:
        panel_layout = build_panel(panel, registry)
        if panel_layout is None:
            raise HTTPException(status_code=404, detail="Panel not found")
        return LayoutResponse(
            generated_at=datetime.now(timezone.utc),
            grid=panel_layout.grid,
            blocks=panel_layout.blocks,
        )
    grid = default_grid()
    blocks = registry.list_blocks()
    layout_blocks = build_layout(blocks, grid)
    return LayoutResponse(
        generated_at=datetime.now(timezone.utc),
        grid=grid,
        blocks=layout_blocks,
    )


@app.get("/api/blocks/{block_id}", response_model=BlockResponse)
def get_block(block_id: str) -> BlockResponse:
    block = registry.resolve(block_id)
    if block is None:
        raise HTTPException(status_code=404, detail="Block not found")
    render = block.render()
    return BlockResponse(
        id=block_id,
        title=block.title,
        html=render.html,
        scripts_before=render.scripts_before,
        scripts_after=render.scripts_after,
        refresh_seconds=render.refresh_seconds,
        updated_at=datetime.now(timezone.utc),
        meta=render.meta,
    )


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
