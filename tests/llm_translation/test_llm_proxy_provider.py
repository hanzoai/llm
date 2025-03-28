import json
import os
import sys
from datetime import datetime
from unittest.mock import AsyncMock

sys.path.insert(
    0, os.path.abspath("../..")
)  # Adds the parent directory to the system-path

import llm
from llm import completion, embedding
import pytest
from unittest.mock import MagicMock, patch
from llm.llms.custom_httpx.http_handler import HTTPHandler, AsyncHTTPHandler
import pytest_asyncio
from openai import AsyncOpenAI


@pytest.mark.asyncio
async def test_llm_gateway_from_sdk():
    llm.set_verbose = True
    messages = [
        {
            "role": "user",
            "content": "Hello world",
        }
    ]
    from openai import OpenAI

    openai_client = OpenAI(api_key="fake-key")

    with patch.object(
        openai_client.chat.completions, "create", new=MagicMock()
    ) as mock_call:
        try:
            completion(
                model="llm_proxy/my-vllm-model",
                messages=messages,
                response_format={"type": "json_object"},
                client=openai_client,
                api_base="my-custom-api-base",
                hello="world",
            )
        except Exception as e:
            print(e)

        mock_call.assert_called_once()

        print("Call KWARGS - {}".format(mock_call.call_args.kwargs))

        assert "hello" in mock_call.call_args.kwargs["extra_body"]


@pytest.mark.asyncio
async def test_llm_gateway_from_sdk_structured_output():
    from pydantic import BaseModel

    class Result(BaseModel):
        answer: str

    llm.set_verbose = True
    from openai import OpenAI

    openai_client = OpenAI(api_key="fake-key")

    with patch.object(
        openai_client.chat.completions, "create", new=MagicMock()
    ) as mock_call:
        try:
            llm.completion(
                model="llm_proxy/openai/gpt-4o",
                messages=[
                    {"role": "user", "content": "What is the capital of France?"}
                ],
                api_key="my-test-api-key",
                user="test",
                response_format=Result,
                base_url="https://llm.ml-serving-internal.scale.com",
                client=openai_client,
            )
        except Exception as e:
            print(e)

        mock_call.assert_called_once()

        print("Call KWARGS - {}".format(mock_call.call_args.kwargs))
        json_schema = mock_call.call_args.kwargs["response_format"]
        assert "json_schema" in json_schema


@pytest.mark.parametrize("is_async", [False, True])
@pytest.mark.asyncio
async def test_llm_gateway_from_sdk_embedding(is_async):
    llm.set_verbose = True
    llm._turn_on_debug()

    if is_async:
        from openai import AsyncOpenAI

        openai_client = AsyncOpenAI(api_key="fake-key")
        mock_method = AsyncMock()
        patch_target = openai_client.embeddings.create
    else:
        from openai import OpenAI

        openai_client = OpenAI(api_key="fake-key")
        mock_method = MagicMock()
        patch_target = openai_client.embeddings.create

    with patch.object(patch_target.__self__, patch_target.__name__, new=mock_method):
        try:
            if is_async:
                await llm.aembedding(
                    model="llm_proxy/my-vllm-model",
                    input="Hello world",
                    client=openai_client,
                    api_base="my-custom-api-base",
                )
            else:
                llm.embedding(
                    model="llm_proxy/my-vllm-model",
                    input="Hello world",
                    client=openai_client,
                    api_base="my-custom-api-base",
                )
        except Exception as e:
            print(e)

        mock_method.assert_called_once()

        print("Call KWARGS - {}".format(mock_method.call_args.kwargs))

        assert "Hello world" == mock_method.call_args.kwargs["input"]
        assert "my-vllm-model" == mock_method.call_args.kwargs["model"]


@pytest.mark.parametrize("is_async", [False, True])
@pytest.mark.asyncio
async def test_llm_gateway_from_sdk_image_generation(is_async):
    llm._turn_on_debug()

    if is_async:
        from openai import AsyncOpenAI

        openai_client = AsyncOpenAI(api_key="fake-key")
        mock_method = AsyncMock()
        patch_target = openai_client.images.generate
    else:
        from openai import OpenAI

        openai_client = OpenAI(api_key="fake-key")
        mock_method = MagicMock()
        patch_target = openai_client.images.generate

    with patch.object(patch_target.__self__, patch_target.__name__, new=mock_method):
        try:
            if is_async:
                response = await hanzo.aimage_generation(
                    model="llm_proxy/dall-e-3",
                    prompt="A beautiful sunset over mountains",
                    client=openai_client,
                    api_base="my-custom-api-base",
                )
            else:
                response = llm.image_generation(
                    model="llm_proxy/dall-e-3",
                    prompt="A beautiful sunset over mountains",
                    client=openai_client,
                    api_base="my-custom-api-base",
                )
            print("response=", response)
        except Exception as e:
            print("got error", e)

        mock_method.assert_called_once()

        print("Call KWARGS - {}".format(mock_method.call_args.kwargs))

        assert (
            "A beautiful sunset over mountains"
            == mock_method.call_args.kwargs["prompt"]
        )
        assert "dall-e-3" == mock_method.call_args.kwargs["model"]


