from pathlib import Path

import pytest

from service_operations.contracts import load_contract, required_columns

CONTRACT_PATH = Path("contracts/service_requests.contract.json")


def test_contract_has_expected_identity_and_controls() -> None:
    contract = load_contract(CONTRACT_PATH)

    assert contract["contract_name"] == "service_requests"
    assert contract["contract_version"] == "1.0.0"
    assert contract["record_count"] == 100
    assert contract["expected_invalid_rows"] == 11
    assert contract["primary_key"] == ["ticket_id"]


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
