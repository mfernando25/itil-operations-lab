from types import SimpleNamespace
from lab import database, metrics


def test_monitor_records_threshold_events(isolated_db, monkeypatch):
    monkeypatch.setattr(metrics.psutil, "cpu_percent", lambda interval=0.15: 96.0)
    monkeypatch.setattr(metrics.psutil, "virtual_memory", lambda: SimpleNamespace(percent=91.0))
    monkeypatch.setattr(metrics.psutil, "disk_usage", lambda path: SimpleNamespace(percent=93.0))
    monkeypatch.setattr(metrics, "folder_size_mb", lambda: 0.0)
    metrics.collect_live_sample()
    codes = {e["event_code"] for e in database.list_events(10)}
    assert {"MON-CPU-REAL", "MON-MEMORY-REAL", "MON-DISK-REAL"}.issubset(codes)


def test_monitor_avoids_repeated_alerts_within_cooldown(isolated_db, monkeypatch):
    monkeypatch.setattr(metrics.psutil, "cpu_percent", lambda interval=0.15: 96.0)
    monkeypatch.setattr(metrics.psutil, "virtual_memory", lambda: SimpleNamespace(percent=20.0))
    monkeypatch.setattr(metrics.psutil, "disk_usage", lambda path: SimpleNamespace(percent=20.0))
    monkeypatch.setattr(metrics, "folder_size_mb", lambda: 0.0)
    metrics.collect_live_sample()
    metrics.collect_live_sample()
    cpu_events = [e for e in database.list_events(10) if e["event_code"] == "MON-CPU-REAL"]
    assert len(cpu_events) == 1
