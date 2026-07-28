"""Generate a deterministic synthetic service-operations CSV fixture."""

from __future__ import annotations

import argparse
import random
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd

SEED = 20260729
DEFAULT_RECORD_COUNT = 100

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
TEAMS = ["business_apps", "data_platform", "network_ops", "service_desk", "workplace"]
SEGMENTS = ["enterprise", "internal", "smb"]


def _format_timestamp(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def generate_dataframe(
    record_count: int = DEFAULT_RECORD_COUNT,
    *,
    seed: int = SEED,
    inject_anomalies: bool = True,
) -> pd.DataFrame:
    """Return deterministic synthetic service requests.

    The committed fixture deliberately contains known quality defects. A clean
    dataset can be generated with ``inject_anomalies=False``.
    """
    if record_count < 20:
        raise ValueError("record_count must be at least 20.")

    rng = random.Random(seed)
    start = datetime(2026, 1, 1, tzinfo=UTC)
    rows: list[dict[str, object]] = []

    for index in range(record_count):
        created_at = start + timedelta(minutes=rng.randrange(0, 90 * 24 * 60))
        priority = rng.choices(
            population=["P1", "P2", "P3", "P4"],
            weights=[5, 20, 45, 30],
            k=1,
        )[0]
        status = rng.choices(["closed", "open"], weights=[82, 18], k=1)[0]
        sla_target = PRIORITY_SLA[priority]

        if status == "closed":
            resolution = rng.randint(20, sla_target * 2)
            closed_at = created_at + timedelta(minutes=resolution)
            closed_text = _format_timestamp(closed_at)
            resolution_value: object = resolution
        else:
            closed_text = ""
            resolution_value = ""

        rows.append(
            {
                "ticket_id": f"SR-{index + 1:06d}",
                "created_at": _format_timestamp(created_at),
                "closed_at": closed_text,
                "priority": priority,
                "category": rng.choice(CATEGORIES),
                "assigned_team": rng.choice(TEAMS),
                "status": status,
                "sla_target_minutes": sla_target,
                "resolution_minutes": resolution_value,
                "reopened_count": rng.choices([0, 1, 2], weights=[86, 11, 3], k=1)[0],
                "escalated": rng.choices(["false", "true"], weights=[90, 10], k=1)[0],
                "customer_segment": rng.choice(SEGMENTS),
                "source_system": "service_portal",
            }
        )

    if inject_anomalies:
        _inject_known_anomalies(rows)

    return pd.DataFrame(rows, columns=COLUMNS)


def _inject_known_anomalies(rows: list[dict[str, object]]) -> None:
    """Inject one bounded set of explainable data-quality failures."""
    indexes = list(range(len(rows) - 10, len(rows)))

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
