# Hanzo Makefile
# Simple Makefile for running tests and basic development tasks

.PHONY: help test test-unit test-integration lint format

# Default target
help:
	@echo "Available commands:"
	@echo "  make test               - Run all tests"
	@echo "  make test-unit          - Run unit tests"
	@echo "  make test-integration   - Run integration tests"

install-dev:
	poetry install --with dev

lint: install-dev
	poetry run pip install types-requests types-setuptools types-redis types-PyYAML
	cd llm && poetry run mypy . --ignore-missing-imports

# Testing
test:
	poetry run pytest tests/

test-unit:
	poetry run pytest tests/llm/

test-integration:
	poetry run pytest tests/ -k "not llm" 