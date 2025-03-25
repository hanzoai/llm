# Testing for `llm/` 

This directory 1:1 maps the the `llm/` directory, and can only contain mocked tests. 

The point of this is to:
1. Increase test coverage of `llm/`
2. Make it easy for contributors to add tests for the `llm/` package and easily run tests without needing LLM API keys. 


## File name conventions

- `llm/proxy/test_caching_routes.py` maps to `llm/proxy/caching_routes.py`
- `test_<filename>.py` maps to `llm/<filename>.py`











