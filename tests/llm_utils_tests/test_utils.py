import copy
import sys
import time
from datetime import datetime
from unittest import mock

from dotenv import load_dotenv

from llm.types.utils import StandardCallbackDynamicParams

load_dotenv()
import os

sys.path.insert(
    0, os.path.abspath("../..")
)  # Adds the parent directory to the system-path
import pytest

import llm
from llm.llms.custom_httpx.http_handler import AsyncHTTPHandler, headers
from llm.llm_core_utils.duration_parser import duration_in_seconds
from llm.llm_core_utils.duration_parser import (
    get_last_day_of_month,
    _extract_from_regex,
)
from llm.utils import (
    check_valid_key,
    create_pretrained_tokenizer,
    create_tokenizer,
    function_to_dict,
    get_llm_provider,
    get_max_tokens,
    get_supported_openai_params,
    get_token_count,
    get_valid_models,
    token_counter,
    trim_messages,
    validate_environment,
)
from unittest.mock import AsyncMock, MagicMock, patch


# Assuming your trim_messages, shorten_message_to_fit_limit, and get_token_count functions are all in a module named 'message_utils'


# Test 1: Check trimming of normal message
def test_basic_trimming():
    messages = [
        {
            "role": "user",
            "content": "This is a long message that definitely exceeds the token limit.",
        }
    ]
    trimmed_messages = trim_messages(messages, model="claude-2", max_tokens=8)
    print("trimmed messages")
    print(trimmed_messages)
    # print(get_token_count(messages=trimmed_messages, model="claude-2"))
    assert (get_token_count(messages=trimmed_messages, model="claude-2")) <= 8


# test_basic_trimming()


def test_basic_trimming_no_max_tokens_specified():
    messages = [
        {
            "role": "user",
            "content": "This is a long message that is definitely under the token limit.",
        }
    ]
    trimmed_messages = trim_messages(messages, model="gpt-4")
    print("trimmed messages for gpt-4")
    print(trimmed_messages)
    # print(get_token_count(messages=trimmed_messages, model="claude-2"))
    assert (
        get_token_count(messages=trimmed_messages, model="gpt-4")
    ) <= llm.model_cost["gpt-4"]["max_tokens"]


# test_basic_trimming_no_max_tokens_specified()


def test_multiple_messages_trimming():
    messages = [
        {
            "role": "user",
            "content": "This is a long message that will exceed the token limit.",
        },
        {
            "role": "user",
            "content": "This is another long message that will also exceed the limit.",
        },
    ]
    trimmed_messages = trim_messages(
        messages=messages, model="gpt-3.5-turbo", max_tokens=20
    )
    # print(get_token_count(messages=trimmed_messages, model="gpt-3.5-turbo"))
    assert (get_token_count(messages=trimmed_messages, model="gpt-3.5-turbo")) <= 20


# test_multiple_messages_trimming()


def test_multiple_messages_no_trimming():
    messages = [
        {
            "role": "user",
            "content": "This is a long message that will exceed the token limit.",
        },
        {
            "role": "user",
            "content": "This is another long message that will also exceed the limit.",
        },
    ]
    trimmed_messages = trim_messages(
        messages=messages, model="gpt-3.5-turbo", max_tokens=100
    )
    print("Trimmed messages")
    print(trimmed_messages)
    assert messages == trimmed_messages


# test_multiple_messages_no_trimming()


def test_large_trimming_multiple_messages():
    messages = [
        {"role": "user", "content": "This is a singlelongwordthatexceedsthelimit."},
        {"role": "user", "content": "This is a singlelongwordthatexceedsthelimit."},
        {"role": "user", "content": "This is a singlelongwordthatexceedsthelimit."},
        {"role": "user", "content": "This is a singlelongwordthatexceedsthelimit."},
        {"role": "user", "content": "This is a singlelongwordthatexceedsthelimit."},
    ]
    trimmed_messages = trim_messages(messages, max_tokens=20, model="gpt-4-0613")
    print("trimmed messages")
    print(trimmed_messages)
    assert (get_token_count(messages=trimmed_messages, model="gpt-4-0613")) <= 20


# test_large_trimming()


def test_large_trimming_single_message():
    messages = [
        {"role": "user", "content": "This is a singlelongwordthatexceedsthelimit."}
    ]
    trimmed_messages = trim_messages(messages, max_tokens=5, model="gpt-4-0613")
    assert (get_token_count(messages=trimmed_messages, model="gpt-4-0613")) <= 5
    assert (get_token_count(messages=trimmed_messages, model="gpt-4-0613")) > 0


def test_trimming_with_system_message_within_max_tokens():
    # This message is 33 tokens long
    messages = [
        {"role": "system", "content": "This is a short system message"},
        {
            "role": "user",
            "content": "This is a medium normal message, let's say llm is awesome.",
        },
    ]
    trimmed_messages = trim_messages(
        messages, max_tokens=30, model="gpt-4-0613"
    )  # The system message should fit within the token limit
    assert len(trimmed_messages) == 2
    assert trimmed_messages[0]["content"] == "This is a short system message"


def test_trimming_with_system_message_exceeding_max_tokens():
    # This message is 33 tokens long. The system message is 13 tokens long.
    messages = [
        {"role": "system", "content": "This is a short system message"},
        {
            "role": "user",
            "content": "This is a medium normal message, let's say llm is awesome.",
        },
    ]
    trimmed_messages = trim_messages(messages, max_tokens=12, model="gpt-4-0613")
    assert len(trimmed_messages) == 1


def test_trimming_with_tool_calls():
    from llm.types.utils import ChatCompletionMessageToolCall, Function, Message

    messages = [
        {
            "role": "user",
            "content": "What's the weather like in San Francisco, Tokyo, and Paris?",
        },
        Message(
            content=None,
            role="assistant",
            tool_calls=[
                ChatCompletionMessageToolCall(
                    function=Function(
                        arguments='{"location": "San Francisco, CA", "unit": "celsius"}',
                        name="get_current_weather",
                    ),
                    id="call_G11shFcS024xEKjiAOSt6Tc9",
                    type="function",
                ),
                ChatCompletionMessageToolCall(
                    function=Function(
                        arguments='{"location": "Tokyo, Japan", "unit": "celsius"}',
                        name="get_current_weather",
                    ),
                    id="call_e0ss43Bg7H8Z9KGdMGWyZ9Mj",
                    type="function",
                ),
                ChatCompletionMessageToolCall(
                    function=Function(
                        arguments='{"location": "Paris, France", "unit": "celsius"}',
                        name="get_current_weather",
                    ),
                    id="call_nRjLXkWTJU2a4l9PZAf5as6g",
                    type="function",
                ),
            ],
            function_call=None,
        ),
        {
            "tool_call_id": "call_G11shFcS024xEKjiAOSt6Tc9",
            "role": "tool",
            "name": "get_current_weather",
            "content": '{"location": "San Francisco", "temperature": "72", "unit": "fahrenheit"}',
        },
        {
            "tool_call_id": "call_e0ss43Bg7H8Z9KGdMGWyZ9Mj",
            "role": "tool",
            "name": "get_current_weather",
            "content": '{"location": "Tokyo", "temperature": "10", "unit": "celsius"}',
        },
        {
            "tool_call_id": "call_nRjLXkWTJU2a4l9PZAf5as6g",
            "role": "tool",
            "name": "get_current_weather",
            "content": '{"location": "Paris", "temperature": "22", "unit": "celsius"}',
        },
    ]
    result = trim_messages(messages=messages, max_tokens=1, return_response_tokens=True)

    print(result)

    assert len(result[0]) == 3  # final 3 messages are tool calls


