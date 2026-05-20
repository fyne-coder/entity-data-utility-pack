from pathlib import Path

from er_reviewer.profiling.columns import profile_columns, profile_csv_columns

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DATA = ROOT / "sample_data"


def test_profile_csv_columns_reports_generic_column_stats() -> None:
    profiles = {
        profile.column: profile for profile in profile_csv_columns(SAMPLE_DATA / "details.csv")
    }

    assert profiles["record_id"].total_rows == 8
    assert profiles["record_id"].likely_unique_id is True
    assert profiles["entity_id"].unique_count == 5
    assert profiles["entity_id"].top_values["p001"] == 2
    assert profiles["company_name"].blank_count == 0
    assert profiles["company_name"].likely_unique_id is False


def test_profile_columns_accepts_iterable_rows() -> None:
    rows = ({"record_id": f"e{index}", "score": str(index)} for index in range(1, 4))

    profiles = {
        profile.column: profile
        for profile in profile_columns(rows, fieldnames=["record_id", "score"])
    }

    assert profiles["record_id"].total_rows == 3
    assert profiles["record_id"].likely_unique_id is True
    assert profiles["score"].inferred_type == "numeric"
