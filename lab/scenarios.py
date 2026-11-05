from __future__ import annotations

import shutil
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

from . import database
from .filesystem import remove_tree

ROOT = Path(__file__).resolve().parents[1]
LAB_DATA = ROOT / "lab_data" / "scenarios"
G3_DIR = LAB_DATA / "g3"


def _activate_state(group: int) -> None:
    database.set_scenario_state(group, True)


def _record(group: int, code: str, title: str, description: str,
            public_evidence: dict | None = None, private: dict | None = None,
            severity: str = "Advertencia") -> int:
    return database.add_event(
        code, group, title, severity, "Portal de matrícula", description,
        public_evidence or {}, private or {},
    )


def activate_group1() -> dict:
    _activate_state(1)
    event_id = _record(
        1, "EV-G1-CI", "Ejecución de pruebas automatizadas fallida",
        "Una ejecución reciente de integración continua terminó con pruebas fallidas. Se requiere determinar qué funcionalidad y cambio están relacionados.",
        {"workflow": "CI - Automated Tests", "result": "failure", "run": "#184"},
        {"root_cause": "Regresión en cálculo de becas: el porcentaje se resta como importe fijo.",
         "expected": "S/ 800.00", "actual": "S/ 980.00", "commit": "a41d9e2"},
    )
    return {"event_id": event_id, "message": "Grupo 1 preparado. Ejecuta el workflow G1 en GitHub Actions para obtener sus logs."}


def activate_group2() -> dict:
    _activate_state(2)
    event_id = _record(
        2, "EV-G2-WORKFLOW", "Workflow interrumpido durante la validación",
        "El workflow se inició, pero no completó el proceso de integración. El equipo debe identificar la etapa afectada y determinar qué actividades llegaron a ejecutarse.",
        {"workflow": "G2 - Prevalidación", "result": "failure", "run": "#92"},
        {"root_cause": "El YAML exige SERVICE_BASE_URL; el repositorio tiene SERVICE_ENDPOINT.",
         "failed_stage": "Validate configuration", "tests_started": False},
    )
    return {"event_id": event_id, "message": "Grupo 2 preparado. Ejecuta el workflow G2 en GitHub Actions para obtener sus logs."}


def _git(path: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", *args], cwd=path, text=True, capture_output=True,
        encoding="utf-8", errors="replace", check=False,
    )
    if check and result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} falló: {result.stderr or result.stdout}")
    return result


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def activate_group3() -> dict:
    """Build an isolated, reproducible local/remote Git divergence and conflict."""
    if shutil.which("git") is None:
        raise RuntimeError("Git no está instalado o no está disponible en PATH.")
    if G3_DIR.exists():
        remove_tree(G3_DIR)
    remote = G3_DIR / "remote.git"
    seed = G3_DIR / "seed"
    student = G3_DIR / "student-workspace"
    admin = G3_DIR / "remote-admin"
    G3_DIR.mkdir(parents=True, exist_ok=True)

    subprocess.run(["git", "init", "--bare", str(remote)], capture_output=True, text=True, check=True)
    subprocess.run(["git", "init", str(seed)], capture_output=True, text=True, check=True)
    _git(seed, "config", "user.name", "Lab Instructor")
    _git(seed, "config", "user.email", "instructor@itil-lab.local")
    _git(seed, "branch", "-M", "main")
    _write(seed / "config" / "enrollment.ini", "retry_limit=2\nrequest_timeout=30\n")
    _write(seed / "README.md", "Repositorio de práctica aislado para el escenario G3.\n")
    _git(seed, "add", ".")
    _git(seed, "commit", "-m", "Base estable del servicio de matrícula")
    _git(seed, "remote", "add", "origin", str(remote))
    _git(seed, "push", "-u", "origin", "main")
    _git(remote, "symbolic-ref", "HEAD", "refs/heads/main")

    subprocess.run(["git", "clone", str(remote), str(student)], capture_output=True, text=True, check=True)
    _git(student, "config", "user.name", "Developer Local")
    _git(student, "config", "user.email", "developer@itil-lab.local")
    _git(student, "switch", "-c", "feature/matricula")
    _write(student / "config" / "enrollment.ini", "retry_limit=4\nrequest_timeout=30\n")
    _git(student, "add", "config/enrollment.ini")
    _git(student, "commit", "-m", "Ajustar reintentos para matrícula")

    subprocess.run(["git", "clone", str(remote), str(admin)], capture_output=True, text=True, check=True)
    _git(admin, "config", "user.name", "Remote Maintainer")
    _git(admin, "config", "user.email", "maintainer@itil-lab.local")
    _write(admin / "config" / "enrollment.ini", "retry_limit=6\nrequest_timeout=30\n")
    _git(admin, "add", "config/enrollment.ini")
    _git(admin, "commit", "-m", "Ajustar reintentos desde remoto")
    _git(admin, "push", "origin", "main")

    pull = _git(student, "pull", "--no-rebase", "origin", "main", check=False)
    status = _git(student, "status", "--short", "--branch", check=False)
    graph = _git(student, "log", "--oneline", "--graph", "--decorate", "--all", "-8", check=False)
    diff = _git(student, "diff", "--", "config/enrollment.ini", check=False)
    _write(student / "evidence" / "initial-rejection.txt",
           "# Evidencia inicial G3\n\nComando ejecutado: `git pull --no-rebase origin main`\n\n"
           f"Código de salida: {pull.returncode}\n\n```text\n{pull.stdout}{pull.stderr}\n```\n")
    _write(student / "evidence" / "local-state.txt",
           "# Estado local G3\n\n```text\n" + status.stdout + "\n" + graph.stdout + "\n```\n\n"
           "La rama local contiene un commit propio que todavía debe conservarse.\n")
    _write(student / "evidence" / "remote-state.txt",
           "# Estado remoto G3\n\n```text\n" + _git(admin, "log", "--oneline", "-4").stdout + "\n\n"
           + _git(admin, "show", "HEAD:config/enrollment.ini").stdout + "```\n\n"
           "La rama remota también avanzó desde la base común.\n")
    _write(student / "evidence" / "working-diff.txt",
           "# Diferencia/conflicto G3\n\n```text\n" + diff.stdout + "\n" + pull.stdout + pull.stderr + "```\n")
    _activate_state(3)
    event_id = _record(
        3, "EV-G3-GIT", "Sincronización remota rechazada",
        "El repositorio remoto contiene cambios que no están en la rama local. Hay modificaciones de trabajo que deben preservarse antes de recuperar la sincronización.",
        {"repository": "itil-lab/enrollment-service", "branch": "feature/matricula",
         "command": "git pull --no-rebase origin main", "result": "conflict"},
        {"conflict_file": "config/enrollment.ini", "local_value": "retry_limit=4",
         "remote_value": "retry_limit=6", "workspace": str(student),
         "resolution_hint": "Revisar ambas modificaciones y resolver el conflicto sin descartar el commit local."},
        severity="Excepción",
    )
    return {"event_id": event_id, "message": "Grupo 3 preparado. El repositorio aislado y el conflicto de Git ya están generados."}


