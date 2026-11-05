from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
import psutil

from . import database

ROOT = Path(__file__).resolve().parents[1]
LAB_STORAGE = ROOT / "lab_data" / "storage_test"
CPU_WARNING = 75.0
MEMORY_WARNING = 85.0
DISK_WARNING = 90.0


def folder_size_mb(path: Path = LAB_STORAGE) -> float:
    total = 0
    if path.exists():
        for item in path.rglob("*"):
            if item.is_file():
                try:
                    total += item.stat().st_size
                except OSError:
                    continue
    return round(total / (1024 * 1024), 2)


def collect_live_sample() -> dict:
    cpu = float(psutil.cpu_percent(interval=0.15))
    memory = float(psutil.virtual_memory().percent)
    disk = float(psutil.disk_usage(str(ROOT)).percent)
    storage_mb = folder_size_mb()
    sample_id = database.add_metric(
        "real", cpu, memory, disk, storage_mb,
        "Lectura del equipo donde se ejecuta el laboratorio.", component="host",
    )
    now = datetime.now().astimezone()
    recent_events = database.list_events(100)
    for code, value, threshold, title in [
        ("CPU", cpu, CPU_WARNING, "Uso de CPU por encima del umbral"),
        ("MEMORY", memory, MEMORY_WARNING, "Uso de memoria por encima del umbral"),
        ("DISK", disk, DISK_WARNING, "Ocupación de disco por encima del umbral"),
    ]:
        if value >= threshold:
            last = next((e for e in recent_events if e["event_code"] == f"MON-{code}-REAL"), None)
            should_log = True
            if last:
                try:
                    last_time = datetime.fromisoformat(last["created_at"])
                    should_log = now - last_time >= timedelta(minutes=15)
                except ValueError:
                    pass
            if should_log:
                database.add_event(
                    f"MON-{code}-REAL", 0, title, "Advertencia", "Monitor del equipo",
                    f"El indicador {code} alcanzó {value:.1f} %, por encima del umbral de {threshold:.1f} %.",
                    {"value": round(value, 1), "threshold": threshold},
                    {"source": "real-host", "metric_id": sample_id},
                )
    return {"id": sample_id, "cpu_percent": round(cpu, 1), "memory_percent": round(memory, 1),
            "disk_percent": round(disk, 1), "storage_used_mb": storage_mb}


def current_metrics(public_group: int | None = None) -> dict:
    history = database.list_metrics(100, source="real")
    if not history:
        collect_live_sample()
        history = database.list_metrics(100, source="real")
    latest = history[-1] if history else {}

    g4_active = public_group == 4 and database.is_scenario_active(4)
    g5_active = public_group == 5 and database.is_scenario_active(5)

    if g4_active:
        scenario_cpu_history = database.list_metrics(group_number=4)
        cpu_history = [
            {**row, "memory_percent": None, "disk_percent": None}
            for row in scenario_cpu_history
        ]
        # Only CPU, requests and latency come from the synthetic G4 case.
        # Memory and disk remain the latest real measurements from this host.
        current = dict(latest)
        if scenario_cpu_history:
            last_cpu = scenario_cpu_history[-1]
            current.update({
                "cpu_percent": last_cpu["cpu_percent"],
                "requests_per_minute": last_cpu["requests_per_minute"],
                "avg_response_ms": last_cpu["avg_response_ms"],
                "cpu_captured_at": last_cpu["captured_at"],
            })
        cpu_history_label = "CPU del servicio · historial sintético de cinco días"
        cpu_source_label = "CPU del servicio · dato sintético"
        cpu_window_label = "Cinco días · datos sintéticos del caso"
    else:
        cpu_history = history
        current = latest
        cpu_history_label = "CPU del equipo · mediciones reales de la sesión"
        cpu_source_label = "Uso real del procesador del equipo"
        cpu_window_label = "Sesión actual · datos reales"

    if g5_active:
        storage_history = database.list_metrics(group_number=5)
        storage_current = storage_history[-1] if storage_history else latest
        storage_history_label = "Almacenamiento del servicio · historial sintético de cinco días"
        storage_window_label = "Cinco días · volumen lógico simulado"
    else:
        # The local laboratory folder is measured on the host; show only its actual session history.
        storage_history = history
        storage_current = latest
        storage_history_label = "Almacenamiento local del laboratorio · sesión actual"
        storage_window_label = "Sesión actual · mediciones reales"

    return {
        "current": current,
        "history": cpu_history,
        "storage_current": storage_current,
        "storage_history": storage_history,
        "cpu_history_label": cpu_history_label,
        "cpu_source_label": cpu_source_label,
        "cpu_window_label": cpu_window_label,
        "storage_history_label": storage_history_label,
        "storage_window_label": storage_window_label,
    }
