from __future__ import annotations

import json
import re
import socket
import struct
import subprocess
import time
from datetime import datetime

from mid.blocks.base import BaseBlock, BlockRender


class NetworkStatusBlock(BaseBlock):
    id = "network-status"
    title = "Estado de red"
    description = "Resumen de la red local"
    refresh_seconds = 3600
    col_span = 4
    row_span = 4
    col = 5
    row = 1
    order = 25

    def render(self) -> BlockRender:
        iface, gateway = _get_default_route()
        stats = _get_interface_stats(iface)
        iface_label = iface or "N/A"
        local_ip = _get_local_ip() or "N/A"
        gateway_label = gateway or "N/A"
        devices = _count_devices()
        latency = _ping_latency()
        uptime = _format_uptime()
        speedtest = _get_speedtest()
        updated = datetime.now().astimezone().strftime("%H:%M:%S")

        rx_total = _format_bytes(stats.rx_bytes) if stats else "N/A"
        tx_total = _format_bytes(stats.tx_bytes) if stats else "N/A"

        devices_label = str(devices) if devices is not None else "N/A"
        speedtest_latency = speedtest.latency_ms if speedtest else None
        latency_label = _format_latency(speedtest_latency) or _format_latency(latency) or "N/A"
        status_label, status_class = _status_from_latency(
            speedtest_latency if speedtest_latency is not None else latency
        )

        download_max = _format_speed(speedtest.download_bps) if speedtest else "N/A"
        upload_max = _format_speed(speedtest.upload_bps) if speedtest else "N/A"
        speedtest_time = speedtest.updated_at if speedtest else None
        speedtest_label = speedtest_time.strftime("%H:%M:%S") if speedtest_time else "N/A"

        html = f"""
        <div class="block-header">
            <h2 class="block-title">{self.title}</h2>
            <span class="block-tag">{iface_label}</span>
        </div>
        <div class="block-body network-body">
            <div class="network-speed">
                <div class="network-speed-item">
                    <div class="network-label">Descarga max</div>
                    <div class="network-value">{download_max}</div>
                </div>
                <div class="network-speed-item">
                    <div class="network-label">Subida max</div>
                    <div class="network-value">{upload_max}</div>
                </div>
            </div>
            <div class="network-grid">
                <div class="network-card">
                    <div class="network-label">Latencia</div>
                    <div class="network-value">{latency_label}</div>
                </div>
                <div class="network-card">
                    <div class="network-label">Dispositivos</div>
                    <div class="network-value">{devices_label}</div>
                </div>
                <div class="network-card">
                    <div class="network-label">IP local</div>
                    <div class="network-value">{local_ip}</div>
                </div>
                <div class="network-card">
                    <div class="network-label">Gateway</div>
                    <div class="network-value">{gateway_label}</div>
                </div>
                <div class="network-card">
                    <div class="network-label">Rx total</div>
                    <div class="network-value">{rx_total}</div>
                </div>
                <div class="network-card">
                    <div class="network-label">Tx total</div>
                    <div class="network-value">{tx_total}</div>
                </div>
                <div class="network-card">
                    <div class="network-label">Uptime red</div>
                    <div class="network-value">{uptime}</div>
                </div>
                <div class="network-card">
                    <div class="network-label">Estado</div>
                    <div class="network-value network-status {status_class}">{status_label}</div>
                </div>
            </div>
            <div class="network-foot">
                <span class="network-foot-label">Speedtest {speedtest_label} · Actualizado {updated}</span>
            </div>
        </div>
        """.strip()

        scripts_after = [
            """
            const styleId = "network-status-styles";
            if (!document.getElementById(styleId)) {
              const style = document.createElement("style");
              style.id = styleId;
              style.textContent = `
                .network-body {
                  display: grid;
                  gap: 10px;
                  align-content: stretch;
                  height: 100%;
                  grid-template-rows: auto 1fr auto;
                }

                .network-speed {
                  display: grid;
                  grid-template-columns: repeat(2, minmax(0, 1fr));
                  gap: 12px;
                  width: 100%;
                }

                .network-speed-item {
                  padding: 12px 14px;
                  border-radius: 14px;
                  background: rgba(34, 211, 238, 0.12);
                  border: 1px solid rgba(34, 211, 238, 0.3);
                }

                .network-speed-item .network-value {
                  font-size: 1.4rem;
                  font-family: "JetBrains Mono", monospace;
                }

                .network-label {
                  color: var(--muted);
                  font-size: 0.74rem;
                  text-transform: uppercase;
                  letter-spacing: 0.08em;
                }

                .network-value {
                  font-weight: 600;
                  font-size: 1.15rem;
                  margin-top: 4px;
                }

                .network-grid {
                  display: grid;
                  grid-template-columns: repeat(4, minmax(0, 1fr));
                  gap: 10px;
                  align-content: stretch;
                }

                .network-card {
                  padding: 10px 12px;
                  border-radius: 12px;
                  background: rgba(15, 23, 42, 0.6);
                  border: 1px solid rgba(148, 163, 184, 0.18);
                }

                .network-status.status-success {
                  color: var(--success);
                }

                .network-status.status-neutral {
                  color: var(--neutral);
                }

                .network-status.status-danger {
                  color: var(--danger);
                }

                .network-foot {
                  display: flex;
                  justify-content: flex-end;
                }

                .network-foot-label {
                  color: var(--muted);
                  font-size: 0.75rem;
                }

                @media (max-width: 900px) {
                  .network-speed {
                    grid-template-columns: 1fr;
                  }

                  .network-grid {
                    grid-template-columns: repeat(2, minmax(0, 1fr));
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


class _NetStats:
    def __init__(self, rx_bytes: int, tx_bytes: int) -> None:
        self.rx_bytes = rx_bytes
        self.tx_bytes = tx_bytes


class _SpeedTestResult:
    def __init__(self, download_bps: float, upload_bps: float, latency_ms: float) -> None:
        self.download_bps = download_bps
        self.upload_bps = upload_bps
        self.latency_ms = latency_ms
        self.updated_at = datetime.now().astimezone()


_SPEEDTEST_CACHE: tuple[float, _SpeedTestResult] | None = None
_SPEEDTEST_TTL_SECONDS = 10 * 60


def _get_default_route() -> tuple[str | None, str | None]:
    try:
        with open("/proc/net/route", "r", encoding="utf-8") as handle:
            for line in handle:
                parts = line.strip().split()
                if len(parts) < 3 or parts[1] != "00000000":
                    continue
                iface = parts[0]
                gateway_hex = parts[2]
                gateway_ip = _hex_to_ip(gateway_hex)
                return iface, gateway_ip
    except OSError:
        return None, None
    return None, None


def _hex_to_ip(hex_str: str) -> str | None:
    try:
        raw = struct.pack("<L", int(hex_str, 16))
        return socket.inet_ntoa(raw)
    except (ValueError, OSError):
        return None


def _get_interface_stats(iface: str | None) -> _NetStats | None:
    stats = _read_net_dev()
    if not stats:
        return None
    if iface and iface in stats:
        rx_bytes, tx_bytes = stats[iface]
        return _NetStats(rx_bytes=rx_bytes, tx_bytes=tx_bytes)

    candidates = {name: values for name, values in stats.items() if name != "lo"}
    if not candidates:
        return None
    best_iface = max(candidates.items(), key=lambda item: item[1][0] + item[1][1])[0]
    rx_bytes, tx_bytes = candidates[best_iface]
    return _NetStats(rx_bytes=rx_bytes, tx_bytes=tx_bytes)


def _read_net_dev() -> dict[str, tuple[int, int]]:
    stats: dict[str, tuple[int, int]] = {}
    try:
        with open("/proc/net/dev", "r", encoding="utf-8") as handle:
            for line in handle:
                if ":" not in line:
                    continue
                iface, data = line.split(":", 1)
                iface = iface.strip()
                fields = data.split()
                if len(fields) < 16:
                    continue
                rx_bytes = int(fields[0])
                tx_bytes = int(fields[8])
                stats[iface] = (rx_bytes, tx_bytes)
    except OSError:
        return {}
    return stats


def _get_local_ip() -> str | None:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except OSError:
        return None


def _count_devices() -> int | None:
    output = _run_command(["ip", "neigh", "show"], timeout=1.5)
    if output:
        count = 0
        for line in output.splitlines():
            if not line.strip() or "FAILED" in line:
                continue
            count += 1
        return count

    try:
        with open("/proc/net/arp", "r", encoding="utf-8") as handle:
            lines = handle.readlines()[1:]
        return sum(1 for line in lines if line.strip())
    except OSError:
        return None


def _ping_latency() -> float | None:
    output = _run_command(["ping", "-c", "1", "-W", "1", "1.1.1.1"], timeout=2)
    if output:
        match = re.search(r"time=([0-9.]+)\\s*ms", output)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass
    return _tcp_latency()


def _run_command(command: list[str], timeout: float, input_text: str | None = None) -> str | None:
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            input=input_text,
        )
    except (subprocess.SubprocessError, FileNotFoundError):
        return None
    stdout = result.stdout.strip()
    stderr = result.stderr.strip()
    if stdout:
        return stdout
    if stderr:
        return stderr
    return None


def _get_speedtest() -> _SpeedTestResult | None:
    cached = _SPEEDTEST_CACHE
    now = time.time()
    if cached and now - cached[0] < _SPEEDTEST_TTL_SECONDS:
        return cached[1]

    result = _run_speedtest()
    if result is None:
        return cached[1] if cached else None

    _cache_speedtest(result)
    return result


def _cache_speedtest(result: _SpeedTestResult) -> None:
    global _SPEEDTEST_CACHE
    _SPEEDTEST_CACHE = (time.time(), result)


def _run_speedtest() -> _SpeedTestResult | None:
    for command in (
        ["speedtest", "--accept-license", "--accept-gdpr", "--format=json"],
        ["speedtest", "--accept-license", "--accept-gdpr", "-f", "json"],
        ["speedtest", "--format=json"],
        ["speedtest", "-f", "json"],
    ):
        payload = _run_command(command, timeout=120, input_text="YES\n")
        if not payload:
            continue
        result = _parse_speedtest(payload)
        if result is not None:
            return result
    return None


def _parse_speedtest(payload: str) -> _SpeedTestResult | None:
    data = _try_parse_json_payload(payload)
    if data is None:
        return _parse_speedtest_text(payload)

    if isinstance(data, dict) and "download" in data and "upload" in data:
        download = data.get("download")
        upload = data.get("upload")
        if isinstance(download, dict) and isinstance(upload, dict):
            download_bps = float(download.get("bandwidth", 0)) * 8
            upload_bps = float(upload.get("bandwidth", 0)) * 8
            latency = data.get("ping", {}).get("latency", 0)
            return _SpeedTestResult(download_bps, upload_bps, float(latency))

        try:
            download_bps = float(download)
            upload_bps = float(upload)
            latency = float(data.get("ping", 0))
        except (TypeError, ValueError):
            return None
        return _SpeedTestResult(download_bps, upload_bps, latency)
    return None


def _try_parse_json_payload(payload: str) -> dict[str, object] | None:
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        pass

    start = payload.find("{")
    if start != -1:
        try:
            return json.loads(payload[start:])
        except json.JSONDecodeError:
            return None
    return None


def _parse_speedtest_text(payload: str) -> _SpeedTestResult | None:
    download_match = re.search(r"Download:\s*([0-9.]+)\s*(Kbps|Mbps|Gbps)", payload)
    upload_match = re.search(r"Upload:\s*([0-9.]+)\s*(Kbps|Mbps|Gbps)", payload)
    latency_match = re.search(r"Latency:\s*([0-9.]+)\s*ms", payload)
    if not download_match or not upload_match:
        return None

    try:
        download_bps = _to_bps(float(download_match.group(1)), download_match.group(2))
        upload_bps = _to_bps(float(upload_match.group(1)), upload_match.group(2))
        latency = float(latency_match.group(1)) if latency_match else 0.0
    except ValueError:
        return None

    return _SpeedTestResult(download_bps, upload_bps, latency)


def _to_bps(value: float, unit: str) -> float:
    unit = unit.lower()
    if unit == "gbps":
        return value * 1_000_000_000
    if unit == "mbps":
        return value * 1_000_000
    if unit == "kbps":
        return value * 1_000
    return value


def _format_speed(bits_per_second: float | None) -> str:
    if bits_per_second is None or bits_per_second <= 0:
        return "N/A"
    mbps = bits_per_second / 1_000_000
    if mbps >= 1000:
        gbps = mbps / 1000
        return f"{gbps:.2f} Gbps"
    if mbps >= 1:
        return f"{mbps:.1f} Mbps"
    kbps = bits_per_second / 1_000
    return f"{kbps:.0f} Kbps"


def _format_latency(latency: float | None) -> str | None:
    if latency is None:
        return None
    return f"{latency:.1f} ms"

def _tcp_latency() -> float | None:
    for host, port in [("1.1.1.1", 443), ("8.8.8.8", 53), ("1.1.1.1", 80)]:
        try:
            start = time.perf_counter()
            with socket.create_connection((host, port), timeout=1.5):
                end = time.perf_counter()
            return (end - start) * 1000
        except OSError:
            continue
    return None


def _format_bytes(value: int) -> str:
    size = float(value)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024 or unit == "TB":
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def _status_from_latency(latency: float | None) -> tuple[str, str]:
    if latency is None:
        return "Sin red", "status-danger"
    if latency < 60:
        return "Excelente", "status-success"
    if latency < 120:
        return "Estable", "status-neutral"
    return "Lenta", "status-danger"


def _format_uptime() -> str:
    try:
        with open("/proc/uptime", "r", encoding="utf-8") as handle:
            raw = handle.read().split()[0]
        seconds = int(float(raw))
    except (OSError, ValueError, IndexError):
        return "N/A"

    hours, remainder = divmod(seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    if hours <= 0:
        return f"{minutes} min"
    return f"{hours} h {minutes} min"
