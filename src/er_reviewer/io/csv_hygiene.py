from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class CsvIssue:
    line_number: int
    issue_type: str
    message: str


@dataclass(frozen=True)
class CsvHygieneReport:
    path: str
    encoding: str
    header_columns: int
    data_rows: int
    issues: list[CsvIssue]

    @property
    def ok(self) -> bool:
        return not self.issues

    def to_rows(self) -> list[dict[str, object]]:
        if not self.issues:
            return [
                {
                    "path": self.path,
                    "issue_type": "ok",
                    "line_number": "",
                    "message": "No CSV hygiene issues found.",
                }
            ]
        return [
            {
                "path": self.path,
                "issue_type": issue.issue_type,
                "line_number": issue.line_number,
                "message": issue.message,
            }
            for issue in self.issues
        ]

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["ok"] = self.ok
        return data


def analyze_csv_hygiene(
    path: str | Path,
    *,
    encoding: str = "utf-8",
    delimiter: str = ",",
) -> CsvHygieneReport:
    """Inspect CSV structure and common byte-level ingestion hazards."""
    csv_path = Path(path)
    issues: list[CsvIssue] = []

    nul_count = _count_nul_bytes(csv_path)
    if nul_count:
        issues.append(CsvIssue(0, "nul_byte", f"Found {nul_count} NUL byte(s)."))

    try:
        header_columns, data_rows, parse_issues = _parse_csv_structure(
            csv_path,
            encoding=encoding,
            delimiter=delimiter,
            errors="strict",
        )
    except UnicodeDecodeError as exc:
        issues.append(
            CsvIssue(
                exc.start,
                "encoding",
                f"File could not be decoded as {encoding}: {exc.reason}.",
            )
        )
        header_columns, data_rows, parse_issues = _parse_csv_structure(
            csv_path,
            encoding=encoding,
            delimiter=delimiter,
            errors="replace",
        )

    return CsvHygieneReport(
        str(csv_path),
        encoding,
        header_columns,
        data_rows,
        issues + parse_issues,
    )


def _count_nul_bytes(path: Path, *, chunk_size: int = 1024 * 1024) -> int:
    count = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            count += chunk.count(b"\x00")
    return count


def _parse_csv_structure(
    path: Path,
    *,
    encoding: str,
    delimiter: str,
    errors: str,
) -> tuple[int, int, list[CsvIssue]]:
    issues: list[CsvIssue] = []
    try:
        with path.open("r", encoding=encoding, errors=errors, newline="") as handle:
            reader = csv.reader(handle, delimiter=delimiter)
            try:
                header = next(reader)
            except StopIteration:
                return 0, 0, issues
            header_columns = len(header)
            data_rows = 0
            for line_number, row in enumerate(reader, start=2):
                data_rows += 1
                if len(row) != header_columns:
                    issues.append(
                        CsvIssue(
                            line_number,
                            "column_count",
                            f"Expected {header_columns} column(s), found {len(row)}.",
                        )
                    )
                for value in row:
                    if "\n" in value or "\r" in value:
                        issues.append(
                            CsvIssue(
                                line_number,
                                "embedded_newline",
                                "Field contains a line break.",
                            )
                        )
            return header_columns, data_rows, issues
    except csv.Error as exc:
        return (
            0,
            0,
            [
                CsvIssue(0, "csv_parse", str(exc)),
            ],
        )
    except UnicodeDecodeError:
        if errors == "strict":
            raise
        return (
            0,
            0,
            [
                CsvIssue(
                    0,
                    "csv_parse",
                    "CSV structure could not be parsed after replacing decode errors.",
                )
            ],
        )


def strip_nul_bytes(path: str | Path, output_path: str | Path) -> int:
    """Write a copy of a file with NUL bytes removed and return bytes removed."""
    raw_bytes = Path(path).read_bytes()
    cleaned = raw_bytes.replace(b"\x00", b"")
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_bytes(cleaned)
    return len(raw_bytes) - len(cleaned)
