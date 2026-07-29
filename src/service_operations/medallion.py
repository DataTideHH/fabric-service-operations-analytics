"""Build a local Bronze, Silver and Gold service-operations pipeline."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from service_operations.contracts import load_contract
from service_operations.validation import ValidationResult, validate_dataframe

PIPELINE_VERSION = "0.2.0"
DEFAULT_INGESTED_AT = "2026-07-29T00:00:00Z"
PRIORITY_ORDER = ["P1", "P2", "P3", "P4"]
INTEGER_KPIS = {
    "total_requests",
    "closed_requests",
    "open_backlog",
    "sla_eligible_requests",
    "sla_met_requests",
    "escalated_requests",
    "reopened_requests",
}
RAW_COLUMNS = [
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


@dataclass(frozen=True)
class MedallionTables:
    """In-memory tables and controls for one deterministic pipeline run."""

    bronze: pd.DataFrame
    silver_valid: pd.DataFrame
    silver_rejected: pd.DataFrame
    silver_issues: pd.DataFrame
    fact_service_requests: pd.DataFrame
    dim_date: pd.DataFrame
    dim_team: pd.DataFrame
    dim_category: pd.DataFrame
    dim_priority: pd.DataFrame
    kpis: pd.DataFrame
    manifest: dict[str, Any]


def build_bronze(input_path: Path | str) -> pd.DataFrame:
    """Load source-shaped text values and add deterministic ingestion metadata."""
    source_path = Path(input_path)
    source_bytes = source_path.read_bytes()
    source = pd.read_csv(
        source_path,
        dtype=str,
        keep_default_na=False,
        na_filter=False,
    )

    missing = [column for column in RAW_COLUMNS if column not in source.columns]
    if missing:
        missing_text = ", ".join(missing)
        raise ValueError(f"Source data is missing required Bronze columns: {missing_text}")

    bronze = source.loc[:, RAW_COLUMNS].copy()
    bronze.insert(0, "source_row", range(2, len(bronze) + 2))
    bronze["source_file"] = source_path.name
    bronze["ingestion_batch_id"] = hashlib.sha256(source_bytes).hexdigest()[:16]
    bronze["ingested_at_utc"] = DEFAULT_INGESTED_AT
    return bronze


def _aggregate_rejections(issues: pd.DataFrame) -> tuple[dict[int, str], dict[int, int]]:
    if issues.empty:
        return {}, {}

    grouped = issues.groupby("source_row")["issue_code"]
    reasons = grouped.agg(lambda values: "|".join(sorted(set(values)))).to_dict()
    counts = grouped.size().astype(int).to_dict()
    return reasons, counts


def _type_valid_records(valid: pd.DataFrame) -> pd.DataFrame:
    typed = valid.copy()
    typed["created_at"] = pd.to_datetime(typed["created_at"], utc=True, errors="raise")
    typed["closed_at"] = pd.to_datetime(
        typed["closed_at"].replace("", pd.NA),
        utc=True,
        errors="raise",
    )

    for column in [
        "source_row",
        "sla_target_minutes",
        "resolution_minutes",
        "reopened_count",
    ]:
        typed[column] = pd.to_numeric(typed[column], errors="raise").astype("Int64")

    typed["escalated"] = (
        typed["escalated"]
        .str.lower()
        .map({"true": True, "false": False})
        .astype("boolean")
    )
    typed["sla_met"] = pd.Series(pd.NA, index=typed.index, dtype="boolean")
    closed_mask = typed["status"].eq("closed")
    typed.loc[closed_mask, "sla_met"] = (
        typed.loc[closed_mask, "resolution_minutes"]
        <= typed.loc[closed_mask, "sla_target_minutes"]
    ).astype("boolean")

    return typed.reset_index(drop=True)


def build_silver(
    bronze: pd.DataFrame,
    contract: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame, ValidationResult]:
    """Split Bronze rows into typed valid records and auditable rejections."""
    validation = validate_dataframe(bronze, contract)
    invalid_source_rows = set(validation.issues["source_row"].astype(int).tolist())

    valid = bronze.loc[~bronze["source_row"].isin(invalid_source_rows)].copy()
    rejected = bronze.loc[bronze["source_row"].isin(invalid_source_rows)].copy()

    reasons, counts = _aggregate_rejections(validation.issues)
    rejected["rejection_reasons"] = rejected["source_row"].map(reasons)
    rejected["issue_count"] = rejected["source_row"].map(counts).astype("Int64")

    return (
        _type_valid_records(valid),
        rejected.reset_index(drop=True),
        validation,
    )


def _string_dimension(values: pd.Series, value_column: str, key_column: str) -> pd.DataFrame:
    unique_values = sorted(values.dropna().astype(str).unique().tolist())
    return pd.DataFrame(
        {
            key_column: range(1, len(unique_values) + 1),
            value_column: unique_values,
        }
    )


def _build_date_dimension(valid: pd.DataFrame) -> pd.DataFrame:
    dates = pd.concat(
        [valid["created_at"].dt.normalize(), valid["closed_at"].dropna().dt.normalize()],
        ignore_index=True,
    )
    dates = dates.drop_duplicates().sort_values(ignore_index=True)
    local_dates = dates.dt.tz_convert(None)

    return pd.DataFrame(
        {
            "date_key": dates.dt.strftime("%Y%m%d").astype(int),
            "full_date": local_dates,
            "year": dates.dt.year.astype(int),
            "quarter": dates.dt.quarter.astype(int),
            "month_number": dates.dt.month.astype(int),
            "month_name": dates.dt.month_name(),
            "day_of_week": dates.dt.day_name(),
        }
    )


def _build_priority_dimension(valid: pd.DataFrame) -> pd.DataFrame:
    observed = set(valid["priority"].astype(str))
    priorities = [priority for priority in PRIORITY_ORDER if priority in observed]
    sla_by_priority = (
        valid.loc[:, ["priority", "sla_target_minutes"]]
        .drop_duplicates()
        .set_index("priority")["sla_target_minutes"]
        .astype(int)
        .to_dict()
    )
    return pd.DataFrame(
        {
            "priority_key": range(1, len(priorities) + 1),
            "priority": priorities,
            "sla_target_minutes": [sla_by_priority[priority] for priority in priorities],
        }
    )


def _build_fact_table(
    valid: pd.DataFrame,
    dim_team: pd.DataFrame,
    dim_category: pd.DataFrame,
    dim_priority: pd.DataFrame,
) -> pd.DataFrame:
    fact = valid.copy()
    fact["created_date_key"] = fact["created_at"].dt.strftime("%Y%m%d").astype(int)
    fact["closed_date_key"] = pd.to_numeric(
        fact["closed_at"].dt.strftime("%Y%m%d"),
        errors="coerce",
    ).astype("Int64")
    fact["team_key"] = fact["assigned_team"].map(
        dim_team.set_index("assigned_team")["team_key"]
    )
    fact["category_key"] = fact["category"].map(
        dim_category.set_index("category")["category_key"]
    )
    fact["priority_key"] = fact["priority"].map(
        dim_priority.set_index("priority")["priority_key"]
    )

    for column in ["team_key", "category_key", "priority_key"]:
        if fact[column].isna().any():
            raise ValueError(f"Gold fact contains unresolved foreign key values in {column}.")
        fact[column] = fact[column].astype(int)

    return fact.loc[
        :,
        [
            "ticket_id",
            "created_date_key",
            "closed_date_key",
            "team_key",
            "category_key",
            "priority_key",
            "status",
            "sla_target_minutes",
            "resolution_minutes",
            "reopened_count",
            "escalated",
            "sla_met",
            "customer_segment",
            "source_system",
            "source_row",
            "ingestion_batch_id",
        ],
    ].reset_index(drop=True)


def _build_kpis(valid: pd.DataFrame) -> pd.DataFrame:
    closed = valid.loc[valid["status"].eq("closed")]
    total_requests = len(valid)
    closed_requests = len(closed)
    open_backlog = total_requests - closed_requests
    sla_met_requests = int(closed["sla_met"].sum())
    escalated_requests = int(valid["escalated"].sum())
    reopened_requests = int((valid["reopened_count"] > 0).sum())

    return pd.DataFrame(
        [
            {
                "total_requests": total_requests,
                "closed_requests": closed_requests,
                "open_backlog": open_backlog,
                "sla_eligible_requests": closed_requests,
                "sla_met_requests": sla_met_requests,
                "sla_compliance_rate": round(sla_met_requests / closed_requests, 4),
                "average_resolution_minutes": round(
                    float(closed["resolution_minutes"].mean()),
                    2,
                ),
                "median_resolution_minutes": round(
                    float(closed["resolution_minutes"].median()),
                    2,
                ),
                "escalated_requests": escalated_requests,
                "escalation_rate": round(escalated_requests / total_requests, 4),
                "reopened_requests": reopened_requests,
                "reopen_rate": round(reopened_requests / total_requests, 4),
            }
        ]
    )


def _foreign_keys_complete(
    fact: pd.DataFrame,
    dim_date: pd.DataFrame,
    dim_team: pd.DataFrame,
    dim_category: pd.DataFrame,
    dim_priority: pd.DataFrame,
) -> bool:
    date_keys = set(dim_date["date_key"])
    closed_keys = set(fact["closed_date_key"].dropna().astype(int))
    return all(
        [
            set(fact["created_date_key"]).issubset(date_keys),
            closed_keys.issubset(date_keys),
            set(fact["team_key"]).issubset(set(dim_team["team_key"])),
            set(fact["category_key"]).issubset(set(dim_category["category_key"])),
            set(fact["priority_key"]).issubset(set(dim_priority["priority_key"])),
        ]
    )


def _native_value(value: Any) -> Any:
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def _build_manifest(
    bronze: pd.DataFrame,
    silver_valid: pd.DataFrame,
    silver_rejected: pd.DataFrame,
    validation: ValidationResult,
    fact: pd.DataFrame,
    dim_date: pd.DataFrame,
    dim_team: pd.DataFrame,
    dim_category: pd.DataFrame,
    dim_priority: pd.DataFrame,
    kpis: pd.DataFrame,
) -> dict[str, Any]:
    kpi_values = {}
    for key, value in kpis.iloc[0].to_dict().items():
        native = _native_value(value)
        kpi_values[key] = int(native) if key in INTEGER_KPIS else native
    return {
        "pipeline_version": PIPELINE_VERSION,
        "source_file": str(bronze["source_file"].iloc[0]),
        "ingestion_batch_id": str(bronze["ingestion_batch_id"].iloc[0]),
        "row_counts": {
            "bronze": len(bronze),
            "silver_valid": len(silver_valid),
            "silver_rejected": len(silver_rejected),
            "silver_issues": len(validation.issues),
            "gold_fact": len(fact),
            "dim_date": len(dim_date),
            "dim_team": len(dim_team),
            "dim_category": len(dim_category),
            "dim_priority": len(dim_priority),
        },
        "issue_counts": validation.issue_counts,
        "controls": {
            "bronze_equals_valid_plus_rejected": len(bronze)
            == len(silver_valid) + len(silver_rejected),
            "valid_equals_fact": len(silver_valid) == len(fact),
            "foreign_keys_complete": _foreign_keys_complete(
                fact,
                dim_date,
                dim_team,
                dim_category,
                dim_priority,
            ),
        },
        "kpis": kpi_values,
    }


def build_medallion(
    input_path: Path | str,
    contract_path: Path | str,
) -> MedallionTables:
    """Build all local Medallion tables and reconciled controls in memory."""
    bronze = build_bronze(input_path)
    contract = load_contract(contract_path)
    silver_valid, silver_rejected, validation = build_silver(bronze, contract)

    dim_date = _build_date_dimension(silver_valid)
    dim_team = _string_dimension(silver_valid["assigned_team"], "assigned_team", "team_key")
    dim_category = _string_dimension(silver_valid["category"], "category", "category_key")
    dim_priority = _build_priority_dimension(silver_valid)
    fact = _build_fact_table(
        silver_valid,
        dim_team,
        dim_category,
        dim_priority,
    )
    kpis = _build_kpis(silver_valid)
    manifest = _build_manifest(
        bronze,
        silver_valid,
        silver_rejected,
        validation,
        fact,
        dim_date,
        dim_team,
        dim_category,
        dim_priority,
        kpis,
    )

    if not all(manifest["controls"].values()):
        raise ValueError("Medallion reconciliation controls failed.")

    return MedallionTables(
        bronze=bronze,
        silver_valid=silver_valid,
        silver_rejected=silver_rejected,
        silver_issues=validation.issues,
        fact_service_requests=fact,
        dim_date=dim_date,
        dim_team=dim_team,
        dim_category=dim_category,
        dim_priority=dim_priority,
        kpis=kpis,
        manifest=manifest,
    )


def write_medallion(tables: MedallionTables, output_dir: Path | str) -> Path:
    """Write local Parquet layers, KPI CSV and a machine-readable manifest."""
    destination = Path(output_dir)
    bronze_dir = destination / "bronze"
    silver_dir = destination / "silver"
    gold_dir = destination / "gold"
    for directory in [bronze_dir, silver_dir, gold_dir]:
        directory.mkdir(parents=True, exist_ok=True)

    tables.bronze.to_parquet(bronze_dir / "service_requests.parquet", index=False)
    tables.silver_valid.to_parquet(
        silver_dir / "service_requests_valid.parquet",
        index=False,
    )
    tables.silver_rejected.to_parquet(
        silver_dir / "service_requests_rejected.parquet",
        index=False,
    )
    tables.silver_issues.to_parquet(
        silver_dir / "service_request_issues.parquet",
        index=False,
    )
    tables.fact_service_requests.to_parquet(
        gold_dir / "fact_service_requests.parquet",
        index=False,
    )
    tables.dim_date.to_parquet(gold_dir / "dim_date.parquet", index=False)
    tables.dim_team.to_parquet(gold_dir / "dim_team.parquet", index=False)
    tables.dim_category.to_parquet(gold_dir / "dim_category.parquet", index=False)
    tables.dim_priority.to_parquet(gold_dir / "dim_priority.parquet", index=False)
    tables.kpis.to_csv(
        gold_dir / "service_operations_kpis.csv",
        index=False,
        lineterminator="\n",
    )

    manifest_path = destination / "medallion_manifest.json"
    manifest_path.write_text(
        json.dumps(tables.manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest_path


def run_medallion(
    input_path: Path | str,
    contract_path: Path | str,
    output_dir: Path | str,
) -> Path:
    """Build and persist one complete local Medallion run."""
    return write_medallion(build_medallion(input_path, contract_path), output_dir)
