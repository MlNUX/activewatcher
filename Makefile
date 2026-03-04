SHELL := /usr/bin/env bash

PYTHON ?= python3
VENV_DIR ?= .venv
VENV_PY := $(VENV_DIR)/bin/python

.PHONY: venv pip-update pip-build frontend-build build

venv:
	@if [[ ! -x "$(VENV_PY)" ]]; then \
		$(PYTHON) -m venv "$(VENV_DIR)"; \
	fi

pip-update: venv
	"$(VENV_PY)" -m pip install --upgrade pip setuptools wheel

pip-build: pip-update
	"$(VENV_PY)" -m pip install -e . --no-build-isolation

frontend-build:
	./scripts/build_frontend.sh

build: pip-build frontend-build
