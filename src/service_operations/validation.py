"""Validate synthetic service requests against the repository data contract."""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from service_operations.contracts import load_contract, required_columns


@dataclass(frozen=True)
class ValidationResult:
    """Data-quality result with row-level evidence."""

    total_rows: int
    valid_rows: int
    invalid_rows: int
    issues: pd.DataFrame

    @property
    def issue_counts(self) -> dict[str, int]:
        counts = Counter(self.issues["issue_code"].tolist())
        return dict(sorted(counts.items()))

    def to_report(self) -> dict[str, Any]:
        return {
            "total_rows": self.total_rows,
            "valid_rows": self.valid_rows,
            "invalid_rows": self.invalid_rows,
            "valid_rate": round(self.valid_rows / self.total_rows, 4)
            if self.total_rows
            else 0.0,
            "issue_counts": self.issue_counts,
        }


def _is_blank(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.strip().eq("")


def _append_issue(
    issues: list[dict[str, object]],
    dataframe: pd.DataFrame,
    mask: pd.Series,
    *,
    issue_code: str,
    field: str,
    message: str,
) -> None:
    for index in dataframe.index[mask]:
        issues.append(
            {
                "source_row": int(index) + 2,
                "ticket_id": str(dataframe.at[index, "ticket_id"])
                if "ticket_id" in dataframe.columns
                else "",
                "issue_code": issue_code,
                "field": field,
                "observed_value": str(dataframe.at[index, field])
                if field in dataframe.columns
                else "",
                "message": message,
            }
        )


def validate_dataframe(
    dataframe: pd.DataFrame,
    contract: dict[str, Any],
) -> ValidationResult:
    """Validate a source dataframe without modifying its raw values."""
    expected_columns = required_columns(contract)
    missing_columns = [name for name in expected_columns if name not in dataframe.columns]
    if missing_columns:
        missing_text = ", ".join(missing_columns)
        raise ValueError(f"Source data is missing required columns: {missing_text}")

    source = dataframe.loc[:, expected_columns].copy()
    issues: list[dict[str, object]] = []

    column_map = {column["name"]: column for column in contract["columns"]}

    for name, definition in column_map.items():
        if not definition.get("nullable", True):
            _append_issue(
                issues,
                source,
                _is_blank(source[name]),
                issue_code="missing_required_value",
                field=name,
                message=f"{name} must not be blank.",
            )

        allowed_values = definition.get("allowed_values")
        if allowed_values:
            values = source[name].fillna("").astype(str).str.strip()
            mask = ~values.isin(allowed_values) & ~values.eq("")
            _append_issue(
                issues,
                source,
                mask,
                issue_code=f"invalid_{name}",
                field=name,
                message=f"{name} is outside the allowed domain.",
            )

    ticket_values = source["ticket_id"].fillna("").astype(str).str.strip()
    ticket_pattern = re.compile(column_map["ticket_id"]["pattern"])
    _append_issue(
        issues,
        source,
        ~ticket_values.map(lambda value: bool(ticket_pattern.fullmatch(value)))
        & ~ticket_values.eq(""),
        issue_code="invalid_ticket_id_format",
        field="ticket_id",
        message="ticket_id must match the documented SR-###### format.",
    )
    _append_issue(
        issues,
        source,
        ticket_values.duplicated(keep=False) & ~ticket_values.eq(""),
        issue_code="duplicate_ticket_id",
        field="ticket_id",
        message="ticket_id must be unique; all duplicate occurrences are rejected.",
    )

    timestamp_format = contract["timestamp_format"]
    created = pd.to_datetime(
        source["created_at"],
        format=timestamp_format,
        errors="coerce",
        utc=True,
    )
    closed_text = source["closed_at"].fillna("").astype(str).str.strip()
    closed = pd.to_datetime(
        closed_text.where(~closed_text.eq("")),
        format=timestamp_format,
        errors="coerce",
        utc=True,
    )
    _append_issue(
        issues,
        source,
        created.isna() & ~_is_blank(source["created_at"]),
        issue_code="invalid_created_at",
        field="created_at",
        message="created_at must use the documented UTC timestamp format.",
    )
    _append_issue(
        issues,
        source,
        closed.isna() & ~closed_text.eq(""),
        issue_code="invalid_closed_at",
        field="closed_at",
        message="closed_at must be blank or use the documented UTC timestamp format.",
    )

    numeric: dict[str, pd.Series] = {}
    for name in ["sla_target_minutes", "resolution_minutes", "reopened_count"]:
        raw = source[name].fillna("").astype(str).str.strip()
        converted = pd.to_numeric(raw.where(~raw.eq("")), errors="coerce")
        numeric[name] = converted
        _append_issue(
            issues,
            source,
            converted.isna() & ~raw.eq(""),
            issue_code=f"invalid_{name}_type",
            field=name,
            message=f"{name} must be an integer when supplied.",
        )

    _append_issue(
        issues,
        source,
        numeric["sla_target_minutes"].notna() & (numeric["sla_target_minutes"] < 1),
        issue_code="invalid_sla_target_range",
        field="sla_target_minutes",
        message="sla_target_minutes must be positive.",
    )
    _append_issue(
        issues,
        source,
        numeric["resolution_minutes"].notna() & (numeric["resolution_minutes"] < 0),
        issue_code="negative_resolution_minutes",
        field="resolution_minutes",
        message="resolution_minutes must not be negative.",
    )
    _append_issue(
        issues,
        source,
        numeric["reopened_count"].notna()
        & ((numeric["reopened_count"] < 0) | (numeric["reopened_count"] > 5)),
        issue_code="invalid_reopened_count_range",
        field="reopened_count",
        message="reopened_count must be between 0 and 5.",
    )

    escalated = source["escalated"].fillna("").astype(str).str.strip().str.lower()
    _append_issue(
        issues,
        source,
        ~escalated.isin(["true", "false"]) & ~escalated.eq(""),
        issue_code="invalid_escalated",
        field="escalated",
        message="escalated must be true or false.",
    )

    priority = source["priority"].fillna("").astype(str).str.strip()
    sla_mapping = contract["business_rules"]["sla_target_by_priority"]
    expected_sla = priority.map(sla_mapping)
    _append_issue(
        issues,
        source,
        expected_sla.notna()
        & numeric["sla_target_minutes"].notna()
        & (numeric["sla_target_minutes"] != expected_sla),
        issue_code="sla_priority_mismatch",
        field="sla_target_minutes",
        message="sla_target_minutes must match the documented priority mapping.",
    )

    status = source["status"].fillna("").astype(str).str.strip()
    closed_mask = status.eq("closed")
    open_mask = status.eq("open")

    _append_issue(
        issues,
        source,
        closed_mask & closed_text.eq(""),
        issue_code="closed_missing_closed_at",
        field="closed_at",
        message="Closed requests require closed_at.",
    )
    _append_issue(
        issues,
        source,
        closed_mask & numeric["resolution_minutes"].isna(),
        issue_code="closed_missing_resolution_minutes",
        field="resolution_minutes",
        message="Closed requests require resolution_minutes.",
    )
    _append_issue(
        issues,
        source,
        open_mask & ~closed_text.eq(""),
        issue_code="open_has_closed_at",
        field="closed_at",
        message="Open requests must not have closed_at.",
    )
    _append_issue(
        issues,
        source,
        open_mask & numeric["resolution_minutes"].notna(),
        issue_code="open_has_resolution_minutes",
        field="resolution_minutes",
        message="Open requests must not have resolution_minutes.",
    )
    _append_issue(
        issues,
        source,
        closed_mask & created.notna() & closed.notna() & (closed < created),
        issue_code="closed_before_created",
        field="closed_at",
        message="closed_at must not be earlier than created_at.",
    )

    issue_frame = pd.DataFrame(
        issues,
        columns=[
            "source_row",
            "ticket_id",
            "issue_code",
            "field",
            "observed_value",
            "message",
        ],
    ).sort_values(["source_row", "issue_code"], ignore_index=True)

    invalid_source_rows = set(issue_frame["source_row"].tolist())
    total_rows = len(source)
    invalid_rows = len(invalid_source_rows)

    return ValidationResult(
        total_rows=total_rows,
        valid_rows=total_rows - invalid_rows,
        invalid_rows=invalid_rows,
        issues=issue_frame,
    )


def validate_file(
    input_path: Path | str,
    contract_path: Path | str,
) -> ValidationResult:
    """Load CSV text values and validate them against the contract."""
    dataframe = pd.read_csv(
        input_path,
        dtype=str,
        keep_default_na=False,
        na_filter=False,
    )
    return validate_dataframe(dataframe, load_contract(contract_path))


def write_report(result: ValidationResult, report_path: Path | str) -> Path:
    """Write a stable JSON summary for CI and later Fabric comparison."""
    destination = Path(report_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(result.to_report(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return destination
