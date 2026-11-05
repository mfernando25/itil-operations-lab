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
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


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
            """
        )
        row = conn.execute(
            "SELECT student_code FROM enrollment_current WHERE student_code='STU-1042'"
        ).fetchone()
        if row is None:
            ts = now_iso()
            conn.execute(
                "INSERT INTO enrollment_current VALUES (?, ?, ?)",
                ("STU-1042", "Pendiente", ts),
            )
            conn.execute(
                "INSERT INTO enrollment_read_model VALUES (?, ?, ?)",
                ("STU-1042", "Pendiente", ts),
            )


def add_metric(source: str, cpu: float | None, memory: float | None,
               disk: float | None, storage_mb: float | None,
               note: str = "", captured_at: str | None = None) -> int:
    with connect() as conn:
        cur = conn.execute(
            """INSERT INTO metric_samples
               (captured_at, source, cpu_percent, memory_percent, disk_percent, storage_used_mb, note)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (captured_at or now_iso(), source, cpu, memory, disk, storage_mb, note),
        )
        return int(cur.lastrowid)


def list_metrics(limit: int = 80) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM (SELECT * FROM metric_samples ORDER BY captured_at DESC, id DESC LIMIT ?) ORDER BY captured_at, id",
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def add_event(event_code: str, group_number: int, title: str, severity: str,
              source: str, description: str, evidence: dict[str, Any] | None = None) -> int:
    with connect() as conn:
        cur = conn.execute(
            """INSERT INTO events
               (event_code, group_number, title, severity, source, description, evidence_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (event_code, group_number, title, severity, source, description,
             json.dumps(evidence or {}, ensure_ascii=False), now_iso()),
        )
        return int(cur.lastrowid)


def list_events(limit: int = 40) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        try:
            item["evidence"] = json.loads(item.pop("evidence_json"))
        except json.JSONDecodeError:
            item["evidence"] = {}
        result.append(item)
    return result


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
        row = conn.execute(
            "SELECT active FROM scenario_state WHERE scenario_id=?", (scenario_id,)
        ).fetchone()
    return bool(row["active"]) if row else False


def get_enrollment(table: str = "enrollment_current") -> dict[str, Any] | None:
    if table not in {"enrollment_current", "enrollment_read_model"}:
        raise ValueError("Tabla no permitida")
    with connect() as conn:
        row = conn.execute(f"SELECT * FROM {table} WHERE student_code='STU-1042'").fetchone()
    return dict(row) if row else None


def update_enrollment_current(status: str) -> None:
    with connect() as conn:
        conn.execute(
            "UPDATE enrollment_current SET enrollment_status=?, updated_at=? WHERE student_code='STU-1042'",
            (status, now_iso()),
        )
