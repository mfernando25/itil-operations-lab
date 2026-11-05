from __future__ import annotations
import argparse
import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lab.database import connect

def main() -> None:
    parser = argparse.ArgumentParser(description="Exporta métricas históricas a CSV.")
    parser.add_argument("--hours", type=int, default=120, help="Horas hacia atrás; 120 equivale a cinco días.")
    parser.add_argument("--output", default="evidence/metricas_historicas.csv")
    args = parser.parse_args()
    if args.hours < 1 or args.hours > 720: parser.error("--hours debe estar entre 1 y 720.")
    cutoff = (datetime.now(timezone.utc).astimezone() - timedelta(hours=args.hours)).isoformat(timespec="seconds")
    with connect() as conn:
        rows = conn.execute("SELECT captured_at, source, cpu_percent, memory_percent, disk_percent, storage_used_mb, note FROM metric_samples WHERE captured_at >= ? ORDER BY captured_at", (cutoff,)).fetchall()
    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(["captured_at", "source", "cpu_percent", "memory_percent", "disk_percent", "storage_used_mb", "note"])
        writer.writerows([tuple(row) for row in rows])
    print(f"Exportadas {len(rows)} muestras a {output}")

if __name__ == "__main__": main()
