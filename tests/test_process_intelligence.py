"""Tests for the deterministic process-intelligence layer."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from service_operations.generator import generate_dataframe, write_dataset
from service_operations.medallion import build_medallion
from service_operations.process_intelligence import (
    EVENT_ORIGIN,
    build_process_intelligence,
    write_process_intelligence,
)

CONTRACT_PATH = Path("contracts/service_requests.contract.json")


def _build_baseline(tmp_path: Path):
    source_path = write_dataset(
        generate_dataframe(),
        tmp_path / "service_requests.csv",
    )
    medallion = build_medallion(source_path, CONTRACT_PATH)
    return build_process_intelligence(medallion.silver_valid)


def test_process_intelligence_reconciles_baseline(tmp_path: Path) -> None:
    tables = _build_baseline(tmp_path)

    assert tables.manifest["event_origin"] == EVENT_ORIGIN
    assert tables.manifest["row_counts"] == {
        "cases": 989,
        "events": 3831,
        "variants": 7,
        "transitions": 7,
        "bottlenecks": 7,
        "exception_paths": 3,
    }
    assert tables.manifest["case_counts"] == {
        "closed": 833,
        "open": 156,
        "escalated": 85,
        "reopened": 48,
        "reopen_occurrences": 51,
    }
    assert all(tables.manifest["controls"].values())

    assert tables.event_log["event_id"].is_unique
    assert int(tables.event_log["activity"].eq("reopened").sum()) == 51
    assert int(tables.event_log["activity"].eq("escalated").sum()) == 85
    assert tables.cases["case_id"].nunique() == 989


def test_variants_bottlenecks_and_exception_paths_are_reviewable(
    tmp_path: Path,
) -> None:
    tables = _build_baseline(tmp_path)

    leading_variant = tables.variants.iloc[0]
    assert leading_variant["case_count"] == 714
    assert leading_variant["process_variant"] == (
        "ticket_created > team_assigned > resolution_recorded > ticket_closed"
    )

    leading_bottleneck = tables.bottlenecks.iloc[0]
    assert leading_bottleneck["source_activity"] == "team_assigned"
    assert leading_bottleneck["target_activity"] == "resolution_recorded"
    assert leading_bottleneck["case_count"] == 758
    assert leading_bottleneck["average_wait_minutes"] == 712.59

    exception_counts = tables.exception_paths.set_index("exception_type")["case_count"].to_dict()
    assert exception_counts == {
        "escalated_only": 81,
        "reopened_only": 44,
        "escalated_and_reopened": 4,
    }


def test_process_outputs_and_manifest_are_written(tmp_path: Path) -> None:
    tables = _build_baseline(tmp_path)
    output_dir = tmp_path / "process-intelligence"

    manifest_path = write_process_intelligence(tables, output_dir)
    written_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert written_manifest == tables.manifest
    for filename in [
        "event_log.parquet",
        "process_cases.parquet",
        "process_variants.parquet",
        "transition_performance.parquet",
        "bottlenecks.parquet",
        "exception_paths.parquet",
        "event_log.csv",
        "process_cases.csv",
        "process_variants.csv",
        "transition_performance.csv",
        "bottlenecks.csv",
        "exception_paths.csv",
    ]:
        assert (output_dir / filename).is_file()

    written_variants = pd.read_csv(output_dir / "process_variants.csv")
    pd.testing.assert_frame_equal(
        written_variants,
        tables.variants,
        check_dtype=False,
    )


def test_process_intelligence_rejects_incomplete_or_empty_sources() -> None:
    with pytest.raises(ValueError, match="at least one valid case"):
        build_process_intelligence(pd.DataFrame())

    with pytest.raises(ValueError, match="missing columns"):
        build_process_intelligence(pd.DataFrame([{"ticket_id": "SR-1"}]))
