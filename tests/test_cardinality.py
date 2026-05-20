from pathlib import Path

from er_reviewer.checks.cardinality import find_one_to_many_mappings_in_csv

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DATA = ROOT / "sample_data"


def test_find_one_to_many_mappings_in_csv_is_column_configurable() -> None:
    issues = find_one_to_many_mappings_in_csv(
        SAMPLE_DATA / "details.csv",
        left_column="persistentId",
        right_column="trusted_id",
    )

    assert len(issues) == 1
    assert issues[0].left_value == "p002"
    assert issues[0].right_values == ("T200", "T201")


def test_find_one_to_many_mappings_in_csv_streams_delimited_rows(tmp_path: Path) -> None:
    path = tmp_path / "mappings.tsv"
    path.write_text("left\tright\nA\t1\nA\t2\nB\t3\n", encoding="utf-8")

    issues = find_one_to_many_mappings_in_csv(
        path,
        left_column="left",
        right_column="right",
        delimiter="\t",
    )

    assert len(issues) == 1
    assert issues[0].left_value == "A"
    assert issues[0].right_values == ("1", "2")
