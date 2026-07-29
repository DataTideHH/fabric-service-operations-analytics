"""Generate a deterministic synthetic service-operations CSV fixture."""

from __future__ import annotations

import argparse
import random
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd

SEED = 20260729
DEFAULT_RECORD_COUNT = 1000
ANOMALY_COUNT = 10
ANALYSIS_WINDOW_DAYS = 90

COLUMNS = [
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

PRIORITY_SLA = {"P1": 240, "P2": 480, "P3": 1440, "P4": 2880}
CATEGORIES = ["access", "application", "hardware", "network", "reporting"]
SEGMENTS = ["enterprise", "internal", "smb"]

CATEGORY_WEIGHTS = [28, 26, 16, 18, 12]
CATEGORY_PRIORITY_WEIGHTS = {
    "access": [1, 10, 55, 34],
    "application": [4, 25, 55, 16],
    "hardware": [1, 15, 50, 34],
    "network": [8, 32, 48, 12],
    "reporting": [1, 8, 55, 36],
}
CATEGORY_TEAM_WEIGHTS = {
    "access": {
        "business_apps": 10,
        "data_platform": 0,
        "network_ops": 0,
        "service_desk": 65,
        "workplace": 25,
    },
    "application": {
        "business_apps": 70,
        "data_platform": 15,
        "network_ops": 0,
        "service_desk": 15,
        "workplace": 0,
    },
    "hardware": {
        "business_apps": 0,
        "data_platform": 0,
        "network_ops": 10,
        "service_desk": 20,
        "workplace": 70,
    },
    "network": {
        "business_apps": 0,
        "data_platform": 5,
        "network_ops": 80,
        "service_desk": 15,
        "workplace": 0,
    },
    "reporting": {
        "business_apps": 25,
        "data_platform": 60,
        "network_ops": 0,
        "service_desk": 15,
        "workplace": 0,
    },
}
OPEN_PROBABILITY = {"P1": 0.05, "P2": 0.09, "P3": 0.14, "P4": 0.18}
TEAM_BREACH_ADJUSTMENT = {
    "business_apps": 0.005,
    "data_platform": -0.005,
    "network_ops": 0.005,
    "service_desk": -0.005,
    "workplace": 0.0,
}


def _format_timestamp(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _weighted_choice(rng: random.Random, weights: dict[str, int]) -> str:
    population = list(weights)
    return rng.choices(
        population=population,
        weights=[weights[key] for key in population],
        k=1,
    )[0]


def _resolution_minutes(
    rng: random.Random,
    *,
    sla_target: int,
    breached: bool,
) -> int:
    if breached:
        return max(sla_target + 1, round(sla_target * rng.uniform(1.05, 1.65)))
    return max(15, round(sla_target * rng.triangular(0.08, 0.95, 0.45)))


def _breach_probability(priority: str, category: str, team: str) -> float:
    probability = 0.035
    probability += {"P1": 0.02, "P2": 0.012, "P3": 0.0, "P4": -0.005}[priority]
    probability += {"application": 0.008, "network": 0.01}.get(category, 0.0)
    probability += TEAM_BREACH_ADJUSTMENT[team]
    return min(max(probability, 0.015), 0.09)


def _reopen_probability(category: str, resolution_ratio: float) -> float:
    probability = 0.045
    probability += {"application": 0.025, "hardware": 0.012, "network": 0.008}.get(
        category,
        0.0,
    )
    if resolution_ratio >= 0.8:
        probability += 0.015
    return min(probability, 0.11)


def _escalation_probability(
    *,
    priority: str,
    customer_segment: str,
    breached: bool,
    reopened_count: int,
    status: str,
) -> float:
    probability = 0.025
    probability += {"P1": 0.20, "P2": 0.065, "P3": 0.015, "P4": 0.0}[priority]
    if customer_segment == "enterprise":
        probability += 0.015
    if breached:
        probability += 0.34
    if reopened_count > 0:
        probability += 0.055
    if status == "open":
        probability += 0.02
    return min(probability, 0.8)


def generate_dataframe(
    record_count: int = DEFAULT_RECORD_COUNT,
    *,
    seed: int = SEED,
    inject_anomalies: bool = True,
) -> pd.DataFrame:
    """Return deterministic synthetic service requests for one 90-day environment.

    The baseline models five operational teams serving one customer environment.
    Eleven source rows become invalid after a bounded set of ten anomaly mutations:
    ten mutated rows plus both occurrences of one duplicated identifier.
    """
    if record_count < 20:
        raise ValueError("record_count must be at least 20.")

    rng = random.Random(seed)
    start = datetime(2026, 1, 1, tzinfo=UTC)
    rows: list[dict[str, object]] = []

    for index in range(record_count):
        created_at = start + timedelta(minutes=rng.randrange(0, ANALYSIS_WINDOW_DAYS * 24 * 60))
        category = rng.choices(CATEGORIES, weights=CATEGORY_WEIGHTS, k=1)[0]
        priority = rng.choices(
            population=["P1", "P2", "P3", "P4"],
            weights=CATEGORY_PRIORITY_WEIGHTS[category],
            k=1,
        )[0]
        assigned_team = _weighted_choice(rng, CATEGORY_TEAM_WEIGHTS[category])
        customer_segment = rng.choices(SEGMENTS, weights=[50, 30, 20], k=1)[0]
        status = "open" if rng.random() < OPEN_PROBABILITY[priority] else "closed"
        sla_target = PRIORITY_SLA[priority]

        if status == "closed":
            breached = rng.random() < _breach_probability(priority, category, assigned_team)
            resolution = _resolution_minutes(
                rng,
                sla_target=sla_target,
                breached=breached,
            )
            closed_at = created_at + timedelta(minutes=resolution)
            closed_text = _format_timestamp(closed_at)
            resolution_value: object = resolution
            resolution_ratio = resolution / sla_target
            reopened_probability = _reopen_probability(category, resolution_ratio)
            if rng.random() < reopened_probability:
                reopened_count = 2 if rng.random() < 0.12 else 1
            else:
                reopened_count = 0
        else:
            breached = False
            closed_text = ""
            resolution_value = ""
            reopened_count = 0

        escalated_probability = _escalation_probability(
            priority=priority,
            customer_segment=customer_segment,
            breached=breached,
            reopened_count=reopened_count,
            status=status,
        )
        escalated = rng.random() < escalated_probability

        rows.append(
            {
                "ticket_id": f"SR-{index + 1:06d}",
                "created_at": _format_timestamp(created_at),
                "closed_at": closed_text,
                "priority": priority,
                "category": category,
                "assigned_team": assigned_team,
                "status": status,
                "sla_target_minutes": sla_target,
                "resolution_minutes": resolution_value,
                "reopened_count": reopened_count,
                "escalated": str(escalated).lower(),
                "customer_segment": customer_segment,
                "source_system": "service_portal",
            }
        )

    if inject_anomalies:
        _inject_known_anomalies(rows)

    return pd.DataFrame(rows, columns=COLUMNS)


def _inject_known_anomalies(rows: list[dict[str, object]]) -> None:
    """Inject one bounded set of explainable data-quality failures."""
    indexes = list(range(len(rows) - ANOMALY_COUNT, len(rows)))

    rows[indexes[0]]["category"] = ""
    rows[indexes[1]]["priority"] = "P5"
    rows[indexes[2]]["assigned_team"] = "unknown_team"

    rows[indexes[3]]["priority"] = "P3"
    rows[indexes[3]]["sla_target_minutes"] = 999

    rows[indexes[4]]["status"] = "closed"
    rows[indexes[4]]["closed_at"] = ""
    rows[indexes[4]]["resolution_minutes"] = 60

    created_open = datetime.strptime(
        str(rows[indexes[5]]["created_at"]),
        "%Y-%m-%dT%H:%M:%SZ",
    ).replace(tzinfo=UTC)
    rows[indexes[5]]["status"] = "open"
    rows[indexes[5]]["closed_at"] = _format_timestamp(created_open + timedelta(minutes=30))
    rows[indexes[5]]["resolution_minutes"] = ""
    rows[indexes[5]]["reopened_count"] = 0

    created_negative = datetime.strptime(
        str(rows[indexes[6]]["created_at"]),
        "%Y-%m-%dT%H:%M:%SZ",
    ).replace(tzinfo=UTC)
    rows[indexes[6]]["status"] = "closed"
    rows[indexes[6]]["closed_at"] = _format_timestamp(created_negative + timedelta(minutes=30))
    rows[indexes[6]]["resolution_minutes"] = -5

    created_reverse = datetime.strptime(
        str(rows[indexes[7]]["created_at"]),
        "%Y-%m-%dT%H:%M:%SZ",
    ).replace(tzinfo=UTC)
    rows[indexes[7]]["status"] = "closed"
    rows[indexes[7]]["closed_at"] = _format_timestamp(created_reverse - timedelta(minutes=15))
    rows[indexes[7]]["resolution_minutes"] = 60

    rows[indexes[8]]["escalated"] = "maybe"

    # The final row reuses a clean earlier identifier. Both occurrences must
    # be treated as invalid because uniqueness cannot be resolved safely.
    rows[indexes[9]]["ticket_id"] = str(rows[5]["ticket_id"])


def write_dataset(dataframe: pd.DataFrame, output_path: Path | str) -> Path:
    """Write stable UTF-8 CSV bytes with Unix line endings."""
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    dataframe.to_csv(destination, index=False, lineterminator="\n", encoding="utf-8")
    return destination


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--records", type=int, default=DEFAULT_RECORD_COUNT)
    parser.add_argument("--clean", action="store_true")
    args = parser.parse_args(argv)

    dataframe = generate_dataframe(
        record_count=args.records,
        inject_anomalies=not args.clean,
    )
    write_dataset(dataframe, args.output)
    print(f"Wrote {len(dataframe)} synthetic rows to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