def test_trimming_should_not_change_original_messages():
    messages = [
        {"role": "system", "content": "This is a short system message"},
        {
            "role": "user",
            "content": "This is a medium normal message, let's say llm is awesome.",
        },
    ]
    messages_copy = copy.deepcopy(messages)
    trimmed_messages = trim_messages(messages, max_tokens=12, model="gpt-4-0613")
    assert messages == messages_copy


@pytest.mark.parametrize("model", ["gpt-4-0125-preview", "claude-3-opus-20240229"])
def test_trimming_with_model_cost_max_input_tokens(model):
    messages = [
        {"role": "system", "content": "This is a normal system message"},
        {
            "role": "user",
            "content": "This is a sentence" * 100000,
        },
    ]
    trimmed_messages = trim_messages(messages, model=model)
    assert (
        get_token_count(trimmed_messages, model=model)
        < llm.model_cost[model]["max_input_tokens"]
    )


def test_aget_valid_models():
    old_environ = os.environ
    os.environ = {"OPENAI_API_KEY": "temp"}  # mock set only openai key in environ

    valid_models = get_valid_models()
    print(valid_models)

    # list of openai supported llms on llm
    expected_models = (
        llm.open_ai_chat_completion_models + llm.open_ai_text_completion_models
    )

    assert valid_models == expected_models

    # reset replicate env key
    os.environ = old_environ

    # GEMINI
    expected_models = llm.gemini_models
    old_environ = os.environ
    os.environ = {"GEMINI_API_KEY": "temp"}  # mock set only openai key in environ

    valid_models = get_valid_models()

    print(valid_models)
    assert valid_models == expected_models

    # reset replicate env key
    os.environ = old_environ


# test_get_valid_models()


def test_bad_key():
    key = "bad-key"
    response = check_valid_key(model="gpt-3.5-turbo", api_key=key)
    print(response, key)
    assert response == False


def test_good_key():
    key = os.environ["OPENAI_API_KEY"]
    response = check_valid_key(model="gpt-3.5-turbo", api_key=key)
    assert response == True


# test validate environment


def test_validate_environment_empty_model():
    api_key = validate_environment()
    if api_key is None:
        raise Exception()


def test_validate_environment_api_key():
    response_obj = validate_environment(model="gpt-3.5-turbo", api_key="sk-my-test-key")
    assert (
        response_obj["keys_in_environment"] is True
    ), f"Missing keys={response_obj['missing_keys']}"


def test_validate_environment_api_base_dynamic():
    for provider in ["ollama", "ollama_chat"]:
        kv = validate_environment(provider + "/mistral", api_base="https://example.com")
        assert kv["keys_in_environment"]
        assert kv["missing_keys"] == []


@mock.patch.dict(os.environ, {"OLLAMA_API_BASE": "foo"}, clear=True)
def test_validate_environment_ollama():
    for provider in ["ollama", "ollama_chat"]:
        kv = validate_environment(provider + "/mistral")
        assert kv["keys_in_environment"]
        assert kv["missing_keys"] == []


@mock.patch.dict(os.environ, {}, clear=True)
def test_validate_environment_ollama_failed():
    for provider in ["ollama", "ollama_chat"]:
        kv = validate_environment(provider + "/mistral")
        assert not kv["keys_in_environment"]
        assert kv["missing_keys"] == ["OLLAMA_API_BASE"]


def test_function_to_dict():
    print("testing function to dict for get current weather")

    def get_current_weather(location: str, unit: str):
        """Get the current weather in a given location

        Parameters
        ----------
        location : str
            The city and state, e.g. San Francisco, CA
        unit : {'celsius', 'fahrenheit'}
            Temperature unit

        Returns
        -------
        str
            a sentence indicating the weather
        """
        if location == "Boston, MA":
            return "The weather is 12F"

    function_json = llm.utils.function_to_dict(get_current_weather)
    print(function_json)

    expected_output = {
        "name": "get_current_weather",
        "description": "Get the current weather in a given location",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "The city and state, e.g. San Francisco, CA",
                },
                "unit": {
                    "type": "string",
                    "description": "Temperature unit",
                    "enum": "['fahrenheit', 'celsius']",
                },
            },
            "required": ["location", "unit"],
        },
    }
    print(expected_output)

    assert function_json["name"] == expected_output["name"]
    assert function_json["description"] == expected_output["description"]
    assert function_json["parameters"]["type"] == expected_output["parameters"]["type"]
    assert (
        function_json["parameters"]["properties"]["location"]
        == expected_output["parameters"]["properties"]["location"]
    )

    # the enum can change it can be - which is why we don't assert on unit
    # {'type': 'string', 'description': 'Temperature unit', 'enum': "['fahrenheit', 'celsius']"}
    # {'type': 'string', 'description': 'Temperature unit', 'enum': "['celsius', 'fahrenheit']"}

    assert (
        function_json["parameters"]["required"]
        == expected_output["parameters"]["required"]
    )

    print("passed")


# test_function_to_dict()


def test_token_counter():
    try:
        messages = [{"role": "user", "content": "hi how are you what time is it"}]
        tokens = token_counter(model="gpt-3.5-turbo", messages=messages)
        print("gpt-35-turbo")
        print(tokens)
        assert tokens > 0

        tokens = token_counter(model="claude-2", messages=messages)
        print("claude-2")
        print(tokens)
        assert tokens > 0

        tokens = token_counter(model="gemini/chat-bison", messages=messages)
        print("gemini/chat-bison")
        print(tokens)
        assert tokens > 0

        tokens = token_counter(model="ollama/llama2", messages=messages)
        print("ollama/llama2")
        print(tokens)
        assert tokens > 0

        tokens = token_counter(model="anthropic.claude-instant-v1", messages=messages)
        print("anthropic.claude-instant-v1")
        print(tokens)
        assert tokens > 0
    except Exception as e:
        pytest.fail(f"Error occurred: {e}")


# test_token_counter()


@pytest.mark.parametrize(
    "model, expected_bool",
    [
        ("gpt-3.5-turbo", True),
        ("azure/gpt-4-1106-preview", True),
        ("groq/gemma-7b-it", True),
        ("anthropic.claude-instant-v1", False),
        ("gemini/gemini-1.5-flash", True),
    ],
)
def test_supports_function_calling(model, expected_bool):
    try:
        assert llm.supports_function_calling(model=model) == expected_bool
    except Exception as e:
        pytest.fail(f"Error occurred: {e}")


@pytest.mark.parametrize(
    "model, expected_bool",
    [
        ("gpt-4o-mini-search-preview", True),
        ("openai/gpt-4o-mini-search-preview", True),
        ("gpt-4o-search-preview", True),
        ("openai/gpt-4o-search-preview", True),
        ("groq/deepseek-r1-distill-llama-70b", False),
        ("groq/llama-3.3-70b-versatile", False),
        ("codestral/codestral-latest", False),
    ],
)
def test_supports_web_search(model, expected_bool):
    try:
        assert llm.supports_web_search(model=model) == expected_bool
    except Exception as e:
        pytest.fail(f"Error occurred: {e}")


def test_get_max_token_unit_test():
    """
    More complete testing in `test_completion_cost.py`
    """
    model = "bedrock/anthropic.claude-3-haiku-20240307-v1:0"

    max_tokens = get_max_tokens(
        model
    )  # Returns a number instead of throwing an Exception

    assert isinstance(max_tokens, int)


def test_get_supported_openai_params() -> None:
    # Mapped provider
    assert isinstance(get_supported_openai_params("gpt-4"), list)

    # Unmapped provider
    assert get_supported_openai_params("nonexistent") is None


