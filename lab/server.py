from __future__ import annotations

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from . import database, evidence, metrics, scenarios, services

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
MONITOR_INTERVAL = max(5, int(os.getenv("MONITOR_INTERVAL_SECONDS", "60")))


def _student_metric(row: dict) -> dict:
    keys = ("id", "captured_at", "cpu_percent", "memory_percent", "disk_percent",
            "storage_used_mb", "requests_per_minute", "avg_response_ms",
            "storage_capacity_gb", "storage_available_gb")
    return {key: row.get(key) for key in keys}


class LabHandler(BaseHTTPRequestHandler):
    server_version = "ITIL-Operations-Lab/2.0"

    def _send(self, status: int, body: bytes, content_type: str = "application/json; charset=utf-8") -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, payload: dict) -> None:
        self._send(status, json.dumps(payload, ensure_ascii=False).encode("utf-8"))

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length < 0 or length > 65536:
            raise ValueError("Solicitud JSON demasiado grande.")
        raw = self.rfile.read(length) if length else b"{}"
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("El cuerpo debe ser un objeto JSON.")
        return payload

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/":
            self._send(200, (WEB / "index.html").read_bytes(), "text/html; charset=utf-8")
        elif path == "/instructor":
            self._send(200, (WEB / "instructor.html").read_bytes(), "text/html; charset=utf-8")
        elif path in {"/app.js", "/instructor.js", "/style.css"}:
            content_type = "text/css; charset=utf-8" if path.endswith(".css") else "application/javascript; charset=utf-8"
            self._send(200, (WEB / path.lstrip("/")).read_bytes(), content_type)
        elif path == "/api/health":
            self._json(200, {"status": "ok", "service": "ITIL Operations Lab", "version": "0.2.2"})
        elif path == "/api/metrics":
            result = metrics.current_metrics(public_group=database.get_public_group())
            self._json(200, {
                "current": _student_metric(result["current"]),
                "history": [_student_metric(row) for row in result["history"]],
                "storage_current": _student_metric(result["storage_current"]),
                "storage_history": [_student_metric(row) for row in result["storage_history"]],
            })
        elif path == "/api/events":
            visible_group = database.get_public_group()
            visible_events = (
                database.list_events(60, include_private=False, group_number=visible_group)
                if visible_group is not None and database.is_scenario_active(visible_group)
                else []
            )
            self._json(200, {"visible_group": visible_group, "events": visible_events})
        elif path == "/api/scenario-state":
            visible_group = database.get_public_group()
            self._json(200, {
                "visible_group": visible_group,
                "active": bool(visible_group and database.is_scenario_active(visible_group)),
            })
        elif path == "/api/services/students/STU-1042":
            contract_mismatch = database.get_public_group() == 6 and database.is_scenario_active(6)
            payload = services.students_service("STU-1042", contract_mismatch)
            self._json(200, payload)
        elif path == "/api/services/courses/CS-204":
            self._json(200, services.courses_service("CS-204"))
        elif path == "/api/portal/student-profile":
            contract_mismatch = database.get_public_group() == 6 and database.is_scenario_active(6)
            payload = services.students_service("STU-1042", contract_mismatch)
            # Consumer contract expects snake_case, provider can drift after an integration.
            if "student_id" not in payload or "course_id" not in payload:
                self._json(502, {"status": "degraded", "message": "No fue posible completar la consulta del perfil."})
            else:
                course = services.courses_service(payload["course_id"])
                self._json(200, {"status": "ok", "student_id": payload["student_id"], "course": course, "name": payload["name"]})
        elif path == "/api/demo/student":
            contract_mismatch = database.get_public_group() == 6 and database.is_scenario_active(6)
            payload = services.students_service("STU-1042", contract_mismatch)
            if "student_id" not in payload:
                self._json(200, {"status": "degraded", "message": "No fue posible completar la consulta del perfil."})
            else:
                self._json(200, {"status": "ok", "student_id": payload["student_id"], "name": payload["name"]})
        elif path == "/api/demo/enrollment":
            current = database.get_enrollment("enrollment_current")
            if database.get_public_group() == 7 and database.is_scenario_active(7):
                cached = database.get_enrollment("enrollment_cache")
            else:
                cached = {
                    "student_code": current["student_code"],
                    "enrollment_status": current["enrollment_status"],
                    "cached_at": current["updated_at"],
                }
            self._json(200, {
                "operation": {"student_code": current["student_code"], "last_updated": current["updated_at"]},
                "consultation": {"student_code": cached["student_code"], "status": cached["enrollment_status"], "cached_at": cached["cached_at"]},
            })
        elif path == "/api/instructor/status":
            events = database.list_events(100, include_private=True)
            self._json(200, {
                "scenarios": database.scenario_states(),
                "events": events,
                "diagnostics": {str(k): v for k, v in evidence.instructor_diagnostics().items()},
                "public_group": database.get_public_group(),
            })
        elif path.startswith("/api/instructor/evidence/"):
            try:
                _, _, _, _, group, pack = path.split("/")
                bundle = evidence.build_bundle(int(group), int(pack))
                self._json(200, bundle)
            except (ValueError, TypeError):
                self._json(400, {"error": "Grupo o paquete inválido. Usa grupo 1–7 y paquete 0–3."})
        elif path == "/api/instructor/git-workspace":
            workspace = scenarios.G3_DIR / "student-workspace"
            self._json(200, {"exists": workspace.exists(), "path": str(workspace) if workspace.exists() else None,
                             "instructions": "Abre esta carpeta en una terminal para examinar el conflicto aislado de Git."})
        else:
            self._json(404, {"error": "Ruta no encontrada"})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/api/instructor/public-group":
            try:
                payload = self._read_json()
                raw_group = payload.get("group")
                group = None if raw_group in (None, "", 0, "0") else int(raw_group)
                database.set_public_group(group)
                label = f"Grupo {group}" if group is not None else "Ningún grupo"
                self._json(200, {"ok": True, "public_group": group,
                                 "message": f"Vista estudiantil asignada a {label}."})
            except (ValueError, TypeError, json.JSONDecodeError) as exc:
                self._json(400, {"ok": False, "error": str(exc)})
        elif path.startswith("/api/instructor/scenarios/") and path.endswith("/activate"):
            try:
                group = int(path.split("/")[4])
                result = scenarios.activate_scenario(group)
                database.set_public_group(group)
                self._json(200, {"ok": True, **result})
            except (ValueError, RuntimeError, IndexError) as exc:
                self._json(400, {"ok": False, "error": str(exc)})
        elif path.startswith("/api/instructor/scenarios/") and path.endswith("/reset"):
            try:
                group = int(path.split("/")[4])
                result = scenarios.reset_scenario(group)
                if database.get_public_group() == group:
                    database.set_public_group(None)
                self._json(200, {"ok": True, **result})
            except (ValueError, IndexError) as exc:
                self._json(400, {"ok": False, "error": str(exc)})
        elif path == "/api/instructor/reset-all":
            scenarios.reset_all()
            database.set_public_group(None)
            self._json(200, {"ok": True, "message": "Todos los escenarios fueron desactivados y el historial de eventos fue limpiado."})
        elif path == "/api/instructor/enrollment/reconcile":
            if not database.is_scenario_active(7):
                self._json(409, {"ok": False, "error": "El escenario 7 no está activo."})
                return
            current = database.get_enrollment("enrollment_current")
            database.update_enrollment_cache(current["enrollment_status"])
            database.add_event(
                "EV-G7-RECONCILED", 7, "Consulta de matrícula actualizada", "Información",
                "Portal de matrícula", "La consulta posterior refleja el estado vigente.",
                {"operation_id": "ENR-78421", "result": "consistent"},
                {"action": "cache invalidated and refreshed", "status": current["enrollment_status"]},
            )
            self._json(200, {"ok": True, "message": "La consulta de matrícula ya refleja el estado vigente."})
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
    print(" ITIL OPERATIONS LAB v0.2.2")
    print(f" Vista de estudiantes: http://{host}:{port}")
    print(f" Panel privado docente: http://{host}:{port}/instructor")
    print(f" Métricas reales del equipo: cada {MONITOR_INTERVAL} segundos")
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
