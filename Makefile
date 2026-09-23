.PHONY: install-dev format format-check lint

VENV := .venv
PYTHON := $(VENV)/bin/python

install-dev: $(PYTHON)
	$(PYTHON) -m pip install -e '.[dev]'
	$(PYTHON) -m pre_commit install

$(PYTHON):
	python3 -m venv $(VENV)

format:
	$(PYTHON) -m ruff format .

format-check:
	$(PYTHON) -m ruff format --check .

lint:
	$(PYTHON) -m ruff check .
