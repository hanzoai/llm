# What is this?
## unit tests for openai tts endpoint

import asyncio
import os
import random
import sys
import time
import traceback
import uuid

from dotenv import load_dotenv

load_dotenv()
import os

sys.path.insert(
    0, os.path.abspath("../..")
)  # Adds the parent directory to the system path
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import openai
import pytest

import llm


@pytest.mark.parametrize(
    "sync_mode",
    [True, False],
)
@pytest.mark.parametrize(
    "model, api_key, api_base",
    [
        (
            "azure/azure-tts",
            os.getenv("AZURE_SWEDEN_API_KEY"),
            os.getenv("AZURE_SWEDEN_API_BASE"),
        ),
        ("openai/tts-1", os.getenv("OPENAI_API_KEY"), None),
    ],
)  # ,
@pytest.mark.asyncio
@pytest.mark.flaky(retries=3, delay=1)
async def test_audio_speech_llm(sync_mode, model, api_base, api_key):
    speech_file_path = Path(__file__).parent / "speech.mp3"

    if sync_mode:
        response = llm.speech(
            model=model,
            voice="alloy",
            input="the quick brown fox jumped over the lazy dogs",
            api_base=api_base,
            api_key=api_key,
            organization=None,
            project=None,
            max_retries=1,
            timeout=600,
            client=None,
            optional_params={},
        )

        from llm.types.llms.openai import HttpxBinaryResponseContent

        assert isinstance(response, HttpxBinaryResponseContent)
    else:
        response = await llm.aspeech(
            model=model,
            voice="alloy",
            input="the quick brown fox jumped over the lazy dogs",
            api_base=api_base,
            api_key=api_key,
            organization=None,
            project=None,
            max_retries=1,
            timeout=600,
            client=None,
            optional_params={},
        )

        from llm.llms.openai.openai import HttpxBinaryResponseContent

        assert isinstance(response, HttpxBinaryResponseContent)


@pytest.mark.parametrize(
    "sync_mode",
    [False, True],
)
@pytest.mark.skip(reason="local only test - we run testing using MockRequests below")
@pytest.mark.asyncio
@pytest.mark.flaky(retries=3, delay=1)
async def test_audio_speech_llm_vertex(sync_mode):
    llm.set_verbose = True
    speech_file_path = Path(__file__).parent / "speech_vertex.mp3"
    model = "vertex_ai/test"
    if sync_mode:
        response = llm.speech(
            model="vertex_ai/test",
            input="hello what llm guardrail do you have",
        )

        response.stream_to_file(speech_file_path)

    else:
        response = await llm.aspeech(
            model="vertex_ai/",
            input="async hello what llm guardrail do you have",
        )

        from types import SimpleNamespace

        from llm.llms.openai.openai import HttpxBinaryResponseContent

        response.stream_to_file(speech_file_path)


@pytest.mark.flaky(retries=6, delay=2)
@pytest.mark.asyncio
async def test_speech_llm_vertex_async():
    # Mock the response
    mock_response = AsyncMock()

    def return_val():
        return {
            "audioContent": "dGVzdCByZXNwb25zZQ==",
        }

    mock_response.json = return_val
    mock_response.status_code = 200

    # Set up the mock for asynchronous calls
    with patch(
        "llm.llms.custom_httpx.http_handler.AsyncHTTPHandler.post",
        new_callable=AsyncMock,
    ) as mock_async_post:
        mock_async_post.return_value = mock_response
        model = "vertex_ai/test"

        try:
            response = await llm.aspeech(
                model=model,
                input="async hello what llm guardrail do you have",
            )
        except llm.APIConnectionError as e:
            if "Your default credentials were not found" in str(e):
                pytest.skip("skipping test, credentials not found")

        # Assert asynchronous call
        mock_async_post.assert_called_once()
        _, kwargs = mock_async_post.call_args
        print("call args", kwargs)

        assert kwargs["url"] == "https://texttospeech.googleapis.com/v1/text:synthesize"

        assert "x-goog-user-project" in kwargs["headers"]
        assert kwargs["headers"]["Authorization"] is not None

        assert kwargs["json"] == {
            "input": {"text": "async hello what llm guardrail do you have"},
            "voice": {"languageCode": "en-US", "name": "en-US-Studio-O"},
            "audioConfig": {"audioEncoding": "LINEAR16", "speakingRate": "1"},
        }


