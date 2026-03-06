from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class GridConfig(BaseModel):
    columns: int = Field(default=12, ge=1)
    row_height: int | None = Field(default=120, ge=40)
    gap: int = Field(default=12, ge=0)
    padding: int = Field(default=16, ge=0)


class BlockPosition(BaseModel):
    col: int = Field(ge=1)
    row: int = Field(ge=1)
    col_span: int = Field(ge=1)
    row_span: int = Field(ge=1)


class BlockLayout(BaseModel):
    id: str
    title: str
    refresh_seconds: int | None = None
    position: BlockPosition
    min_height: int | None = None


class LayoutResponse(BaseModel):
    generated_at: datetime
    grid: GridConfig
    blocks: list[BlockLayout]


class BlockResponse(BaseModel):
    id: str
    title: str
    html: str
    scripts_before: list[str] = Field(default_factory=list)
    scripts_after: list[str] = Field(default_factory=list)
    refresh_seconds: int | None = None
    updated_at: datetime
    meta: dict[str, Any] = Field(default_factory=dict)
