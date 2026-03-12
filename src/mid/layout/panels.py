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
    weather_clock = registry.get("weather-clock")
    network_status = registry.get("network-status")
    padel_availability = registry.get("tweve-padel-availability")
    if weather_clock is None or network_status is None or padel_availability is None:
        return None

    grid = GridConfig(columns=2, row_height=None, gap=12, padding=16)
    blocks: list[BlockLayout] = [
        BlockLayout(
            id=f"{weather_clock.id}-1",
            title=weather_clock.title,
            refresh_seconds=weather_clock.refresh_seconds,
            position=BlockPosition(col=1, row=1, col_span=1, row_span=1),
            min_height=None,
        ),
        BlockLayout(
            id=padel_availability.id,
            title=padel_availability.title,
            refresh_seconds=padel_availability.refresh_seconds,
            position=BlockPosition(col=2, row=1, col_span=1, row_span=2),
            min_height=None,
        ),
        BlockLayout(
            id=network_status.id,
            title=network_status.title,
            refresh_seconds=network_status.refresh_seconds,
            position=BlockPosition(col=1, row=2, col_span=1, row_span=1),
            min_height=None,
        ),
    ]
    return PanelLayout(grid=grid, blocks=blocks)
