from __future__ import annotations

import argparse
import csv
import json
import sys
import tomllib
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any, cast

from er_reviewer import __version__
from er_reviewer._csv_utils import write_dict_rows
from er_reviewer.checks.cardinality import (
    find_one_to_many_mappings,
    find_one_to_many_mappings_in_csv,
)
from er_reviewer.checks.clusters import summarize_clusters, summarize_clusters_in_csv
from er_reviewer.checks.duplicates import (
    find_duplicate_candidates,
    find_duplicate_candidates_in_csv,
)
from er_reviewer.checks.lookup import lookup_entity, lookup_entity_in_csv
from er_reviewer.checks.similarity import compare_cluster_pairs_csv
from er_reviewer.compare.exports import compare_export_membership, compare_export_membership_csv
from er_reviewer.io.csv_hygiene import analyze_csv_hygiene
from er_reviewer.io.table import TableFormat, read_table_rows, resolve_table_format
from er_reviewer.profiling.columns import profile_columns, profile_csv_columns
from er_reviewer.profiling.pairs import (
    find_grouping_candidates,
    find_grouping_candidates_in_csv,
    find_identical_column_pairs,
    find_identical_column_pairs_in_csv,
)
from er_reviewer.reporting.charts import write_bar_chart_svg, write_match_score_distribution_svg
from er_reviewer.reporting.html_report import ReportSection, write_report_artifacts
from er_reviewer.reporting.redaction import redact_sections


def _write_rows(
    rows: Iterable[dict[str, object]],
    output: str | None,
    *,
    fieldnames: list[str] | None = None,
) -> None:
    rows = list(rows)
    if output:
        write_dict_rows(output, rows, fieldnames=fieldnames)
        return
    if not rows:
        return
    writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames or list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)


def _table_format(args: argparse.Namespace) -> TableFormat:
    return cast(TableFormat, getattr(args, "format", "auto"))


def _read_table_rows(args: argparse.Namespace) -> list[dict[str, str]]:
    return read_table_rows(
        args.input,
        format=_table_format(args),
        encoding=args.encoding,
        delimiter=args.delimiter,
        sheet_name=args.sheet_name,
    )


def _is_csv_like(path: str | Path, table_format: TableFormat) -> bool:
    resolved_format = resolve_table_format(path, format=table_format)
    return resolved_format in {"csv", "tsv"}


def _resolved_delimiter(path: str | Path, table_format: TableFormat, delimiter: str) -> str:
    return "\t" if resolve_table_format(path, format=table_format) == "tsv" else delimiter


def _cmd_hygiene(args: argparse.Namespace) -> int:
    report = analyze_csv_hygiene(args.input, encoding=args.encoding, delimiter=args.delimiter)
    _write_rows(report.to_rows(), args.out)
    return 0 if report.ok else 1


def _cmd_profile(args: argparse.Namespace) -> int:
    if _is_csv_like(args.input, _table_format(args)):
        profiles = profile_csv_columns(
            args.input,
            encoding=args.encoding,
            delimiter=_resolved_delimiter(args.input, _table_format(args), args.delimiter),
        )
    else:
        profiles = profile_columns(_read_table_rows(args))
    rows = [profile.to_dict() for profile in profiles]
    _write_rows(rows, args.out)
    return 0


def _cmd_pair_profile(args: argparse.Namespace) -> int:
    if (
        _is_csv_like(args.input, _table_format(args))
        and args.encoding == "utf-8"
        and _resolved_delimiter(args.input, _table_format(args), args.delimiter) == ","
    ):
        grouping_candidates = find_grouping_candidates_in_csv(args.input, threshold=args.threshold)
        identical_pairs = find_identical_column_pairs_in_csv(args.input)
    else:
        rows = _read_table_rows(args)
        grouping_candidates = find_grouping_candidates(rows, threshold=args.threshold)
        identical_pairs = find_identical_column_pairs(rows)
    grouping_rows = [candidate.to_dict() for candidate in grouping_candidates]
    identical_rows = [pair.to_dict() for pair in identical_pairs]

    if args.identical_out:
        _write_rows(
            identical_rows,
            args.identical_out,
            fieldnames=["left_column", "right_column", "compared_rows"],
        )
    _write_rows(grouping_rows, args.out)
    return 0


