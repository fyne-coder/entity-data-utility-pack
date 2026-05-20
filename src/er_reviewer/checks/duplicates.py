from __future__ import annotations

import re
import warnings
from collections import defaultdict
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from difflib import SequenceMatcher
from hashlib import blake2b
from importlib import import_module
from pathlib import Path
from typing import Any, Literal, cast

from er_reviewer._csv_utils import read_dict_rows, require_columns

TOKEN_RE = re.compile(r"[A-Za-z0-9]+")
OversizedBlockBehavior = Literal["fail", "warn", "sample"]


@dataclass(frozen=True)
class DuplicateCandidate:
    block_value: str
    left_id: str
    right_id: str
    score: float
    column_scores: dict[str, float]

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["score"] = round(self.score, 4)
        data["column_scores"] = "; ".join(
            f"{column}={round(score, 4)}" for column, score in self.column_scores.items()
        )
        return data


class DuplicateBlockSizeError(ValueError):
    """Raised when an opted-in duplicate block guardrail is exceeded."""


def normalize_for_matching(value: str, *, profile: str = "basic") -> str:
    if profile == "none":
        return value.strip()
    if profile != "basic":
        raise ValueError(f"Unknown normalization profile: {profile}")
    return " ".join(TOKEN_RE.findall(value.casefold()))


def _token_sort(value: str, *, normalization: str = "basic") -> str:
    return " ".join(sorted(normalize_for_matching(value, profile=normalization).split()))


def token_sort_similarity(left: str, right: str, *, normalization: str = "basic") -> float:
    """Dependency-free token-sort similarity in the 0..1 range."""
    left_norm = _token_sort(left.strip(), normalization=normalization)
    right_norm = _token_sort(right.strip(), normalization=normalization)
    if not left_norm and not right_norm:
        return 1.0
    if not left_norm or not right_norm:
        return 0.0
    return SequenceMatcher(None, left_norm, right_norm).ratio()


def rapidfuzz_token_sort_similarity(left: str, right: str) -> float:
    """Use rapidfuzz when installed, without making it a hard dependency."""
    try:
        fuzz = import_module("rapidfuzz.fuzz")
    except ImportError as exc:
        raise RuntimeError(
            "rapidfuzz is not installed. Install the analysis extra or use difflib."
        ) from exc
    token_sort_ratio = cast(Callable[[str, str], float], cast(Any, fuzz).token_sort_ratio)
    return token_sort_ratio(left, right) / 100


def resolve_similarity_scorer(name: str = "auto") -> Callable[[str, str], float]:
    if name == "difflib":
        return token_sort_similarity
    if name == "rapidfuzz":
        return rapidfuzz_token_sort_similarity
    if name != "auto":
        raise ValueError(f"Unknown duplicate scorer: {name}")
    try:
        return rapidfuzz_token_sort_similarity if _rapidfuzz_available() else token_sort_similarity
    except RuntimeError:
        return token_sort_similarity


def _rapidfuzz_available() -> bool:
    try:
        import_module("rapidfuzz")
    except ImportError:
        return False
    return True


def _validate_guardrails(
    *,
    max_block_size: int | None,
    sample_rate: float,
    oversized_block_behavior: OversizedBlockBehavior,
    workers: int,
) -> None:
    if max_block_size is not None and max_block_size < 2:
        raise ValueError("max_block_size must be at least 2 when provided")
    if not 0 < sample_rate <= 1:
        raise ValueError("sample_rate must be greater than 0 and less than or equal to 1")
    if oversized_block_behavior not in {"fail", "warn", "sample"}:
        raise ValueError("oversized_block_behavior must be one of: fail, warn, sample")
    if workers < 1:
        raise ValueError("workers must be at least 1")


def _stable_fraction(parts: Iterable[str]) -> float:
    digest = blake2b("\x1f".join(parts).encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "big") / 2**64


def _sample_block_rows(
    block_value: str,
    block_rows: list[tuple[int, dict[str, str]]],
    *,
    id_column: str | None,
    max_block_size: int,
) -> list[tuple[int, dict[str, str]]]:
    ranked_rows = sorted(
        block_rows,
        key=lambda item: _stable_fraction(
            [
                block_value,
                str(item[0]),
                (item[1].get(id_column or "") or "").strip(),
                "\x1e".join(f"{key}={value}" for key, value in sorted(item[1].items())),
            ]
        ),
    )
    selected_positions = {position for position, _row in ranked_rows[:max_block_size]}
    return [item for item in block_rows if item[0] in selected_positions]


def _pair_selected(
    block_value: str,
    left_index: int,
    left: dict[str, str],
    right_index: int,
    right: dict[str, str],
    *,
    id_column: str | None,
    sample_rate: float,
) -> bool:
    if sample_rate >= 1:
        return True
    return (
        _stable_fraction(
            [
                block_value,
                str(left_index),
                (left.get(id_column or "") or "").strip(),
                str(right_index),
                (right.get(id_column or "") or "").strip(),
            ]
        )
        < sample_rate
    )


