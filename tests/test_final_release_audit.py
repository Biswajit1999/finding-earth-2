from scripts.final_release_audit import audit


def test_all_scientific_release_gates_pass() -> None:
    result = audit()
    assert result["gate_count"] >= 25
    assert result["failed"] == []
    assert result["passed"] == result["gate_count"]
