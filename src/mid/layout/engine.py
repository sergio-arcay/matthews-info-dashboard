from __future__ import annotations

from dataclasses import dataclass

from mid.blocks.base import BaseBlock, BlockLayoutSpec
from mid.layout.schemas import BlockLayout, BlockPosition, GridConfig


@dataclass
class LayoutResult:
    grid: GridConfig
    blocks: list[BlockLayout]


def default_grid() -> GridConfig:
    return GridConfig(columns=12, row_height=120, gap=12, padding=16)


def build_layout(blocks: list[BaseBlock], grid: GridConfig) -> list[BlockLayout]:
    occupied: set[tuple[int, int]] = set()
    layouts: list[BlockLayout] = []

    for block in blocks:
        spec = block.layout_spec()
        col, row = _place_block(spec, grid, occupied)
        _occupy(occupied, col, row, spec)
        min_height = spec.min_height
        if min_height is None:
            min_height = spec.row_span * grid.row_height + (spec.row_span - 1) * grid.gap
        layouts.append(
            BlockLayout(
                id=spec.id,
                title=spec.title,
                refresh_seconds=spec.refresh_seconds,
                position=BlockPosition(
                    col=col,
                    row=row,
                    col_span=spec.col_span,
                    row_span=spec.row_span,
                ),
                min_height=min_height,
            )
        )

    return layouts


def _place_block(spec: BlockLayoutSpec, grid: GridConfig, occupied: set[tuple[int, int]]) -> tuple[int, int]:
    if spec.col is not None and spec.row is not None:
        if _fits(spec.col, spec.row, spec, grid, occupied):
            return spec.col, spec.row

    row = 1
    while True:
        for col in range(1, grid.columns - spec.col_span + 2):
            if _fits(col, row, spec, grid, occupied):
                return col, row
        row += 1


def _fits(
    col: int,
    row: int,
    spec: BlockLayoutSpec,
    grid: GridConfig,
    occupied: set[tuple[int, int]],
) -> bool:
    if col < 1 or row < 1:
        return False
    if col + spec.col_span - 1 > grid.columns:
        return False
    for r in range(row, row + spec.row_span):
        for c in range(col, col + spec.col_span):
            if (r, c) in occupied:
                return False
    return True


def _occupy(occupied: set[tuple[int, int]], col: int, row: int, spec: BlockLayoutSpec) -> None:
    for r in range(row, row + spec.row_span):
        for c in range(col, col + spec.col_span):
            occupied.add((r, c))
