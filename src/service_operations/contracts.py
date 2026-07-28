"""Load and inspect the machine-readable service-request data contract."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_CONTRACT_PATH = Path("contracts/service_requests.contract.json")


def load_contract(path: Path | str = DEFAULT_CONTRACT_PATH) -> dict[str, Any]:
    """Load a JSON data contract and perform minimal structural checks."""
    contract_path = Path(path)
    with contract_path.open(encoding="utf-8") as handle:
        contract: dict[str, Any] = json.load(handle)

    required_keys = {
        "contract_name",
        "contract_version",
        "record_count",
        "expected_invalid_rows",
        "primary_key",
        "timestamp_format",
        "columns",
        "business_rules",
        "safety",
    }
    missing = required_keys.difference(contract)
    if missing:
        missing_text = ", ".join(sorted(missing))
        raise ValueError(f"Contract is missing required keys: {missing_text}")

    column_names = [column["name"] for column in contract["columns"]]
    if len(column_names) != len(set(column_names)):
        raise ValueError("Contract column names must be unique.")

    return contract


def required_columns(contract: dict[str, Any]) -> list[str]:
    """Return contract columns in their required source order."""
    return [column["name"] for column in contract["columns"]]


def column_definition(contract: dict[str, Any], name: str) -> dict[str, Any]:
    """Return one column definition or raise a clear error."""
    for column in contract["columns"]:
        if column["name"] == name:
            return column
    raise KeyError(f"Unknown contract column: {name}")