def test_get_chat_completion_prompt():
    """
    Unit test to ensure get_chat_completion_prompt updates messages in logging object.
    """
    from llm.llm_core_utils.llm_logging import Logging

    llm_logging_obj = Logging(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "hi"}],
        stream=False,
        call_type="acompletion",
        llm_call_id="1234",
        start_time=datetime.now(),
        function_id="1234",
    )

    updated_message = "hello world"

    llm_logging_obj.get_chat_completion_prompt(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": updated_message}],
        non_default_params={},
        prompt_id="1234",
        prompt_variables=None,
    )

    assert llm_logging_obj.messages == [
        {"role": "user", "content": updated_message}
    ]


def test_redact_msgs_from_logs():
    """
    Tests that turn_off_message_logging does not modify the response_obj

    On the proxy some users were seeing the redaction impact client side responses
    """
    from llm.llm_core_utils.llm_logging import Logging
    from llm.llm_core_utils.redact_messages import (
        redact_message_input_output_from_logging,
    )

    llm.turn_off_message_logging = True

    response_obj = llm.ModelResponse(
        choices=[
            {
                "finish_reason": "stop",
                "index": 0,
                "message": {
                    "content": "I'm LLaMA, an AI assistant developed by Meta AI that can understand and respond to human input in a conversational manner.",
                    "role": "assistant",
                },
            }
        ]
    )

    llm_logging_obj = Logging(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "hi"}],
        stream=False,
        call_type="acompletion",
        llm_call_id="1234",
        start_time=datetime.now(),
        function_id="1234",
    )

    _redacted_response_obj = redact_message_input_output_from_logging(
        result=response_obj,
        model_call_details=llm_logging_obj.model_call_details,
    )

    # Assert the response_obj content is NOT modified
    assert (
        response_obj.choices[0].message.content
        == "I'm LLaMA, an AI assistant developed by Meta AI that can understand and respond to human input in a conversational manner."
    )

    llm.turn_off_message_logging = False
    print("Test passed")


def test_redact_msgs_from_logs_with_dynamic_params():
    """
    Tests redaction behavior based on standard_callback_dynamic_params setting:
    In all tests llm.turn_off_message_logging is True


    1. When standard_callback_dynamic_params.turn_off_message_logging is False (or not set): No redaction should occur. User has opted out of redaction.
    2. When standard_callback_dynamic_params.turn_off_message_logging is True: Redaction should occur. User has opted in to redaction.
    3. standard_callback_dynamic_params.turn_off_message_logging not set, llm.turn_off_message_logging is True: Redaction should occur.
    """
    from llm.llm_core_utils.llm_logging import Logging
    from llm.llm_core_utils.redact_messages import (
        redact_message_input_output_from_logging,
    )

    llm.turn_off_message_logging = True
    test_content = "I'm LLaMA, an AI assistant developed by Meta AI that can understand and respond to human input in a conversational manner."
    response_obj = llm.ModelResponse(
        choices=[
            {
                "finish_reason": "stop",
                "index": 0,
                "message": {
                    "content": test_content,
                    "role": "assistant",
                },
            }
        ]
    )

    llm_logging_obj = Logging(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "hi"}],
        stream=False,
        call_type="acompletion",
        llm_call_id="1234",
        start_time=datetime.now(),
        function_id="1234",
    )

    # Test Case 1: standard_callback_dynamic_params = False (or not set)
    standard_callback_dynamic_params = StandardCallbackDynamicParams(
        turn_off_message_logging=False
    )
    llm_logging_obj.model_call_details["standard_callback_dynamic_params"] = (
        standard_callback_dynamic_params
    )
    _redacted_response_obj = redact_message_input_output_from_logging(
        result=response_obj,
        model_call_details=llm_logging_obj.model_call_details,
    )
    # Assert no redaction occurred
    assert _redacted_response_obj.choices[0].message.content == test_content

    # Test Case 2: standard_callback_dynamic_params = True
    standard_callback_dynamic_params = StandardCallbackDynamicParams(
        turn_off_message_logging=True
    )
    llm_logging_obj.model_call_details["standard_callback_dynamic_params"] = (
        standard_callback_dynamic_params
    )
    _redacted_response_obj = redact_message_input_output_from_logging(
        result=response_obj,
        model_call_details=llm_logging_obj.model_call_details,
    )
    # Assert redaction occurred
    assert _redacted_response_obj.choices[0].message.content == "redacted-by-llm"

    # Test Case 3: standard_callback_dynamic_params does not override llm.turn_off_message_logging
    # since llm.turn_off_message_logging is True redaction should occur
    standard_callback_dynamic_params = StandardCallbackDynamicParams()
    llm_logging_obj.model_call_details["standard_callback_dynamic_params"] = (
        standard_callback_dynamic_params
    )
    _redacted_response_obj = redact_message_input_output_from_logging(
        result=response_obj,
        model_call_details=llm_logging_obj.model_call_details,
    )
    # Assert no redaction occurred
    assert _redacted_response_obj.choices[0].message.content == "redacted-by-llm"

    # Reset settings
    llm.turn_off_message_logging = False
    print("Test passed")


@pytest.mark.parametrize(
    "duration, unit",
    [("7s", "s"), ("7m", "m"), ("7h", "h"), ("7d", "d"), ("7mo", "mo")],
)
def test_extract_from_regex(duration, unit):
    value, _unit = _extract_from_regex(duration=duration)

    assert value == 7
    assert _unit == unit


def test_duration_in_seconds():
    """
    Test if duration int is correctly calculated for different str
    """
    import time

    now = time.time()
    current_time = datetime.fromtimestamp(now)

    if current_time.month == 12:
        target_year = current_time.year + 1
        target_month = 1
    else:
        target_year = current_time.year
        target_month = current_time.month + 1

    # Determine the day to set for next month
    target_day = current_time.day
    last_day_of_target_month = get_last_day_of_month(target_year, target_month)

    if target_day > last_day_of_target_month:
        target_day = last_day_of_target_month

    next_month = datetime(
        year=target_year,
        month=target_month,
        day=target_day,
        hour=current_time.hour,
        minute=current_time.minute,
        second=current_time.second,
        microsecond=current_time.microsecond,
    )

    # Calculate the duration until the first day of the next month
    duration_until_next_month = next_month - current_time
    expected_duration = int(duration_until_next_month.total_seconds())

    value = duration_in_seconds(duration="1mo")

    assert value - expected_duration < 2


def test_duration_in_seconds_basic():
    assert duration_in_seconds(duration="3s") == 3
    assert duration_in_seconds(duration="3m") == 180
    assert duration_in_seconds(duration="3h") == 10800
    assert duration_in_seconds(duration="3d") == 259200
    assert duration_in_seconds(duration="3w") == 1814400


def test_get_llm_provider_ft_models():
    """
    All ft prefixed models should map to OpenAI
    gpt-3.5-turbo-0125 (recommended),
    gpt-3.5-turbo-1106,
    gpt-3.5-turbo,
    gpt-4-0613 (experimental)
    gpt-4o-2024-05-13.
    babbage-002, davinci-002,

    """
    model, custom_llm_provider, _, _ = get_llm_provider(model="ft:gpt-3.5-turbo-0125")
    assert custom_llm_provider == "openai"

    model, custom_llm_provider, _, _ = get_llm_provider(model="ft:gpt-3.5-turbo-1106")
    assert custom_llm_provider == "openai"

    model, custom_llm_provider, _, _ = get_llm_provider(model="ft:gpt-3.5-turbo")
    assert custom_llm_provider == "openai"

    model, custom_llm_provider, _, _ = get_llm_provider(model="ft:gpt-4-0613")
    assert custom_llm_provider == "openai"

    model, custom_llm_provider, _, _ = get_llm_provider(model="ft:gpt-3.5-turbo")
    assert custom_llm_provider == "openai"

    model, custom_llm_provider, _, _ = get_llm_provider(model="ft:gpt-4o-2024-05-13")
    assert custom_llm_provider == "openai"


