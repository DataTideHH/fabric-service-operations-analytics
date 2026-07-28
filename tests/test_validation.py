import json
from pathlib import Path

import pytest

from service_operations.contracts import load_contract
from service_operations.generator import generate_dataframe
from service_operations.validation import (
    validate_dataframe,
    validate_file,
    write_report,
)

CONTRACT_PATH = Path("contracts/service_requests.contract.json")
FIXTURE_PATH = Path("data/raw/service_requests.csv")

EXPECTED_ISSUES = {
    "closed_before_created": 1,
    "closed_missing_closed_at": 1,
    "duplicate_ticket_id": 2,
    "invalid_assigned_team": 1,
    "invalid_escalated": 1,
    "invalid_priority": 1,
    "missing_required_value": 1,
    "negative_resolution_minutes": 1,
    "open_has_closed_at": 1,
    "sla_priority_mismatch": 1,
}


def test_committed_fixture_has_expected_control_totals() -> None:
    result = validate_file(FIXTURE_PATH, CONTRACT_PATH)

    assert result.total_rows == 100
    assert result.valid_rows == 89
    assert result.invalid_rows == 11
    assert result.issue_counts == EXPECTED_ISSUES


def test_clean_generation_passes_contract() -> None:
    contract = load_contract(CONTRACT_PATH)
    result = validate_dataframe(
        generate_dataframe(inject_anomalies=False).astype(str),
        contract,
    )

    assert result.invalid_rows == 0
    assert result.issues.empty


def test_missing_required_column_fails_fast() -> None:
    contract = load_contract(CONTRACT_PATH)
    source = generate_dataframe().drop(columns=["category"])

    with pytest.raises(ValueError, match="missing required columns: category"):
        validate_dataframe(source, contract)


def test_report_is_stable_and_machine_readable(tmp_path: Path) -> None:
    result = validate_file(FIXTURE_PATH, CONTRACT_PATH)
    report_path = write_report(result, tmp_path / "validation_report.json")
    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert report == {
        "invalid_rows": 11,
        "issue_counts": EXPECTED_ISSUES,
        "total_rows": 100,
        "valid_rate": 0.89,
        "valid_rows": 89,
    }


def test_duplicate_rule_rejects_all_occurrences() -> None:
    contract = load_contract(CONTRACT_PATH)
    source = generate_dataframe(inject_anomalies=False).astype(str)
    source.loc[1, "ticket_id"] = source.loc[0, "ticket_id"]

    result = validate_dataframe(source, contract)
    duplicates = result.issues[result.issues["issue_code"] == "duplicate_ticket_id"]

    assert result.invalid_rows == 2
    assert len(duplicates) == 2
