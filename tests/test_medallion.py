import json
from pathlib import Path

import pandas as pd
import pytest

from service_operations.generator import generate_dataframe, write_dataset
from service_operations.medallion import build_medallion, write_medallion

CONTRACT_PATH = Path("contracts/service_requests.contract.json")
EVIDENCE_MANIFEST = Path("evidence/medallion_manifest.json")
EVIDENCE_KPIS = Path("evidence/service_operations_kpis.csv")

EXPECTED_ROW_COUNTS = {
    "bronze": 1000,
    "silver_valid": 989,
    "silver_rejected": 11,
    "silver_issues": 11,
    "gold_fact": 989,
    "dim_date": 91,
    "dim_team": 5,
    "dim_category": 5,
    "dim_priority": 4,
}

EXPECTED_KPIS = {
    "total_requests": 989,
    "closed_requests": 833,
    "open_backlog": 156,
    "open_backlog_rate": 0.1577,
    "sla_eligible_requests": 833,
    "sla_met_requests": 799,
    "sla_compliance_rate": 0.9592,
    "average_resolution_minutes": 835.84,
    "median_resolution_minutes": 694.0,
    "escalated_requests": 85,
    "escalation_rate": 0.0859,
    "reopen_eligible_requests": 833,
    "reopened_requests": 48,
    "reopen_rate": 0.0576,
}


@pytest.fixture(scope="module")
def input_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("fixture") / "service_requests.csv"
    return write_dataset(generate_dataframe(), path)


@pytest.fixture(scope="module")
def tables(input_path: Path):
    return build_medallion(input_path, CONTRACT_PATH)


def test_bronze_preserves_source_rows_and_adds_metadata(tables) -> None:
    assert len(tables.bronze) == 1000
    assert tables.bronze["source_row"].tolist() == list(range(2, 1002))
    assert tables.bronze["source_file"].unique().tolist() == ["service_requests.csv"]
    assert tables.bronze["ingestion_batch_id"].unique().tolist() == ["292ed8fb2857e392"]


def test_silver_reconciles_valid_and_rejected_rows(tables) -> None:
    assert len(tables.silver_valid) == 989
    assert len(tables.silver_rejected) == 11
    assert len(tables.silver_valid) + len(tables.silver_rejected) == len(tables.bronze)
    assert tables.silver_valid["ticket_id"].is_unique
    assert tables.silver_rejected["rejection_reasons"].notna().all()
    assert tables.silver_valid["created_at"].dt.tz is not None
    assert str(tables.silver_valid["escalated"].dtype) == "boolean"


def test_gold_star_schema_has_complete_foreign_keys(tables) -> None:
    fact = tables.fact_service_requests
    assert len(fact) == 989
    assert fact["ticket_id"].is_unique
    assert set(fact["team_key"]).issubset(set(tables.dim_team["team_key"]))
    assert set(fact["category_key"]).issubset(set(tables.dim_category["category_key"]))
    assert set(fact["priority_key"]).issubset(set(tables.dim_priority["priority_key"]))
    assert set(fact["created_date_key"]).issubset(set(tables.dim_date["date_key"]))
    assert set(fact["closed_date_key"].dropna().astype(int)).issubset(
        set(tables.dim_date["date_key"])
    )


def test_manifest_and_kpis_match_verified_controls(tables) -> None:
    assert tables.manifest["row_counts"] == EXPECTED_ROW_COUNTS
    assert tables.manifest["controls"] == {
        "bronze_equals_valid_plus_rejected": True,
        "foreign_keys_complete": True,
        "valid_equals_fact": True,
    }
    assert tables.manifest["kpis"] == EXPECTED_KPIS


def test_operational_baseline_stays_within_documented_ranges(tables) -> None:
    kpis = tables.manifest["kpis"]
    assert 0.93 <= kpis["sla_compliance_rate"] <= 0.96
    assert 0.05 <= kpis["reopen_rate"] <= 0.09
    assert 0.07 <= kpis["escalation_rate"] <= 0.12
    assert 0.10 <= kpis["open_backlog_rate"] <= 0.18
    assert kpis["reopen_eligible_requests"] == kpis["closed_requests"]
    assert (
        tables.silver_valid.loc[tables.silver_valid["status"].eq("open"), "reopened_count"]
        .eq(0)
        .all()
    )


def test_committed_text_evidence_matches_generated_tables(tables) -> None:
    committed_manifest = json.loads(EVIDENCE_MANIFEST.read_text(encoding="utf-8"))
    committed_kpis = pd.read_csv(EVIDENCE_KPIS)
    assert tables.manifest == committed_manifest
    pd.testing.assert_frame_equal(tables.kpis, committed_kpis, check_dtype=False)


def test_write_medallion_persists_all_layers(tables, tmp_path: Path) -> None:
    output_dir = tmp_path / "lakehouse"
    manifest_path = write_medallion(tables, output_dir)
    expected_paths = [
        output_dir / "bronze/service_requests.parquet",
        output_dir / "silver/service_requests_valid.parquet",
        output_dir / "silver/service_requests_rejected.parquet",
        output_dir / "silver/service_request_issues.parquet",
        output_dir / "gold/fact_service_requests.parquet",
        output_dir / "gold/dim_date.parquet",
        output_dir / "gold/dim_team.parquet",
        output_dir / "gold/dim_category.parquet",
        output_dir / "gold/dim_priority.parquet",
        output_dir / "gold/service_operations_kpis.csv",
        manifest_path,
    ]
    assert all(path.is_file() for path in expected_paths)
    assert len(pd.read_parquet(output_dir / "bronze/service_requests.parquet")) == 1000
    assert len(pd.read_parquet(output_dir / "silver/service_requests_valid.parquet")) == 989
    assert len(pd.read_parquet(output_dir / "gold/fact_service_requests.parquet")) == 989
    assert json.loads(manifest_path.read_text(encoding="utf-8")) == tables.manifest