@pytest.mark.parametrize("langfuse_trace_id", [None, "my-unique-trace-id"])
@pytest.mark.parametrize(
    "langfuse_existing_trace_id", [None, "my-unique-existing-trace-id"]
)
def test_logging_trace_id(langfuse_trace_id, langfuse_existing_trace_id):
    """
    - Unit test for `_get_trace_id` function in Logging obj
    """
    from llm.llm_core_utils.llm_logging import Logging

    llm.success_callback = ["langfuse"]
    llm_call_id = "my-unique-call-id"
    llm_logging_obj = Logging(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "hi"}],
        stream=False,
        call_type="acompletion",
        llm_call_id=llm_call_id,
        start_time=datetime.now(),
        function_id="1234",
    )

    metadata = {}

    if langfuse_trace_id is not None:
        metadata["trace_id"] = langfuse_trace_id
    if langfuse_existing_trace_id is not None:
        metadata["existing_trace_id"] = langfuse_existing_trace_id

    llm.completion(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "Hey how's it going?"}],
        mock_response="Hey!",
        llm_logging_obj=llm_logging_obj,
        metadata=metadata,
    )

    time.sleep(3)
    assert llm_logging_obj._get_trace_id(service_name="langfuse") is not None

    ## if existing_trace_id exists
    if langfuse_existing_trace_id is not None:
        assert (
            llm_logging_obj._get_trace_id(service_name="langfuse")
            == langfuse_existing_trace_id
        )
    ## if trace_id exists
    elif langfuse_trace_id is not None:
        assert (
            llm_logging_obj._get_trace_id(service_name="langfuse")
            == langfuse_trace_id
        )
    ## if existing_trace_id exists
    else:
        assert (
            llm_logging_obj._get_trace_id(service_name="langfuse")
            == llm_call_id
        )


def test_convert_model_response_object():
    """
    Unit test to ensure model response object correctly handles openrouter errors.
    """
    args = {
        "response_object": {
            "id": None,
            "choices": None,
            "created": None,
            "model": None,
            "object": None,
            "service_tier": None,
            "system_fingerprint": None,
            "usage": None,
            "error": {
                "message": '{"type":"error","error":{"type":"invalid_request_error","message":"Output blocked by content filtering policy"}}',
                "code": 400,
            },
        },
        "model_response_object": llm.ModelResponse(
            id="chatcmpl-b88ce43a-7bfc-437c-b8cc-e90d59372cfb",
            choices=[
                llm.Choices(
                    finish_reason="stop",
                    index=0,
                    message=llm.Message(content="default", role="assistant"),
                )
            ],
            created=1719376241,
            model="openrouter/anthropic/claude-3.5-sonnet",
            object="chat.completion",
            system_fingerprint=None,
            usage=llm.Usage(),
        ),
        "response_type": "completion",
        "stream": False,
        "start_time": None,
        "end_time": None,
        "hidden_params": None,
    }

    try:
        llm.convert_to_model_response_object(**args)
        pytest.fail("Expected this to fail")
    except Exception as e:
        assert hasattr(e, "status_code")
        assert e.status_code == 400
        assert hasattr(e, "message")
        assert (
            e.message
            == '{"type":"error","error":{"type":"invalid_request_error","message":"Output blocked by content filtering policy"}}'
        )


@pytest.mark.parametrize(
    "content, expected_reasoning, expected_content",
    [
        (None, None, None),
        (
            "<think>I am thinking here</think>The sky is a canvas of blue",
            "I am thinking here",
            "The sky is a canvas of blue",
        ),
        ("I am a regular response", None, "I am a regular response"),
    ],
)
def test_parse_content_for_reasoning(content, expected_reasoning, expected_content):
    assert llm.utils._parse_content_for_reasoning(content) == (
        expected_reasoning,
        expected_content,
    )


@pytest.mark.parametrize(
    "model, expected_bool",
    [
        ("vertex_ai/gemini-1.5-pro", True),
        ("gemini/gemini-1.5-pro", True),
        ("predibase/llama3-8b-instruct", True),
        ("gpt-3.5-turbo", False),
        ("groq/llama3-70b-8192", True),
    ],
)
def test_supports_response_schema(model, expected_bool):
    """
    Unit tests for 'supports_response_schema' helper function.

    Should be true for gemini-1.5-pro on google ai studio / vertex ai AND predibase models
    Should be false otherwise
    """
    os.environ["LLM_LOCAL_MODEL_COST_MAP"] = "True"
    llm.model_cost = llm.get_model_cost_map(url="")

    from llm.utils import supports_response_schema

    response = supports_response_schema(model=model, custom_llm_provider=None)

    assert expected_bool == response


@pytest.mark.parametrize(
    "model, expected_bool",
    [
        ("gpt-3.5-turbo", True),
        ("gpt-4", True),
        ("command-nightly", False),
        ("gemini-pro", True),
    ],
)
def test_supports_function_calling_v2(model, expected_bool):
    """
    Unit test for 'supports_function_calling' helper function.
    """
    from llm.utils import supports_function_calling

    response = supports_function_calling(model=model, custom_llm_provider=None)
    assert expected_bool == response


@pytest.mark.parametrize(
    "model, expected_bool",
    [
        ("gpt-4-vision-preview", True),
        ("gpt-3.5-turbo", False),
        ("claude-3-opus-20240229", True),
        ("gemini-pro-vision", True),
        ("command-nightly", False),
    ],
)
def test_supports_vision(model, expected_bool):
    """
    Unit test for 'supports_vision' helper function.
    """
    from llm.utils import supports_vision

    response = supports_vision(model=model, custom_llm_provider=None)
    assert expected_bool == response


def test_usage_object_null_tokens():
    """
    Unit test.

    Asserts Usage obj always returns int.

    Fixes https://github.com/hanzoai/llm/issues/5096
    """
    usage_obj = llm.Usage(prompt_tokens=2, completion_tokens=None, total_tokens=2)

    assert usage_obj.completion_tokens == 0


def test_is_base64_encoded():
    import base64

    import requests

    llm.set_verbose = True
    url = "https://dummyimage.com/100/100/fff&text=Test+image"
    response = requests.get(url)
    file_data = response.content

    encoded_file = base64.b64encode(file_data).decode("utf-8")
    base64_image = f"data:image/png;base64,{encoded_file}"

    from llm.utils import is_base64_encoded

    assert is_base64_encoded(s=base64_image) is True


@mock.patch("httpx.AsyncClient")
@mock.patch.dict(
    os.environ,
    {"SSL_VERIFY": "/certificate.pem", "SSL_CERTIFICATE": "/client.pem"},
    clear=True,
)
def test_async_http_handler(mock_async_client):
    import httpx

    timeout = 120
    event_hooks = {"request": [lambda r: r]}
    concurrent_limit = 2

    AsyncHTTPHandler(timeout, event_hooks, concurrent_limit)

    mock_async_client.assert_called_with(
        cert="/client.pem",
        transport=None,
        event_hooks=event_hooks,
        headers=headers,
        limits=httpx.Limits(
            max_connections=concurrent_limit,
            max_keepalive_connections=concurrent_limit,
        ),
        timeout=timeout,
        verify="/certificate.pem",
    )


