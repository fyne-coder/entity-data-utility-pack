from pathlib import Path

import pytest

import er_reviewer.checks.similarity as similarity_module
from er_reviewer.checks.similarity import (
    compare_cluster_pairs_csv,
    jaccard_similarity,
    similarity_band,
)

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DATA = ROOT / "sample_data"


def test_jaccard_similarity_handles_case_and_punctuation() -> None:
    assert jaccard_similarity("Acme, Corp", "ACME Corporation") == 1 / 3


def test_compare_cluster_pairs_scores_candidate_pairs() -> None:
    similarities = compare_cluster_pairs_csv(
        SAMPLE_DATA / "details.csv",
        SAMPLE_DATA / "similar.csv",
        cluster_column="entity_id",
        left_pair_column="left_entity_id",
        right_pair_column="right_entity_id",
        compare_columns=["company_name"],
    )

    assert similarities[0].left_cluster_id == "p003"
    assert similarities[0].right_cluster_id == "p004"
    assert similarities[0].similarity > 0


def test_tfidf_method_reports_missing_optional_dependency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_import_module(name: str) -> object:
        if name == "sklearn.feature_extraction.text":
            raise ImportError("simulated missing optional dependency")
        raise AssertionError(f"Unexpected import: {name}")

    monkeypatch.setattr(similarity_module, "import_module", fake_import_module)

    with pytest.raises(RuntimeError, match="scikit-learn is not installed"):
        compare_cluster_pairs_csv(
            SAMPLE_DATA / "details.csv",
            SAMPLE_DATA / "similar.csv",
            cluster_column="entity_id",
            left_pair_column="left_entity_id",
            right_pair_column="right_entity_id",
            compare_columns=["company_name"],
            method="tfidf",
        )


def test_similarity_band_rejects_inverted_thresholds() -> None:
    with pytest.raises(ValueError, match="review_threshold"):
        similarity_band(0.8, review_threshold=0.9, likely_match_threshold=0.7)
