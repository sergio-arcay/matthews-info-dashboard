from __future__ import annotations

import random
from datetime import datetime

from mid.blocks.base import BaseBlock, BlockRender


class KpiBlock(BaseBlock):
    id = "kpi"
    title = "Indicadores clave"
    description = "KPIs simulados"
    refresh_seconds = 30
    col_span = 8
    row_span = 2
    col = 1
    row = 3
    order = 40

    def render(self) -> BlockRender:
        sales = random.randint(120, 280)
        conversion = random.uniform(2.1, 6.8)
        tickets = random.randint(8, 24)
        updated = datetime.now().astimezone().strftime("%H:%M")

        html = f"""
        <div class="block-header">
            <h2 class="block-title">{self.title}</h2>
            <span class="block-tag">{updated}</span>
        </div>
        <div class="block-body kpi-body">
            <div class="kpi">
                <div class="kpi-label">Ventas</div>
                <div class="kpi-value">${sales}k</div>
                <div class="kpi-delta positive">+{random.randint(2, 9)}%</div>
            </div>
            <div class="kpi">
                <div class="kpi-label">Conversión</div>
                <div class="kpi-value">{conversion:.1f}%</div>
                <div class="kpi-delta negative">-{random.uniform(0.2, 1.4):.1f}%</div>
            </div>
            <div class="kpi">
                <div class="kpi-label">Tickets abiertos</div>
                <div class="kpi-value">{tickets}</div>
                <div class="kpi-delta neutral">{random.randint(0, 3)} nuevos</div>
            </div>
        </div>
        """.strip()
        return BlockRender(html=html, refresh_seconds=self.refresh_seconds)
