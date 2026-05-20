from pathlib import Path

import pytest

import er_reviewer.checks.duplicates as duplicates_module
from er_reviewer.checks.duplicates import (
    DuplicateBlockSizeError,
    find_duplicate_candidates,
    find_duplicate_candidates_in_csv,
    rapidfuzz_token_sort_similarity,
    resolve_similarity_scorer,
)

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DATA = ROOT / "sample_data"


def test_find_duplicate_candidates_blocks_and_scores_configured_columns() -> None:
    candidates = find_duplicate_candidates_in_csv(
        SAMPLE_DATA / "people_duplicates.csv",
        block_column="Date Of Birth",
        match_columns=["Full Name"],
        id_column="Entity ID",
        threshold=0.8,
        scorer="difflib",
    )

    pairs = {(candidate.left_id, candidate.right_id) for candidate in candidates}
    assert ("t001", "t002") in pairs
    assert ("t003", "t004") in pairs
    assert all(candidate.score >= 0.8 for candidate in candidates)


def test_find_duplicate_candidates_fails_when_block_guardrail_exceeded() -> None:
    rows = [
        {"block": "same", "name": "Jane Smith", "id": "1"},
        {"block": "same", "name": "Jane Smith", "id": "2"},
        {"block": "same", "name": "Jane Smith", "id": "3"},
    ]

    with pytest.raises(DuplicateBlockSizeError, match="above max_block_size=2"):
        find_duplicate_candidates(
            rows,
            block_column="block",
            match_columns=["name"],
            id_column="id",
            scorer="difflib",
            max_block_size=2,
        )


def test_find_duplicate_candidates_warns_and_preserves_full_block_when_configured() -> None:
    rows = [
        {"block": "same", "name": "Jane Smith", "id": "1"},
        {"block": "same", "name": "Jane Smith", "id": "2"},
        {"block": "same", "name": "Jane Smith", "id": "3"},
    ]

    with pytest.warns(RuntimeWarning, match="processing all pairs"):
        candidates = find_duplicate_candidates(
            rows,
            block_column="block",
            match_columns=["name"],
            id_column="id",
            scorer="difflib",
            max_block_size=2,
            oversized_block_behavior="warn",
        )

    assert {(candidate.left_id, candidate.right_id) for candidate in candidates} == {
        ("1", "2"),
        ("1", "3"),
        ("2", "3"),
    }


def test_find_duplicate_candidates_samples_oversized_blocks_deterministically() -> None:
    rows = [{"block": "same", "name": "Jane Smith", "id": str(index)} for index in range(1, 7)]

    with pytest.warns(RuntimeWarning, match="deterministically sampling 3 rows"):
        first = find_duplicate_candidates(
            rows,
            block_column="block",
            match_columns=["name"],
            id_column="id",
            scorer="difflib",
            max_block_size=3,
            oversized_block_behavior="sample",
            workers=2,
        )
    with pytest.warns(RuntimeWarning, match="deterministically sampling 3 rows"):
        second = find_duplicate_candidates(
            rows,
            block_column="block",
            match_columns=["name"],
            id_column="id",
            scorer="difflib",
            max_block_size=3,
            oversized_block_behavior="sample",
            workers=2,
        )

    assert [candidate.to_dict() for candidate in first] == [
        candidate.to_dict() for candidate in second
    ]
    assert len(first) == 3


def test_find_duplicate_candidates_sample_rate_is_deterministic() -> None:
    rows = [{"block": "same", "name": "Jane Smith", "id": str(index)} for index in range(1, 7)]

    first = find_duplicate_candidates(
        rows,
        block_column="block",
        match_columns=["name"],
        id_column="id",
        scorer="difflib",
        sample_rate=0.4,
    )
    second = find_duplicate_candidates(
        rows,
        block_column="block",
        match_columns=["name"],
        id_column="id",
        scorer="difflib",
        sample_rate=0.4,
    )

    assert [candidate.to_dict() for candidate in first] == [
        candidate.to_dict() for candidate in second
    ]
    assert 0 < len(first) < 15


def test_resolve_similarity_scorer_uses_difflib_without_extra_dependency() -> None:
    scorer = resolve_similarity_scorer("difflib")

    assert scorer("Jane Smith", "Smith Jane") == 1.0


def test_rapidfuzz_scorer_reports_missing_optional_dependency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_import_module(name: str) -> object:
        if name == "rapidfuzz.fuzz":
            raise ImportError("simulated missing optional dependency")
        raise AssertionError(f"Unexpected import: {name}")

    monkeypatch.setattr(duplicates_module, "import_module", fake_import_module)

    with pytest.raises(RuntimeError, match="rapidfuzz is not installed"):
        rapidfuzz_token_sort_similarity("Jane Smith", "Smith Jane")
