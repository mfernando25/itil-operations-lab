from __future__ import annotations

from pathlib import Path
from datetime import datetime, timedelta
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
    sample_id = database.add_metric("real", cpu, memory, disk, storage_mb, "Métrica del equipo que ejecuta el laboratorio")

    alerts = []
    thresholds = [
        ("CPU", cpu, CPU_WARNING, "Uso de CPU por encima del umbral"),
        ("MEMORY", memory, MEMORY_WARNING, "Uso de memoria por encima del umbral"),
        ("DISK", disk, DISK_WARNING, "Ocupación de disco por encima del umbral"),
    ]
    recent_events = database.list_events(100)
    now = datetime.now().astimezone()
    for code, value, threshold, title in thresholds:
        if value >= threshold:
            alerts.append((code, value, threshold))
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
                    {"metric_id": sample_id, "value": round(value, 1), "threshold": threshold, "source": "real"},
                )

    return {
        "id": sample_id,
        "source": "real",
        "cpu_percent": round(cpu, 1),
        "memory_percent": round(memory, 1),
        "disk_percent": round(disk, 1),
        "storage_used_mb": storage_mb,
        "alerts": alerts,
    }


def current_metrics() -> dict:
    history = database.list_metrics(80)
    if not history:
        collect_live_sample()
        history = database.list_metrics(80)
    latest = history[-1] if history else {}
    return {"current": latest, "history": history}
