import os
import sys
import traceback

from dotenv import load_dotenv

load_dotenv()
import io
import os

sys.path.insert(
    0, os.path.abspath("../..")
)  # Adds the parent directory to the system path
import json

import pytest

import llm
from llm import RateLimitError, Timeout, completion, completion_cost, embedding


# Cloud flare AI test
@pytest.mark.asyncio
@pytest.mark.parametrize("stream", [True, False])
async def test_completion_cloudflare(stream):
    try:
        llm.set_verbose = False
        response = await llm.acompletion(
            model="cloudflare/@cf/meta/llama-2-7b-chat-int8",
            messages=[{"content": "what llm are you", "role": "user"}],
            max_tokens=15,
            stream=stream,
        )
        print(response)
        if stream is True:
            async for chunk in response:
                print(chunk)
        else:
            print(response)

    except Exception as e:
        pytest.fail(f"Error occurred: {e}")
