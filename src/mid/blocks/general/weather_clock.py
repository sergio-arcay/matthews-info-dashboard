from __future__ import annotations

import json
import time
from datetime import datetime
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from mid.blocks.base import BaseBlock, BlockRender

_LOCATION_CACHE: tuple[float, dict[str, object]] | None = None
_LOCATION_TTL_SECONDS = 60 * 60
_WEATHER_CODES = {
    0: "Despejado",
    1: "Principalmente despejado",
    2: "Parcialmente nublado",
    3: "Nublado",
    45: "Niebla",
    48: "Niebla con escarcha",
    51: "Llovizna ligera",
    53: "Llovizna moderada",
    55: "Llovizna intensa",
    56: "Llovizna helada",
    57: "Llovizna helada intensa",
    61: "Lluvia ligera",
    63: "Lluvia moderada",
    65: "Lluvia intensa",
    66: "Lluvia helada",
    67: "Lluvia helada intensa",
    71: "Nieve ligera",
    73: "Nieve moderada",
    75: "Nieve intensa",
    77: "Granizo",
    80: "Chubascos ligeros",
    81: "Chubascos moderados",
    82: "Chubascos intensos",
    85: "Chubascos de nieve",
    86: "Chubascos de nieve intensos",
    95: "Tormenta",
    96: "Tormenta con granizo",
    99: "Tormenta fuerte con granizo",
}