def activate_group4() -> dict:
    # Ten generated samples spanning five calendar days, with correlated workload and latency.
    cpu_values = [38, 42, 47, 53, 59, 66, 72, 81, 89, 94]
    rpm_values = [420, 460, 510, 590, 680, 790, 930, 1110, 1320, 1480]
    latency_values = [310, 340, 390, 470, 610, 780, 1020, 1510, 1980, 2450]
    now = datetime.now().astimezone().replace(minute=0, second=0, microsecond=0)
    ids = []
    for index, (cpu, rpm, latency) in enumerate(zip(cpu_values, rpm_values, latency_values)):
        captured = (now - timedelta(days=5) + timedelta(hours=12 * index)).isoformat(timespec="seconds")
        ids.append(database.add_metric(
            "scenario", cpu, 54 + index * 1.1, 61, 0,
            "Carga operativa del portal durante la ventana histórica de análisis.", captured,
            requests_per_minute=rpm, avg_response_ms=latency,
            component="enrollment-api", scenario_group=4,
        ))
    _activate_state(4)
    event_id = _record(
        4, "EV-G4-CPU", "Aumento sostenido de consumo de CPU",
        "El uso de CPU aumenta durante varios días y coincide con el crecimiento de solicitudes y tiempos de respuesta. El portal continúa disponible, pero presenta degradación.",
        {"window": "5 días", "latest_cpu_percent": 94, "latest_response_ms": 2450},
        {"metric_ids": ids, "cpu_series": cpu_values, "requests_per_minute": rpm_values,
         "avg_response_ms": latency_values, "primary_component": "enrollment-api",
         "scenario_data": True},
    )
    return {"event_id": event_id, "message": "Grupo 4 preparado con una serie histórica de cinco días y métricas de carga y latencia."}


