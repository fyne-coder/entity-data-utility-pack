from __future__ import annotations

import csv
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DictRowSource:
    fieldnames: list[str]
    rows: Iterator[dict[str, str]]


@contextmanager
def open_dict_row_source(
    path: str | Path,
    *,
    encoding: str = "utf-8",
    delimiter: str = ",",
) -> Iterator[DictRowSource]:
    """Open a CSV as a lazy dictionary row source with header metadata."""
    with Path(path).open("r", encoding=encoding, newline="") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        yield DictRowSource(
            fieldnames=list(reader.fieldnames or []),
            rows=(dict(row) for row in reader),
        )


def iter_dict_rows(
    path: str | Path,
    *,
    encoding: str = "utf-8",
    delimiter: str = ",",
) -> Iterator[dict[str, str]]:
    """Iterate a CSV file as dictionaries without materializing all rows."""
    with open_dict_row_source(path, encoding=encoding, delimiter=delimiter) as source:
        yield from source.rows


def chunked_rows(
    rows: Iterable[dict[str, str]],
    *,
    chunk_size: int,
) -> Iterator[list[dict[str, str]]]:
    """Yield dictionary rows in fixed-size chunks."""
    if chunk_size < 1:
        raise ValueError("chunk_size must be >= 1")

    chunk: list[dict[str, str]] = []
    for row in rows:
        chunk.append(row)
        if len(chunk) == chunk_size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk


def iter_dict_row_chunks(
    path: str | Path,
    *,
    chunk_size: int,
    encoding: str = "utf-8",
    delimiter: str = ",",
) -> Iterator[list[dict[str, str]]]:
    """Iterate CSV dictionary rows in chunks without loading the full file."""
    yield from chunked_rows(
        iter_dict_rows(path, encoding=encoding, delimiter=delimiter),
        chunk_size=chunk_size,
    )


def read_dict_rows(
    path: str | Path,
    *,
    encoding: str = "utf-8",
    delimiter: str = ",",
) -> list[dict[str, str]]:
    """Read a CSV file as dictionaries without normalizing column names."""
    with Path(path).open("r", encoding=encoding, newline="") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        return [dict(row) for row in reader]


def write_dict_rows(
    path: str | Path,
    rows: Iterable[dict[str, object]],
    *,
    fieldnames: list[str] | None = None,
    encoding: str = "utf-8",
) -> None:
    rows = list(rows)
    if fieldnames is None:
        fieldnames = []
        for row in rows:
            for key in row:
                if key not in fieldnames:
                    fieldnames.append(key)

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding=encoding, newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def require_columns(fieldnames: Iterable[str] | None, required: Iterable[str]) -> None:
    available = set(fieldnames or [])
    missing = [name for name in required if name not in available]
    if missing:
        raise ValueError(f"Missing required column(s): {', '.join(missing)}")
