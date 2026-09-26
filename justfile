sources := "eh_fifty.py test_eh_fifty.py conftest.py"

# list recipes
default:
    just --list

# update project environment
sync:
    uv sync

# format code with ruff
format:
    uv run ruff check --select I --fix {{sources}}
    uv run ruff format {{sources}}

# check code formatting with ruff
check-format:
    uv run ruff check --select I {{sources}}
    uv run ruff format --check {{sources}}

# run ruff lint check
check-lint:
    uv run ruff check {{sources}}

# run mypy check
check-mypy:
    uv run mypy --no-error-summary {{sources}}

# run all checks
check: check-format check-lint check-mypy

# run tests
test *args:
    uv run pytest --verbose test_eh_fifty.py {{args}}