def _cmd_mappings(args: argparse.Namespace) -> int:
    if _is_csv_like(args.input, _table_format(args)):
        issues = find_one_to_many_mappings_in_csv(
            args.input,
            left_column=args.left,
            right_column=args.right,
            encoding=args.encoding,
            delimiter=_resolved_delimiter(args.input, _table_format(args), args.delimiter),
        )
    else:
        issues = find_one_to_many_mappings(
            _read_table_rows(args),
            left_column=args.left,
            right_column=args.right,
        )
    rows = [issue.to_dict() for issue in issues]
    _write_rows(rows, args.out)
    return 1 if rows else 0


def _cmd_compare(args: argparse.Namespace) -> int:
    old_format = cast(TableFormat, args.old_format)
    new_format = cast(TableFormat, args.new_format)
    if _is_csv_like(args.old, old_format) and _is_csv_like(args.new, new_format):
        issues = compare_export_membership_csv(
            args.old,
            args.new,
            id_column=args.id,
            member_column=args.member,
            old_encoding=args.old_encoding,
            new_encoding=args.new_encoding,
            old_delimiter=_resolved_delimiter(args.old, old_format, args.old_delimiter),
            new_delimiter=_resolved_delimiter(args.new, new_format, args.new_delimiter),
            include_narratives=args.narrative,
        )
    else:
        issues = compare_export_membership(
            read_table_rows(
                args.old,
                format=old_format,
                encoding=args.old_encoding,
                delimiter=args.old_delimiter,
                sheet_name=args.old_sheet_name,
            ),
            read_table_rows(
                args.new,
                format=new_format,
                encoding=args.new_encoding,
                delimiter=args.new_delimiter,
                sheet_name=args.new_sheet_name,
            ),
            id_column=args.id,
            member_column=args.member,
            include_narratives=args.narrative,
        )
    rows = [issue.to_dict() for issue in issues]
    _write_rows(rows, args.out)
    return 1 if rows else 0


def _split_columns(values: list[str]) -> list[str]:
    columns: list[str] = []
    for value in values:
        columns.extend(column.strip() for column in value.split(",") if column.strip())
    return columns


def _cmd_duplicates(args: argparse.Namespace) -> int:
    if _is_csv_like(args.input, _table_format(args)):
        candidates = find_duplicate_candidates_in_csv(
            args.input,
            block_column=args.block,
            match_columns=_split_columns(args.match),
            id_column=args.id,
            threshold=args.threshold,
            scorer=args.scorer,
            normalization=args.normalization,
            encoding=args.encoding,
            delimiter=_resolved_delimiter(args.input, _table_format(args), args.delimiter),
            max_block_size=args.max_block_size,
            sample_rate=args.sample_rate,
            oversized_block_behavior=args.oversized_block_behavior,
            workers=args.workers,
        )
    else:
        candidates = find_duplicate_candidates(
            _read_table_rows(args),
            block_column=args.block,
            match_columns=_split_columns(args.match),
            id_column=args.id,
            threshold=args.threshold,
            scorer=args.scorer,
            normalization=args.normalization,
            max_block_size=args.max_block_size,
            sample_rate=args.sample_rate,
            oversized_block_behavior=args.oversized_block_behavior,
            workers=args.workers,
        )
    rows = [candidate.to_dict() for candidate in candidates]
    _write_rows(rows, args.out)
    return 1 if rows else 0


