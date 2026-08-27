import copy
import json
from datetime import date
from pathlib import Path

import pytest

from service_operations.ai_handoff import (
    build_ai_handoff,
    validate_ai_handoff,
    write_ai_handoff,
)

ANALYTICS_MANIFEST = Path("evidence/analytics_manifest.json")
TEAM_EVIDENCE = Path("evidence/sla_by_team.csv")
METRIC_CONTRACT = Path("analytics/metric_contract.json")
SCHEMA = Path("contracts/ai-service-operations-snapshot.schema.json")
COMMITTED_HANDOFF = Path("evidence/ai_service_operations_snapshot.json")
SOURCE_REVISION = "0a6c4ebffe366d7133215634d836a5d9b102e7fb"


def _snapshot() -> dict:
    return build_ai_handoff(
        ANALYTICS_MANIFEST,
        TEAM_EVIDENCE,
        METRIC_CONTRACT,
        source_revision=SOURCE_REVISION,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 3, 31),
    )


def test_ai_handoff_reconciles_and_preserves_metric_semantics() -> None:
    snapshot = _snapshot()

    assert snapshot["contractVersion"] == "2.0.0"
    assert snapshot["overall"] == {
        "eligibleOperations": 833,
        "withinSlaOperations": 799,
        "breachedOperations": 34,
        "slaAttainmentRatePercent": 95.92,
        "slaBreachRatePercent": 4.08,
    }
    assert snapshot["comparisonDimension"] == "assigned_team"
    assert snapshot["groups"][0] == {
        "group": "network_ops",
        "eligibleOperations": 129,
        "withinSlaOperations": 120,
        "breachedOperations": 9,
        "slaAttainmentRatePercent": 93.02,
        "slaBreachRatePercent": 6.98,
    }
    assert len(snapshot["source"]["resourceFingerprints"]) == 3
    assert all(len(digest) == 64 for digest in snapshot["source"]["resourceFingerprints"].values())
    validate_ai_handoff(snapshot, SCHEMA)


def test_committed_ai_handoff_matches_generated_evidence() -> None:
    assert _snapshot() == json.loads(COMMITTED_HANDOFF.read_text(encoding="utf-8"))


def test_ai_handoff_rejects_non_reconciling_team_population(tmp_path: Path) -> None:
    manifest = json.loads(ANALYTICS_MANIFEST.read_text(encoding="utf-8"))
    tampered = copy.deepcopy(manifest)
    tampered["global_kpis"]["closed_requests"] += 1
    tampered["global_kpis"]["sla_met_requests"] += 1
    tampered_path = tmp_path / "analytics_manifest.json"
    tampered_path.write_text(json.dumps(tampered), encoding="utf-8")

    with pytest.raises(ValueError, match="Team SLA counts do not reconcile"):
        build_ai_handoff(
            tampered_path,
            TEAM_EVIDENCE,
            METRIC_CONTRACT,
            source_revision=SOURCE_REVISION,
            period_start=date(2026, 1, 1),
            period_end=date(2026, 3, 31),
        )


def test_write_ai_handoff_uses_stable_json(tmp_path: Path) -> None:
    output = write_ai_handoff(_snapshot(), tmp_path / "handoff.json", SCHEMA)

    assert output.read_bytes().endswith(b"\n")
    assert json.loads(output.read_text(encoding="utf-8")) == _snapshot()
