"""Intentionally failing integration test for Group 1; run manually only."""
from scenario_tests.group1.updated_service_logic import calculate_enrollment_fee


def test_enrollment_fee_after_scholarship_update():
    # A 20% scholarship on a base fee of 1000 should leave 800 to pay.
    assert calculate_enrollment_fee(1000, 20) == 800