def activate_group5() -> dict:
    # Data describes a 10 GB logical volume. Small placeholder files are created only;
    # no large real files are written to the laptop.
    used_gb = [2.4, 3.3, 4.6, 6.8, 8.7]
    available_gb = [7.6, 6.7, 5.4, 3.2, 1.3]
    log_gb = [0.8, 1.3, 2.0, 3.0, 3.9]
    backup_gb = [1.2, 1.6, 2.0, 2.8, 3.6]
    gateway_gb = [0.4, 0.4, 0.6, 1.0, 1.2]
    now = datetime.now().astimezone().replace(hour=9, minute=0, second=0, microsecond=0)
    ids = []
    for index, (used, available) in enumerate(zip(used_gb, available_gb)):
        captured = (now - timedelta(days=4 - index)).isoformat(timespec="seconds")
        ids.append(database.add_metric(
            "scenario", None, None, None, round(used * 1024, 1),
            "Consumo del volumen lógico de registros y respaldos.", captured,
            storage_capacity_gb=10.0, storage_available_gb=available,
            component="enrollment-volume", scenario_group=5,
        ))
    _write(ROOT / "lab_data" / "storage_test" / "README.txt",
           "Escenario de capacidad G5. Las series representan un volumen lógico de 10 GB.\n"
           "No se han escrito archivos de ese tamaño en el disco real.\n")
    _activate_state(5)
    event_id = _record(
        5, "EV-G5-STORAGE", "Crecimiento sostenido del almacenamiento",
        "Los registros y respaldos ocupan una proporción creciente del volumen del servicio. El espacio disponible se aproxima al límite preventivo; el servicio continúa funcionando.",
        {"window": "5 días", "capacity_gb": 10.0, "used_gb": 8.7,
         "available_gb": 1.3, "usage_percent": 87.0},
        {"metric_ids": ids, "log_growth_gb": log_gb, "backup_growth_gb": backup_gb,
         "gateway_growth_gb": gateway_gb, "retention_policy": "rotation disabled",
         "scenario_data": True},
    )
    return {"event_id": event_id, "message": "Grupo 5 preparado con cinco días de crecimiento, capacidad y distribución del almacenamiento."}


def activate_group6() -> dict:
    _activate_state(6)
    event_id = _record(
        6, "EV-G6-CONTRACT", "Respuesta incompleta en consulta de perfil",
        "Después de integrar una actualización, el portal no puede completar la información de perfil que solicita a otro componente.",
        {"service": "portal-api", "operation": "GET /api/portal/student-profile", "result": "degraded"},
        {"provider": "students-service v2.4.0", "consumer": "enrollment-service v2.3.0",
         "provider_fields": ["studentId", "courseId"],
         "consumer_fields": ["student_id", "course_id"],
         "commit": "c82f190", "missing_contract_test": True},
        severity="Excepción",
    )
    return {"event_id": event_id, "message": "Grupo 6 preparado. La comunicación entre servicios ya refleja una incompatibilidad."}


def activate_group7() -> dict:
    # Update the authoritative record but intentionally leave the read cache unchanged.
    database.update_enrollment_current("Confirmada")
    _activate_state(7)
    event_id = _record(
        7, "EV-G7-CACHE", "Consulta muestra un estado anterior",
        "Una operación fue registrada correctamente, pero la consulta posterior continúa mostrando el estado que tenía antes de la operación.",
        {"operation_id": "ENR-78421", "write_result": "accepted", "read_result": "stale"},
        {"student_code": "STU-1042", "authoritative_status": "Confirmada",
         "cached_status": "Pendiente", "cache_key": "enrollment:STU-1042",
         "write_time": database.get_enrollment("enrollment_current")["updated_at"],
         "cache_time": database.get_enrollment("enrollment_cache")["cached_at"]},
        severity="Excepción",
    )
    return {"event_id": event_id, "message": "Grupo 7 preparado. El registro principal se actualizó y la caché conserva el estado anterior."}


ACTIVATORS = {
    1: activate_group1, 2: activate_group2, 3: activate_group3,
    4: activate_group4, 5: activate_group5, 6: activate_group6, 7: activate_group7,
}


def activate_scenario(scenario_id: int) -> dict:
    if scenario_id not in ACTIVATORS:
        raise ValueError("Grupo inválido; utiliza un número del 1 al 7.")
    return ACTIVATORS[scenario_id]()


def reset_scenario(scenario_id: int) -> dict:
    if scenario_id not in range(1, 8):
        raise ValueError("Grupo inválido.")
    # Remove G3's nested Git repositories before marking the scenario inactive.
    # If Windows still has a handle open, preserve the active state and report the path.
    if scenario_id == 3 and G3_DIR.exists():
        remove_tree(G3_DIR)
    database.set_scenario_state(scenario_id, False)
    if scenario_id == 7:
        database.update_enrollment_current("Pendiente")
        database.update_enrollment_cache("Pendiente")
    if scenario_id == 6:
        # The route derives its behavior from scenario_state, so this deactivates the mismatch.
        pass
    # Keep event history for auditability. Each event is timestamped and remains visible.
    return {"message": f"Grupo {scenario_id} desactivado. El historial de eventos se conserva."}


def reset_all() -> None:
    for group in range(1, 8):
        reset_scenario(group)
    database.reset_events()
