from pathlib import Path

import pandas as pd
import pytest

from service_operations.generator import generate_dataframe, write_dataset

FIXTURE_PATH = Path("data/raw/service_requests.csv")


def test_generation_is_deterministic() -> None:
    first = generate_dataframe()
    second = generate_dataframe()

    pd.testing.assert_frame_equal(first, second)


def test_committed_fixture_matches_generator(tmp_path: Path) -> None:
    generated_path = tmp_path / "service_requests.csv"
    write_dataset(generate_dataframe(), generated_path)

    assert generated_path.read_bytes() == FIXTURE_PATH.read_bytes()


def test_clean_generation_contains_no_injected_anomalies() -> None:
    clean = generate_dataframe(inject_anomalies=False)

    assert clean["ticket_id"].is_unique
    assert set(clean["priority"]) <= {"P1", "P2", "P3", "P4"}
    assert set(clean["escalated"]) <= {"true", "false"}


def test_generator_rejects_too_small_fixture() -> None:
    with pytest.raises(ValueError, match="at least 20"):
        generate_dataframe(record_count=19)
