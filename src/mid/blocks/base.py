from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class BlockRender:
    html: str
    refresh_seconds: int | None
    scripts_before: list[str] = field(default_factory=list)
    scripts_after: list[str] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class BlockLayoutSpec:
    id: str
    title: str
    refresh_seconds: int | None
    col_span: int
    row_span: int
    col: int | None = None
    row: int | None = None
    min_height: int | None = None


class BaseBlock(ABC):
    id: str = ""
    title: str = ""
    description: str = ""
    refresh_seconds: int | None = 30
    col_span: int = 4
    row_span: int = 2
    col: int | None = None
    row: int | None = None
    min_height: int | None = None
    order: int = 100

    def layout_spec(self) -> BlockLayoutSpec:
        if not self.id:
            raise ValueError("Block id must be defined")
        if not self.title:
            raise ValueError(f"Block '{self.id}' must define a title")
        return BlockLayoutSpec(
            id=self.id,
            title=self.title,
            refresh_seconds=self.refresh_seconds,
            col_span=self.col_span,
            row_span=self.row_span,
            col=self.col,
            row=self.row,
            min_height=self.min_height,
        )

    @abstractmethod
    def render(self) -> BlockRender:
        raise NotImplementedError
