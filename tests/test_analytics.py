import json
from pathlib import Path

import pandas as pd
import pytest

from service_operations.analytics import build_analytics, write_analytics
from service_operations.generator import generate_dataframe, write_dataset
from service_operations.medallion import build_medallion, write_medallion

CONTRACT_PATH = Path("contracts/service_requests.contract.json")
SQL_DIR = Path("analytics/sql")
EVIDENCE_MANIFEST = Path("evidence/analytics_manifest.json")
EVIDENCE_TEAM = Path("evidence/sla_by_team.csv")
EVIDENCE_CATEGORY = Path("evidence/sla_by_category.csv")
EVIDENCE_PRIORITY = Path("evidence/sla_by_priority.csv")

EXPECTED_ROW_COUNTS = {
    "service_requests_enriched": 989,
    "sla_by_team": 5,
    "sla_by_category": 5,
    "sla_by_priority": 4,
    "sla_by_team_category": 15,
    "daily_service_operations": 90,
    "sla_breach_details": 34,
}

EXPECTED_GLOBAL_KPIS = {
    "total_requests": 989,
    "closed_requests": 833,
    "sla_met_requests": 799,
    "sla_breaches": 34,
    "sla_compliance_rate": 0.9592,
    "reopened_requests": 48,
    "reopen_rate": 0.0576,
    "escalated_requests": 85,
    "escalation_rate": 0.0859,
    "open_backlog": 156,
    "open_backlog_rate": 0.1577,
}


@pytest.fixture(scope="module")
def medallion_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("analytics-medallion")
    source_path = write_dataset(generate_dataframe(), root / "service_requests.csv")
    tables = build_medallion(source_path, CONTRACT_PATH)
    write_medallion(tables, root / "medallion")
    return root / "medallion"


@pytest.fixture(scope="module")
def tables(medallion_dir: Path):
    return build_analytics(medallion_dir, SQL_DIR)


def test_analytics_manifest_reconciles_to_gold(tables) -> None:
    assert tables.manifest["row_counts"] == EXPECTED_ROW_COUNTS
    assert tables.manifest["global_kpis"] == EXPECTED_GLOBAL_KPIS
    assert all(tables.manifest["controls"].values())


def test_sla_breach_detail_population_is_exact(tables) -> None:
    breaches = tables.sla_breach_details

    assert len(breaches) == 34
    assert breaches["status"].eq("closed").all()
    assert breaches["resolution_overrun_minutes"].gt(0).all()
    assert set(breaches["assigned_team"]) <= {
        "business_apps",
        "data_platform",
        "network_ops",
        "service_desk",
        "workplace",
    }


def test_team_summary_uses_explicit_denominators(tables) -> None:
    team = tables.sla_by_team.set_index("assigned_team")

    assert int(team["closed_requests"].sum()) == 833
    assert int(team["sla_met_requests"].sum()) == 799
    assert int(team["sla_breaches"].sum()) == 34
    assert team.loc["network_ops", "sla_compliance_rate"] == pytest.approx(0.9302)
    assert team.loc["workplace", "sla_compliance_rate"] == pytest.approx(0.9932)


def test_category_and_priority_summaries_expose_concentration(tables) -> None:
    category = tables.sla_by_category.set_index("category")
    priority = tables.sla_by_priority.set_index("priority")

    assert category.loc["application", "sla_breaches"] == 16
    assert category.loc["network", "sla_breach_rate"] == pytest.approx(0.0857)
    assert priority.loc["P1", "sla_breach_rate"] == pytest.approx(0.1818)
    assert priority.loc["P3", "sla_breaches"] == 17


def test_daily_and_team_category_marts_reconcile(tables) -> None:
    assert int(tables.daily_service_operations["total_requests"].sum()) == 989
    assert int(tables.daily_service_operations["sla_breaches"].sum()) == 34
    assert int(tables.sla_by_team_category["closed_requests"].sum()) == 833
    assert int(tables.sla_by_team_category["sla_breaches"].sum()) == 34


def test_committed_analytics_evidence_matches_generated_tables(tables) -> None:
    committed_manifest = json.loads(EVIDENCE_MANIFEST.read_text(encoding="utf-8"))
    committed_team = pd.read_csv(EVIDENCE_TEAM)
    committed_category = pd.read_csv(EVIDENCE_CATEGORY)
    committed_priority = pd.read_csv(EVIDENCE_PRIORITY)

    assert tables.manifest == committed_manifest
    pd.testing.assert_frame_equal(tables.sla_by_team, committed_team, check_dtype=False)
    pd.testing.assert_frame_equal(tables.sla_by_category, committed_category, check_dtype=False)
    pd.testing.assert_frame_equal(tables.sla_by_priority, committed_priority, check_dtype=False)


def test_write_analytics_persists_all_marts(tables, tmp_path: Path) -> None:
    manifest_path = write_analytics(tables, tmp_path / "analytics")
    expected = [
        "service_requests_enriched.parquet",
        "sla_by_team.parquet",
        "sla_by_category.parquet",
        "sla_by_priority.parquet",
        "sla_by_team_category.parquet",
        "daily_service_operations.parquet",
        "sla_breach_details.parquet",
        "sla_by_team.csv",
        "sla_by_category.csv",
        "sla_by_priority.csv",
        "analytics_manifest.json",
    ]

    assert all((tmp_path / "analytics" / name).is_file() for name in expected)
    assert json.loads(manifest_path.read_text(encoding="utf-8")) == tables.manifest
