import pytest
from lab.service_logic import calculate_enrollment_fee, enrollment_status, student_payload

def test_calculate_enrollment_fee_without_scholarship():
    assert calculate_enrollment_fee(1000, 0) == 1000

def test_calculate_enrollment_fee_with_scholarship():
    assert calculate_enrollment_fee(1000, 20) == 800

def test_calculate_enrollment_fee_rejects_invalid_scholarship():
    with pytest.raises(ValueError):
        calculate_enrollment_fee(1000, 120)

def test_student_payload_uses_expected_contract():
    assert student_payload("STU-1042")["student_id"] == "STU-1042"

def test_enrollment_status():
    assert enrollment_status("Confirmada") == "Confirmada"
