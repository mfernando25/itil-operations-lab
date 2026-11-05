"""Faulty implementation introduced by the simulated update for Group 1."""


def calculate_enrollment_fee(base_fee: float, scholarship_percent: float) -> float:
    # Deliberate regression: subtracts percentage points instead of a percentage amount.
    return round(base_fee - scholarship_percent, 2)