@pytest.mark.asyncio
async def test_speech_llm_vertex_async_with_voice():
    # Mock the response
    mock_response = AsyncMock()

    def return_val():
        return {
            "audioContent": "dGVzdCByZXNwb25zZQ==",
        }

    mock_response.json = return_val
    mock_response.status_code = 200

    # Set up the mock for asynchronous calls
    with patch(
        "llm.llms.custom_httpx.http_handler.AsyncHTTPHandler.post",
        new_callable=AsyncMock,
    ) as mock_async_post:
        mock_async_post.return_value = mock_response
        model = "vertex_ai/test"

        try:
            response = await llm.aspeech(
                model=model,
                input="async hello what llm guardrail do you have",
                voice={
                    "languageCode": "en-UK",
                    "name": "en-UK-Studio-O",
                },
                audioConfig={
                    "audioEncoding": "LINEAR22",
                    "speakingRate": "10",
                },
            )
        except llm.APIConnectionError as e:
            if "Your default credentials were not found" in str(e):
                pytest.skip("skipping test, credentials not found")

        # Assert asynchronous call
        mock_async_post.assert_called_once()
        _, kwargs = mock_async_post.call_args
        print("call args", kwargs)

        assert kwargs["url"] == "https://texttospeech.googleapis.com/v1/text:synthesize"

        assert "x-goog-user-project" in kwargs["headers"]
        assert kwargs["headers"]["Authorization"] is not None

        assert kwargs["json"] == {
            "input": {"text": "async hello what llm guardrail do you have"},
            "voice": {"languageCode": "en-UK", "name": "en-UK-Studio-O"},
            "audioConfig": {"audioEncoding": "LINEAR22", "speakingRate": "10"},
        }


@pytest.mark.asyncio
async def test_speech_llm_vertex_async_with_voice_ssml():
    # Mock the response
    mock_response = AsyncMock()

    def return_val():
        return {
            "audioContent": "dGVzdCByZXNwb25zZQ==",
        }

    mock_response.json = return_val
    mock_response.status_code = 200

    ssml = """
    <speak>
        <p>Hello, world!</p>
        <p>This is a test of the <break strength="medium" /> text-to-speech API.</p>
    </speak>
    """

    # Set up the mock for asynchronous calls
    with patch(
        "llm.llms.custom_httpx.http_handler.AsyncHTTPHandler.post",
        new_callable=AsyncMock,
    ) as mock_async_post:
        mock_async_post.return_value = mock_response
        model = "vertex_ai/test"

        try:
            response = await llm.aspeech(
                input=ssml,
                model=model,
                voice={
                    "languageCode": "en-UK",
                    "name": "en-UK-Studio-O",
                },
                audioConfig={
                    "audioEncoding": "LINEAR22",
                    "speakingRate": "10",
                },
            )
        except llm.APIConnectionError as e:
            if "Your default credentials were not found" in str(e):
                pytest.skip("skipping test, credentials not found")

        # Assert asynchronous call
        mock_async_post.assert_called_once()
        _, kwargs = mock_async_post.call_args
        print("call args", kwargs)

        assert kwargs["url"] == "https://texttospeech.googleapis.com/v1/text:synthesize"

        assert "x-goog-user-project" in kwargs["headers"]
        assert kwargs["headers"]["Authorization"] is not None

        assert kwargs["json"] == {
            "input": {"ssml": ssml},
            "voice": {"languageCode": "en-UK", "name": "en-UK-Studio-O"},
            "audioConfig": {"audioEncoding": "LINEAR22", "speakingRate": "10"},
        }


@pytest.mark.skip(reason="causes openai rate limit errors")
def test_audio_speech_cost_calc():
    from llm.integrations.custom_logger import CustomLogger

    model = "azure/azure-tts"
    api_base = os.getenv("AZURE_SWEDEN_API_BASE")
    api_key = os.getenv("AZURE_SWEDEN_API_KEY")

    custom_logger = CustomLogger()
    llm.set_verbose = True

    with patch.object(custom_logger, "log_success_event") as mock_cost_calc:
        llm.callbacks = [custom_logger]
        llm.speech(
            model=model,
            voice="alloy",
            input="the quick brown fox jumped over the lazy dogs",
            api_base=api_base,
            api_key=api_key,
            base_model="azure/tts-1",
        )

        time.sleep(1)

        mock_cost_calc.assert_called_once()

        print(
            f"mock_cost_calc.call_args: {mock_cost_calc.call_args.kwargs['kwargs'].keys()}"
        )
        standard_logging_payload = mock_cost_calc.call_args.kwargs["kwargs"][
            "standard_logging_object"
        ]
        print(f"standard_logging_payload: {standard_logging_payload}")
        assert standard_logging_payload["response_cost"] > 0
