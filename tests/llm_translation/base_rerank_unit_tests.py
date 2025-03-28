import asyncio
import httpx
import json
import pytest
import sys
from typing import Any, Dict, List
from unittest.mock import MagicMock, Mock, patch
import os

sys.path.insert(
    0, os.path.abspath("../..")
)  # Adds the parent directory to the system path
import llm
from llm.exceptions import BadRequestError
from llm.llms.custom_httpx.http_handler import AsyncHTTPHandler, HTTPHandler
from llm.utils import (
    CustomStreamWrapper,
    get_supported_openai_params,
    get_optional_params,
)

# test_example.py
from abc import ABC, abstractmethod


def assert_response_shape(response, custom_llm_provider):
    expected_response_shape = {"id": str, "results": list, "meta": dict}

    expected_results_shape = {"index": int, "relevance_score": float}

    expected_meta_shape = {"api_version": dict, "billed_units": dict}

    expected_api_version_shape = {"version": str}

    expected_billed_units_shape = {"search_units": int}
    expected_billed_units_total_tokens_shape = {"total_tokens": int}

    assert isinstance(response.id, expected_response_shape["id"])
    assert isinstance(response.results, expected_response_shape["results"])
    for result in response.results:
        assert isinstance(result["index"], expected_results_shape["index"])
        assert isinstance(
            result["relevance_score"], expected_results_shape["relevance_score"]
        )
    assert isinstance(response.meta, expected_response_shape["meta"])

    if custom_llm_provider == "cohere":

        assert isinstance(
            response.meta["api_version"], expected_meta_shape["api_version"]
        )
        assert isinstance(
            response.meta["api_version"]["version"],
            expected_api_version_shape["version"],
        )
    assert isinstance(
        response.meta["billed_units"], expected_meta_shape["billed_units"]
    )
    if "total_tokens" in response.meta["billed_units"]:
        assert isinstance(
            response.meta["billed_units"]["total_tokens"],
            expected_billed_units_total_tokens_shape["total_tokens"],
        )
    else:
        assert isinstance(
            response.meta["billed_units"]["search_units"],
            expected_billed_units_shape["search_units"],
        )


class BaseLLMRerankTest(ABC):
    """
    Abstract base test class that enforces a common test across all test classes.
    """

    @abstractmethod
    def get_base_rerank_call_args(self) -> dict:
        """Must return the base rerank call args"""
        pass

    @abstractmethod
    def get_custom_llm_provider(self) -> llm.LLMProviders:
        """Must return the custom llm provider"""
        pass

    @pytest.mark.asyncio()
    @pytest.mark.parametrize("sync_mode", [True, False])
    async def test_basic_rerank(self, sync_mode):
        llm._turn_on_debug()
        os.environ["LLM_LOCAL_MODEL_COST_MAP"] = "True"
        llm.model_cost = llm.get_model_cost_map(url="")
        rerank_call_args = self.get_base_rerank_call_args()
        custom_llm_provider = self.get_custom_llm_provider()
        if sync_mode is True:
            response = llm.rerank(
                **rerank_call_args,
                query="hello",
                documents=["hello", "world"],
                top_n=2,
            )

            print("re rank response: ", response)

            assert response.id is not None
            assert response.results is not None

            assert response._hidden_params["response_cost"] is not None
            assert response._hidden_params["response_cost"] > 0

            assert_response_shape(
                response=response, custom_llm_provider=custom_llm_provider.value
            )
        else:
            response = await llm.arerank(
                **rerank_call_args,
                query="hello",
                documents=["hello", "world"],
                top_n=2,
            )

            print("async re rank response: ", response)

            assert response.id is not None
            assert response.results is not None

            assert_response_shape(
                response=response, custom_llm_provider=custom_llm_provider.value
            )
