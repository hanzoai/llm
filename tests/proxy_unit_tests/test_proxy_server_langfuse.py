import os
import sys
import traceback

from dotenv import load_dotenv

load_dotenv()
import io
import os

# this file is to test llm/proxy

sys.path.insert(
    0, os.path.abspath("../..")
)  # Adds the parent directory to the system path
import logging

import pytest

import llm
from llm import RateLimitError, Timeout, completion, completion_cost, embedding

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Set the desired logging level
    format="%(asctime)s - %(levelname)s - %(message)s",
)

from fastapi import FastAPI

# test /chat/completion request to the proxy
from fastapi.testclient import TestClient

from llm.proxy.proxy_server import (  # Replace with the actual module where your FastAPI router is defined
    router,
    save_worker_config,
)

filepath = os.path.dirname(os.path.abspath(__file__))
config_fp = f"{filepath}/test_configs/test_config.yaml"
save_worker_config(
    config=config_fp,
    model=None,
    alias=None,
    api_base=None,
    api_version=None,
    debug=False,
    temperature=None,
    max_tokens=None,
    request_timeout=600,
    max_budget=None,
    telemetry=False,
    drop_params=True,
    add_function_to_prompt=False,
    headers=None,
    save=False,
    use_queue=False,
)
app = FastAPI()
app.include_router(router)  # Include your router in the test app


# Here you create a fixture that will be used by your tests
# Make sure the fixture returns TestClient(app)
@pytest.fixture(autouse=True)
def client():
    with TestClient(app) as client:
        yield client


@pytest.mark.skip(
    reason="Init multiple Langfuse clients causing OOM issues. Reduce init clients on ci/cd. "
)
def test_chat_completion(client):
    try:
        # Your test data
        test_data = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {"role": "user", "content": "hi"},
            ],
            "max_tokens": 10,
        }
        print("testing proxy server")
        headers = {"Authorization": f"Bearer {os.getenv('PROXY_MASTER_KEY')}"}
        response = client.post("/v1/chat/completions", json=test_data, headers=headers)
        print(f"response - {response.text}")
        assert response.status_code == 200
        result = response.json()
        print(f"Received response: {result}")
    except Exception as e:
        pytest.fail(f"LLM Proxy test failed. Exception - {str(e)}")