@mock.patch("httpx.AsyncClient")
@mock.patch.dict(os.environ, {}, clear=True)
def test_async_http_handler_force_ipv4(mock_async_client):
    """
    Test AsyncHTTPHandler when llm.force_ipv4 is True

    This is prod test - we need to ensure that httpx always uses ipv4 when llm.force_ipv4 is True
    """
    import httpx
    from llm.llms.custom_httpx.http_handler import AsyncHTTPHandler

    # Set force_ipv4 to True
    llm.force_ipv4 = True

    try:
        timeout = 120
        event_hooks = {"request": [lambda r: r]}
        concurrent_limit = 2

        AsyncHTTPHandler(timeout, event_hooks, concurrent_limit)

        # Get the call arguments
        call_args = mock_async_client.call_args[1]

        ############# IMPORTANT ASSERTION #################
        # Assert transport exists and is configured correctly for using ipv4
        assert isinstance(call_args["transport"], httpx.AsyncHTTPTransport)
        print(call_args["transport"])
        assert call_args["transport"]._pool._local_address == "0.0.0.0"
        ####################################

        # Assert other parameters match
        assert call_args["event_hooks"] == event_hooks
        assert call_args["headers"] == headers
        assert isinstance(call_args["limits"], httpx.Limits)
        assert call_args["limits"].max_connections == concurrent_limit
        assert call_args["limits"].max_keepalive_connections == concurrent_limit
        assert call_args["timeout"] == timeout
        assert call_args["verify"] is True
        assert call_args["cert"] is None

    finally:
        # Reset force_ipv4 to default
        llm.force_ipv4 = False


@pytest.mark.parametrize(
    "model, expected_bool", [("gpt-3.5-turbo", False), ("gpt-4o-audio-preview", True)]
)
def test_supports_audio_input(model, expected_bool):
    os.environ["LLM_LOCAL_MODEL_COST_MAP"] = "True"
    llm.model_cost = llm.get_model_cost_map(url="")

    from llm.utils import supports_audio_input, supports_audio_output

    supports_pc = supports_audio_input(model=model)

    assert supports_pc == expected_bool


def test_is_base64_encoded_2():
    from llm.utils import is_base64_encoded

    assert (
        is_base64_encoded(
            s="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/x+AAwMCAO+ip1sAAAAASUVORK5CYII="
        )
        is True
    )

    assert is_base64_encoded(s="Dog") is False


@pytest.mark.parametrize(
    "messages, expected_bool",
    [
        ([{"role": "user", "content": "hi"}], True),
        ([{"role": "user", "content": [{"type": "text", "text": "hi"}]}], True),
        (
            [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "file",
                            "file": {
                                "file_id": "123",
                                "file_name": "test.txt",
                                "file_size": 100,
                                "file_type": "text/plain",
                                "file_url": "https://example.com/test.txt",
                            },
                        }
                    ],
                }
            ],
            True,
        ),
        (
            [
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "url": "https://example.com/image.png"}
                    ],
                }
            ],
            True,
        ),
        (
            [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "hi"},
                        {
                            "type": "image",
                            "source": {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": "1234",
                                },
                            },
                        },
                    ],
                }
            ],
            False,
        ),
    ],
)
def test_validate_chat_completion_user_messages(messages, expected_bool):
    from llm.utils import validate_chat_completion_user_messages

    if expected_bool:
        ## Valid message
        validate_chat_completion_user_messages(messages=messages)
    else:
        ## Invalid message
        with pytest.raises(Exception):
            validate_chat_completion_user_messages(messages=messages)


@pytest.mark.parametrize(
    "tool_choice, expected_bool",
    [
        ({"type": "function", "function": {"name": "get_current_weather"}}, True),
        ({"type": "tool", "name": "get_current_weather"}, False),
        (None, True),
        ("auto", True),
        ("required", True),
    ],
)
def test_validate_chat_completion_tool_choice(tool_choice, expected_bool):
    from llm.utils import validate_chat_completion_tool_choice

    if expected_bool:
        validate_chat_completion_tool_choice(tool_choice=tool_choice)
    else:
        with pytest.raises(Exception):
            validate_chat_completion_tool_choice(tool_choice=tool_choice)


def test_models_by_provider():
    """
    Make sure all providers from model map are in the valid providers list
    """
    os.environ["LLM_LOCAL_MODEL_COST_MAP"] = "True"
    llm.model_cost = llm.get_model_cost_map(url="")

    from llm import models_by_provider

    providers = set()
    for k, v in llm.model_cost.items():
        if "_" in v["llm_provider"] and "-" in v["llm_provider"]:
            continue
        elif k == "sample_spec":
            continue
        elif (
            v["llm_provider"] == "sagemaker"
            or v["llm_provider"] == "bedrock_converse"
        ):
            continue
        else:
            providers.add(v["llm_provider"])

    for provider in providers:
        assert provider in models_by_provider.keys()


@pytest.mark.parametrize(
    "llm_params, disable_end_user_cost_tracking, expected_end_user_id",
    [
        ({}, False, None),
        ({"user_api_key_end_user_id": "123"}, False, "123"),
        ({"user_api_key_end_user_id": "123"}, True, None),
    ],
)
def test_get_end_user_id_for_cost_tracking(
    llm_params, disable_end_user_cost_tracking, expected_end_user_id
):
    from llm.utils import get_end_user_id_for_cost_tracking

    llm.disable_end_user_cost_tracking = disable_end_user_cost_tracking
    assert (
        get_end_user_id_for_cost_tracking(llm_params=llm_params)
        == expected_end_user_id
    )


@pytest.mark.parametrize(
    "llm_params, disable_end_user_cost_tracking_prometheus_only, expected_end_user_id",
    [
        ({}, False, None),
        ({"user_api_key_end_user_id": "123"}, False, "123"),
        ({"user_api_key_end_user_id": "123"}, True, None),
    ],
)
def test_get_end_user_id_for_cost_tracking_prometheus_only(
    llm_params, disable_end_user_cost_tracking_prometheus_only, expected_end_user_id
):
    from llm.utils import get_end_user_id_for_cost_tracking

    llm.disable_end_user_cost_tracking_prometheus_only = (
        disable_end_user_cost_tracking_prometheus_only
    )
    assert (
        get_end_user_id_for_cost_tracking(
            llm_params=llm_params, service_type="prometheus"
        )
        == expected_end_user_id
    )


def test_is_prompt_caching_enabled_error_handling():
    """
    Assert that `is_prompt_caching_valid_prompt` safely handles errors in `token_counter`.
    """
    with patch(
        "llm.utils.token_counter",
        side_effect=Exception(
            "Mocked error, This should not raise an error. Instead is_prompt_caching_valid_prompt should return False."
        ),
    ):
        result = llm.utils.is_prompt_caching_valid_prompt(
            messages=[{"role": "user", "content": "test"}],
            tools=None,
            custom_llm_provider="anthropic",
            model="anthropic/claude-3-5-sonnet-20240620",
        )

        assert result is False  # Should return False when an error occurs


def test_is_prompt_caching_enabled_return_default_image_dimensions():
    """
    Assert that `is_prompt_caching_valid_prompt` calls token_counter with use_default_image_token_count=True
    when processing messages containing images

    IMPORTANT: Ensures Get token counter does not make a GET request to the image url
    """
    with patch("llm.utils.token_counter") as mock_token_counter:
        llm.utils.is_prompt_caching_valid_prompt(
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "What is in this image?"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": "https://www.gstatic.com/webp/gallery/1.webp",
                                "detail": "high",
                            },
                        },
                    ],
                }
            ],
            tools=None,
            custom_llm_provider="openai",
            model="gpt-4o-mini",
        )

        # Assert token_counter was called with use_default_image_token_count=True
        args_to_mock_token_counter = mock_token_counter.call_args[1]
        print("args_to_mock", args_to_mock_token_counter)
        assert args_to_mock_token_counter["use_default_image_token_count"] is True


