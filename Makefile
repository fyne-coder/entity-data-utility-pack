.PHONY: ci check test lint typecheck format format-check clean

ci: check

check: format-check lint typecheck test

test:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src pytest -q -p no:cacheprovider
	@$(MAKE) clean

lint:
	ruff check src tests scripts
	python3 scripts/check_syntax.py src tests scripts

typecheck:
	@if python3 -m mypy --version >/dev/null 2>&1; then \
		python3 -m mypy; \
	else \
		uv run --extra dev mypy; \
	fi

format:
	ruff format src tests scripts

format-check:
	ruff format --check src tests scripts

clean:
	@rm -rf .pytest_cache
	@rm -rf .mypy_cache .ruff_cache
	@rm -rf .venv
	@find src tests -type d -name __pycache__ -prune -exec rm -rf {} +
