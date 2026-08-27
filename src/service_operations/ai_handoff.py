"""Build a governed, deterministic snapshot for downstream AI orchestration."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd
from jsonschema import Draft202012Validator

HANDOFF_SCHEMA_VERSION = "1.0.0"
HANDOFF_CONTRACT_VERSION = "2.0.0"
PRODUCER_VERSION = "0.4.0"
SOURCE_REPOSITORY = "https://github.com/DataTideHH/fabric-service-operations-analytics"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _percent(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        raise ValueError("SLA denominator must be positive.")
    return round(numerator * 100 / denominator, 2)


def _metric(metric_contract: dict[str, Any], name: str) -> dict[str, Any]:
    matches = [metric for metric in metric_contract["metrics"] if metric["name"] == name]
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one metric contract entry for {name}.")
    return matches[0]


def build_ai_handoff(
    analytics_manifest_path: Path | str,
    team_evidence_path: Path | str,
    metric_contract_path: Path | str,
    *,
    source_revision: str,
    period_start: date,
    period_end: date,
) -> dict[str, Any]:
    """Build and reconcile the downstream AI snapshot from committed analytics evidence."""
    manifest_path = Path(analytics_manifest_path)
    team_path = Path(team_evidence_path)
    contract_path = Path(metric_contract_path)
    manifest = _read_json(manifest_path)
    metric_contract = _read_json(contract_path)
    teams = pd.read_csv(team_path)

    if not source_revision or len(source_revision) != 40:
        raise ValueError("source_revision must be a full 40-character Git commit SHA.")
    if period_end < period_start:
        raise ValueError("Reporting-period end must not precede its start.")
    if not all(manifest["controls"].values()):
        raise ValueError("Analytics manifest contains a failed reconciliation control.")

    global_kpis = manifest["global_kpis"]
    eligible = int(global_kpis["closed_requests"])
    within_sla = int(global_kpis["sla_met_requests"])
    breaches = int(global_kpis["sla_breaches"])
    if within_sla + breaches != eligible:
        raise ValueError("Global SLA counts do not reconcile.")

    team_eligible = int(teams["closed_requests"].sum())
    team_within_sla = int(teams["sla_met_requests"].sum())
    team_breaches = int(teams["sla_breaches"].sum())
    if (team_eligible, team_within_sla, team_breaches) != (eligible, within_sla, breaches):
        raise ValueError("Team SLA counts do not reconcile to the global population.")

    groups = []
    for row in teams.itertuples(index=False):
        group_eligible = int(row.closed_requests)
        group_within_sla = int(row.sla_met_requests)
        group_breaches = int(row.sla_breaches)
        if group_within_sla + group_breaches != group_eligible:
            raise ValueError(f"SLA counts do not reconcile for team {row.assigned_team}.")
        groups.append(
            {
                "group": str(row.assigned_team),
                "eligibleOperations": group_eligible,
                "withinSlaOperations": group_within_sla,
                "breachedOperations": group_breaches,
                "slaAttainmentRatePercent": _percent(group_within_sla, group_eligible),
                "slaBreachRatePercent": _percent(group_breaches, group_eligible),
            }
        )
    groups.sort(key=lambda group: (-group["slaBreachRatePercent"], group["group"]))

    compliance_metric = _metric(metric_contract, "sla_compliance_rate")
    breach_metric = _metric(metric_contract, "sla_breach_rate")
    period_label = f"{period_start.isoformat()}/{period_end.isoformat()}"
    return {
        "schemaVersion": HANDOFF_SCHEMA_VERSION,
        "contractVersion": HANDOFF_CONTRACT_VERSION,
        "snapshotId": f"fsoa-{period_start.isoformat()}-{period_end.isoformat()}-v1",
        "asOfDate": period_end.isoformat(),
        "reportingPeriod": {
            "startDate": period_start.isoformat(),
            "endDate": period_end.isoformat(),
            "label": period_label,
        },
        "producer": {
            "application": "fabric-service-operations-analytics",
            "version": PRODUCER_VERSION,
        },
        "source": {
            "repository": SOURCE_REPOSITORY,
            "revision": source_revision,
            "scenario": "deterministic-synthetic-service-operations",
            "ingestionBatchId": manifest["source_ingestion_batch_id"],
            "resourceFingerprints": {
                "analytics/metric_contract.json": _sha256(contract_path),
                "evidence/analytics_manifest.json": _sha256(manifest_path),
                "evidence/sla_by_team.csv": _sha256(team_path),
            },
        },
        "metric": {
            "name": "sla_attainment_rate",
            "definition": "sla_met_requests / closed_requests",
            "eligiblePopulation": compliance_metric["eligible_population"],
            "breachDefinition": "sla_breaches / closed_requests",
            "breachEligiblePopulation": breach_metric["eligible_population"],
        },
        "overall": {
            "eligibleOperations": eligible,
            "withinSlaOperations": within_sla,
            "breachedOperations": breaches,
            "slaAttainmentRatePercent": _percent(within_sla, eligible),
            "slaBreachRatePercent": _percent(breaches, eligible),
        },
        "comparisonDimension": "assigned_team",
        "groups": groups,
        "interpretationBoundary": {
            "supportedInterpretations": [
                "Describe observed SLA attainment and breach rates in this snapshot.",
                "Compare resolver teams using the same governed metric definition.",
                "Identify the highest or lowest observed rate when the metric is explicit.",
            ],
            "unsupportedInterpretations": [
                metric_contract["interpretation_boundary"],
                "Predict future performance from this snapshot.",
                "Infer individual or team quality, effort, or accountability.",
                "Treat 'worst' as well-defined when the comparison metric is not stated.",
            ],
            "requiredLanguage": "Use observational language such as 'the snapshot shows'; explicitly say when causality or an ambiguous ranking is not supported.",
        },
    }


def validate_ai_handoff(snapshot: dict[str, Any], schema_path: Path | str) -> None:
    """Validate a handoff snapshot against the repository-owned JSON Schema."""
    schema = _read_json(Path(schema_path))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(
        schema,
        format_checker=Draft202012Validator.FORMAT_CHECKER,
    ).validate(snapshot)


def write_ai_handoff(
    snapshot: dict[str, Any],
    output_path: Path | str,
    schema_path: Path | str,
) -> Path:
    """Validate and write stable UTF-8 JSON bytes."""
    validate_ai_handoff(snapshot, schema_path)
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(snapshot, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return destination