class WeatherClockBlock(BaseBlock):
    id = "weather-clock"
    title = "Hora y clima"
    description = "Reloj local con clima"
    refresh_seconds = 3600
    col_span = 4
    row_span = 4
    col = 1
    row = 1
    order = 15

    def render(self) -> BlockRender:
        location = _resolve_location()
        weather = _fetch_weather(location)
        location_name = str(location.get("name") or "Local")
        temp_label = _format_temp(weather.get("temperature"))
        feels_label = _format_temp(weather.get("feels"))
        humidity_label = _format_value(weather.get("humidity"), "%")
        wind_label = _format_value(weather.get("wind"), " km/h")
        condition_label = weather.get("condition") or "Sin datos"
        rain_morning = _format_percent(weather.get("rain_morning"))
        rain_afternoon = _format_percent(weather.get("rain_afternoon"))
        rain_night = _format_percent(weather.get("rain_night"))
        updated_at = weather.get("updated_at") or datetime.now().astimezone()
        updated_label = f"Actualizado {updated_at.strftime('%H:%M')}"
        html = f"""
        <div class="block-header">
            <h2 class="block-title">{self.title}</h2>
            <span class="block-tag" data-weather-location>{location_name}</span>
        </div>
        <div class="block-body weather-clock-body">
            <div class="weather-clock-main">
                <div class="weather-clock-time" data-weather-time>--:--</div>
                <div class="weather-clock-weekday" data-weather-weekday>--</div>
                <div class="weather-clock-date" data-weather-date>--</div>
                <div class="weather-updated" data-weather-updated>{updated_label}</div>
            </div>
            <div class="weather-clock-weather">
                <div class="weather-temp" data-weather-temp>{temp_label}</div>
                <div class="weather-condition" data-weather-condition>{condition_label}</div>
                <div class="weather-meta">
                    <div class="weather-chip">
                        <span>Humedad</span>
                        <strong data-weather-humidity>{humidity_label}</strong>
                    </div>
                    <div class="weather-chip">
                        <span>Viento</span>
                        <strong data-weather-wind>{wind_label}</strong>
                    </div>
                    <div class="weather-chip">
                        <span>Sensa.</span>
                        <strong data-weather-feels>{feels_label}</strong>
                    </div>
                    <div class="weather-chip">
                        <span>Lluvia mañana</span>
                        <strong data-weather-rain-morning>{rain_morning}</strong>
                    </div>
                    <div class="weather-chip">
                        <span>Lluvia tarde</span>
                        <strong data-weather-rain-afternoon>{rain_afternoon}</strong>
                    </div>
                    <div class="weather-chip">
                        <span>Lluvia noche</span>
                        <strong data-weather-rain-night>{rain_night}</strong>
                    </div>
                </div>
            </div>
        </div>
        """.strip()

        script = """
            const timeEl = context.blockEl.querySelector("[data-weather-time]");
            const dateEl = context.blockEl.querySelector("[data-weather-date]");
            const weekdayEl = context.blockEl.querySelector("[data-weather-weekday]");
            if (!timeEl || !dateEl || !weekdayEl) return;

            const styleId = "weather-clock-styles";
            if (!document.getElementById(styleId)) {
              const style = document.createElement("style");
              style.id = styleId;
              style.textContent = `
                .weather-clock-body {
                  display: grid;
                  grid-template-columns: 1.15fr 0.85fr;
                  gap: 12px;
                  align-items: stretch;
                  height: 100%;
                }

                .weather-clock-main {
                  display: flex;
                  flex-direction: column;
                  gap: 4px;
                  justify-content: center;
                }

                .weather-clock-time {
                  font-size: clamp(2.6rem, 5vw, 3.6rem);
                  font-weight: 700;
                  font-family: "JetBrains Mono", monospace;
                }

                .weather-clock-weekday {
                  text-transform: capitalize;
                  font-size: 1.05rem;
                }

                .weather-clock-date {
                  color: var(--muted);
                  font-size: 0.95rem;
                }

                .weather-updated {
                  color: var(--muted);
                  font-size: 0.75rem;
                }

                .weather-clock-weather {
                  display: flex;
                  flex-direction: column;
                  gap: 8px;
                  justify-content: center;
                }

                .weather-temp {
                  font-size: 2.2rem;
                  font-weight: 700;
                }

                .weather-condition {
                  color: var(--muted);
                  text-transform: capitalize;
                  font-size: 0.95rem;
                }

                .weather-meta {
                  display: grid;
                  grid-template-columns: repeat(3, minmax(110px, 1fr));
                  gap: 8px;
                }

                .weather-chip {
                  display: flex;
                  justify-content: space-between;
                  align-items: center;
                  gap: 8px;
                  padding: 8px 12px;
                  border-radius: 12px;
                  background: rgba(15, 23, 42, 0.6);
                  border: 1px solid rgba(148, 163, 184, 0.18);
                  font-size: 0.8rem;
                  color: var(--muted);
                }

                .weather-chip strong {
                  color: var(--text);
                  font-weight: 600;
                }

                @media (max-width: 900px) {
                  .weather-clock-body {
                    grid-template-columns: 1fr;
                  }
                }
              `;
              document.head.appendChild(style);
            }

            const timerKey = "weatherClockTimer";
            const existingTimer = context.blockEl.dataset[timerKey];
            if (existingTimer) {
              window.clearInterval(Number(existingTimer));
            }

            const formatterTime = new Intl.DateTimeFormat("es-ES", {
              hour: "2-digit",
              minute: "2-digit",
              second: "2-digit",
            });
            const formatterDate = new Intl.DateTimeFormat("es-ES", {
              day: "2-digit",
              month: "long",
              year: "numeric",
            });
            const formatterWeekday = new Intl.DateTimeFormat("es-ES", {
              weekday: "long",
            });

            function updateClock() {
              const now = new Date();
              timeEl.textContent = formatterTime.format(now);
              dateEl.textContent = formatterDate.format(now);
              weekdayEl.textContent = formatterWeekday.format(now);
            }

            updateClock();
            const intervalId = window.setInterval(updateClock, 1000);
            context.blockEl.dataset[timerKey] = String(intervalId);

            """.strip()
        scripts_after = [script]
        return BlockRender(
            html=html,
            refresh_seconds=self.refresh_seconds,
            scripts_after=scripts_after,
        )


def _resolve_location() -> dict[str, object]:
    cached = _LOCATION_CACHE
    now = time.time()
    if cached and now - cached[0] < _LOCATION_TTL_SECONDS:
        return cached[1]

    location = _fetch_location_from_ipapi()
    _cache_location(location)
    return location


def _cache_location(location: dict[str, object]) -> None:
    global _LOCATION_CACHE
    _LOCATION_CACHE = (time.time(), location)


