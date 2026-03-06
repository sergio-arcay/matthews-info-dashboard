from __future__ import annotations

import os
import platform
from datetime import datetime

from mid.blocks.base import BaseBlock, BlockRender


class SystemStatusBlock(BaseBlock):
    id = "system-status"
    title = "Estado del sistema"
    description = "Resumen del host"
    refresh_seconds = 20
    col_span = 4
    row_span = 2
    col = 5
    row = 1
    order = 20

    def render(self) -> BlockRender:
        hostname = platform.node() or "host"
        os_name = f"{platform.system()} {platform.release()}"
        python_ver = platform.python_version()
        load_avg = _load_average()
        updated = datetime.now().astimezone().strftime("%H:%M:%S")

        load_html = "" if load_avg is None else f"<div class=\"stat-value\">{load_avg}</div>"
        load_label = "N/A" if load_avg is None else "Load promedio"

        html = f"""
        <div class="block-header">
            <h2 class="block-title">{self.title}</h2>
            <span class="block-tag">{hostname}</span>
        </div>
        <div class="block-body stats-body">
            <div class="stat">
                <div class="stat-label">Sistema</div>
                <div class="stat-value">{os_name}</div>
            </div>
            <div class="stat">
                <div class="stat-label">Python</div>
                <div class="stat-value">{python_ver}</div>
            </div>
            <div class="stat">
                <div class="stat-label">{load_label}</div>
                {load_html}
            </div>
            <div class="stat">
                <div class="stat-label">Actualizado</div>
                <div class="stat-value">{updated}</div>
            </div>
        </div>
        """.strip()
        return BlockRender(html=html, refresh_seconds=self.refresh_seconds)


def _load_average() -> str | None:
    if hasattr(os, "getloadavg"):
        try:
            loads = os.getloadavg()
            return f"{loads[0]:.2f} / {loads[1]:.2f} / {loads[2]:.2f}"
        except OSError:
            return None
    return None
