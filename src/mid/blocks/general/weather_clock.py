from __future__ import annotations

import json
import time
from urllib.error import URLError
from urllib.request import urlopen

from mid.blocks.base import BaseBlock, BlockRender

_LOCATION_CACHE: tuple[float, dict[str, object]] | None = None
_LOCATION_TTL_SECONDS = 60 * 60


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
        location_json = json.dumps(location)
        html = f"""
        <div class="block-header">
            <h2 class="block-title">{self.title}</h2>
            <span class="block-tag" data-weather-location>{location.get("name", "Local")}</span>
        </div>
        <div class="block-body weather-clock-body">
            <div class="weather-clock-main">
                <div class="weather-clock-time" data-weather-time>--:--</div>
                <div class="weather-clock-weekday" data-weather-weekday>--</div>
                <div class="weather-clock-date" data-weather-date>--</div>
                <div class="weather-updated" data-weather-updated>Actualizado --</div>
            </div>
            <div class="weather-clock-weather">
                <div class="weather-temp" data-weather-temp>--</div>
                <div class="weather-condition" data-weather-condition>Sin datos</div>
                <div class="weather-meta">
                    <div class="weather-chip">
                        <span>Humedad</span>
                        <strong data-weather-humidity>--</strong>
                    </div>
                    <div class="weather-chip">
                        <span>Viento</span>
                        <strong data-weather-wind>--</strong>
                    </div>
                    <div class="weather-chip">
                        <span>Sensa.</span>
                        <strong data-weather-feels>--</strong>
                    </div>
                    <div class="weather-chip">
                        <span>Lluvia mañana</span>
                        <strong data-weather-rain-morning>--</strong>
                    </div>
                    <div class="weather-chip">
                        <span>Lluvia tarde</span>
                        <strong data-weather-rain-afternoon>--</strong>
                    </div>
                    <div class="weather-chip">
                        <span>Lluvia noche</span>
                        <strong data-weather-rain-night>--</strong>
                    </div>
                </div>
            </div>
        </div>
        """.strip()

        script = """
            const timeEl = context.blockEl.querySelector("[data-weather-time]");
            const dateEl = context.blockEl.querySelector("[data-weather-date]");
            const weekdayEl = context.blockEl.querySelector("[data-weather-weekday]");
            const locationEl = context.blockEl.querySelector("[data-weather-location]");
            const updatedEl = context.blockEl.querySelector("[data-weather-updated]");
            const tempEl = context.blockEl.querySelector("[data-weather-temp]");
            const conditionEl = context.blockEl.querySelector("[data-weather-condition]");
            const humidityEl = context.blockEl.querySelector("[data-weather-humidity]");
            const windEl = context.blockEl.querySelector("[data-weather-wind]");
            const feelsEl = context.blockEl.querySelector("[data-weather-feels]");
            const rainMorningEl = context.blockEl.querySelector("[data-weather-rain-morning]");
            const rainAfternoonEl = context.blockEl.querySelector("[data-weather-rain-afternoon]");
            const rainNightEl = context.blockEl.querySelector("[data-weather-rain-night]");
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

            const defaultLocation = __DEFAULT_LOCATION__;
            if (!window.weatherClockLocation) {
              window.weatherClockLocation = defaultLocation;
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

            const weatherCodes = {
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
            };

            async function resolveLocation() {
              const current = window.weatherClockLocation || {};
              const hasCoords = Number.isFinite(current.lat) && Number.isFinite(current.lon);
              if (hasCoords) return current;
              try {
                const response = await fetch("https://ipapi.co/json/");
                if (response.ok) {
                  const data = await response.json();
                  const nameParts = [data.city, data.region, data.country_name].filter(Boolean);
                  const name = nameParts.join(", ") || "Local";
                  const lat = Number(data.latitude);
                  const lon = Number(data.longitude);
                  if (Number.isFinite(lat) && Number.isFinite(lon)) {
                    const resolved = { name, lat, lon };
                    window.weatherClockLocation = resolved;
                    return resolved;
                  }
                }
              } catch (error) {
                console.warn("No se pudo resolver ubicacion", error);
              }
              return current;
            }

            function formatTemp(value) {
              if (!Number.isFinite(value)) return "--";
              return `${value.toFixed(1)}°C`;
            }

            function formatValue(value, suffix) {
              if (!Number.isFinite(value)) return "--";
              return `${value.toFixed(0)}${suffix}`;
            }

            function formatPercent(value) {
              if (!Number.isFinite(value)) return "--";
              return `${Math.round(value)}%`;
            }

            function computeRainChances(payload) {
              const hourly = payload.hourly || {};
              const times = Array.isArray(hourly.time) ? hourly.time : [];
              const probs = Array.isArray(hourly.precipitation_probability)
                ? hourly.precipitation_probability
                : [];
              if (!times.length || times.length !== probs.length) return null;
              const baseTime = payload.current?.time || times[0];
              const dateKey = typeof baseTime === "string" ? baseTime.split("T")[0] : null;
              if (!dateKey) return null;

              const buckets = {
                morning: [],
                afternoon: [],
                night: [],
              };
              for (let i = 0; i < times.length; i += 1) {
                const timeStr = times[i];
                if (typeof timeStr !== "string") continue;
                const [datePart, hourPart] = timeStr.split("T");
                if (datePart !== dateKey) continue;
                const hour = Number(hourPart?.slice(0, 2));
                if (!Number.isFinite(hour)) continue;
                if (hour >= 7 && hour < 13) {
                  buckets.morning.push(Number(probs[i]));
                } else if (hour >= 13 && hour < 21) {
                  buckets.afternoon.push(Number(probs[i]));
                } else if (hour >= 21 && hour < 24) {
                  buckets.night.push(Number(probs[i]));
                }
              }

              function maxOrNull(values) {
                const filtered = values.filter((v) => Number.isFinite(v));
                if (!filtered.length) return null;
                return Math.max(...filtered);
              }

              return {
                morning: maxOrNull(buckets.morning),
                afternoon: maxOrNull(buckets.afternoon),
                night: maxOrNull(buckets.night),
              };
            }

            async function updateWeather() {
              const location = await resolveLocation();
              if (locationEl && location && location.name) {
                locationEl.textContent = location.name;
              }
              if (!location || !Number.isFinite(location.lat) || !Number.isFinite(location.lon)) {
                if (conditionEl) conditionEl.textContent = "Sin ubicacion";
                return;
              }
              const url = `https://api.open-meteo.com/v1/forecast?latitude=${location.lat}&longitude=${location.lon}&current=temperature_2m,apparent_temperature,relative_humidity_2m,wind_speed_10m,weather_code&hourly=precipitation_probability&forecast_days=1&timezone=auto`;
              try {
                const response = await fetch(url);
                if (!response.ok) throw new Error(`HTTP ${response.status}`);
                const payload = await response.json();
                const current = payload.current || {};
                const temp = Number(current.temperature_2m);
                const feels = Number(current.apparent_temperature);
                const humidity = Number(current.relative_humidity_2m);
                const wind = Number(current.wind_speed_10m);
                const code = Number(current.weather_code);
                const label = weatherCodes[code] || "Condicion variable";
                if (tempEl) tempEl.textContent = formatTemp(temp);
                if (feelsEl) feelsEl.textContent = formatTemp(feels);
                if (humidityEl) humidityEl.textContent = formatValue(humidity, "%");
                if (windEl) windEl.textContent = formatValue(wind, " km/h");
                if (conditionEl) conditionEl.textContent = label;
                const rain = computeRainChances(payload);
                if (rainMorningEl) {
                  rainMorningEl.textContent = rain ? formatPercent(rain.morning) : "--";
                }
                if (rainAfternoonEl) {
                  rainAfternoonEl.textContent = rain ? formatPercent(rain.afternoon) : "--";
                }
                if (rainNightEl) {
                  rainNightEl.textContent = rain ? formatPercent(rain.night) : "--";
                }
                if (updatedEl) {
                  const now = new Date();
                  updatedEl.textContent = `Actualizado ${formatterTime.format(now)}`;
                }
              } catch (error) {
                if (conditionEl) conditionEl.textContent = "Sin datos";
              }
            }

            updateWeather();
            const weatherTimerKey = "weatherClockWeatherTimer";
            const existingWeatherTimer = context.blockEl.dataset[weatherTimerKey];
            if (existingWeatherTimer) {
              window.clearInterval(Number(existingWeatherTimer));
            }
            const weatherInterval = window.setInterval(updateWeather, 5 * 60 * 1000);
            context.blockEl.dataset[weatherTimerKey] = String(weatherInterval);
            """.strip()
        script = script.replace("__DEFAULT_LOCATION__", location_json)
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
