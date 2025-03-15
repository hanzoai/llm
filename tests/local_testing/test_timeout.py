#### What this tests ####
#    This tests the timeout decorator

import os
import sys
import traceback

sys.path.insert(
    0, os.path.abspath("../..")
)  # Adds the parent directory to the system path
import time
import uuid

import httpx
import openai
import pytest

import llm


@pytest.mark.parametrize(
    "model, provider",
    [
        ("gpt-3.5-turbo", "openai"),
        ("anthropic.claude-instant-v1", "bedrock"),
        ("azure/chatgpt-v-2", "azure"),
    ],
)
@pytest.mark.parametrize("sync_mode", [True, False])
@pytest.mark.asyncio
async def test_httpx_timeout(model, provider, sync_mode):
    """
    Test if setting httpx.timeout works for completion calls
    """
    timeout_val = httpx.Timeout(10.0, connect=60.0)

    messages = [{"role": "user", "content": "Hey, how's it going?"}]

    if sync_mode:
        response = llm.completion(
            model=model, messages=messages, timeout=timeout_val
        )
    else:
        response = await llm.acompletion(
            model=model, messages=messages, timeout=timeout_val
        )

    print(f"response: {response}")


def test_timeout():
    # this Will Raise a timeout
    llm.set_verbose = False
    try:
        response = llm.completion(
            model="gpt-3.5-turbo",
            timeout=0.01,
            messages=[{"role": "user", "content": "hello, write a 20 pg essay"}],
        )
    except openai.APITimeoutError as e:
        print(
            "Passed: Raised correct exception. Got openai.APITimeoutError\nGood Job", e
        )
        print(type(e))
        pass
    except Exception as e:
        pytest.fail(
            f"Did not raise error `openai.APITimeoutError`. Instead raised error type: {type(e)}, Error: {e}"
        )


# test_timeout()


def test_bedrock_timeout():
    # this Will Raise a timeout
    llm.set_verbose = True
    try:
        response = llm.completion(
            model="bedrock/anthropic.claude-instant-v1",
            timeout=0.01,
            messages=[{"role": "user", "content": "hello, write a 20 pg essay"}],
        )
        pytest.fail("Did not raise error `openai.APITimeoutError`")
    except openai.APITimeoutError as e:
        print(
            "Passed: Raised correct exception. Got openai.APITimeoutError\nGood Job", e
        )
        print(type(e))
        pass
    except Exception as e:
        pytest.fail(
            f"Did not raise error `openai.APITimeoutError`. Instead raised error type: {type(e)}, Error: {e}"
        )


def test_hanging_request_azure():
    llm.set_verbose = True
    import asyncio

    try:
        router = llm.Router(
            model_list=[
                {
                    "model_name": "azure-gpt",
                    "llm_params": {
                        "model": "azure/chatgpt-v-2",
                        "api_base": os.environ["AZURE_API_BASE"],
                        "api_key": os.environ["AZURE_API_KEY"],
                    },
                },
                {
                    "model_name": "openai-gpt",
                    "llm_params": {"model": "gpt-3.5-turbo"},
                },
            ],
            num_retries=0,
        )

        encoded = llm.utils.encode(model="gpt-3.5-turbo", text="blue")[0]

        async def _test():
            response = await router.acompletion(
                model="azure-gpt",
                messages=[
                    {"role": "user", "content": f"what color is red {uuid.uuid4()}"}
                ],
                logit_bias={encoded: 100},
                timeout=0.01,
            )
            print(response)
            return response

        response = asyncio.run(_test())

        if response.choices[0].message.content is not None:
            pytest.fail("Got a response, expected a timeout")
    except openai.APITimeoutError as e:
        print(
            "Passed: Raised correct exception. Got openai.APITimeoutError\nGood Job", e
        )
        print(type(e))
        pass
    except Exception as e:
        pytest.fail(
            f"Did not raise error `openai.APITimeoutError`. Instead raised error type: {type(e)}, Error: {e}"
        )


