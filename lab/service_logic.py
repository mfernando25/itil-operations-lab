"""Small application logic used by the CI and contract scenarios."""


def calculate_enrollment_fee(base_fee: float, scholarship_percent: float) -> float:
    """Calculate the fee after scholarship discount."""
    if base_fee < 0 or not 0 <= scholarship_percent <= 100:
        raise ValueError("Invalid fee or scholarship percentage")
    return round(base_fee * (1 - scholarship_percent / 100), 2)


def student_payload(student_code: str) -> dict:
    """Return the stable API contract used by the profile component."""
    return {"student_id": student_code, "name": "Estudiante de prueba", "program": "Ingeniería"}


def enrollment_status(current_status: str) -> str:
    """Return the current enrollment status."""
    return current_status