def _cmd_clusters(args: argparse.Namespace) -> int:
    match_columns = _split_columns(args.match_column or [])
    if _is_csv_like(args.input, _table_format(args)):
        summaries = summarize_clusters_in_csv(
            args.input,
            cluster_column=args.cluster,
            match_columns=match_columns or None,
            match_prefix=args.match_prefix,
            large_cluster_size=args.large_cluster_size,
            low_match_score=args.low_match_score,
            encoding=args.encoding,
            delimiter=_resolved_delimiter(args.input, _table_format(args), args.delimiter),
        )
    else:
        summaries = summarize_clusters(
            _read_table_rows(args),
            cluster_column=args.cluster,
            match_columns=match_columns or None,
            match_prefix=args.match_prefix,
            large_cluster_size=args.large_cluster_size,
            low_match_score=args.low_match_score,
        )
    rows = [summary.to_dict() for summary in summaries]
    if args.chart_out:
        write_bar_chart_svg(
            args.chart_out,
            [(summary.cluster_id, summary.size) for summary in summaries],
            title="Cluster Sizes",
        )
    _write_rows(rows, args.out)
    return 0


def _cmd_similarity(args: argparse.Namespace) -> int:
    rows = [
        similarity.to_dict()
        for similarity in compare_cluster_pairs_csv(
            args.details,
            args.pairs,
            cluster_column=args.cluster,
            left_pair_column=args.left_pair,
            right_pair_column=args.right_pair,
            compare_columns=_split_columns(args.compare),
            method=args.method,
            review_threshold=args.review_threshold,
            likely_match_threshold=args.likely_match_threshold,
            details_encoding=args.details_encoding,
            pairs_encoding=args.pairs_encoding,
            details_delimiter=args.details_delimiter,
            pairs_delimiter=args.pairs_delimiter,
        )
    ]
    _write_rows(rows, args.out)
    return 0


def _parse_mapping_specs(values: list[str] | None) -> list[tuple[str, str]]:
    specs: list[tuple[str, str]] = []
    for value in values or []:
        if ":" not in value:
            raise ValueError("--mapping must use LEFT:RIGHT format")
        left, right = value.split(":", 1)
        specs.append((left.strip(), right.strip()))
    return specs


