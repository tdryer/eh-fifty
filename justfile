# list recipes
default:
    just --list

# update project environment
sync:
    uv sync

# run isort check
check-isort:
    uv run isort --check eh_fifty.py tests.py conftest.py

# run black check
check-black:
    uv run black --check eh_fifty.py tests.py conftest.py

# run pylint check
check-pylint:
    uv run pylint eh_fifty.py tests.py conftest.py

# run mypy check
check-mypy:
    uv run mypy --no-error-summary eh_fifty.py tests.py conftest.py

# run all checks
check: check-isort check-black check-pylint check-mypy

# run tests
test *args:
    uv run pytest --verbose tests.py {{args}}
