.PHONY: develop
develop:
	python -m venv venv
	venv/bin/pip install --editable .[dev]

.PHONY: check
check: isort black pylint mypy

.PHONY: isort
isort:
	venv/bin/isort --check eh_fifty.py

.PHONY: black
black:
	venv/bin/black --check --quiet eh_fifty.py

.PHONY: pylint
pylint:
	venv/bin/pylint eh_fifty.py

.PHONY: mypy
mypy:
	venv/bin/mypy --no-error-summary eh_fifty.py

.PHONY: clean
clean:
	rm -rf venv __pycache__ *.egg-info
