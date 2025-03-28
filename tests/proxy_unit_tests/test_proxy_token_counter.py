# Test the following scenarios:
# 1. Generate a Key, and use it to make a call


import sys, os
import traceback
from dotenv import load_dotenv
from fastapi import Request
from datetime import datetime

load_dotenv()
import os, io, time

# this file is to test llm/proxy

sys.path.insert(
    0, os.path.abspath("../..")
)  # Adds the parent directory to the system path
import pytest, logging, asyncio
import llm, asyncio
from llm.proxy.proxy_server import token_counter
from llm.proxy.utils import PrismaClient, ProxyLogging, hash_token, update_spend
from llm._logging import verbose_proxy_logger

verbose_proxy_logger.setLevel(level=logging.DEBUG)

from llm.proxy._types import TokenCountRequest, TokenCountResponse


from llm import Router


@pytest.mark.asyncio
async def test_vLLM_token_counting():
    """
    Test Token counter for vLLM models
    - User passes model="special-alias"
    - token_counter should infer that special_alias -> maps to wolfram/miquliz-120b-v2.0
    -> token counter should use hugging face tokenizer
    """

    llm_router = Router(
        model_list=[
            {
                "model_name": "special-alias",
                "llm_params": {
                    "model": "openai/wolfram/miquliz-120b-v2.0",
                    "api_base": "https://exampleopenaiendpoint-production.up.railway.app/",
                },
            }
        ]
    )

    setattr(llm.proxy.proxy_server, "llm_router", llm_router)

    response = await token_counter(
        request=TokenCountRequest(
            model="special-alias",
            messages=[{"role": "user", "content": "hello"}],
        )
    )

    print("response: ", response)

    assert (
        response.tokenizer_type == "openai_tokenizer"
    )  # SHOULD use the default tokenizer
    assert response.model_used == "wolfram/miquliz-120b-v2.0"


@pytest.mark.asyncio
async def test_token_counting_model_not_in_model_list():
    """
    Test Token counter - when a model is not in model_list
    -> should use the default OpenAI tokenizer
    """

    llm_router = Router(
        model_list=[
            {
                "model_name": "gpt-4",
                "llm_params": {
                    "model": "gpt-4",
                },
            }
        ]
    )

    setattr(llm.proxy.proxy_server, "llm_router", llm_router)

    response = await token_counter(
        request=TokenCountRequest(
            model="special-alias",
            messages=[{"role": "user", "content": "hello"}],
        )
    )

    print("response: ", response)

    assert (
        response.tokenizer_type == "openai_tokenizer"
    )  # SHOULD use the OpenAI tokenizer
    assert response.model_used == "special-alias"


@pytest.mark.asyncio
async def test_gpt_token_counting():
    """
    Test Token counter
    -> should work for gpt-4
    """

    llm_router = Router(
        model_list=[
            {
                "model_name": "gpt-4",
                "llm_params": {
                    "model": "gpt-4",
                },
            }
        ]
    )

    setattr(llm.proxy.proxy_server, "llm_router", llm_router)

    response = await token_counter(
        request=TokenCountRequest(
            model="gpt-4",
            messages=[{"role": "user", "content": "hello"}],
        )
    )

    print("response: ", response)

    assert (
        response.tokenizer_type == "openai_tokenizer"
    )  # SHOULD use the OpenAI tokenizer
    assert response.request_model == "gpt-4"
