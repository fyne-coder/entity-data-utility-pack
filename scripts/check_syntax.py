from __future__ import annotations

import ast
import sys
from pathlib import Path


def iter_python_files(paths: list[str]) -> list[Path]:
    files: list[Path] = []
    for raw_path in paths:
        path = Path(raw_path)
        if path.is_file() and path.suffix == ".py":
            files.append(path)
        elif path.is_dir():
            files.extend(sorted(path.rglob("*.py")))
    return files


def main(argv: list[str] | None = None) -> int:
    paths = argv or sys.argv[1:] or ["src", "tests"]
    failed = False
    for path in iter_python_files(paths):
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            failed = True
            print(f"{path}: {exc}", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
