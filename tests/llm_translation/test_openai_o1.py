import json
import os
import sys
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock

sys.path.insert(
    0, os.path.abspath("../..")
)  # Adds the parent directory to the system path


import httpx
import pytest
from respx import MockRouter

import llm
from llm import Choices, Message, ModelResponse
from base_llm_unit_tests import BaseLLMChatTest, BaseOSeriesModelsTest


@pytest.mark.parametrize("model", ["o1-preview", "o1-mini", "o1"])
@pytest.mark.asyncio
async def test_o1_handle_system_role(model):
    """
    Tests that:
    - max_tokens is translated to 'max_completion_tokens'
    - role 'system' is translated to 'user'
    """
    from openai import AsyncOpenAI
    from llm.utils import supports_system_messages

    os.environ["LLM_LOCAL_MODEL_COST_MAP"] = "True"
    llm.model_cost = llm.get_model_cost_map(url="")

    llm.set_verbose = True

    client = AsyncOpenAI(api_key="fake-api-key")

    with patch.object(
        client.chat.completions.with_raw_response, "create"
    ) as mock_client:
        try:
            await llm.acompletion(
                model=model,
                max_tokens=10,
                messages=[{"role": "system", "content": "Be a good bot!"}],
                client=client,
            )
        except Exception as e:
            print(f"Error: {e}")

        mock_client.assert_called_once()
        request_body = mock_client.call_args.kwargs

        print("request_body: ", request_body)

        assert request_body["model"] == model
        assert request_body["max_completion_tokens"] == 10
        if supports_system_messages(model, "openai"):
            assert request_body["messages"] == [
                {"role": "system", "content": "Be a good bot!"}
            ]
        else:
            assert request_body["messages"] == [
                {"role": "user", "content": "Be a good bot!"}
            ]


@pytest.mark.parametrize(
    "model, expected_tool_calling_support",
    [("o1-preview", False), ("o1-mini", False), ("o1", True)],
)
@pytest.mark.asyncio
async def test_o1_handle_tool_calling_optional_params(
    model, expected_tool_calling_support
):
    """
    Tests that:
    - max_tokens is translated to 'max_completion_tokens'
    - role 'system' is translated to 'user'
    """
    from openai import AsyncOpenAI
    from llm.utils import ProviderConfigManager
    from llm.types.utils import LlmProviders

    os.environ["LLM_LOCAL_MODEL_COST_MAP"] = "True"
    llm.model_cost = llm.get_model_cost_map(url="")

    config = ProviderConfigManager.get_provider_chat_config(
        model=model, provider=LlmProviders.OPENAI
    )

    supported_params = config.get_supported_openai_params(model=model)

    assert expected_tool_calling_support == ("tools" in supported_params)


@pytest.mark.asyncio
@pytest.mark.parametrize("model", ["gpt-4", "gpt-4-0314", "gpt-4-32k", "o1-preview"])
async def test_o1_max_completion_tokens(model: str):
    """
    Tests that:
    - max_completion_tokens is passed directly to OpenAI chat completion models
    """
    from openai import AsyncOpenAI

    llm.set_verbose = True

    client = AsyncOpenAI(api_key="fake-api-key")

    with patch.object(
        client.chat.completions.with_raw_response, "create"
    ) as mock_client:
        try:
            await llm.acompletion(
                model=model,
                max_completion_tokens=10,
                messages=[{"role": "user", "content": "Hello!"}],
                client=client,
            )
        except Exception as e:
            print(f"Error: {e}")

        mock_client.assert_called_once()
        request_body = mock_client.call_args.kwargs

        print("request_body: ", request_body)

        assert request_body["model"] == model
        assert request_body["max_completion_tokens"] == 10
        assert request_body["messages"] == [{"role": "user", "content": "Hello!"}]


def test_llm_responses():
    """
    ensures that type of completion_tokens_details is correctly handled / returned
    """
    from llm import ModelResponse
    from llm.types.utils import CompletionTokensDetails

    response = ModelResponse(
        usage={
            "completion_tokens": 436,
            "prompt_tokens": 14,
            "total_tokens": 450,
            "completion_tokens_details": {"reasoning_tokens": 0},
        }
    )

    print("response: ", response)

    assert isinstance(response.usage.completion_tokens_details, CompletionTokensDetails)


class TestOpenAIO1(BaseOSeriesModelsTest, BaseLLMChatTest):
    def get_base_completion_call_args(self):
        return {
            "model": "o1",
        }

    def get_client(self):
        from openai import OpenAI

        return OpenAI(api_key="fake-api-key")

    def test_tool_call_no_arguments(self, tool_call_no_arguments):
        """Test that tool calls with no arguments is translated correctly. Relevant issue: https://github.com/BerriAI/llm/issues/6833"""
        pass

    def test_prompt_caching(self):
        """Temporary override. o1 prompt caching is not working."""
        pass


class TestOpenAIO3(BaseOSeriesModelsTest, BaseLLMChatTest):
    def get_base_completion_call_args(self):
        return {
            "model": "o3-mini",
        }

    def get_client(self):
        from openai import OpenAI

        return OpenAI(api_key="fake-api-key")

    def test_tool_call_no_arguments(self, tool_call_no_arguments):
        """Test that tool calls with no arguments is translated correctly. Relevant issue: https://github.com/BerriAI/llm/issues/6833"""
        pass


def test_o1_supports_vision():
    """Test that o1 supports vision"""
    os.environ["LLM_LOCAL_MODEL_COST_MAP"] = "True"
    llm.model_cost = llm.get_model_cost_map(url="")
    for k, v in llm.model_cost.items():
        if k.startswith("o1") and v.get("llm_provider") == "openai":
            assert v.get("supports_vision") is True, f"{k} does not support vision"


def test_o3_reasoning_effort():
    resp = llm.completion(
        model="o3-mini",
        messages=[{"role": "user", "content": "Hello!"}],
        reasoning_effort="high",
    )
    assert resp.choices[0].message.content is not None


@pytest.mark.parametrize("model", ["o1-preview", "o1-mini", "o1", "o3-mini"])
def test_streaming_response(model):
    """Test that streaming response is returned correctly"""
    from llm import completion

    response = completion(
        model=model,
        messages=[
            {"role": "system", "content": "Be a good bot!"},
            {"role": "user", "content": "Hello!"},
        ],
        stream=True,
    )

    assert response is not None

    chunks = []
    for chunk in response:
        chunks.append(chunk)

    resp = llm.stream_chunk_builder(chunks=chunks)
    print(resp)
