from pathlib import Path

from er_reviewer.profiling.pairs import (
    find_grouping_candidates_in_csv,
    find_identical_column_pairs,
    find_identical_column_pairs_in_csv,
)

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DATA = ROOT / "sample_data"


def test_find_grouping_candidates_works_for_product_fixture() -> None:
    candidates = find_grouping_candidates_in_csv(SAMPLE_DATA / "products.csv", threshold=0.5)

    by_column = {candidate.column: candidate for candidate in candidates}
    assert by_column["category"].most_common_value == "Widget"
    assert by_column["category"].dominance_ratio == 0.5
    assert "sku" not in by_column


def test_find_identical_column_pairs_detects_duplicate_columns() -> None:
    pairs = find_identical_column_pairs(
        [
            {"left": "a", "right": "a", "different": "x"},
            {"left": "b", "right": "b", "different": "x"},
        ]
    )

    assert len(pairs) == 1
    assert pairs[0].left_column == "left"
    assert pairs[0].right_column == "right"


def test_find_identical_column_pairs_fingerprints_missing_values_distinctly() -> None:
    pairs = find_identical_column_pairs(
        [
            {"left": "ab", "right": "a", "different": "a"},
            {"left": "c", "right": "bc", "different": ""},
            {"left": "", "right": "", "different": "bc"},
        ]
    )

    assert [(pair.left_column, pair.right_column) for pair in pairs] == []


def test_find_identical_column_pairs_in_csv_uses_streaming_fingerprints(tmp_path: Path) -> None:
    path = tmp_path / "pairs.csv"
    path.write_text(
        "left,right,different\nalpha,alpha,alpha\nbeta,beta,\n,,beta\n",
        encoding="utf-8",
    )

    pairs = find_identical_column_pairs_in_csv(path)

    assert len(pairs) == 1
    assert pairs[0].left_column == "left"
    assert pairs[0].right_column == "right"
    assert pairs[0].compared_rows == 3
