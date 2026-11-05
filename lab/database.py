from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "lab.db"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_columns(conn: sqlite3.Connection, table: str, columns: dict[str, str]) -> None:
    existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
    for name, definition in columns.items():
        if name not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")


def init_db() -> None:
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS metric_samples (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                captured_at TEXT NOT NULL,
                source TEXT NOT NULL,
                cpu_percent REAL,
                memory_percent REAL,
                disk_percent REAL,
                storage_used_mb REAL,
                note TEXT
            );
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_code TEXT NOT NULL,
                group_number INTEGER,
                title TEXT NOT NULL,
                severity TEXT NOT NULL,
                source TEXT NOT NULL,
                description TEXT NOT NULL,
                evidence_json TEXT NOT NULL DEFAULT '{}',
                status TEXT NOT NULL DEFAULT 'Detectado',
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS scenario_state (
                scenario_id INTEGER PRIMARY KEY,
                active INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS enrollment_current (
                student_code TEXT PRIMARY KEY,
                enrollment_status TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS enrollment_read_model (
                student_code TEXT PRIMARY KEY,
                enrollment_status TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS enrollment_cache (
                student_code TEXT PRIMARY KEY,
                enrollment_status TEXT NOT NULL,
                cached_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS lab_settings (
                setting_key TEXT PRIMARY KEY,
                setting_value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
        _ensure_columns(conn, "metric_samples", {
            "requests_per_minute": "REAL",
            "avg_response_ms": "REAL",
            "storage_capacity_gb": "REAL",
            "storage_available_gb": "REAL",
            "component": "TEXT",
            "scenario_group": "INTEGER",
        })
        _ensure_columns(conn, "events", {"private_json": "TEXT NOT NULL DEFAULT '{}'"})
        ts = now_iso()
        conn.execute(
            "INSERT OR IGNORE INTO lab_settings VALUES (?, ?, ?)",
            ("public_group", "0", ts),
        )
        conn.execute(
            "INSERT OR IGNORE INTO enrollment_current VALUES (?, ?, ?)",
            ("STU-1042", "Pendiente", ts),
        )
        conn.execute(
            "INSERT OR IGNORE INTO enrollment_read_model VALUES (?, ?, ?)",
            ("STU-1042", "Pendiente", ts),
        )
        conn.execute(
            "INSERT OR IGNORE INTO enrollment_cache VALUES (?, ?, ?)",
            ("STU-1042", "Pendiente", ts),
        )


def add_metric(source: str, cpu: float | None = None, memory: float | None = None,
               disk: float | None = None, storage_mb: float | None = None,
               note: str = "", captured_at: str | None = None,
               requests_per_minute: float | None = None,
               avg_response_ms: float | None = None,
               storage_capacity_gb: float | None = None,
               storage_available_gb: float | None = None,
               component: str = "", scenario_group: int | None = None) -> int:
    with connect() as conn:
        cur = conn.execute(
            """INSERT INTO metric_samples
               (captured_at, source, cpu_percent, memory_percent, disk_percent,
                storage_used_mb, note, requests_per_minute, avg_response_ms,
                storage_capacity_gb, storage_available_gb, component, scenario_group)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (captured_at or now_iso(), source, cpu, memory, disk, storage_mb, note,
             requests_per_minute, avg_response_ms, storage_capacity_gb,
             storage_available_gb, component, scenario_group),
        )
        return int(cur.lastrowid)


def list_metrics(limit: int = 120, group_number: int | None = None, source: str | None = None) -> list[dict[str, Any]]:
    with connect() as conn:
        if group_number == 4:
            rows = conn.execute(
                "SELECT * FROM metric_samples WHERE scenario_group=4 ORDER BY captured_at, id"
            ).fetchall()
        elif group_number == 5:
            rows = conn.execute(
                "SELECT * FROM metric_samples WHERE scenario_group=5 ORDER BY captured_at, id"
            ).fetchall()
        elif source:
            rows = conn.execute(
                "SELECT * FROM (SELECT * FROM metric_samples WHERE source=? ORDER BY captured_at DESC, id DESC LIMIT ?) ORDER BY captured_at, id",
                (source, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM (SELECT * FROM metric_samples ORDER BY captured_at DESC, id DESC LIMIT ?) ORDER BY captured_at, id",
                (limit,),
            ).fetchall()
    return [dict(row) for row in rows]



def delete_scenario_metrics(group_number: int) -> int:
    """Delete generated metric samples for G4 or G5 before a new case run."""
    if group_number not in {4, 5}:
        raise ValueError("Solo se pueden limpiar las métricas sintéticas de G4 o G5.")
    with connect() as conn:
        cur = conn.execute(
            "DELETE FROM metric_samples WHERE scenario_group=?",
            (group_number,),
        )
        return int(cur.rowcount)

def add_event(event_code: str, group_number: int, title: str, severity: str,
              source: str, description: str, evidence: dict[str, Any] | None = None,
              private: dict[str, Any] | None = None) -> int:
    with connect() as conn:
        cur = conn.execute(
            """INSERT INTO events
               (event_code, group_number, title, severity, source, description,
                evidence_json, private_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (event_code, group_number, title, severity, source, description,
             json.dumps(evidence or {}, ensure_ascii=False),
             json.dumps(private or {}, ensure_ascii=False), now_iso()),
        )
        return int(cur.lastrowid)


def list_events(limit: int = 50, include_private: bool = False,
                group_number: int | None = None) -> list[dict[str, Any]]:
    with connect() as conn:
        if group_number is None:
            rows = conn.execute("SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM events WHERE group_number=? ORDER BY id DESC LIMIT ?",
                (group_number, limit),
            ).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        try:
            item["evidence"] = json.loads(item.pop("evidence_json"))
        except json.JSONDecodeError:
            item["evidence"] = {}
        private_raw = item.pop("private_json", "{}")
        if include_private:
            try:
                item["private_evidence"] = json.loads(private_raw)
            except json.JSONDecodeError:
                item["private_evidence"] = {}
        result.append(item)
    return result


def set_public_group(group_number: int | None) -> None:
    """Select the only scenario whose events appear on the shared student dashboard."""
    if group_number is not None and group_number not in range(1, 8):
        raise ValueError("El grupo visible debe estar entre 1 y 7 o quedar sin asignar.")
    value = str(group_number or 0)
    with connect() as conn:
        conn.execute(
            """INSERT INTO lab_settings (setting_key, setting_value, updated_at)
               VALUES ('public_group', ?, ?)
               ON CONFLICT(setting_key) DO UPDATE SET
                   setting_value=excluded.setting_value,
                   updated_at=excluded.updated_at""",
            (value, now_iso()),
        )


def get_public_group() -> int | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT setting_value FROM lab_settings WHERE setting_key='public_group'"
        ).fetchone()
    if not row:
        return None
    value = int(row["setting_value"])
    return value if value in range(1, 8) else None


def set_scenario_state(scenario_id: int, active: bool) -> None:
    with connect() as conn:
        conn.execute(
            """INSERT INTO scenario_state (scenario_id, active, updated_at)
               VALUES (?, ?, ?)
               ON CONFLICT(scenario_id) DO UPDATE SET active=excluded.active, updated_at=excluded.updated_at""",
            (scenario_id, int(active), now_iso()),
        )


def is_scenario_active(scenario_id: int) -> bool:
    with connect() as conn:
        row = conn.execute("SELECT active FROM scenario_state WHERE scenario_id=?", (scenario_id,)).fetchone()
    return bool(row["active"]) if row else False


def scenario_states() -> dict[str, bool]:
    return {str(i): is_scenario_active(i) for i in range(1, 8)}


def get_enrollment(table: str = "enrollment_current") -> dict[str, Any] | None:
    allowed = {"enrollment_current", "enrollment_read_model", "enrollment_cache"}
    if table not in allowed:
        raise ValueError("Tabla no permitida")
    with connect() as conn:
        row = conn.execute(f"SELECT * FROM {table} WHERE student_code='STU-1042'").fetchone()
    return dict(row) if row else None


def update_enrollment_current(status: str) -> None:
    ts = now_iso()
    with connect() as conn:
        conn.execute(
            "UPDATE enrollment_current SET enrollment_status=?, updated_at=? WHERE student_code='STU-1042'",
            (status, ts),
        )
        conn.execute(
            "UPDATE enrollment_read_model SET enrollment_status=?, updated_at=? WHERE student_code='STU-1042'",
            (status, ts),
        )


def update_enrollment_cache(status: str) -> None:
    with connect() as conn:
        conn.execute(
            "UPDATE enrollment_cache SET enrollment_status=?, cached_at=? WHERE student_code='STU-1042'",
            (status, now_iso()),
        )


def reset_events() -> None:
    with connect() as conn:
        conn.execute("DELETE FROM events")
