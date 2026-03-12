from __future__ import annotations

import json
import os
from datetime import date, timedelta
from urllib.error import URLError
from urllib.request import Request, urlopen

from mid.blocks.base import BaseBlock, BlockRender

_MAX_DAYS = 7
_DEFAULT_DAYS = 7
_DEFAULT_ORDER_URL = "http://localhost:8000/order"
_DEFAULT_ORDER_TIMEOUT = 150.0
_WEEKDAYS = ["Lun", "Mar", "Mie", "Jue", "Vie", "Sab", "Dom"]
_MONTHS = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]


class TwevePadelAvailabilityBlock(BaseBlock):
    id = "tweve-padel-availability"
    title = "Pistas libres"
    description = "Disponibilidad de pistas de padel"
    refresh_seconds = 3600
    col_span = 4
    row_span = 4
    col = 1
    row = 1
    order = 35
    days_to_show = _DEFAULT_DAYS

    def render(self) -> BlockRender:
        days_to_show = max(1, min(int(self.days_to_show), _MAX_DAYS))
        day_keys = _build_day_keys(days_to_show)
        print(day_keys)
        availability = _fetch_padel_availability(day_keys)

        if availability is None:
            html = f"""
            <div class="block-header">
                <h2 class="block-title">{self.title}</h2>
                <span class="block-tag">Sin datos</span>
            </div>
            <div class="block-body padel-body">
                <div class="padel-empty">Sin disponibilidad cargada</div>
            </div>
            """.strip()
        else:
            today = date.today()
            days_html = "\n".join(
                _render_day(day_key, availability.get(day_key, {}), today) for day_key in day_keys
            )
            html = f"""
            <div class="block-header">
                <h2 class="block-title">{self.title}</h2>
                <span class="block-tag">{days_to_show} dias</span>
            </div>
            <div class="block-body padel-body">
                <div class="padel-days" style="grid-template-columns: repeat({len(day_keys)}, minmax(0, 1fr));">
                    {days_html}
                </div>
            </div>
            """.strip()

        scripts_after = [
            """
            const styleId = "padel-availability-styles";
            if (!document.getElementById(styleId)) {
              const style = document.createElement("style");
              style.id = styleId;
              style.textContent = `
                .padel-body {
                  height: 100%;
                  min-height: 0;
                }

                .padel-days {
                  display: grid;
                  gap: 10px;
                  height: 100%;
                  min-height: 0;
                }

                .padel-day {
                  display: flex;
                  flex-direction: column;
                  gap: 8px;
                  padding: 10px 12px;
                  border-radius: 14px;
                  background: rgba(15, 23, 42, 0.6);
                  border: 1px solid rgba(148, 163, 184, 0.18);
                  min-height: 0;
                }

                .padel-day-header {
                  display: flex;
                  justify-content: space-between;
                  align-items: baseline;
                  gap: 6px;
                }

                .padel-day-title {
                  font-weight: 600;
                  font-size: 0.9rem;
                  white-space: nowrap;
                }

                .padel-day-sub {
                  font-size: 0.72rem;
                  letter-spacing: 0.08em;
                  text-transform: uppercase;
                  color: var(--muted);
                  white-space: nowrap;
                }

                .padel-slots {
                  display: flex;
                  flex-wrap: wrap;
                  gap: 6px;
                  justify-content: center;
                  align-content: flex-start;
                  overflow: auto;
                  min-height: 0;
                  flex: 1;
                }

                .padel-day-footer {
                  display: flex;
                  justify-content: flex-end;
                }

                .padel-slot {
                  display: inline-flex;
                  align-items: center;
                  gap: 4px;
                  padding: 4px 8px;
                  border-radius: 999px;
                  background: rgba(34, 211, 238, 0.12);
                  border: 1px solid rgba(34, 211, 238, 0.3);
                  font-size: 0.75rem;
                  white-space: nowrap;
                }

                .padel-slot-time {
                  font-family: "JetBrains Mono", monospace;
                }

                .padel-slot-count {
                  color: var(--accent);
                  font-weight: 600;
                }

                .padel-empty {
                  color: var(--muted);
                  font-size: 0.8rem;
                }

                @media (max-width: 900px) {
                  .padel-days {
                    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
                  }
                }
              `;
              document.head.appendChild(style);
            }
            """.strip(),
        ]
        return BlockRender(
            html=html,
            refresh_seconds=self.refresh_seconds,
            scripts_after=scripts_after,
        )


