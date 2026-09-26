sources := "eh_fifty.py tests.py conftest.py"

# list recipes
default:
    just --list

# update project environment
sync:
    uv sync

# format imports and code with ruff
format:
    uv run ruff check --select I --fix {{sources}}
    uv run ruff format {{sources}}

# check import order and code formatting with ruff
check-format:
    uv run ruff check --select I {{sources}}
    uv run ruff format --check {{sources}}

# run pylint check
check-pylint:
    uv run pylint {{sources}}

# run mypy check
check-mypy:
    uv run mypy --no-error-summary {{sources}}

# run all checks
check: check-format check-pylint check-mypy

# run tests
test *args:
    uv run pytest --verbose tests.py {{args}}