def _fetch_location_from_ipapi() -> dict[str, object]:
    try:
        with urlopen("https://ipapi.co/json/", timeout=2) as response:
            payload = json.load(response)
    except (URLError, ValueError):
        return {"name": "Local", "lat": None, "lon": None}

    lat = payload.get("latitude")
    lon = payload.get("longitude")
    try:
        lat_val = float(lat) if lat is not None else None
        lon_val = float(lon) if lon is not None else None
    except (TypeError, ValueError):
        lat_val = None
        lon_val = None

    name_parts = [payload.get("city"), payload.get("region"), payload.get("country_name")]
    name = ", ".join(part for part in name_parts if part) or "Local"

    if lat_val is None or lon_val is None:
        return {"name": name, "lat": None, "lon": None}

    return {"name": name, "lat": lat_val, "lon": lon_val}


def _fetch_weather(location: dict[str, object]) -> dict[str, object]:
    lat = _to_float(location.get("lat"))
    lon = _to_float(location.get("lon"))
    if lat is None or lon is None:
        return {"condition": "Sin ubicacion"}

    query = urlencode(
        {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,apparent_temperature,relative_humidity_2m,wind_speed_10m,weather_code",
            "hourly": "precipitation_probability",
            "forecast_days": 1,
            "timezone": "auto",
        }
    )
    url = f"https://api.open-meteo.com/v1/forecast?{query}"
    try:
        with urlopen(url, timeout=3) as response:
            payload = json.load(response)
    except (URLError, ValueError):
        return {}

    current = payload.get("current") if isinstance(payload, dict) else {}
    if not isinstance(current, dict):
        current = {}

    temp = _to_float(current.get("temperature_2m"))
    feels = _to_float(current.get("apparent_temperature"))
    humidity = _to_float(current.get("relative_humidity_2m"))
    wind = _to_float(current.get("wind_speed_10m"))
    code = _to_int(current.get("weather_code"))
    condition = _WEATHER_CODES.get(code, "Condicion variable") if code is not None else None

    rain = _compute_rain_chances(payload) if isinstance(payload, dict) else None

    return {
        "temperature": temp,
        "feels": feels,
        "humidity": humidity,
        "wind": wind,
        "condition": condition,
        "rain_morning": rain.get("morning") if rain else None,
        "rain_afternoon": rain.get("afternoon") if rain else None,
        "rain_night": rain.get("night") if rain else None,
        "updated_at": datetime.now().astimezone(),
    }


def _compute_rain_chances(payload: dict[str, object]) -> dict[str, float | None] | None:
    hourly = payload.get("hourly")
    if not isinstance(hourly, dict):
        return None
    times = hourly.get("time")
    probs = hourly.get("precipitation_probability")
    if not isinstance(times, list) or not isinstance(probs, list) or len(times) != len(probs):
        return None
    if not times:
        return None

    base_time = payload.get("current", {}).get("time") if isinstance(payload.get("current"), dict) else None
    if not isinstance(base_time, str):
        base_time = times[0] if isinstance(times[0], str) else None
    if not isinstance(base_time, str) or "T" not in base_time:
        return None
    date_key = base_time.split("T", 1)[0]

    buckets: dict[str, list[float]] = {"morning": [], "afternoon": [], "night": []}
    for time_str, prob in zip(times, probs):
        if not isinstance(time_str, str):
            continue
        parts = time_str.split("T", 1)
        if len(parts) != 2 or parts[0] != date_key:
            continue
        hour_str = parts[1][:2]
        hour = _to_int(hour_str)
        if hour is None:
            continue
        value = _to_float(prob)
        if value is None:
            continue
        if 7 <= hour < 13:
            buckets["morning"].append(value)
        elif 13 <= hour < 21:
            buckets["afternoon"].append(value)
        elif 21 <= hour < 24:
            buckets["night"].append(value)

    def max_or_none(values: list[float]) -> float | None:
        return max(values) if values else None

    return {
        "morning": max_or_none(buckets["morning"]),
        "afternoon": max_or_none(buckets["afternoon"]),
        "night": max_or_none(buckets["night"]),
    }


def _format_temp(value: float | None) -> str:
    if value is None:
        return "--"
    return f"{value:.1f}°C"


def _format_value(value: float | None, suffix: str) -> str:
    if value is None:
        return "--"
    return f"{value:.0f}{suffix}"


def _format_percent(value: float | None) -> str:
    if value is None:
        return "--"
    return f"{round(value)}%"


def _to_float(value: object) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: object) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