def _cmd_report(args: argparse.Namespace) -> int:
    config = _load_config(args.config) if args.config else {}
    input_path = Path(str(_config_value(args, config, "input")))
    out_dir = Path(str(_config_value(args, config, "out_dir")))
    title = str(_config_value(args, config, "title", "Entity Data Review"))
    encoding = str(_config_value(args, config, "encoding", "utf-8"))
    delimiter = str(_config_value(args, config, "delimiter", ","))
    table_format = cast(TableFormat, _config_value(args, config, "format", "auto"))
    sheet_name = _config_value(args, config, "sheet_name", 0)
    max_output_rows = _config_optional_int(args, config, "max_output_rows")
    sections: list[ReportSection] = []
    csv_like = _is_csv_like(input_path, table_format)
    table_rows: list[dict[str, str]] | None = None

    if not csv_like:
        table_rows = read_table_rows(
            input_path,
            format=table_format,
            encoding=encoding,
            delimiter=delimiter,
            sheet_name=cast(str | int, sheet_name),
        )

    if csv_like:
        hygiene_report = analyze_csv_hygiene(input_path, encoding=encoding, delimiter=delimiter)
        sections.append(
            ReportSection(
                title="CSV Hygiene",
                rows=hygiene_report.to_rows(),
                csv_filename="hygiene.csv",
                summary="No issues found."
                if hygiene_report.ok
                else f"{len(hygiene_report.issues)} issue(s) found.",
            )
        )
    else:
        sections.append(
            ReportSection(
                title="Input Hygiene",
                rows=[
                    {
                        "check": "csv_hygiene",
                        "status": "skipped",
                        "detail": "CSV byte/row hygiene checks apply only to CSV/TSV input.",
                    }
                ],
                csv_filename="hygiene.csv",
                summary="CSV-specific hygiene checks skipped for non-CSV input.",
            )
        )

    if table_rows is None:
        profile_items = profile_csv_columns(input_path, encoding=encoding, delimiter=delimiter)
    else:
        profile_items = profile_columns(table_rows)
    profile_rows = [profile.to_dict() for profile in profile_items]
    sections.append(
        ReportSection(
            title="Column Profile",
            rows=profile_rows,
            csv_filename="profile.csv",
            summary=f"{len(profile_rows)} column(s) profiled.",
        )
    )

    for left_column, right_column in _parse_mapping_specs(
        _config_list(args, config, "mapping", "mappings")
    ):
        if table_rows is None:
            mapping_issues = find_one_to_many_mappings_in_csv(
                input_path,
                left_column=left_column,
                right_column=right_column,
                encoding=encoding,
                delimiter=delimiter,
            )
        else:
            mapping_issues = find_one_to_many_mappings(
                table_rows,
                left_column=left_column,
                right_column=right_column,
            )
        rows = [issue.to_dict() for issue in mapping_issues]
        sections.append(
            ReportSection(
                title=f"One-to-Many Mapping: {left_column} -> {right_column}",
                rows=rows,
                csv_filename=f"mapping_{_safe_name(left_column)}_to_{_safe_name(right_column)}.csv",
                summary=f"{len(rows)} issue(s) found.",
            )
        )

    cluster_column = _config_optional(args, config, "cluster")
    if cluster_column:
        if table_rows is None:
            cluster_summaries = summarize_clusters_in_csv(
                input_path,
                cluster_column=cluster_column,
                match_prefix=_config_optional(args, config, "match_prefix"),
                large_cluster_size=int(str(_config_value(args, config, "large_cluster_size", 10))),
                low_match_score=float(str(_config_value(args, config, "low_match_score", 0.85))),
                encoding=encoding,
                delimiter=delimiter,
            )
        else:
            cluster_summaries = summarize_clusters(
                table_rows,
                cluster_column=cluster_column,
                match_prefix=_config_optional(args, config, "match_prefix"),
                large_cluster_size=int(str(_config_value(args, config, "large_cluster_size", 10))),
                low_match_score=float(str(_config_value(args, config, "low_match_score", 0.85))),
            )
        cluster_rows = [summary.to_dict() for summary in cluster_summaries]
        sections.append(
            ReportSection(
                title="Cluster Summary",
                rows=cluster_rows,
                csv_filename="clusters.csv",
                summary=f"{len(cluster_rows)} cluster(s) summarized. SVG: cluster_sizes.svg",
            )
        )
        write_bar_chart_svg(
            out_dir / "cluster_sizes.svg",
            _cluster_chart_items(cluster_rows),
            title="Cluster Sizes",
        )
        match_scores = _cluster_match_scores(cluster_rows)
        if match_scores:
            write_match_score_distribution_svg(
                out_dir / "match_score_distribution.svg",
                match_scores,
                title="Average Match Score Distribution",
            )

    duplicate_block = _config_optional(args, config, "duplicate_block")
    duplicate_match = _config_list(args, config, "duplicate_match")
    if not duplicate_block and isinstance(config.get("duplicates"), dict):
        duplicate_block = str(cast(dict[str, object], config["duplicates"]).get("block", ""))
        duplicate_match = _as_str_list(cast(dict[str, object], config["duplicates"]).get("match"))
    if duplicate_block and duplicate_match:
        duplicate_max_block_size = _config_optional_int(args, config, "duplicate_max_block_size")
        duplicate_sample_rate = float(
            str(_config_value(args, config, "duplicate_sample_rate", 1.0))
        )
        duplicate_oversized_behavior = str(
            _config_value(args, config, "duplicate_oversized_block_behavior", "fail")
        )
        duplicate_workers = int(str(_config_value(args, config, "duplicate_workers", 1)))
        if table_rows is None:
            duplicate_candidates = find_duplicate_candidates_in_csv(
                input_path,
                block_column=duplicate_block,
                match_columns=_split_columns(duplicate_match),
                id_column=_config_optional(args, config, "duplicate_id"),
                threshold=float(str(_config_value(args, config, "duplicate_threshold", 0.85))),
                scorer=str(_config_value(args, config, "duplicate_scorer", "auto")),
                normalization=str(_config_value(args, config, "normalization", "basic")),
                encoding=encoding,
                delimiter=delimiter,
                max_block_size=duplicate_max_block_size,
                sample_rate=duplicate_sample_rate,
                oversized_block_behavior=cast(Any, duplicate_oversized_behavior),
                workers=duplicate_workers,
            )
        else:
            duplicate_candidates = find_duplicate_candidates(
                table_rows,
                block_column=duplicate_block,
                match_columns=_split_columns(duplicate_match),
                id_column=_config_optional(args, config, "duplicate_id"),
                threshold=float(str(_config_value(args, config, "duplicate_threshold", 0.85))),
                scorer=str(_config_value(args, config, "duplicate_scorer", "auto")),
                normalization=str(_config_value(args, config, "normalization", "basic")),
                max_block_size=duplicate_max_block_size,
                sample_rate=duplicate_sample_rate,
                oversized_block_behavior=cast(Any, duplicate_oversized_behavior),
                workers=duplicate_workers,
            )
        duplicate_rows = [candidate.to_dict() for candidate in duplicate_candidates]
        sections.append(
            ReportSection(
                title="Duplicate Candidates",
                rows=duplicate_rows,
                csv_filename="duplicate_candidates.csv",
                summary=f"{len(duplicate_rows)} candidate pair(s) found.",
            )
        )

    redact_columns = _split_columns(_config_list(args, config, "redact"))
    if redact_columns:
        sections = cast(
            list[ReportSection],
            redact_sections(
                sections,
                columns=redact_columns,
                mode=str(_config_value(args, config, "redact_mode", "mask")),
            ),
        )

    report_path = write_report_artifacts(
        out_dir,
        title=title,
        sections=sections,
        max_rows_per_section=max_output_rows,
    )
    workbook_out = _config_optional(args, config, "workbook_out")
    if workbook_out:
        from er_reviewer.reporting.workbook import write_workbook

        write_workbook(
            workbook_out,
            sections={section.title: section.rows for section in sections},
            max_rows_per_sheet=max_output_rows,
        )
    pdf_out = _config_optional(args, config, "pdf_out")
    if pdf_out:
        from er_reviewer.reporting.pdf_report import write_pdf_report

        write_pdf_report(report_path, pdf_out)
    print(report_path)
    return 0


