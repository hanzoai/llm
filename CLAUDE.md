# LLM Project Command Reference and Style Guide

## Build Commands
- Install dependencies: `poetry install --with dev`
- Run server: `uvicorn llm.proxy.proxy_server:app --host localhost --port 4000 --reload`
- Run docker services: `docker-compose up db prometheus`

## Test Commands
- Run all tests: `source .venv-py312/bin/activate && python -m pytest tests/`
- Run unit tests: `source .venv-py312/bin/activate && python -m pytest tests/llm/`
- Run a single test: `source .venv-py312/bin/activate && python -m pytest tests/path/to/test_file.py::test_function_name -v`

## Lint/Format Commands
- Type check: `cd llm && poetry run mypy . --ignore-missing-imports`
- Format code: `poetry run black .`
- Sort imports: `poetry run isort .`
- Lint code: `poetry run ruff check .`

## Code Style Guidelines
- Follow Google Python Style Guide
- Line length: 120 characters maximum
- Type annotations required for function parameters and return values
- Use pydantic for data validation
- Async patterns preferred for IO operations
- Include docstrings for public functions
- Error handling: Use exception mapping defined in llm/exceptions.py
- Naming: snake_case for variables/functions, CamelCase for classes
- Imports: Use isort with black profile
- Tests: Pytest with descriptive test function names (test_should_*)