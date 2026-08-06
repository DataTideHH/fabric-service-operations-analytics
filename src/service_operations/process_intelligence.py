"""Build a deterministic process-intelligence layer from valid service requests."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from service_operations.medallion import build_medallion

PROCESS_INTELLIGENCE_VERSION = "0.1.0"
EVENT_ORIGIN = "derived_synthetic_scenario"
MIN_BOTTLENECK_CASES = 10


@dataclass(frozen=True)
class ProcessIntelligenceTables:
    """In-memory event-log, case, variant and transition outputs."""

    event_log: pd.DataFrame
    cases: pd.DataFrame
    variants: pd.DataFrame
    transitions: pd.DataFrame
    bottlenecks: pd.DataFrame
    exception_paths: pd.DataFrame
    manifest: dict[str, Any]


def _fraction_timestamp(start: pd.Timestamp, end: pd.Timestamp, fraction: float) -> pd.Timestamp:
    return start + ((end - start) * fraction)


def _case_events(record: Any) -> list[tuple[str, pd.Timestamp, int]]:
    created_at = record.created_at
    events: list[tuple[str, pd.Timestamp, int]] = [("ticket_created", created_at, 0)]

    if record.status == "closed":
        closed_at = record.closed_at
        duration_minutes = (closed_at - created_at).total_seconds() / 60
        assigned_minutes = min(15, max(1, round(duration_minutes * 0.05)))
        events.append(("team_assigned", created_at + pd.Timedelta(minutes=assigned_minutes), 1))

        reopened_count = int(record.reopened_count)
        if bool(record.escalated):
            escalation_fraction = 0.30 if reopened_count else 0.45
            events.append(
                ("escalated", _fraction_timestamp(created_at, closed_at, escalation_fraction), 2)
            )

        if reopened_count == 1:
            events.extend(
                [
                    (
                        "resolution_recorded",
                        _fraction_timestamp(created_at, closed_at, 0.58),
                        3,
                    ),
                    ("reopened", _fraction_timestamp(created_at, closed_at, 0.68), 4),
                ]
            )
        elif reopened_count == 2:
            events.extend(
                [
                    (
                        "resolution_recorded",
                        _fraction_timestamp(created_at, closed_at, 0.38),
                        3,
                    ),
                    ("reopened", _fraction_timestamp(created_at, closed_at, 0.47), 4),
                    (
                        "resolution_recorded",
                        _fraction_timestamp(created_at, closed_at, 0.68),
                        5,
                    ),
                    ("reopened", _fraction_timestamp(created_at, closed_at, 0.76), 6),
                ]
            )

        events.extend(
            [
                (
                    "resolution_recorded",
                    _fraction_timestamp(created_at, closed_at, 0.90),
                    7,
                ),
                ("ticket_closed", closed_at, 8),
            ]
        )
    else:
        assigned_minutes = min(15, max(1, round(int(record.sla_target_minutes) * 0.05)))
        events.append(("team_assigned", created_at + pd.Timedelta(minutes=assigned_minutes), 1))
        if bool(record.escalated):
            escalation_minutes = max(
                assigned_minutes + 1,
                round(int(record.sla_target_minutes) * 0.75),
            )
            events.append(("escalated", created_at + pd.Timedelta(minutes=escalation_minutes), 2))

    return sorted(events, key=lambda event: (event[1], event[2]))


def _build_event_log(valid: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    for record in valid.itertuples(index=False):
        base = {
            "case_id": record.ticket_id,
            "assigned_team": record.assigned_team,
            "category": record.category,
            "priority": record.priority,
            "customer_segment": record.customer_segment,
            "status": record.status,
            "sla_met": record.sla_met,
            "escalated_case": bool(record.escalated),
            "reopened_count": int(record.reopened_count),
            "event_origin": EVENT_ORIGIN,
        }
        for event_index, (activity, event_timestamp, _) in enumerate(
            _case_events(record),
            start=1,
        ):
            rows.append(
                {
                    "event_id": f"{record.ticket_id}-E{event_index:02d}",
                    **base,
                    "event_index": event_index,
                    "activity": activity,
                    "event_timestamp": event_timestamp,
                }
            )

    return pd.DataFrame(rows).sort_values(
        ["case_id", "event_index"],
        ignore_index=True,
    )


def _exception_type(escalated: bool, reopened_count: int) -> str:
    if escalated and reopened_count:
        return "escalated_and_reopened"
    if reopened_count:
        return "reopened_only"
    if escalated:
        return "escalated_only"
    return "standard"


def _build_cases(valid: pd.DataFrame, event_log: pd.DataFrame) -> pd.DataFrame:
    event_summary = (
        event_log.groupby("case_id", sort=True)
        .agg(
            event_count=("event_id", "size"),
            first_event_at=("event_timestamp", "min"),
            last_event_at=("event_timestamp", "max"),
            process_variant=("activity", lambda values: " > ".join(values)),
        )
        .reset_index()
    )
    event_summary["observed_span_minutes"] = (
        (event_summary["last_event_at"] - event_summary["first_event_at"])
        .dt.total_seconds()
        .div(60)
        .round(2)
    )

    cases = valid.loc[
        :,
        [
            "ticket_id",
            "assigned_team",
            "category",
            "priority",
            "customer_segment",
            "status",
            "sla_target_minutes",
            "resolution_minutes",
            "reopened_count",
            "escalated",
            "sla_met",
        ],
    ].rename(columns={"ticket_id": "case_id", "escalated": "escalated_case"})
    cases = cases.merge(event_summary, on="case_id", how="left", validate="one_to_one")
    cases["throughput_minutes"] = cases["resolution_minutes"].astype("Float64")
    cases["exception_type"] = [
        _exception_type(bool(escalated), int(reopened))
        for escalated, reopened in zip(
            cases["escalated_case"],
            cases["reopened_count"],
            strict=True,
        )
    ]
    return cases.drop(columns=["resolution_minutes"]).sort_values(
        "case_id",
        ignore_index=True,
    )


def _rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def _build_variants(cases: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for variant, group in cases.groupby("process_variant", sort=True):
        closed = group.loc[group["status"].eq("closed")]
        breach_count = int(closed["sla_met"].eq(False).sum())
        rows.append(
            {
                "process_variant": variant,
                "case_count": len(group),
                "case_share": _rate(len(group), len(cases)),
                "closed_cases": len(closed),
                "open_cases": int(group["status"].eq("open").sum()),
                "exception_cases": int(group["exception_type"].ne("standard").sum()),
                "average_throughput_minutes": (
                    round(float(closed["throughput_minutes"].mean()), 2)
                    if not closed.empty
                    else None
                ),
                "sla_breach_rate": _rate(breach_count, len(closed)),
            }
        )

    return pd.DataFrame(rows).sort_values(
        ["case_count", "process_variant"],
        ascending=[False, True],
        ignore_index=True,
    )


def _build_transitions(event_log: pd.DataFrame) -> pd.DataFrame:
    ordered = event_log.sort_values(["case_id", "event_index"]).copy()
    ordered["target_activity"] = ordered.groupby("case_id")["activity"].shift(-1)
    ordered["target_timestamp"] = ordered.groupby("case_id")["event_timestamp"].shift(-1)
    ordered = ordered.loc[ordered["target_activity"].notna()].copy()
    ordered["wait_minutes"] = (
        (ordered["target_timestamp"] - ordered["event_timestamp"]).dt.total_seconds().div(60)
    )

    rows: list[dict[str, Any]] = []
    for (source, target), group in ordered.groupby(
        ["activity", "target_activity"],
        sort=True,
    ):
        rows.append(
            {
                "source_activity": source,
                "target_activity": target,
                "case_count": len(group),
                "average_wait_minutes": round(float(group["wait_minutes"].mean()), 2),
                "median_wait_minutes": round(float(group["wait_minutes"].median()), 2),
                "p90_wait_minutes": round(float(group["wait_minutes"].quantile(0.90)), 2),
            }
        )

    return pd.DataFrame(rows).sort_values(
        ["case_count", "source_activity", "target_activity"],
        ascending=[False, True, True],
        ignore_index=True,
    )


def _build_bottlenecks(transitions: pd.DataFrame) -> pd.DataFrame:
    candidates = transitions.loc[transitions["case_count"] >= MIN_BOTTLENECK_CASES].copy()
    candidates = candidates.sort_values(
        ["average_wait_minutes", "case_count", "source_activity", "target_activity"],
        ascending=[False, False, True, True],
        ignore_index=True,
    )
    candidates.insert(0, "bottleneck_rank", range(1, len(candidates) + 1))
    candidates["interpretation_boundary"] = (
        "Derived synthetic waiting time; concentration signal, not causal root cause."
    )
    return candidates


def _build_exception_paths(cases: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "exception_type",
        "case_count",
        "closed_cases",
        "open_cases",
        "average_throughput_minutes",
        "sla_breach_rate",
        "reopen_occurrences",
    ]
    exception_cases = cases.loc[cases["exception_type"].ne("standard")]
    rows: list[dict[str, Any]] = []
    for exception_type, group in exception_cases.groupby("exception_type", sort=True):
        closed = group.loc[group["status"].eq("closed")]
        breach_count = int(closed["sla_met"].eq(False).sum())
        rows.append(
            {
                "exception_type": exception_type,
                "case_count": len(group),
                "closed_cases": len(closed),
                "open_cases": int(group["status"].eq("open").sum()),
                "average_throughput_minutes": (
                    round(float(closed["throughput_minutes"].mean()), 2)
                    if not closed.empty
                    else None
                ),
                "sla_breach_rate": _rate(breach_count, len(closed)),
                "reopen_occurrences": int(group["reopened_count"].sum()),
            }
        )
    if not rows:
        return pd.DataFrame(columns=columns)
    return pd.DataFrame(rows, columns=columns).sort_values(
        ["case_count", "exception_type"],
        ascending=[False, True],
        ignore_index=True,
    )


def _event_indexes_contiguous(event_log: pd.DataFrame) -> bool:
    for indexes in event_log.groupby("case_id")["event_index"]:
        values = indexes[1].astype(int).tolist()
        if values != list(range(1, len(values) + 1)):
            return False
    return True


def _timestamps_monotonic(event_log: pd.DataFrame) -> bool:
    return all(
        group["event_timestamp"].is_monotonic_increasing
        for _, group in event_log.groupby("case_id", sort=False)
    )


def _build_manifest(
    valid: pd.DataFrame,
    event_log: pd.DataFrame,
    cases: pd.DataFrame,
    variants: pd.DataFrame,
    transitions: pd.DataFrame,
    bottlenecks: pd.DataFrame,
    exception_paths: pd.DataFrame,
) -> dict[str, Any]:
    first_activities = event_log.groupby("case_id")["activity"].first()
    last_activities = event_log.groupby("case_id")["activity"].last()
    closed_case_ids = set(cases.loc[cases["status"].eq("closed"), "case_id"])
    open_case_ids = set(cases.loc[cases["status"].eq("open"), "case_id"])

    controls = {
        "case_count_matches_valid_source": len(cases) == len(valid),
        "event_ids_unique": event_log["event_id"].is_unique,
        "event_indexes_contiguous": _event_indexes_contiguous(event_log),
        "event_timestamps_monotonic": _timestamps_monotonic(event_log),
        "first_activity_is_ticket_created": first_activities.eq("ticket_created").all(),
        "closed_cases_end_with_ticket_closed": last_activities.loc[sorted(closed_case_ids)]
        .eq("ticket_closed")
        .all(),
        "open_cases_do_not_end_with_ticket_closed": last_activities.loc[sorted(open_case_ids)]
        .ne("ticket_closed")
        .all(),
        "reopened_events_reconcile": int(event_log["activity"].eq("reopened").sum())
        == int(valid["reopened_count"].sum()),
        "escalation_events_reconcile": int(event_log["activity"].eq("escalated").sum())
        == int(valid["escalated"].sum()),
        "closed_throughput_matches_source": all(
            float(case.throughput_minutes)
            == float(valid.set_index("ticket_id").loc[case.case_id, "resolution_minutes"])
            for case in cases.loc[cases["status"].eq("closed")].itertuples(index=False)
        ),
    }

    controls = {name: bool(passed) for name, passed in controls.items()}

    return {
        "process_intelligence_version": PROCESS_INTELLIGENCE_VERSION,
        "event_origin": EVENT_ORIGIN,
        "interpretation_boundary": (
            "Event timestamps between ticket creation and closure are deterministic scenario "
            "derivations. The outputs support process-analysis practice but do not represent "
            "observed production history or causal root-cause evidence."
        ),
        "row_counts": {
            "cases": len(cases),
            "events": len(event_log),
            "variants": len(variants),
            "transitions": len(transitions),
            "bottlenecks": len(bottlenecks),
            "exception_paths": len(exception_paths),
        },
        "case_counts": {
            "closed": int(cases["status"].eq("closed").sum()),
            "open": int(cases["status"].eq("open").sum()),
            "escalated": int(cases["escalated_case"].sum()),
            "reopened": int(cases["reopened_count"].gt(0).sum()),
            "reopen_occurrences": int(cases["reopened_count"].sum()),
        },
        "controls": controls,
    }


def build_process_intelligence(valid: pd.DataFrame) -> ProcessIntelligenceTables:
    """Build deterministic process-intelligence outputs from typed valid records."""
    required = {
        "ticket_id",
        "created_at",
        "closed_at",
        "assigned_team",
        "category",
        "priority",
        "customer_segment",
        "status",
        "sla_target_minutes",
        "resolution_minutes",
        "reopened_count",
        "escalated",
        "sla_met",
    }
    if valid.empty:
        raise ValueError("Process-intelligence source must contain at least one valid case.")
    missing = sorted(required.difference(valid.columns))
    if missing:
        raise ValueError(f"Process-intelligence source is missing columns: {', '.join(missing)}")

    event_log = _build_event_log(valid)
    cases = _build_cases(valid, event_log)
    variants = _build_variants(cases)
    transitions = _build_transitions(event_log)
    bottlenecks = _build_bottlenecks(transitions)
    exception_paths = _build_exception_paths(cases)
    manifest = _build_manifest(
        valid,
        event_log,
        cases,
        variants,
        transitions,
        bottlenecks,
        exception_paths,
    )
    if not all(manifest["controls"].values()):
        failed = [name for name, passed in manifest["controls"].items() if not passed]
        raise ValueError(f"Process-intelligence controls failed: {', '.join(failed)}")

    return ProcessIntelligenceTables(
        event_log=event_log,
        cases=cases,
        variants=variants,
        transitions=transitions,
        bottlenecks=bottlenecks,
        exception_paths=exception_paths,
        manifest=manifest,
    )


def write_process_intelligence(
    tables: ProcessIntelligenceTables,
    output_dir: Path | str,
) -> Path:
    """Write process-intelligence Parquet, CSV and manifest outputs."""
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)

    parquet_outputs = {
        "event_log.parquet": tables.event_log,
        "process_cases.parquet": tables.cases,
        "process_variants.parquet": tables.variants,
        "transition_performance.parquet": tables.transitions,
        "bottlenecks.parquet": tables.bottlenecks,
        "exception_paths.parquet": tables.exception_paths,
    }
    for filename, dataframe in parquet_outputs.items():
        dataframe.to_parquet(destination / filename, index=False)

    csv_outputs = {
        "event_log.csv": tables.event_log,
        "process_cases.csv": tables.cases,
        "process_variants.csv": tables.variants,
        "transition_performance.csv": tables.transitions,
        "bottlenecks.csv": tables.bottlenecks,
        "exception_paths.csv": tables.exception_paths,
    }
    for filename, dataframe in csv_outputs.items():
        dataframe.to_csv(destination / filename, index=False, lineterminator="\n")

    manifest_path = destination / "process_intelligence_manifest.json"
    manifest_path.write_text(
        json.dumps(tables.manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest_path


def run_process_intelligence(
    input_path: Path | str,
    contract_path: Path | str,
    output_dir: Path | str,
) -> Path:
    """Build the validated Silver population and publish process outputs."""
    medallion = build_medallion(input_path, contract_path)
    tables = build_process_intelligence(medallion.silver_valid)
    return write_process_intelligence(tables, output_dir)