def _cmd_lookup(args: argparse.Namespace) -> int:
    if _is_csv_like(args.input, _table_format(args)):
        rows = lookup_entity_in_csv(
            args.input,
            id_column=args.id,
            id_value=args.value,
            cluster_column=args.cluster,
            encoding=args.encoding,
            delimiter=_resolved_delimiter(args.input, _table_format(args), args.delimiter),
        )
    else:
        rows = lookup_entity(
            _read_table_rows(args),
            id_column=args.id,
            id_value=args.value,
            cluster_column=args.cluster,
        )
    if args.redact:
        from er_reviewer.reporting.redaction import redact_rows

        rows = redact_rows(
            rows,
            columns=_split_columns(args.redact),
            mode=args.redact_mode,
        )
    _write_rows(rows, args.out)
    return 0 if rows else 1


def _safe_name(value: str) -> str:
    return "".join(char.lower() if char.isalnum() else "_" for char in value).strip("_")


def _cluster_chart_items(rows: list[dict[str, object]]) -> list[tuple[str, int]]:
    items: list[tuple[str, int]] = []
    for row in rows:
        size = row["size"]
        if not isinstance(size, int):
            raise ValueError("Cluster row size must be an integer.")
        items.append((str(row["cluster_id"]), size))
    return items


def _cluster_match_scores(rows: list[dict[str, object]]) -> list[float]:
    scores: list[float] = []
    for row in rows:
        value = row.get("average_match_score")
        if value in (None, ""):
            continue
        try:
            scores.append(float(str(value)))
        except ValueError:
            continue
    return scores


def _load_config(path: str | Path) -> dict[str, object]:
    config_path = Path(path)
    if config_path.suffix.lower() == ".json":
        return cast(dict[str, object], json.loads(config_path.read_text(encoding="utf-8")))
    if config_path.suffix.lower() in {".toml", ".tml"}:
        return cast(dict[str, object], tomllib.loads(config_path.read_text(encoding="utf-8")))
    raise ValueError("Report config must be JSON or TOML.")


def _config_value(
    args: argparse.Namespace,
    config: dict[str, object],
    name: str,
    default: object | None = None,
) -> object:
    value = getattr(args, name, None)
    if value not in (None, [], ""):
        return value
    if name in config:
        return config[name]
    if default is not None:
        return default
    raise ValueError(f"Missing required report value: {name.replace('_', '-')}")