def test_token_counter_with_image_url_with_detail_high():
    """
    Assert that token_counter does not make a GET request to the image url when `use_default_image_token_count=True`

    PROD TEST this is importat - Can impact latency very badly
    """
    from llm.constants import DEFAULT_IMAGE_TOKEN_COUNT
    from llm._logging import verbose_logger
    import logging

    verbose_logger.setLevel(logging.DEBUG)

    _tokens = llm.utils.token_counter(
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": "https://www.gstatic.com/webp/gallery/1.webp",
                            "detail": "high",
                        },
                    },
                ],
            }
        ],
        model="gpt-4o-mini",
        use_default_image_token_count=True,
    )
    print("tokens", _tokens)
    assert _tokens == DEFAULT_IMAGE_TOKEN_COUNT + 7


def test_fireworks_ai_document_inlining():
    """
    With document inlining, all fireworks ai models are now:
    - supports_pdf
    - supports_vision
    """
    from llm.utils import supports_pdf_input, supports_vision

    llm._turn_on_debug()

    assert supports_pdf_input("fireworks_ai/llama-3.1-8b-instruct") is True
    assert supports_vision("fireworks_ai/llama-3.1-8b-instruct") is True


def test_logprobs_type():
    from llm.types.utils import Logprobs

    logprobs = {
        "text_offset": None,
        "token_logprobs": None,
        "tokens": None,
        "top_logprobs": None,
    }
    logprobs = Logprobs(**logprobs)
    assert logprobs.text_offset is None
    assert logprobs.token_logprobs is None
    assert logprobs.tokens is None
    assert logprobs.top_logprobs is None


def test_get_valid_models_openai_proxy(monkeypatch):
    from llm.utils import get_valid_models
    import llm

    llm._turn_on_debug()

    monkeypatch.setenv("LLM_PROXY_API_KEY", "sk-1234")
    monkeypatch.setenv("LLM_PROXY_API_BASE", "https://llm-api.up.railway.app/")
    monkeypatch.delenv("FIREWORKS_AI_ACCOUNT_ID", None)
    monkeypatch.delenv("FIREWORKS_AI_API_KEY", None)

    mock_response_data = {
        "object": "list",
        "data": [
            {
                "id": "gpt-4o",
                "object": "model",
                "created": 1686935002,
                "owned_by": "organization-owner",
            },
        ],
    }

    # Create a mock response object
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_response_data

    with patch.object(
        llm.module_level_client, "get", return_value=mock_response
    ) as mock_post:
        valid_models = get_valid_models(check_provider_endpoint=True)
        assert "llm_proxy/gpt-4o" in valid_models


def test_get_valid_models_fireworks_ai(monkeypatch):
    from llm.utils import get_valid_models
    import llm

    llm._turn_on_debug()

    monkeypatch.setenv("FIREWORKS_API_KEY", "sk-1234")
    monkeypatch.setenv("FIREWORKS_ACCOUNT_ID", "1234")
    monkeypatch.setattr(llm, "provider_list", ["fireworks_ai"])

    mock_response_data = {
        "models": [
            {
                "name": "accounts/fireworks/models/llama-3.1-8b-instruct",
                "displayName": "<string>",
                "description": "<string>",
                "createTime": "2023-11-07T05:31:56Z",
                "createdBy": "<string>",
                "state": "STATE_UNSPECIFIED",
                "status": {"code": "OK", "message": "<string>"},
                "kind": "KIND_UNSPECIFIED",
                "githubUrl": "<string>",
                "huggingFaceUrl": "<string>",
                "baseModelDetails": {
                    "worldSize": 123,
                    "checkpointFormat": "CHECKPOINT_FORMAT_UNSPECIFIED",
                    "parameterCount": "<string>",
                    "moe": True,
                    "tunable": True,
                },
                "peftDetails": {
                    "baseModel": "<string>",
                    "r": 123,
                    "targetModules": ["<string>"],
                },
                "teftDetails": {},
                "public": True,
                "conversationConfig": {
                    "style": "<string>",
                    "system": "<string>",
                    "template": "<string>",
                },
                "contextLength": 123,
                "supportsImageInput": True,
                "supportsTools": True,
                "importedFrom": "<string>",
                "fineTuningJob": "<string>",
                "defaultDraftModel": "<string>",
                "defaultDraftTokenCount": 123,
                "precisions": ["PRECISION_UNSPECIFIED"],
                "deployedModelRefs": [
                    {
                        "name": "<string>",
                        "deployment": "<string>",
                        "state": "STATE_UNSPECIFIED",
                        "default": True,
                        "public": True,
                    }
                ],
                "cluster": "<string>",
                "deprecationDate": {"year": 123, "month": 123, "day": 123},
            }
        ],
        "nextPageToken": "<string>",
        "totalSize": 123,
    }

    # Create a mock response object
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_response_data

    with patch.object(
        llm.module_level_client, "get", return_value=mock_response
    ) as mock_post:
        valid_models = get_valid_models(check_provider_endpoint=True)
        mock_post.assert_called_once()
        assert (
            "fireworks_ai/accounts/fireworks/models/llama-3.1-8b-instruct"
            in valid_models
        )


def test_get_valid_models_default(monkeypatch):
    """
    Ensure that the default models is used when error retrieving from model api.

    Prevent regression for existing usage.
    """
    from llm.utils import get_valid_models
    import llm

    monkeypatch.setenv("FIREWORKS_API_KEY", "sk-1234")
    valid_models = get_valid_models()
    assert len(valid_models) > 0


def test_supports_vision_gemini():
    os.environ["LLM_LOCAL_MODEL_COST_MAP"] = "True"
    llm.model_cost = llm.get_model_cost_map(url="")
    from llm.utils import supports_vision

    assert supports_vision("gemini-1.5-pro") is True


def test_pick_cheapest_chat_model_from_llm_provider():
    from llm.llm_core_utils.llm_request_utils import (
        pick_cheapest_chat_models_from_llm_provider,
    )

    assert len(pick_cheapest_chat_models_from_llm_provider("openai", n=3)) == 3

    assert len(pick_cheapest_chat_models_from_llm_provider("unknown", n=1)) == 0


def test_get_potential_model_names():
    from llm.utils import _get_potential_model_names

    assert _get_potential_model_names(
        model="bedrock/ap-northeast-1/anthropic.claude-instant-v1",
        custom_llm_provider="bedrock",
    )


@pytest.mark.parametrize("num_retries", [0, 1, 5])
def test_get_num_retries(num_retries):
    from llm.utils import _get_wrapper_num_retries

    assert _get_wrapper_num_retries(
        kwargs={"num_retries": num_retries}, exception=Exception("test")
    ) == (
        num_retries,
        {
            "num_retries": num_retries,
        },
    )


def test_add_custom_logger_callback_to_specific_event(monkeypatch):
    from llm.utils import _add_custom_logger_callback_to_specific_event

    monkeypatch.setattr(llm, "success_callback", [])
    monkeypatch.setattr(llm, "failure_callback", [])

    _add_custom_logger_callback_to_specific_event("langfuse", "success")

    assert len(llm.success_callback) == 1
    assert len(llm.failure_callback) == 0


def test_add_custom_logger_callback_to_specific_event_e2e(monkeypatch):

    monkeypatch.setattr(llm, "success_callback", [])
    monkeypatch.setattr(llm, "failure_callback", [])
    monkeypatch.setattr(llm, "callbacks", [])

    llm.success_callback = ["humanloop"]

    curr_len_success_callback = len(llm.success_callback)
    curr_len_failure_callback = len(llm.failure_callback)

    llm.completion(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Hello, world!"}],
        mock_response="Testing langfuse",
    )

    assert len(llm.success_callback) == curr_len_success_callback
    assert len(llm.failure_callback) == curr_len_failure_callback