# test_hanging_request_azure()


def test_hanging_request_openai():
    llm.set_verbose = True
    try:
        router = llm.Router(
            model_list=[
                {
                    "model_name": "azure-gpt",
                    "llm_params": {
                        "model": "azure/chatgpt-v-2",
                        "api_base": os.environ["AZURE_API_BASE"],
                        "api_key": os.environ["AZURE_API_KEY"],
                    },
                },
                {
                    "model_name": "openai-gpt",
                    "llm_params": {"model": "gpt-3.5-turbo"},
                },
            ],
            num_retries=0,
        )

        encoded = llm.utils.encode(model="gpt-3.5-turbo", text="blue")[0]
        response = router.completion(
            model="openai-gpt",
            messages=[{"role": "user", "content": "what color is red"}],
            logit_bias={encoded: 100},
            timeout=0.01,
        )
        print(response)

        if response.choices[0].message.content is not None:
            pytest.fail("Got a response, expected a timeout")
    except openai.APITimeoutError as e:
        print(
            "Passed: Raised correct exception. Got openai.APITimeoutError\nGood Job", e
        )
        print(type(e))
        pass
    except Exception as e:
        pytest.fail(
            f"Did not raise error `openai.APITimeoutError`. Instead raised error type: {type(e)}, Error: {e}"
        )


# test_hanging_request_openai()

# test_timeout()


def test_timeout_streaming():
    # this Will Raise a timeout
    llm.set_verbose = False
    try:
        response = llm.completion(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "hello, write a 20 pg essay"}],
            timeout=0.0001,
            stream=True,
        )
        for chunk in response:
            print(chunk)
    except openai.APITimeoutError as e:
        print(
            "Passed: Raised correct exception. Got openai.APITimeoutError\nGood Job", e
        )
        print(type(e))
        pass
    except Exception as e:
        pytest.fail(
            f"Did not raise error `openai.APITimeoutError`. Instead raised error type: {type(e)}, Error: {e}"
        )


# test_timeout_streaming()


@pytest.mark.skip(reason="local test")
def test_timeout_ollama():
    # this Will Raise a timeout
    import llm

    llm.set_verbose = True
    try:
        llm.request_timeout = 0.1
        llm.set_verbose = True
        response = llm.completion(
            model="ollama/phi",
            messages=[{"role": "user", "content": "hello, what llm are u"}],
            max_tokens=1,
            api_base="https://test-ollama-endpoint.onrender.com",
        )
        # Add any assertions here to check the response
        llm.request_timeout = None
        print(response)
    except openai.APITimeoutError as e:
        print("got a timeout error! Passed ! ")
        pass


# test_timeout_ollama()


@pytest.mark.parametrize("streaming", [True, False])
@pytest.mark.parametrize("sync_mode", [True, False])
@pytest.mark.asyncio
async def test_anthropic_timeout(streaming, sync_mode):
    llm.set_verbose = False

    try:
        if sync_mode:
            response = llm.completion(
                model="claude-3-5-sonnet-20240620",
                timeout=0.01,
                messages=[{"role": "user", "content": "hello, write a 20 pg essay"}],
                stream=streaming,
            )
            if isinstance(response, llm.CustomStreamWrapper):
                for chunk in response:
                    pass
        else:
            response = await llm.acompletion(
                model="claude-3-5-sonnet-20240620",
                timeout=0.01,
                messages=[{"role": "user", "content": "hello, write a 20 pg essay"}],
                stream=streaming,
            )
            if isinstance(response, llm.CustomStreamWrapper):
                async for chunk in response:
                    pass
        pytest.fail("Did not raise error `openai.APITimeoutError`")
    except openai.APITimeoutError as e:
        print(
            "Passed: Raised correct exception. Got openai.APITimeoutError\nGood Job", e
        )
        print(type(e))
        pass