def _config_optional(args: argparse.Namespace, config: dict[str, object], name: str) -> str | None:
    value = getattr(args, name, None)
    if value not in (None, [], ""):
        return str(value)
    if name in config and config[name] not in (None, ""):
        return str(config[name])
    return None


def _config_optional_int(
    args: argparse.Namespace,
    config: dict[str, object],
    name: str,
) -> int | None:
    value = _config_optional(args, config, name)
    if value is None:
        return None
    return int(value)


def _config_list(
    args: argparse.Namespace,
    config: dict[str, object],
    name: str,
    plural_name: str | None = None,
) -> list[str]:
    value = getattr(args, name, None)
    if value:
        return _as_str_list(value)
    if name in config:
        return _as_str_list(config[name])
    if plural_name and plural_name in config:
        return _as_str_list(config[plural_name])
    return []


def _as_str_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        items: list[str] = []
        for item in value:
            if isinstance(item, dict) and {"left", "right"} <= set(item):
                items.append(f"{item['left']}:{item['right']}")
            else:
                items.append(str(item))
        return items
    return [str(value)]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="er-review")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    hygiene = subparsers.add_parser("hygiene", help="Check CSV structure and encoding hazards.")
    hygiene.add_argument("input", type=Path)
    _add_csv_options(hygiene)
    hygiene.add_argument("--out", help="CSV output path. Defaults to stdout.")
    hygiene.set_defaults(func=_cmd_hygiene)

    profile = subparsers.add_parser("profile", help="Profile CSV columns.")
    profile.add_argument("input", type=Path)
    _add_table_options(profile)
    profile.add_argument("--out", help="CSV output path. Defaults to stdout.")
    profile.set_defaults(func=_cmd_profile)

    pair_profile = subparsers.add_parser(
        "pair-profile", help="Find grouping candidates and identical column pairs."
    )
    pair_profile.add_argument("input", type=Path)
    _add_table_options(pair_profile)
    pair_profile.add_argument("--threshold", type=float, default=0.5)
    pair_profile.add_argument(
        "--out", help="Grouping-candidate CSV output path. Defaults to stdout."
    )
    pair_profile.add_argument(
        "--identical-out", help="Optional identical-column-pairs CSV output path."
    )
    pair_profile.set_defaults(func=_cmd_pair_profile)

    mappings = subparsers.add_parser("mappings", help="Find one-to-many mappings.")
    mappings.add_argument("input", type=Path)
    _add_table_options(mappings)
    mappings.add_argument("--left", required=True, help="Left-hand column.")
    mappings.add_argument("--right", required=True, help="Right-hand column.")
    mappings.add_argument("--out", help="CSV output path. Defaults to stdout.")
    mappings.set_defaults(func=_cmd_mappings)

    compare = subparsers.add_parser("compare", help="Compare grouped membership across exports.")
    compare.add_argument("old", type=Path)
    compare.add_argument("new", type=Path)
    compare.add_argument("--old-encoding", default="utf-8")
    compare.add_argument("--new-encoding", default="utf-8")
    compare.add_argument("--old-delimiter", default=",")
    compare.add_argument("--new-delimiter", default=",")
    compare.add_argument(
        "--old-format",
        choices=["auto", "csv", "tsv", "xlsx", "parquet"],
        default="auto",
        help="Old export format. Excel and Parquet require the optional tables extra.",
    )
    compare.add_argument(
        "--new-format",
        choices=["auto", "csv", "tsv", "xlsx", "parquet"],
        default="auto",
        help="New export format. Excel and Parquet require the optional tables extra.",
    )
    compare.add_argument("--old-sheet-name", default=0)
    compare.add_argument("--new-sheet-name", default=0)
    compare.add_argument(
        "--narrative",
        action="store_true",
        help="Include member reassignment, split, and merge narrative rows.",
    )
    compare.add_argument("--id", required=True, help="Grouping identifier column.")
    compare.add_argument("--member", required=True, help="Member/entity column.")
    compare.add_argument("--out", help="CSV output path. Defaults to stdout.")
    compare.set_defaults(func=_cmd_compare)

    duplicates = subparsers.add_parser(
        "duplicates", help="Find duplicate candidates within blocking groups."
    )
    duplicates.add_argument("input", type=Path)
    _add_table_options(duplicates)
    duplicates.add_argument("--block", required=True, help="Blocking column.")
    duplicates.add_argument(
        "--match",
        required=True,
        action="append",
        help="Match column. May be repeated or comma-separated.",
    )
    duplicates.add_argument("--id", help="Optional row identifier column.")
    duplicates.add_argument("--threshold", type=float, default=0.85)
    duplicates.add_argument(
        "--scorer",
        choices=["auto", "difflib", "rapidfuzz"],
        default="auto",
        help="Similarity scorer. auto uses rapidfuzz when installed, otherwise difflib.",
    )
    duplicates.add_argument(
        "--normalization",
        choices=["basic", "none"],
        default="basic",
        help="Value normalization before scoring.",
    )
    duplicates.add_argument(
        "--max-block-size",
        type=int,
        help="Optional guardrail for the largest duplicate blocking group to score.",
    )
    duplicates.add_argument(
        "--oversized-block-behavior",
        choices=["fail", "warn", "sample"],
        default="fail",
        help="Behavior when --max-block-size is exceeded.",
    )
    duplicates.add_argument(
        "--sample-rate",
        type=float,
        default=1.0,
        help="Deterministic pair sampling rate within duplicate blocks.",
    )
    duplicates.add_argument("--workers", type=int, default=1, help="Duplicate block workers.")
    duplicates.add_argument("--out", help="CSV output path. Defaults to stdout.")
    duplicates.set_defaults(func=_cmd_duplicates)

    clusters = subparsers.add_parser(
        "clusters", help="Summarize cluster size and optional match scores."
    )
    clusters.add_argument("input", type=Path)
    _add_table_options(clusters)
    clusters.add_argument("--cluster", required=True, help="Cluster identifier column.")
    clusters.add_argument(
        "--match-column",
        action="append",
        help="Numeric match-score column. May be repeated or comma-separated.",
    )
    clusters.add_argument("--match-prefix", help="Prefix for numeric match-score columns.")
    clusters.add_argument("--large-cluster-size", type=int, default=10)
    clusters.add_argument("--low-match-score", type=float, default=0.85)
    clusters.add_argument("--chart-out", help="Optional SVG bar chart output path.")
    clusters.add_argument("--out", help="CSV output path. Defaults to stdout.")
    clusters.set_defaults(func=_cmd_clusters)

    similarity = subparsers.add_parser(
        "similarity", help="Score candidate cluster pairs by token Jaccard similarity."
    )
    similarity.add_argument("details", type=Path)
    similarity.add_argument("pairs", type=Path)
    similarity.add_argument("--details-encoding", default="utf-8")
    similarity.add_argument("--pairs-encoding", default="utf-8")
    similarity.add_argument("--details-delimiter", default=",")
    similarity.add_argument("--pairs-delimiter", default=",")
    similarity.add_argument(
        "--cluster", required=True, help="Cluster identifier column in details CSV."
    )
    similarity.add_argument(
        "--left-pair", default="left_entity_id", help="Left entity/group column in pairs CSV."
    )
    similarity.add_argument(
        "--right-pair", default="right_entity_id", help="Right entity/group column in pairs CSV."
    )
    similarity.add_argument(
        "--method",
        choices=["jaccard", "tfidf"],
        default="jaccard",
        help="Similarity method. tfidf requires the analysis extra.",
    )
    similarity.add_argument(
        "--compare",
        required=True,
        action="append",
        help="Detail column to compare. May be repeated or comma-separated.",
    )
    similarity.add_argument("--review-threshold", type=float, default=0.65)
    similarity.add_argument("--likely-match-threshold", type=float, default=0.85)
    similarity.add_argument("--out", help="CSV output path. Defaults to stdout.")
    similarity.set_defaults(func=_cmd_similarity)

    report = subparsers.add_parser(
        "report", help="Write section CSVs plus consolidated HTML and optional workbook reports."
    )
    report.add_argument("input", nargs="?", type=Path)
    _add_table_options(report)
    report.add_argument("--config", help="Optional JSON/TOML report recipe.")
    report.add_argument("--out-dir", type=Path)
    report.add_argument("--workbook-out", help="Optional .xlsx workbook output path.")
    report.add_argument("--title")
    report.add_argument(
        "--mapping",
        action="append",
        help="Optional one-to-many mapping check in LEFT:RIGHT format. May be repeated.",
    )
    report.add_argument("--cluster", help="Optional cluster identifier column.")
    report.add_argument(
        "--match-prefix",
        help="Optional numeric match-score prefix for cluster summaries.",
    )
    report.add_argument("--duplicate-block", help="Optional duplicate blocking column.")
    report.add_argument(
        "--duplicate-match",
        action="append",
        help="Optional duplicate match column. May be repeated or comma-separated.",
    )
    report.add_argument("--duplicate-id", help="Optional duplicate row identifier column.")
    report.add_argument("--duplicate-threshold", type=float, default=0.85)
    report.add_argument(
        "--duplicate-scorer",
        choices=["auto", "difflib", "rapidfuzz"],
        default="auto",
        help="Duplicate scorer for report duplicate candidates.",
    )
    report.add_argument(
        "--normalization",
        choices=["basic", "none"],
        default="basic",
        help="Duplicate value normalization before scoring.",
    )
    report.add_argument("--duplicate-max-block-size", type=int)
    report.add_argument(
        "--duplicate-oversized-block-behavior",
        choices=["fail", "warn", "sample"],
        default="fail",
    )
    report.add_argument("--duplicate-sample-rate", type=float, default=1.0)
    report.add_argument("--duplicate-workers", type=int, default=1)
    report.add_argument("--large-cluster-size", type=int, default=10)
    report.add_argument("--low-match-score", type=float, default=0.85)
    report.add_argument(
        "--max-output-rows",
        type=int,
        help="Cap rows displayed in HTML previews and optional workbook sheets.",
    )
    report.add_argument("--pdf-out", help="Optional PDF output path. Requires reports extra.")
    report.add_argument(
        "--redact",
        action="append",
        help="Column to redact from report outputs. May be repeated or comma-separated.",
    )
    report.add_argument("--redact-mode", choices=["mask", "hash"], default="mask")
    report.set_defaults(func=_cmd_report)

    lookup = subparsers.add_parser("lookup", help="Show one entity and optional cluster siblings.")
    lookup.add_argument("input", type=Path)
    _add_table_options(lookup)
    lookup.add_argument("--id", required=True, help="Identifier column.")
    lookup.add_argument("--value", required=True, help="Identifier value to find.")
    lookup.add_argument("--cluster", help="Optional cluster column for sibling lookup.")
    lookup.add_argument(
        "--redact",
        action="append",
        help="Column to redact from lookup output. May be repeated or comma-separated.",
    )
    lookup.add_argument("--redact-mode", choices=["mask", "hash"], default="mask")
    lookup.add_argument("--out", help="CSV output path. Defaults to stdout.")
    lookup.set_defaults(func=_cmd_lookup)

    return parser


def _add_csv_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--encoding", default="utf-8", help="Input text encoding.")
    parser.add_argument("--delimiter", default=",", help="Input CSV delimiter.")


def _add_table_options(parser: argparse.ArgumentParser) -> None:
    _add_csv_options(parser)
    parser.add_argument(
        "--format",
        choices=["auto", "csv", "tsv", "xlsx", "parquet"],
        default="auto",
        help="Input table format. Excel and Parquet require the optional tables extra.",
    )
    parser.add_argument(
        "--sheet-name",
        default=0,
        help="Excel worksheet name or index for --format xlsx. Defaults to the first sheet.",
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handler = cast(Callable[[argparse.Namespace], int], cast(Any, args).func)
    try:
        return handler(args)
    except (RuntimeError, ValueError) as exc:
        print(f"{parser.prog}: error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