@pytest.mark.parametrize("is_async", [False, True])
@pytest.mark.asyncio
async def test_llm_gateway_from_sdk_transcription(is_async):
    llm.set_verbose = True
    llm._turn_on_debug()

    if is_async:
        from openai import AsyncOpenAI

        openai_client = AsyncOpenAI(api_key="fake-key")
        mock_method = AsyncMock()
        patch_target = openai_client.audio.transcriptions.create
    else:
        from openai import OpenAI

        openai_client = OpenAI(api_key="fake-key")
        mock_method = MagicMock()
        patch_target = openai_client.audio.transcriptions.create

    with patch.object(patch_target.__self__, patch_target.__name__, new=mock_method):
        try:
            if is_async:
                await llm.atranscription(
                    model="llm_proxy/whisper-1",
                    file=b"sample_audio",
                    client=openai_client,
                    api_base="my-custom-api-base",
                )
            else:
                llm.transcription(
                    model="llm_proxy/whisper-1",
                    file=b"sample_audio",
                    client=openai_client,
                    api_base="my-custom-api-base",
                )
        except Exception as e:
            print(e)

        mock_method.assert_called_once()

        print("Call KWARGS - {}".format(mock_method.call_args.kwargs))

        assert "whisper-1" == mock_method.call_args.kwargs["model"]


@pytest.mark.parametrize("is_async", [False, True])
@pytest.mark.asyncio
async def test_llm_gateway_from_sdk_speech(is_async):
    llm.set_verbose = True

    if is_async:
        from openai import AsyncOpenAI

        openai_client = AsyncOpenAI(api_key="fake-key")
        mock_method = AsyncMock()
        patch_target = openai_client.audio.speech.create
    else:
        from openai import OpenAI

        openai_client = OpenAI(api_key="fake-key")
        mock_method = MagicMock()
        patch_target = openai_client.audio.speech.create

    with patch.object(patch_target.__self__, patch_target.__name__, new=mock_method):
        try:
            if is_async:
                await llm.aspeech(
                    model="llm_proxy/tts-1",
                    input="Hello, this is a test of text to speech",
                    voice="alloy",
                    client=openai_client,
                    api_base="my-custom-api-base",
                )
            else:
                llm.speech(
                    model="llm_proxy/tts-1",
                    input="Hello, this is a test of text to speech",
                    voice="alloy",
                    client=openai_client,
                    api_base="my-custom-api-base",
                )
        except Exception as e:
            print(e)

        mock_method.assert_called_once()

        print("Call KWARGS - {}".format(mock_method.call_args.kwargs))

        assert (
            "Hello, this is a test of text to speech"
            == mock_method.call_args.kwargs["input"]
        )
        assert "tts-1" == mock_method.call_args.kwargs["model"]
        assert "alloy" == mock_method.call_args.kwargs["voice"]


@pytest.mark.parametrize("is_async", [False, True])
@pytest.mark.asyncio
async def test_llm_gateway_from_sdk_rerank(is_async):
    llm.set_verbose = True
    llm._turn_on_debug()

    if is_async:
        client = AsyncHTTPHandler()
        mock_method = AsyncMock()
        patch_target = client.post
    else:
        client = HTTPHandler()
        mock_method = MagicMock()
        patch_target = client.post

    with patch.object(client, "post", new=mock_method):
        mock_response = MagicMock()

        # Create a mock response similar to OpenAI's rerank response
        mock_response.text = json.dumps(
            {
                "id": "rerank-123456",
                "object": "reranking",
                "results": [
                    {
                        "index": 0,
                        "relevance_score": 0.9,
                        "document": {
                            "id": "0",
                            "text": "Machine learning is a field of study in artificial intelligence",
                        },
                    },
                    {
                        "index": 1,
                        "relevance_score": 0.2,
                        "document": {
                            "id": "1",
                            "text": "Biology is the study of living organisms",
                        },
                    },
                ],
                "model": "rerank-english-v2.0",
                "usage": {"prompt_tokens": 10, "total_tokens": 10},
            }
        )

        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.json = lambda: json.loads(mock_response.text)

        if is_async:
            mock_method.return_value = mock_response
        else:
            mock_method.return_value = mock_response

        try:
            if is_async:
                response = await llm.arerank(
                    model="llm_proxy/rerank-english-v2.0",
                    query="What is machine learning?",
                    documents=[
                        "Machine learning is a field of study in artificial intelligence",
                        "Biology is the study of living organisms",
                    ],
                    client=client,
                    api_base="my-custom-api-base",
                )
            else:
                response = llm.rerank(
                    model="llm_proxy/rerank-english-v2.0",
                    query="What is machine learning?",
                    documents=[
                        "Machine learning is a field of study in artificial intelligence",
                        "Biology is the study of living organisms",
                    ],
                    client=client,
                    api_base="my-custom-api-base",
                )
        except Exception as e:
            print(e)

        # Verify the request
        mock_method.assert_called_once()
        call_args = mock_method.call_args
        print("call_args=", call_args)

        # Check that the URL is correct
        assert "my-custom-api-base/v1/rerank" == call_args.kwargs["url"]

        # Check that the request body contains the expected data
        request_body = json.loads(call_args.kwargs["data"])
        assert request_body["query"] == "What is machine learning?"
        assert request_body["model"] == "rerank-english-v2.0"
        assert len(request_body["documents"]) == 2
