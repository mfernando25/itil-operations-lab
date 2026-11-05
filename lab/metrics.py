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


def current_metrics() -> dict:
    history = database.list_metrics(100, source="real")
    if not history:
        collect_live_sample()
        history = database.list_metrics(100, source="real")
    latest = history[-1] if history else {}
    if database.is_scenario_active(4):
        cpu_history = database.list_metrics(group_number=4)
        current = cpu_history[-1] if cpu_history else latest
    else:
        cpu_history = history
        current = latest
    if database.is_scenario_active(5):
        storage_history = database.list_metrics(group_number=5)
        storage_current = storage_history[-1] if storage_history else latest
    else:
        storage_history = []
        storage_current = latest
    return {
        "current": current,
        "history": cpu_history,
        "storage_current": storage_current,
        "storage_history": storage_history,
    }