def test_custom_logger_exists_in_callbacks_individual_functions(monkeypatch):
    """
    Test _custom_logger_class_exists_in_success_callbacks and _custom_logger_class_exists_in_failure_callbacks helper functions
    Tests if logger is found in different callback lists
    """
    from llm.integrations.custom_logger import CustomLogger
    from llm.utils import (
        _custom_logger_class_exists_in_failure_callbacks,
        _custom_logger_class_exists_in_success_callbacks,
    )

    # Create a mock CustomLogger class
    class MockCustomLogger(CustomLogger):
        def log_success_event(self, kwargs, response_obj, start_time, end_time):
            pass

        def log_failure_event(self, kwargs, response_obj, start_time, end_time):
            pass

    # Reset all callback lists
    for list_name in [
        "callbacks",
        "_async_success_callback",
        "_async_failure_callback",
        "success_callback",
        "failure_callback",
    ]:
        monkeypatch.setattr(llm, list_name, [])

    mock_logger = MockCustomLogger()

    # Test 1: No logger exists in any callback list
    assert _custom_logger_class_exists_in_success_callbacks(mock_logger) == False
    assert _custom_logger_class_exists_in_failure_callbacks(mock_logger) == False

    # Test 2: Logger exists in success_callback
    llm.success_callback.append(mock_logger)
    assert _custom_logger_class_exists_in_success_callbacks(mock_logger) == True
    assert _custom_logger_class_exists_in_failure_callbacks(mock_logger) == False

    # Reset callbacks
    llm.success_callback = []

    # Test 3: Logger exists in _async_success_callback
    llm._async_success_callback.append(mock_logger)
    assert _custom_logger_class_exists_in_success_callbacks(mock_logger) == True
    assert _custom_logger_class_exists_in_failure_callbacks(mock_logger) == False

    # Reset callbacks
    llm._async_success_callback = []

    # Test 4: Logger exists in failure_callback
    llm.failure_callback.append(mock_logger)
    assert _custom_logger_class_exists_in_success_callbacks(mock_logger) == False
    assert _custom_logger_class_exists_in_failure_callbacks(mock_logger) == True

    # Reset callbacks
    llm.failure_callback = []

    # Test 5: Logger exists in _async_failure_callback
    llm._async_failure_callback.append(mock_logger)
    assert _custom_logger_class_exists_in_success_callbacks(mock_logger) == False
    assert _custom_logger_class_exists_in_failure_callbacks(mock_logger) == True

    # Test 6: Logger exists in both success and failure callbacks
    llm.success_callback.append(mock_logger)
    llm.failure_callback.append(mock_logger)
    assert _custom_logger_class_exists_in_success_callbacks(mock_logger) == True
    assert _custom_logger_class_exists_in_failure_callbacks(mock_logger) == True

    # Test 7: Different instance of same logger class
    mock_logger_2 = MockCustomLogger()
    assert _custom_logger_class_exists_in_success_callbacks(mock_logger_2) == True
    assert _custom_logger_class_exists_in_failure_callbacks(mock_logger_2) == True


@pytest.mark.asyncio
async def test_add_custom_logger_callback_to_specific_event_with_duplicates(
    monkeypatch,
):
    """
    Test that when a callback exists in both success_callback and _async_success_callback,
    it's not added again
    """
    from llm.integrations.langfuse.langfuse_prompt_management import (
        LangfusePromptManagement,
    )

    # Reset all callback lists
    monkeypatch.setattr(llm, "callbacks", [])
    monkeypatch.setattr(llm, "_async_success_callback", [])
    monkeypatch.setattr(llm, "_async_failure_callback", [])
    monkeypatch.setattr(llm, "success_callback", [])
    monkeypatch.setattr(llm, "failure_callback", [])

    # Add logger to both success_callback and _async_success_callback
    langfuse_logger = LangfusePromptManagement()
    llm.success_callback.append(langfuse_logger)
    llm._async_success_callback.append(langfuse_logger)

    # Get initial lengths
    initial_success_callback_len = len(llm.success_callback)
    initial_async_success_callback_len = len(llm._async_success_callback)

    # Make a completion call
    await llm.acompletion(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Hello, world!"}],
        mock_response="Testing duplicate callbacks",
    )

    # Assert no new callbacks were added
    assert len(llm.success_callback) == initial_success_callback_len
    assert len(llm._async_success_callback) == initial_async_success_callback_len


@pytest.mark.asyncio
async def test_add_custom_logger_callback_to_specific_event_with_duplicates_success_callback(
    monkeypatch,
):
    """
    Test that when a callback exists in both success_callback and _async_success_callback,
    it's not added again
    """
    from llm.integrations.langfuse.langfuse_prompt_management import (
        LangfusePromptManagement,
    )

    # Reset all callback lists
    monkeypatch.setattr(llm, "callbacks", [])
    monkeypatch.setattr(llm, "_async_success_callback", [])
    monkeypatch.setattr(llm, "_async_failure_callback", [])
    monkeypatch.setattr(llm, "success_callback", [])
    monkeypatch.setattr(llm, "failure_callback", [])

    # Add logger to both success_callback and _async_success_callback
    langfuse_logger = LangfusePromptManagement()
    llm.success_callback.append(langfuse_logger)

    # Get initial lengths
    initial_success_callback_len = len(llm.success_callback)
    initial_async_success_callback_len = len(llm._async_success_callback)

    # Make a completion call
    await llm.acompletion(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Hello, world!"}],
        mock_response="Testing duplicate callbacks",
    )

    # Assert no new callbacks were added
    assert len(llm.success_callback) == initial_success_callback_len
    assert len(llm._async_success_callback) == initial_async_success_callback_len


@pytest.mark.asyncio
async def test_add_custom_logger_callback_to_specific_event_with_duplicates_callbacks(
    monkeypatch,
):
    """
    Test that when a callback exists in both success_callback and _async_success_callback,
    it's not added again
    """
    from llm.integrations.langfuse.langfuse_prompt_management import (
        LangfusePromptManagement,
    )

    # Reset all callback lists
    monkeypatch.setattr(llm, "callbacks", [])
    monkeypatch.setattr(llm, "_async_success_callback", [])
    monkeypatch.setattr(llm, "_async_failure_callback", [])
    monkeypatch.setattr(llm, "success_callback", [])
    monkeypatch.setattr(llm, "failure_callback", [])

    # Add logger to both success_callback and _async_success_callback
    langfuse_logger = LangfusePromptManagement()
    llm.callbacks.append(langfuse_logger)

    # Make a completion call
    await llm.acompletion(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Hello, world!"}],
        mock_response="Testing duplicate callbacks",
    )

    # Assert no new callbacks were added
    initial_callbacks_len = len(llm.callbacks)
    initial_async_success_callback_len = len(llm._async_success_callback)
    initial_success_callback_len = len(llm.success_callback)
    print(
        f"Num callbacks before: llm.callbacks: {len(llm.callbacks)}, llm._async_success_callback: {len(llm._async_success_callback)}, llm.success_callback: {len(llm.success_callback)}"
    )

    for _ in range(10):
        await llm.acompletion(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Hello, world!"}],
            mock_response="Testing duplicate callbacks",
        )

    assert len(llm.callbacks) == initial_callbacks_len
    assert len(llm._async_success_callback) == initial_async_success_callback_len
    assert len(llm.success_callback) == initial_success_callback_len

    print(
        f"Num callbacks after 10 mock calls: llm.callbacks: {len(llm.callbacks)}, llm._async_success_callback: {len(llm._async_success_callback)}, llm.success_callback: {len(llm.success_callback)}"
    )


