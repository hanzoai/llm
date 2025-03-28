import json
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

import os
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from openai import OpenAI
from openai.types.chat import ChatCompletionMessage
from openai.types.chat.chat_completion import ChatCompletion, Choice
from respx import MockRouter

import llm
from llm import RateLimitError, Timeout, completion, completion_cost, embedding
from llm.llms.custom_httpx.http_handler import AsyncHTTPHandler, HTTPHandler
from llm.llm_core_utils.prompt_templates.factory import anthropic_messages_pt
from llm.router import Router


@pytest.mark.asyncio()
@pytest.mark.respx()
async def test_aaaaazure_tenant_id_auth(respx_mock: MockRouter):
    """

    Tests when we set  tenant_id, client_id, client_secret they don't get sent with the request

    PROD Test
    """

    router = Router(
        model_list=[
            {
                "model_name": "gpt-3.5-turbo",
                "llm_params": {  # params for llm completion/embedding call
                    "model": "azure/chatgpt-v-2",
                    "api_base": os.getenv("AZURE_API_BASE"),
                    "tenant_id": os.getenv("AZURE_TENANT_ID"),
                    "client_id": os.getenv("AZURE_CLIENT_ID"),
                    "client_secret": os.getenv("AZURE_CLIENT_SECRET"),
                },
            },
        ],
    )

    mock_response = AsyncMock()
    obj = ChatCompletion(
        id="foo",
        model="gpt-4",
        object="chat.completion",
        choices=[
            Choice(
                finish_reason="stop",
                index=0,
                message=ChatCompletionMessage(
                    content="Hello world!",
                    role="assistant",
                ),
            )
        ],
        created=int(datetime.now().timestamp()),
    )
    llm.set_verbose = True

    mock_request = respx_mock.post(url__regex=r".*/chat/completions.*").mock(
        return_value=httpx.Response(200, json=obj.model_dump(mode="json"))
    )

    await router.acompletion(
        model="gpt-3.5-turbo", messages=[{"role": "user", "content": "Hello world!"}]
    )

    # Ensure all mocks were called
    respx_mock.assert_all_called()

    for call in mock_request.calls:
        print(call)
        print(call.request.content)

        json_body = json.loads(call.request.content)
        print(json_body)

        assert json_body == {
            "messages": [{"role": "user", "content": "Hello world!"}],
            "model": "chatgpt-v-2",
            "stream": False,
        }
