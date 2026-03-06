from __future__ import annotations

from mid.blocks.base import BaseBlock, BlockRender


class ClockBlock(BaseBlock):
    id = "clock"
    title = "Hora actual"
    description = "Reloj del sistema"
    refresh_seconds = None
    col_span = 4
    row_span = 4
    col = 1
    row = 1
    order = 10

    def render(self) -> BlockRender:
        html = f"""
        <div class="block-header">
            <h2 class="block-title">{self.title}</h2>
            <span class="block-tag">Local</span>
        </div>
        <div class="block-body clock-body">
            <div class="clock-time" data-clock-time></div>
            <div class="clock-date" data-clock-date></div>
        </div>
        """.strip()
        scripts_after = [
            """
            const timeEl = context.blockEl.querySelector("[data-clock-time]");
            const dateEl = context.blockEl.querySelector("[data-clock-date]");
            if (!timeEl || !dateEl) return;
            const existing = context.blockEl.dataset.clockTimer;
            if (existing) {
              window.clearInterval(Number(existing));
            }
            const formatterTime = new Intl.DateTimeFormat("es-ES", {
              hour: "2-digit",
              minute: "2-digit",
              second: "2-digit",
            });
            const formatterDate = new Intl.DateTimeFormat("es-ES", {
              weekday: "long",
              year: "numeric",
              month: "long",
              day: "numeric",
            });
            function updateClock() {
              const now = new Date();
              timeEl.textContent = formatterTime.format(now);
              dateEl.textContent = formatterDate.format(now);
            }
            updateClock();
            const timerId = window.setInterval(updateClock, 1000);
            context.blockEl.dataset.clockTimer = String(timerId);
            """.strip(),
        ]
        return BlockRender(
            html=html,
            refresh_seconds=self.refresh_seconds,
            scripts_after=scripts_after,
        )
