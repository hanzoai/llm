import os

import llm

try:
    # New and recommended way to access resources
    from importlib import resources

    filename = str(resources.files(llm).joinpath("llm_core_utils/tokenizers"))
except (ImportError, AttributeError):
    # Old way to access resources, which setuptools deprecated some time ago
    import pkg_resources  # type: ignore

    filename = pkg_resources.resource_filename(__name__, "llm_core_utils/tokenizers")

os.environ["TIKTOKEN_CACHE_DIR"] = os.getenv(
    "CUSTOM_TIKTOKEN_CACHE_DIR", filename
)  # use local copy of tiktoken b/c of - https://github.com/hanzoai/llm/issues/1071
import tiktoken

encoding = tiktoken.get_encoding("cl100k_base")