def find_duplicate_candidates(
    rows: list[dict[str, str]],
    *,
    block_column: str,
    match_columns: Iterable[str],
    id_column: str | None = None,
    threshold: float = 0.85,
    scorer: str | Callable[[str, str], float] = "auto",
    normalization: str = "basic",
    max_block_size: int | None = None,
    sample_rate: float = 1.0,
    oversized_block_behavior: OversizedBlockBehavior = "fail",
    workers: int = 1,
) -> list[DuplicateCandidate]:
    match_columns = list(match_columns)
    required = [block_column, *match_columns]
    if id_column:
        required.append(id_column)
    require_columns(rows[0].keys() if rows else [], required)
    _validate_guardrails(
        max_block_size=max_block_size,
        sample_rate=sample_rate,
        oversized_block_behavior=oversized_block_behavior,
        workers=workers,
    )
    if isinstance(scorer, str):
        resolved_similarity = resolve_similarity_scorer(scorer)
    else:
        resolved_similarity = scorer

    def similarity(left: str, right: str) -> float:
        if isinstance(scorer, str) and scorer == "difflib":
            return token_sort_similarity(left, right, normalization=normalization)
        if (
            isinstance(scorer, str)
            and scorer == "auto"
            and resolved_similarity is token_sort_similarity
        ):
            return token_sort_similarity(left, right, normalization=normalization)
        if isinstance(scorer, str) and scorer == "rapidfuzz":
            left_norm = normalize_for_matching(left, profile=normalization)
            right_norm = normalize_for_matching(right, profile=normalization)
            return resolved_similarity(left_norm, right_norm)
        return resolved_similarity(left, right)

    blocks: dict[str, list[tuple[int, dict[str, str]]]] = defaultdict(list)
    for row in rows:
        block_value = (row.get(block_column) or "").strip()
        if block_value:
            blocks[block_value].append((len(blocks[block_value]), row))

    def score_block(
        block_value: str,
        block_rows: list[tuple[int, dict[str, str]]],
    ) -> list[DuplicateCandidate]:
        if max_block_size is not None and len(block_rows) > max_block_size:
            message = (
                f"Duplicate block {block_value!r} contains {len(block_rows)} rows, "
                f"above max_block_size={max_block_size}"
            )
            if oversized_block_behavior == "fail":
                raise DuplicateBlockSizeError(message)
            if oversized_block_behavior == "warn":
                warnings.warn(f"{message}; processing all pairs", RuntimeWarning, stacklevel=2)
            else:
                warnings.warn(
                    f"{message}; deterministically sampling {max_block_size} rows",
                    RuntimeWarning,
                    stacklevel=2,
                )
                block_rows = _sample_block_rows(
                    block_value,
                    block_rows,
                    id_column=id_column,
                    max_block_size=max_block_size,
                )

        block_candidates: list[DuplicateCandidate] = []
        for left_index in range(len(block_rows)):
            for right_index in range(left_index + 1, len(block_rows)):
                left_block_index, left = block_rows[left_index]
                right_block_index, right = block_rows[right_index]
                if not _pair_selected(
                    block_value,
                    left_block_index,
                    left,
                    right_block_index,
                    right,
                    id_column=id_column,
                    sample_rate=sample_rate,
                ):
                    continue
                column_scores = {
                    column: similarity(left.get(column, ""), right.get(column, ""))
                    for column in match_columns
                }
                score = sum(column_scores.values()) / len(column_scores)
                if score >= threshold:
                    block_candidates.append(
                        DuplicateCandidate(
                            block_value=block_value,
                            left_id=(left.get(id_column or "") or str(left_block_index)).strip(),
                            right_id=(right.get(id_column or "") or str(right_block_index)).strip(),
                            score=score,
                            column_scores=column_scores,
                        )
                    )
        return block_candidates

    candidates: list[DuplicateCandidate] = []
    if workers == 1 or len(blocks) <= 1:
        for block_value, block_rows in blocks.items():
            candidates.extend(score_block(block_value, block_rows))
    else:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            for block_candidates in executor.map(
                lambda item: score_block(item[0], item[1]), blocks.items()
            ):
                candidates.extend(block_candidates)

    return sorted(candidates, key=lambda candidate: (-candidate.score, candidate.left_id))


def find_duplicate_candidates_in_csv(
    path: str | Path,
    *,
    block_column: str,
    match_columns: Iterable[str],
    id_column: str | None = None,
    threshold: float = 0.85,
    scorer: str | Callable[[str, str], float] = "auto",
    normalization: str = "basic",
    encoding: str = "utf-8",
    delimiter: str = ",",
    max_block_size: int | None = None,
    sample_rate: float = 1.0,
    oversized_block_behavior: OversizedBlockBehavior = "fail",
    workers: int = 1,
) -> list[DuplicateCandidate]:
    return find_duplicate_candidates(
        read_dict_rows(path, encoding=encoding, delimiter=delimiter),
        block_column=block_column,
        match_columns=match_columns,
        id_column=id_column,
        threshold=threshold,
        scorer=scorer,
        normalization=normalization,
        max_block_size=max_block_size,
        sample_rate=sample_rate,
        oversized_block_behavior=oversized_block_behavior,
        workers=workers,
    )
