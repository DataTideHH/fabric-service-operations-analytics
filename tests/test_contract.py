from pathlib import Path

import pytest

from service_operations.contracts import load_contract, required_columns

CONTRACT_PATH = Path("contracts/service_requests.contract.json")


def test_contract_has_expected_identity_and_controls() -> None:
    contract = load_contract(CONTRACT_PATH)

    assert contract["contract_name"] == "service_requests"
    assert contract["contract_version"] == "1.1.0"
    assert contract["record_count"] == 1000
    assert contract["expected_invalid_rows"] == 11
    assert contract["primary_key"] == ["ticket_id"]


def test_contract_documents_the_synthetic_operating_scenario() -> None:
    scenario = load_contract(CONTRACT_PATH)["scenario"]

    assert scenario["name"] == "single_customer_90_day_baseline"
    assert scenario["analysis_window_days"] == 90
    assert scenario["customer_environments"] == 1
    assert scenario["operational_teams"] == 5
    assert scenario["kpi_design_ranges"] == {
        "sla_compliance_rate": [0.93, 0.96],
        "reopen_rate": [0.05, 0.09],
        "escalation_rate": [0.07, 0.12],
        "open_backlog_rate": [0.1, 0.18],
    }


def test_contract_column_order_is_stable() -> None:
    contract = load_contract(CONTRACT_PATH)

    assert required_columns(contract) == [
        "ticket_id",
        "created_at",
        "closed_at",
        "priority",
        "category",
        "assigned_team",
        "status",
        "sla_target_minutes",
        "resolution_minutes",
        "reopened_count",
        "escalated",
        "customer_segment",
        "source_system",
    ]


def test_contract_excludes_personal_data_fields() -> None:
    contract = load_contract(CONTRACT_PATH)
    columns = set(required_columns(contract))
    forbidden = set(contract["safety"]["forbidden_columns"])

    assert contract["safety"]["synthetic_only"] is True
    assert columns.isdisjoint(forbidden)


def test_contract_loader_rejects_incomplete_contract(tmp_path: Path) -> None:
    path = tmp_path / "contract.json"
    path.write_text('{"contract_name": "broken"}', encoding="utf-8")

    with pytest.raises(ValueError, match="missing required keys"):
        load_contract(path)
