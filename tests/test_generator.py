import hashlib
from pathlib import Path

import pandas as pd
import pytest

from service_operations.generator import generate_dataframe, write_dataset

EXPECTED_FIXTURE_SHA256 = "292ed8fb2857e3927936a5b3ca002492b146875d04baee77a9322de287db8914"


def test_generation_is_deterministic() -> None:
    first = generate_dataframe()
    second = generate_dataframe()

    pd.testing.assert_frame_equal(first, second)


def test_generated_fixture_has_stable_bytes(tmp_path: Path) -> None:
    generated_path = tmp_path / "service_requests.csv"
    write_dataset(generate_dataframe(), generated_path)

    digest = hashlib.sha256(generated_path.read_bytes()).hexdigest()
    assert digest == EXPECTED_FIXTURE_SHA256


def test_clean_generation_contains_no_injected_anomalies() -> None:
    clean = generate_dataframe(inject_anomalies=False)

    assert len(clean) == 1000
    assert clean["ticket_id"].is_unique
    assert set(clean["priority"]) <= {"P1", "P2", "P3", "P4"}
    assert set(clean["escalated"]) <= {"true", "false"}


def test_open_requests_cannot_be_reopened() -> None:
    clean = generate_dataframe(inject_anomalies=False)
    open_requests = clean.loc[clean["status"].eq("open")]

    assert open_requests["closed_at"].eq("").all()
    assert open_requests["resolution_minutes"].eq("").all()
    assert open_requests["reopened_count"].eq(0).all()


def test_category_and_team_assignment_are_correlated() -> None:
    clean = generate_dataframe(inject_anomalies=False)

    network = clean.loc[clean["category"].eq("network")]
    application = clean.loc[clean["category"].eq("application")]
    reporting = clean.loc[clean["category"].eq("reporting")]

    assert network["assigned_team"].eq("network_ops").mean() >= 0.65
    assert application["assigned_team"].eq("business_apps").mean() >= 0.55
    assert reporting["assigned_team"].eq("data_platform").mean() >= 0.45


def test_generator_rejects_too_small_fixture() -> None:
    with pytest.raises(ValueError, match="at least 20"):
        generate_dataframe(record_count=19)