def test_add_custom_logger_callback_to_specific_event_e2e_failure(monkeypatch):
    from llm.integrations.openmeter import OpenMeterLogger

    monkeypatch.setattr(llm, "success_callback", [])
    monkeypatch.setattr(llm, "failure_callback", [])
    monkeypatch.setattr(llm, "callbacks", [])
    monkeypatch.setenv("OPENMETER_API_KEY", "wedlwe")
    monkeypatch.setenv("OPENMETER_API_URL", "https://openmeter.dev")

    llm.failure_callback = ["openmeter"]

    curr_len_success_callback = len(llm.success_callback)
    curr_len_failure_callback = len(llm.failure_callback)

    llm.completion(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Hello, world!"}],
        mock_response="Testing langfuse",
    )

    assert len(llm.success_callback) == curr_len_success_callback
    assert len(llm.failure_callback) == curr_len_failure_callback

    assert any(
        isinstance(callback, OpenMeterLogger) for callback in llm.failure_callback
    )


@pytest.mark.asyncio
async def test_wrapper_kwargs_passthrough():
    from llm.utils import client
    from llm.llm_core_utils.llm_logging import (
        Logging as LLMLoggingObject,
    )

    # Create mock original function
    mock_original = AsyncMock()

    # Apply decorator
    @client
    async def test_function(**kwargs):
        return await mock_original(**kwargs)

    # Test kwargs
    test_kwargs = {"base_model": "gpt-4o-mini"}

    # Call decorated function
    await test_function(**test_kwargs)

    mock_original.assert_called_once()

    # get llm logging object
    llm_logging_obj: LLMLoggingObject = mock_original.call_args.kwargs.get(
        "llm_logging_obj"
    )
    assert llm_logging_obj is not None

    print(
        f"llm_logging_obj.model_call_details: {llm_logging_obj.model_call_details}"
    )

    # get base model
    assert (
        llm_logging_obj.model_call_details["llm_params"]["base_model"]
        == "gpt-4o-mini"
    )


def test_dict_to_response_format_helper():
    from llm.llms.base_llm.base_utils import _dict_to_response_format_helper

    args = {
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "schema": {
                    "$defs": {
                        "CalendarEvent": {
                            "properties": {
                                "name": {"title": "Name", "type": "string"},
                                "date": {"title": "Date", "type": "string"},
                                "participants": {
                                    "items": {"type": "string"},
                                    "title": "Participants",
                                    "type": "array",
                                },
                            },
                            "required": ["name", "date", "participants"],
                            "title": "CalendarEvent",
                            "type": "object",
                            "additionalProperties": False,
                        }
                    },
                    "properties": {
                        "events": {
                            "items": {"$ref": "#/$defs/CalendarEvent"},
                            "title": "Events",
                            "type": "array",
                        }
                    },
                    "required": ["events"],
                    "title": "EventsList",
                    "type": "object",
                    "additionalProperties": False,
                },
                "name": "EventsList",
                "strict": True,
            },
        },
        "ref_template": "/$defs/{model}",
    }
    _dict_to_response_format_helper(**args)


def test_validate_user_messages_invalid_content_type():
    from llm.utils import validate_chat_completion_user_messages

    messages = [{"content": [{"type": "invalid_type", "text": "Hello"}]}]

    with pytest.raises(Exception) as e:
        validate_chat_completion_user_messages(messages)

    assert "Invalid message" in str(e)
    print(e)


from llm.integrations.custom_guardrail import CustomGuardrail
from llm.utils import get_applied_guardrails
from unittest.mock import Mock


@pytest.mark.parametrize(
    "test_case",
    [
        {
            "name": "default_on_guardrail",
            "callbacks": [
                CustomGuardrail(guardrail_name="test_guardrail", default_on=True)
            ],
            "kwargs": {"metadata": {"requester_metadata": {"guardrails": []}}},
            "expected": ["test_guardrail"],
        },
        {
            "name": "request_specific_guardrail",
            "callbacks": [
                CustomGuardrail(guardrail_name="test_guardrail", default_on=False)
            ],
            "kwargs": {
                "metadata": {"requester_metadata": {"guardrails": ["test_guardrail"]}}
            },
            "expected": ["test_guardrail"],
        },
        {
            "name": "multiple_guardrails",
            "callbacks": [
                CustomGuardrail(guardrail_name="default_guardrail", default_on=True),
                CustomGuardrail(guardrail_name="request_guardrail", default_on=False),
            ],
            "kwargs": {
                "metadata": {
                    "requester_metadata": {"guardrails": ["request_guardrail"]}
                }
            },
            "expected": ["default_guardrail", "request_guardrail"],
        },
        {
            "name": "empty_metadata",
            "callbacks": [
                CustomGuardrail(guardrail_name="test_guardrail", default_on=False)
            ],
            "kwargs": {},
            "expected": [],
        },
        {
            "name": "none_callback",
            "callbacks": [
                None,
                CustomGuardrail(guardrail_name="test_guardrail", default_on=True),
            ],
            "kwargs": {},
            "expected": ["test_guardrail"],
        },
        {
            "name": "non_guardrail_callback",
            "callbacks": [
                Mock(),
                CustomGuardrail(guardrail_name="test_guardrail", default_on=True),
            ],
            "kwargs": {},
            "expected": ["test_guardrail"],
        },
    ],
)
def test_get_applied_guardrails(test_case):

    # Setup
    llm.callbacks = test_case["callbacks"]

    # Execute
    result = get_applied_guardrails(test_case["kwargs"])

    # Assert
    assert sorted(result) == sorted(test_case["expected"])


@pytest.mark.parametrize(
    "endpoint, params, expected_bool",
    [
        ("localhost:4000/v1/rerank", ["max_chunks_per_doc"], True),
        ("localhost:4000/v2/rerank", ["max_chunks_per_doc"], False),
        ("localhost:4000", ["max_chunks_per_doc"], True),
        ("localhost:4000/v1/rerank", ["max_tokens_per_doc"], True),
        ("localhost:4000/v2/rerank", ["max_tokens_per_doc"], False),
        ("localhost:4000", ["max_tokens_per_doc"], False),
        (
            "localhost:4000/v1/rerank",
            ["max_chunks_per_doc", "max_tokens_per_doc"],
            True,
        ),
        (
            "localhost:4000/v2/rerank",
            ["max_chunks_per_doc", "max_tokens_per_doc"],
            False,
        ),
        ("localhost:4000", ["max_chunks_per_doc", "max_tokens_per_doc"], False),
    ],
)
def test_should_use_cohere_v1_client(endpoint, params, expected_bool):
    assert llm.utils.should_use_cohere_v1_client(endpoint, params) == expected_bool


def test_add_openai_metadata():
    from llm.utils import add_openai_metadata

    metadata = {
        "user_api_key_end_user_id": "123",
        "hidden_params": {"api_key": "123"},
        "llm_parent_otel_span": MagicMock(),
        "none-val": None,
        "int-val": 1,
        "dict-val": {"a": 1, "b": 2},
    }

    result = add_openai_metadata(metadata)

    assert result == {
        "user_api_key_end_user_id": "123",
    }


def test_message_object():
    from llm.types.utils import Message

    message = Message(content="Hello, world!", role="user")
    assert message.content == "Hello, world!"
    assert message.role == "user"
    assert not hasattr(message, "audio")
    assert not hasattr(message, "thinking_blocks")
    assert not hasattr(message, "reasoning_content")


def test_delta_object():
    from llm.types.utils import Delta

    delta = Delta(content="Hello, world!", role="user")
    assert delta.content == "Hello, world!"
    assert delta.role == "user"
    assert not hasattr(delta, "thinking_blocks")
    assert not hasattr(delta, "reasoning_content")
