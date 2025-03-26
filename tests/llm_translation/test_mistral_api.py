import asyncio
import os
import sys
import traceback

from dotenv import load_dotenv

import llm.types
import llm.types.utils
from llm.llms.anthropic.chat import ModelResponseIterator

load_dotenv()
import io
import os

sys.path.insert(
    0, os.path.abspath("../..")
)  # Adds the parent directory to the system path
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest

import llm

from llm.llms.anthropic.common_utils import process_anthropic_headers
from httpx import Headers
from base_llm_unit_tests import BaseLLMChatTest


class TestMistralCompletion(BaseLLMChatTest):
    def get_base_completion_call_args(self) -> dict:
        llm.set_verbose = True
        return {"model": "mistral/mistral-small-latest"}

    def test_tool_call_no_arguments(self, tool_call_no_arguments):
        """Test that tool calls with no arguments is translated correctly. Relevant issue: https://github.com/BerriAI/llm/issues/6833"""
        pass

    def test_multilingual_requests(self):
        """
        Mistral API raises a 400 BadRequest error when the request contains invalid utf-8 sequences.
        """
        pass
