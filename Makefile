PYTHON = python
SOURCES = eh_fifty.py tests.py

.PHONY: develop
develop:
	$(PYTHON) -m venv venv
	venv/bin/pip install --editable .[dev]

.PHONY: test
test:
	venv/bin/pytest --verbose tests.py

.PHONY: check
check: isort black pylint mypy

.PHONY: isort
isort:
	venv/bin/isort --check $(SOURCES)

.PHONY: black
black:
	venv/bin/black --check --quiet $(SOURCES)

.PHONY: pylint
pylint:
	venv/bin/pylint $(SOURCES)

.PHONY: mypy
mypy:
	venv/bin/mypy --no-error-summary $(SOURCES)

.PHONY: clean
clean:
	rm -rf venv __pycache__ *.egg-info dist
