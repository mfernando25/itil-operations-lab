from datetime import datetime
from lab import database, scenarios, evidence, services, metrics


def test_group1_and_group2_create_student_safe_notifications(isolated_db):
    scenarios.activate_group1()
    scenarios.activate_group2()
    events = database.list_events(10)
    assert {e["event_code"] for e in events} >= {"EV-G1-CI", "EV-G2-WORKFLOW"}
    assert all("root_cause" not in e["evidence"] for e in events)
    private = database.list_events(10, include_private=True)
    assert any("root_cause" in e["private_evidence"] for e in private)


def test_group3_builds_isolated_divergent_git_repository(isolated_db):
    result = scenarios.activate_group3()
    workspace = scenarios.G3_DIR / "student-workspace"
    assert result["event_id"] > 0
    assert (workspace / "evidence" / "initial-rejection.txt").exists()
    text = (workspace / "evidence" / "initial-rejection.txt").read_text(encoding="utf-8")
    assert "CONFLICT" in text.upper() or "Automatic merge failed" in text
    status = (workspace / "evidence" / "local-state.txt").read_text(encoding="utf-8")
    assert "feature/matricula" in status

    scenarios.reset_scenario(3)
    assert not scenarios.G3_DIR.exists()
    assert not database.is_scenario_active(3)


def test_group4_generates_five_day_cpu_and_service_history(isolated_db):
    result = scenarios.activate_group4()
    assert result["event_id"] > 0
    rows = database.list_metrics(group_number=4)
    assert len(rows) == 10
    assert rows[0]["cpu_percent"] < rows[-1]["cpu_percent"]
    assert rows[-1]["requests_per_minute"] == 1480
    assert rows[-1]["avg_response_ms"] == 2450
    days = {datetime.fromisoformat(row["captured_at"]).date() for row in rows}
    assert len(days) == 5
    assert all(sum(1 for row in rows if datetime.fromisoformat(row["captured_at"]).date() == day) == 2 for day in days)
    bundle = evidence.build_bundle(4, 1)["markdown"]
    assert "Historial de cinco días" in bundle
    assert "2450" in bundle


def test_group5_generates_five_day_log_and_backup_growth_without_large_files(isolated_db):
    result = scenarios.activate_group5()
    assert result["event_id"] > 0
    rows = database.list_metrics(group_number=5)
    assert len(rows) == 10
    assert rows[0]["storage_available_gb"] > rows[-1]["storage_available_gb"]
    assert rows[-1]["storage_capacity_gb"] == 10.0
    assert rows[-1]["storage_available_gb"] == 1.3
    days = {datetime.fromisoformat(row["captured_at"]).date() for row in rows}
    assert len(days) == 5
    assert all(sum(1 for row in rows if datetime.fromisoformat(row["captured_at"]).date() == day) == 2 for day in days)
    assert evidence.build_bundle(5, 2)["filename"] == "G5_evidencia_2.md"



def test_g4_dashboard_uses_synthetic_cpu_and_real_host_memory_disk(isolated_db):
    database.add_metric("real", cpu=21.0, memory=48.0, disk=67.0, storage_mb=12.0)
    scenarios.activate_group4()

    result = metrics.current_metrics(public_group=4)
    assert result["current"]["cpu_percent"] == 94.0
    assert result["current"]["memory_percent"] == 48.0
    assert result["current"]["disk_percent"] == 67.0
    assert len(result["history"]) == 10
    assert all(row["memory_percent"] is None for row in result["history"])
    assert all(row["disk_percent"] is None for row in result["history"])
    assert result["history"][-1]["requests_per_minute"] == 1480
    assert result["history"][-1]["avg_response_ms"] == 2450
    assert "sintético" in result["cpu_history_label"]


def test_g5_dashboard_uses_real_host_resources_and_synthetic_service_storage(isolated_db):
    database.add_metric("real", cpu=22.0, memory=49.0, disk=68.0, storage_mb=13.0)
    scenarios.activate_group5()

    result = metrics.current_metrics(public_group=5)
    assert result["current"]["cpu_percent"] == 22.0
    assert result["current"]["memory_percent"] == 49.0
    assert result["current"]["disk_percent"] == 68.0
    assert len(result["history"]) == 1
    assert len(result["storage_history"]) == 10
    assert result["storage_current"]["storage_capacity_gb"] == 10.0
    assert result["storage_current"]["storage_available_gb"] == 1.3
    assert "sintético" in result["storage_history_label"]


def test_g4_g5_reactivation_and_reset_do_not_accumulate_synthetic_samples(isolated_db):
    for group, activate in ((4, scenarios.activate_group4), (5, scenarios.activate_group5)):
        activate()
        assert len(database.list_metrics(group_number=group)) == 10

        activate()
        assert len(database.list_metrics(group_number=group)) == 10

        scenarios.reset_scenario(group)
        assert database.list_metrics(group_number=group) == []

        activate()
        assert len(database.list_metrics(group_number=group)) == 10

def test_group6_contract_mismatch_is_reproducible(isolated_db):
    assert "student_id" in services.students_service("STU-1042")
    scenarios.activate_group6()
    payload = services.students_service("STU-1042", contract_mismatch=True)
    assert "studentId" in payload
    assert "student_id" not in payload
    assert database.is_scenario_active(6)
    scenarios.reset_scenario(6)
    assert not database.is_scenario_active(6)


def test_group7_stale_cache_and_reconciliation(isolated_db):
    scenarios.activate_group7()
    assert database.get_enrollment("enrollment_current")["enrollment_status"] == "Confirmada"
    assert database.get_enrollment("enrollment_cache")["enrollment_status"] == "Pendiente"
    database.update_enrollment_cache("Confirmada")
    assert database.get_enrollment("enrollment_cache")["enrollment_status"] == "Confirmada"
    scenarios.reset_scenario(7)
    assert database.get_enrollment("enrollment_current")["enrollment_status"] == "Pendiente"
    assert database.get_enrollment("enrollment_cache")["enrollment_status"] == "Pendiente"


def test_each_group_has_initial_and_three_supplementary_evidence_packs(isolated_db):
    for group in range(1, 8):
        for pack in range(4):
            bundle = evidence.build_bundle(group, pack)
            assert bundle["markdown"].startswith("# G")
            assert bundle["filename"].endswith(".md")
