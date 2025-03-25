import importlib_metadata

try:
    version = importlib_metadata.version("llm")
except Exception:
    pass
