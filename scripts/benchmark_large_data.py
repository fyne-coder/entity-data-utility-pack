from __future__ import annotations

import argparse
import csv
import resource
import subprocess
import sys
import time
from pathlib import Path


def generate_fixture(path: Path, *, rows: int, clusters: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "entity_id",
                "cluster_id",
                "source_id",
                "company_name",
                "match_score",
                "amount",
                "statement_date",
            ],
        )
        writer.writeheader()
        for index in range(rows):
            cluster_number = index % clusters
            writer.writerow(
                {
                    "entity_id": f"e{index:08d}",
                    "cluster_id": f"c{cluster_number:06d}",
                    "source_id": f"s{index % 50:03d}",
                    "company_name": f"Company {cluster_number:06d}",
                    "match_score": f"{0.70 + (index % 30) / 100:.2f}",
                    "amount": f"{(index % 10000) / 7:.2f}",
                    "statement_date": f"2026-05-{(index % 28) + 1:02d}",
                }
            )


def run_command(command: list[str]) -> tuple[float, int]:
    started = time.perf_counter()
    completed = subprocess.run(command, check=False)
    elapsed = time.perf_counter() - started
    return elapsed, completed.returncode


def peak_rss_mb() -> float:
    # macOS reports bytes; Linux reports KiB.
    usage = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    if sys.platform == "darwin":
        return usage / (1024 * 1024)
    return usage / 1024


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate and benchmark synthetic ER data.")
    parser.add_argument("--rows", type=int, default=100_000)
    parser.add_argument("--clusters", type=int, default=10_000)
    parser.add_argument("--work-dir", type=Path, default=Path("output/benchmarks"))
    parser.add_argument("--keep", action="store_true")
    args = parser.parse_args(argv)

    input_path = args.work_dir / f"synthetic_{args.rows}.csv"
    profile_out = args.work_dir / "profile.csv"
    clusters_out = args.work_dir / "clusters.csv"
    mappings_out = args.work_dir / "mappings.csv"

    generate_fixture(input_path, rows=args.rows, clusters=args.clusters)
    commands = [
        [
            sys.executable,
            "-m",
            "er_reviewer.cli",
            "profile",
            str(input_path),
            "--out",
            str(profile_out),
        ],
        [
            sys.executable,
            "-m",
            "er_reviewer.cli",
            "clusters",
            str(input_path),
            "--cluster",
            "cluster_id",
            "--match-prefix",
            "match_score",
            "--out",
            str(clusters_out),
        ],
        [
            sys.executable,
            "-m",
            "er_reviewer.cli",
            "mappings",
            str(input_path),
            "--left",
            "cluster_id",
            "--right",
            "source_id",
            "--out",
            str(mappings_out),
        ],
    ]

    print("command,elapsed_seconds,exit_code")
    failed = False
    for command in commands:
        elapsed, exit_code = run_command(command)
        print(f"{' '.join(command)},{elapsed:.3f},{exit_code}")
        if exit_code not in {0, 1}:
            failed = True

    print(f"peak_child_rss_mb,{peak_rss_mb():.1f},")
    if not args.keep:
        for path in (input_path, profile_out, clusters_out, mappings_out):
            path.unlink(missing_ok=True)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
