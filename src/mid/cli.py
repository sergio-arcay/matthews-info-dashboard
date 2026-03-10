from __future__ import annotations

import sys
from pathlib import Path

import uvicorn


def _ensure_src_on_path() -> None:
    src_dir = Path(__file__).resolve().parents[1]
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))


def dev() -> None:
    _ensure_src_on_path()
    uvicorn.run("mid.main:app", host="0.0.0.0", port=8001, reload=True)


def start() -> None:
    _ensure_src_on_path()
    uvicorn.run("mid.main:app", host="0.0.0.0", port=8001)
