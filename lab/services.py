"""Logical service boundaries used by the classroom API (single-process prototype)."""
from __future__ import annotations

from . import database


def students_service(student_code: str, contract_mismatch: bool = False) -> dict:
    payload = {
        "student_id": student_code,
        "name": "Estudiante de prueba",
        "program": "Ingeniería de Sistemas",
        "course_id": "CS-204",
    }
    if contract_mismatch:
        return {
            "studentId": payload["student_id"],
            "name": payload["name"],
            "program": payload["program"],
            "courseId": payload["course_id"],
        }
    return payload


def courses_service(course_id: str) -> dict:
    return {"course_id": course_id, "name": "Gestión de Servicios de TI", "status": "Activo"}


def enrollment_service(student_code: str) -> dict:
    return {"student_id": student_code, "enrollment": database.get_enrollment("enrollment_current")}
