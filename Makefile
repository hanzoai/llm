# LLM Makefile
# Simple Makefile for running tests and basic development tasks

.PHONY: help test test-unit test-integration lint format

# Default target
help:
	@echo "Available commands:"
	@echo "  make test               - Run all tests"
	@echo "  make test-unit          - Run unit tests"
	@echo "  make test-integration   - Run integration tests"
	@echo "  make test-unit-helm     - Run helm unit tests"

install-dev:
	poetry install --with dev

lint: install-dev
	poetry run pip install types-requests types-setuptools types-redis types-PyYAML
	cd llm && poetry run mypy . --ignore-missing-imports

# Testing
test:
	source .venv-py312/bin/activate && python -m pytest tests/

test-unit:
	source .venv-py312/bin/activate && python -m pytest tests/llm/

test-integration:
	source .venv-py312/bin/activate && python -m pytest tests/ -k "not llm"

test-unit-helm:
	helm unittest -f 'tests/*.yaml' deploy/charts/llm-helm