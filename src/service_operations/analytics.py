"""Build a reproducible DuckDB SQL analytics layer from local Gold Parquet tables."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

ANALYTICS_VERSION = "0.1.0"
MART_NAMES = [
    "service_requests_enriched",
    "sla_by_team",
    "sla_by_category",
    "sla_by_priority",
    "sla_by_team_category",
    "daily_service_operations",
    "sla_breach_details",
]


@dataclass(frozen=True)
class AnalyticsTables:
    """Materialized analytics tables and reconciled controls for one run."""

    service_requests_enriched: pd.DataFrame
    sla_by_team: pd.DataFrame
    sla_by_category: pd.DataFrame
    sla_by_priority: pd.DataFrame
    sla_by_team_category: pd.DataFrame
    daily_service_operations: pd.DataFrame
    sla_breach_details: pd.DataFrame
    manifest: dict[str, Any]


def _sql_literal(path: Path) -> str:
    return str(path.resolve()).replace("'", "''")


def _register_parquet_views(connection: duckdb.DuckDBPyConnection, medallion_dir: Path) -> None:
    files = {
        "fact_service_requests": medallion_dir / "gold/fact_service_requests.parquet",
        "dim_date": medallion_dir / "gold/dim_date.parquet",
        "dim_team": medallion_dir / "gold/dim_team.parquet",
        "dim_category": medallion_dir / "gold/dim_category.parquet",
        "dim_priority": medallion_dir / "gold/dim_priority.parquet",
    }
    missing = [str(path) for path in files.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Missing Gold Parquet input: {', '.join(missing)}")

    for view_name, path in files.items():
        connection.execute(
            f"CREATE OR REPLACE VIEW {view_name} AS "
            f"SELECT * FROM read_parquet('{_sql_literal(path)}')"
        )


def _read_sql(sql_dir: Path, name: str) -> str:
    path = sql_dir / f"{name}.sql"
    if not path.is_file():
        raise FileNotFoundError(f"Missing analytics SQL file: {path}")
    return path.read_text(encoding="utf-8").strip().rstrip(";")


def _frame(connection: duckdb.DuckDBPyConnection, sql: str) -> pd.DataFrame:
    return connection.execute(sql).fetchdf()


def _build_manifest(
    medallion_manifest: dict[str, Any],
    tables: dict[str, pd.DataFrame],
) -> dict[str, Any]:
    global_kpis = medallion_manifest["kpis"]
    expected_breaches = int(global_kpis["closed_requests"] - global_kpis["sla_met_requests"])
    team = tables["sla_by_team"]
    category = tables["sla_by_category"]
    priority = tables["sla_by_priority"]
    team_category = tables["sla_by_team_category"]
    daily = tables["daily_service_operations"]
    breach_details = tables["sla_breach_details"]

    weighted_team_rate = round(
        int(team["sla_met_requests"].sum()) / int(team["closed_requests"].sum()),
        4,
    )
    controls = {
        "enriched_equals_gold_fact": len(tables["service_requests_enriched"])
        == medallion_manifest["row_counts"]["gold_fact"],
        "breach_details_equals_global_breaches": len(breach_details) == expected_breaches,
        "team_closed_reconciles": int(team["closed_requests"].sum())
        == global_kpis["closed_requests"],
        "category_closed_reconciles": int(category["closed_requests"].sum())
        == global_kpis["closed_requests"],
        "priority_closed_reconciles": int(priority["closed_requests"].sum())
        == global_kpis["closed_requests"],
        "team_category_closed_reconciles": int(team_category["closed_requests"].sum())
        == global_kpis["closed_requests"],
        "daily_requests_reconcile": int(daily["total_requests"].sum())
        == global_kpis["total_requests"],
        "weighted_team_sla_equals_global": weighted_team_rate
        == global_kpis["sla_compliance_rate"],
        "all_breach_rows_are_closed": bool(breach_details["status"].eq("closed").all()),
        "all_breach_overruns_are_positive": bool(
            breach_details["resolution_overrun_minutes"].gt(0).all()
        ),
    }
    return {
        "analytics_version": ANALYTICS_VERSION,
        "source_ingestion_batch_id": medallion_manifest["ingestion_batch_id"],
        "row_counts": {name: len(frame) for name, frame in tables.items()},
        "controls": controls,
        "global_kpis": {
            "total_requests": global_kpis["total_requests"],
            "closed_requests": global_kpis["closed_requests"],
            "sla_met_requests": global_kpis["sla_met_requests"],
            "sla_breaches": expected_breaches,
            "sla_compliance_rate": global_kpis["sla_compliance_rate"],
            "reopened_requests": global_kpis["reopened_requests"],
            "reopen_rate": global_kpis["reopen_rate"],
            "escalated_requests": global_kpis["escalated_requests"],
            "escalation_rate": global_kpis["escalation_rate"],
            "open_backlog": global_kpis["open_backlog"],
            "open_backlog_rate": global_kpis["open_backlog_rate"],
        },
    }


def build_analytics(
    medallion_dir: Path | str,
    sql_dir: Path | str,
) -> AnalyticsTables:
    """Execute the versioned SQL layer against local Gold Parquet tables."""
    medallion_path = Path(medallion_dir)
    sql_path = Path(sql_dir)
    manifest_path = medallion_path / "medallion_manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Missing Medallion manifest: {manifest_path}")
    medallion_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    with duckdb.connect(database=":memory:") as connection:
        _register_parquet_views(connection, medallion_path)
        enriched_sql = _read_sql(sql_path, "service_requests_enriched")
        connection.execute(
            "CREATE OR REPLACE TEMP VIEW service_requests_enriched AS " + enriched_sql
        )

        frames: dict[str, pd.DataFrame] = {
            "service_requests_enriched": _frame(
                connection,
                "SELECT * FROM service_requests_enriched ORDER BY ticket_id",
            )
        }
        for name in MART_NAMES[1:]:
            frames[name] = _frame(connection, _read_sql(sql_path, name))

    manifest = _build_manifest(medallion_manifest, frames)
    if not all(manifest["controls"].values()):
        failed = [name for name, passed in manifest["controls"].items() if not passed]
        raise ValueError(f"Analytics reconciliation controls failed: {', '.join(failed)}")

    return AnalyticsTables(
        service_requests_enriched=frames["service_requests_enriched"],
        sla_by_team=frames["sla_by_team"],
        sla_by_category=frames["sla_by_category"],
        sla_by_priority=frames["sla_by_priority"],
        sla_by_team_category=frames["sla_by_team_category"],
        daily_service_operations=frames["daily_service_operations"],
        sla_breach_details=frames["sla_breach_details"],
        manifest=manifest,
    )


def write_analytics(tables: AnalyticsTables, output_dir: Path | str) -> Path:
    """Persist analytics marts as Parquet plus reviewable CSV and JSON evidence."""
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)

    frames = {
        "service_requests_enriched": tables.service_requests_enriched,
        "sla_by_team": tables.sla_by_team,
        "sla_by_category": tables.sla_by_category,
        "sla_by_priority": tables.sla_by_priority,
        "sla_by_team_category": tables.sla_by_team_category,
        "daily_service_operations": tables.daily_service_operations,
        "sla_breach_details": tables.sla_breach_details,
    }
    for name, frame in frames.items():
        frame.to_parquet(destination / f"{name}.parquet", index=False)

    for name in ["sla_by_team", "sla_by_category", "sla_by_priority"]:
        frames[name].to_csv(destination / f"{name}.csv", index=False, lineterminator="\n")

    manifest_path = destination / "analytics_manifest.json"
    manifest_path.write_text(
        json.dumps(tables.manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest_path


def run_analytics(
    medallion_dir: Path | str,
    sql_dir: Path | str,
    output_dir: Path | str,
) -> Path:
    """Build and persist the complete local SQL analytics layer."""
    return write_analytics(build_analytics(medallion_dir, sql_dir), output_dir)