def _build_day_keys(days: int) -> list[str]:
    today = date.today()
    return [(today + timedelta(days=offset)).isoformat() for offset in range(days)]


def _fetch_padel_availability(
    day_keys: list[str],
) -> dict[str, dict[str, list[dict[str, str]]]] | None:
    if not day_keys:
        return {}
    payload = {
        "action": "check-vigo-padel-twelve",
        "passkey": "contrasena",
        "payload": {"dates_to_check": day_keys},
    }
    data = json.dumps(payload).encode("utf-8")
    url = _resolve_order_url()
    timeout = _resolve_order_timeout()
    request = Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urlopen(request, timeout=timeout) as response:
            result = json.load(response)
    except (URLError, ValueError):
        return None

    data_payload = result.get("result", {}).get("data")
    if not isinstance(data_payload, dict):
        return None
    return data_payload


def _render_day(day_key: str, day_data: dict[str, list[dict[str, str]]], today: date) -> str:
    day_date = _parse_date(day_key)
    if day_date is None:
        title = day_key
        subtitle = ""
    else:
        title, subtitle = _format_day_label(day_date, today)
    slots = _merge_day_slots(day_data)
    if slots:
        slots_html = "\n".join(
            f"""
            <div class="padel-slot">
                <span class="padel-slot-time">{start}</span>
                <span class="padel-slot-count">({count})</span>
            </div>
            """.strip()
            for start, _, count in slots
        )
    else:
        slots_html = '<div class="padel-empty">Sin pistas</div>'

    return f"""
    <div class="padel-day">
        <div class="padel-day-header">
            <div class="padel-day-title">{title}</div>
        </div>
        <div class="padel-slots">
            {slots_html}
        </div>
        <div class="padel-day-footer">
            <div class="padel-day-sub">{subtitle}</div>
        </div>
    </div>
    """.strip()


def _merge_day_slots(day_data: dict[str, list[dict[str, str]]]) -> list[tuple[str, str, int]]:
    if not isinstance(day_data, dict):
        return []
    counts: dict[tuple[str, str], int] = {}
    for slots in day_data.values():
        if not isinstance(slots, list):
            continue
        for slot in slots:
            if not isinstance(slot, dict):
                continue
            start = slot.get("start")
            end = slot.get("end")
            if not isinstance(start, str) or not isinstance(end, str):
                continue
            key = (start, end)
            counts[key] = counts.get(key, 0) + 1

    merged = [(start, end, count) for (start, end), count in counts.items()]
    merged.sort(key=lambda item: (_time_to_minutes(item[0]), _time_to_minutes(item[1])))
    return merged


def _time_to_minutes(value: str) -> int:
    try:
        hour_str, minute_str = value.split(":")
        hour = int(hour_str)
        minute = int(minute_str)
        if hour == 24:
            hour = 0
        return hour * 60 + minute
    except (ValueError, AttributeError):
        return 10**9


def _parse_date(value: str) -> date | None:
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _format_day_label(day_date: date, today: date) -> tuple[str, str]:
    weekday = _WEEKDAYS[day_date.weekday()]
    month = _MONTHS[day_date.month - 1]
    title = f"{weekday} {day_date.day:02d}"
    subtitle = month
    return title, subtitle


def _resolve_order_url() -> str:
    raw = os.getenv("PADEL_ORDER_URL", _DEFAULT_ORDER_URL).strip()
    return raw or _DEFAULT_ORDER_URL


def _resolve_order_timeout() -> float:
    raw = os.getenv("PADEL_ORDER_TIMEOUT", "").strip()
    if not raw:
        return _DEFAULT_ORDER_TIMEOUT
    try:
        value = float(raw)
    except ValueError:
        return _DEFAULT_ORDER_TIMEOUT
    return value if value > 0 else _DEFAULT_ORDER_TIMEOUT
