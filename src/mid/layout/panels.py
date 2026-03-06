from __future__ import annotations

from dataclasses import dataclass

from mid.blocks.registry import BlockRegistry
from mid.layout.schemas import BlockLayout, BlockPosition, GridConfig


@dataclass
class PanelLayout:
    grid: GridConfig
    blocks: list[BlockLayout]


def build_panel(panel_id: str, registry: BlockRegistry) -> PanelLayout | None:
    if panel_id == "raspi-dashboard":
        return _build_raspi_dashboard(registry)
    return None


def _build_raspi_dashboard(registry: BlockRegistry) -> PanelLayout | None:
    clock = registry.get("clock")
    if clock is None:
        return None

    grid = GridConfig(columns=2, row_height=None, gap=12, padding=16)
    positions = [
        (1, 1),
        (2, 1),
        (1, 2),
        (2, 2),
    ]
    blocks: list[BlockLayout] = []
    for idx, (col, row) in enumerate(positions, start=1):
        blocks.append(
            BlockLayout(
                id=f"{clock.id}-{idx}",
                title=clock.title,
                refresh_seconds=clock.refresh_seconds,
                position=BlockPosition(
                    col=col,
                    row=row,
                    col_span=1,
                    row_span=1,
                ),
                min_height=None,
            )
        )
    return PanelLayout(grid=grid, blocks=blocks)
