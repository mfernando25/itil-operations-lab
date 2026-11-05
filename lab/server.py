from __future__ import annotations

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from . import database, metrics, scenarios

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
MONITOR_INTERVAL = max(5, int(os.getenv("MONITOR_INTERVAL_SECONDS", "60")))


class LabHandler(BaseHTTPRequestHandler):
    server_version = "ITIL-Operations-Lab/1.0"

    def _send(self, status: int, body: bytes, content_type: str = "application/json; charset=utf-8") -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, payload: dict) -> None:
        self._send(status, json.dumps(payload, ensure_ascii=False).encode("utf-8"))

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/":
            self._send(200, (WEB / "index.html").read_bytes(), "text/html; charset=utf-8")
        elif path == "/app.js":
            self._send(200, (WEB / "app.js").read_bytes(), "application/javascript; charset=utf-8")
        elif path == "/style.css":
            self._send(200, (WEB / "style.css").read_bytes(), "text/css; charset=utf-8")
        elif path == "/api/health":
            self._json(200, {"status": "ok", "service": "ITIL Operations Lab"})
        elif path == "/api/metrics":
            self._json(200, metrics.current_metrics())
        elif path == "/api/metrics/export-preview":
            self._json(200, {"history": database.list_metrics(500)})
        elif path == "/api/events":
            self._json(200, {"events": database.list_events(50)})
        elif path == "/api/scenario-state":
            self._json(200, {str(i): database.is_scenario_active(i) for i in range(4, 8)})
        elif path == "/api/demo/student":
            if database.is_scenario_active(6):
                self._json(200, {"studentId": "STU-1042", "name": "Estudiante de prueba", "program": "Ingeniería"})
            else:
                self._json(200, {"student_id": "STU-1042", "name": "Estudiante de prueba", "program": "Ingeniería"})
        elif path == "/api/demo/enrollment":
            current = database.get_enrollment("enrollment_current")
            read = database.get_enrollment("enrollment_read_model") if database.is_scenario_active(7) else current
            self._json(200, {"write_model": current, "read_model": read})
        else:
            self._json(404, {"error": "Ruta no encontrada"})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path.startswith("/api/scenarios/") and path.endswith("/activate"):
            try:
                scenario_id = int(path.split("/")[3])
                result = scenarios.activate_scenario(scenario_id)
                self._json(200, {"ok": True, **result})
            except (ValueError, IndexError) as exc:
                self._json(400, {"ok": False, "error": str(exc)})
        elif path.startswith("/api/scenarios/") and path.endswith("/reset"):
            try:
                scenario_id = int(path.split("/")[3])
                self._json(200, {"ok": True, **scenarios.reset_scenario(scenario_id)})
            except (ValueError, IndexError) as exc:
                self._json(400, {"ok": False, "error": str(exc)})
        elif path == "/api/enrollment/reconcile":
            if not database.is_scenario_active(7):
                self._json(409, {"ok": False, "error": "El escenario 7 no está activo."})
                return
            current = database.get_enrollment("enrollment_current")
            with database.connect() as conn:
                conn.execute(
                    "UPDATE enrollment_read_model SET enrollment_status=?, updated_at=? WHERE student_code='STU-1042'",
                    (current["enrollment_status"], database.now_iso()),
                )
            database.add_event("EV-G7-RECONCILED", 7, "Modelo de consulta actualizado", "Información", "Portal de matrícula",
                               "El modelo de consulta fue sincronizado con el registro actual.",
                               {"status": current["enrollment_status"]})
            self._json(200, {"ok": True, "message": "Modelo de consulta sincronizado."})
        else:
            self._json(404, {"error": "Ruta no encontrada"})

    def log_message(self, fmt: str, *args) -> None:
        print(f"[HTTP] {self.address_string()} - {fmt % args}")


def _monitor_loop(stop_event: threading.Event) -> None:
    while not stop_event.is_set():
        try:
            metrics.collect_live_sample()
        except Exception as exc:
            print(f"[MONITOR] No se pudo registrar una muestra: {exc}")
        stop_event.wait(MONITOR_INTERVAL)


def run_server() -> None:
    database.init_db()
    host = os.getenv("LAB_HOST", "127.0.0.1")
    port = int(os.getenv("LAB_PORT", "8000"))
    stop_event = threading.Event()
    monitor = threading.Thread(target=_monitor_loop, args=(stop_event,), daemon=True)
    monitor.start()
    server = ThreadingHTTPServer((host, port), LabHandler)
    print("=" * 58)
    print(" ITIL OPERATIONS LAB")
    print(f" Dashboard: http://{host}:{port}")
    print(f" Historial: SQLite · muestreo cada {MONITOR_INTERVAL} segundos")
    print(" Detener: Ctrl+C")
    print("=" * 58)
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        print("\nDeteniendo laboratorio...")
    finally:
        stop_event.set()
        server.shutdown()
        server.server_close()
