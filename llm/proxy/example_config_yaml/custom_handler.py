import time
from typing import Any, Optional

import llm
from llm import CustomLLM, ImageObject, ImageResponse, completion, get_llm_provider
from llm.llms.custom_httpx.http_handler import AsyncHTTPHandler
from llm.types.utils import ModelResponse


class MyCustomLLM(CustomLLM):
    def completion(self, *args, **kwargs) -> ModelResponse:
        return llm.completion(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Hello world"}],
            mock_response="Hi!",
        )  # type: ignore

    async def acompletion(self, *args, **kwargs) -> llm.ModelResponse:
        return llm.completion(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Hello world"}],
            mock_response="Hi!",
        )  # type: ignore


my_custom_llm = MyCustomLLM()
