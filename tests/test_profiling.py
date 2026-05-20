from pathlib import Path

from er_reviewer.profiling.columns import profile_columns, profile_csv_columns

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DATA = ROOT / "sample_data"


def test_profile_csv_columns_reports_generic_column_stats() -> None:
    profiles = {
        profile.column: profile for profile in profile_csv_columns(SAMPLE_DATA / "details.csv")
    }

    assert profiles["entityId"].total_rows == 8
    assert profiles["entityId"].likely_unique_id is True
    assert profiles["persistentId"].unique_count == 5
    assert profiles["persistentId"].top_values["p001"] == 2
    assert profiles["company_name"].blank_count == 0
    assert profiles["company_name"].likely_unique_id is False


def test_profile_columns_accepts_iterable_rows() -> None:
    rows = ({"entityId": f"e{index}", "score": str(index)} for index in range(1, 4))

    profiles = {
        profile.column: profile
        for profile in profile_columns(rows, fieldnames=["entityId", "score"])
    }

    assert profiles["entityId"].total_rows == 3
    assert profiles["entityId"].likely_unique_id is True
    assert profiles["score"].inferred_type == "numeric"
