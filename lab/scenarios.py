from __future__ import annotations

from pathlib import Path
from datetime import datetime, timedelta, timezone
from . import database

ROOT = Path(__file__).resolve().parents[1]
STORAGE_DIR = ROOT / "lab_data" / "storage_test"


def activate_group4() -> dict:
    # Controlled metric injection: it does not consume CPU on the host.
    sample_id = database.add_metric(
        "simulated", 94.0, 48.0, 61.0, 0.0,
        "Métrica simulada para el escenario de CPU; no representa consumo real del equipo.",
    )
    event_id = database.add_event(
        "EV-G4-CPU", 4, "Consumo elevado de CPU", "Advertencia", "Dashboard",
        "El indicador de CPU supera el umbral de laboratorio. El servicio continúa respondiendo.",
        {"cpu_percent": 94.0, "threshold": 75.0, "metric_id": sample_id, "source": "simulated"},
    )
    database.set_scenario_state(4, True)
    return {"event_id": event_id, "metric_id": sample_id, "message": "Escenario 4 activado. El valor es simulado."}


def activate_group5() -> dict:
    # Five-day simulated trend, explicitly labelled as lab data.
    values = [42.0, 51.0, 60.0, 73.0, 88.0]
    ids = []
    today = datetime.now(timezone.utc).astimezone()
    for day, used in enumerate(values, start=1):
        captured_at = (today - timedelta(days=5-day)).isoformat(timespec="seconds")
        ids.append(database.add_metric(
            "simulated", 24.0, 55.0, 64.0, used,
            f"Historial simulado de laboratorio: día {day} de 5; almacenamiento usado={used} MB.",
            captured_at=captured_at,
        ))
    event_id = database.add_event(
        "EV-G5-STORAGE", 5, "Crecimiento sostenido del almacenamiento", "Advertencia", "Dashboard",
        "El almacenamiento de laboratorio muestra una tendencia creciente y se aproxima al umbral configurado.",
        {"history_mb": values, "capacity_mb": 100.0, "threshold_percent": 80.0, "metric_ids": ids, "source": "simulated"},
    )
    database.set_scenario_state(5, True)
    return {"event_id": event_id, "metric_ids": ids, "message": "Escenario 5 activado con cinco puntos históricos simulados."}


def activate_group6() -> dict:
    database.set_scenario_state(6, True)
    event_id = database.add_event(
        "EV-G6-CONTRACT", 6, "Respuesta inconsistente entre componentes", "Excepción", "Portal de matrícula",
        "La vista de perfil no presenta el identificador del estudiante después de la integración.",
        {"endpoint": "/api/demo/student", "expected_field": "student_id", "actual_field": "studentId"},
    )
    return {"event_id": event_id, "message": "Escenario 6 activado: incompatibilidad de contrato entre componentes."}


def activate_group7() -> dict:
    database.update_enrollment_current("Confirmada")
    # Deliberately leave the read model with its previous value.
    database.set_scenario_state(7, True)
    event_id = database.add_event(
        "EV-G7-STALE", 7, "Estado de matrícula desactualizado", "Excepción", "Portal de matrícula",
        "La operación figura registrada, pero la consulta del portal continúa mostrando el estado anterior.",
        {"student_code": "STU-1042", "write_status": "Confirmada", "read_status": "Pendiente"},
    )
    return {"event_id": event_id, "message": "Escenario 7 activado: lectura desactualizada del modelo de consulta."}


def reset_scenario(scenario_id: int) -> dict:
    database.set_scenario_state(scenario_id, False)
    if scenario_id == 7:
        database.update_enrollment_current("Pendiente")
        with database.connect() as conn:
            conn.execute(
                "UPDATE enrollment_read_model SET enrollment_status='Pendiente', updated_at=? WHERE student_code='STU-1042'",
                (database.now_iso(),),
            )
    if scenario_id == 6:
        pass
    return {"message": f"Escenario {scenario_id} desactivado. Los eventos históricos se conservan."}


def activate_scenario(scenario_id: int) -> dict:
    actions = {4: activate_group4, 5: activate_group5, 6: activate_group6, 7: activate_group7}
    if scenario_id not in actions:
        raise ValueError("Los escenarios locales disponibles son 4, 5, 6 y 7.")
    return actions[scenario_id]()
