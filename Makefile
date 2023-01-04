SOURCES = eh_fifty.py tests.py

.PHONY: shell
shell:
	hatch -e test shell

.PHONY: test
test:
	pytest --verbose tests.py

.PHONY: check
check: isort black pylint mypy

.PHONY: isort
isort:
	isort --check $(SOURCES)

.PHONY: black
black:
	black --check --quiet $(SOURCES)

.PHONY: pylint
pylint:
	pylint $(SOURCES)

.PHONY: mypy
mypy:
	mypy --no-error-summary $(SOURCES)

.PHONY: clean
clean:
	hatch env prune
	rm -rf venv __pycache__ *.egg-info dist .mypy_cache .pytest_cache
