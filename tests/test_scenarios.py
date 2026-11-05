from lab import database, scenarios


def test_group4_creates_simulated_cpu_alert(isolated_db):
    result = scenarios.activate_group4()
    assert result["event_id"] > 0
    event = database.list_events(1)[0]
    assert event["event_code"] == "EV-G4-CPU"
    assert event["evidence"]["cpu_percent"] == 94.0
    assert event["evidence"]["source"] == "simulated"


def test_group5_creates_five_day_storage_history(isolated_db):
    result = scenarios.activate_group5()
    assert len(result["metric_ids"]) == 5
    samples = database.list_metrics(10)
    values = [sample["storage_used_mb"] for sample in samples if sample["source"] == "simulated"]
    assert values == [42.0, 51.0, 60.0, 73.0, 88.0]


def test_group6_activates_contract_mismatch(isolated_db):
    scenarios.activate_group6()
    assert database.is_scenario_active(6) is True
    assert database.list_events(1)[0]["event_code"] == "EV-G6-CONTRACT"


def test_group7_activates_stale_read_and_reset_restores_data(isolated_db):
    scenarios.activate_group7()
    assert database.get_enrollment("enrollment_current")["enrollment_status"] == "Confirmada"
    assert database.get_enrollment("enrollment_read_model")["enrollment_status"] == "Pendiente"
    scenarios.reset_scenario(7)
    assert database.get_enrollment("enrollment_current")["enrollment_status"] == "Pendiente"
    assert database.get_enrollment("enrollment_read_model")["enrollment_status"] == "Pendiente"
