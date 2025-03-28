#### What this tests ####
#  Allow the user to map the function to the prompt, if the model doesn't support function calling

import sys, os, pytest
import traceback

sys.path.insert(
    0, os.path.abspath("../..")
)  # Adds the parent directory to the system path
import llm


## case 1: set_function_to_prompt not set
def test_function_call_non_openai_model():
    try:
        model = "claude-3-5-haiku-20241022"
        messages = [{"role": "user", "content": "what's the weather in sf?"}]
        functions = [
            {
                "name": "get_current_weather",
                "description": "Get the current weather in a given location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "The city and state, e.g. San Francisco, CA",
                        },
                        "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
                    },
                    "required": ["location"],
                },
            }
        ]
        response = llm.completion(
            model=model, messages=messages, functions=functions
        )
        pytest.fail(f"An error occurred")
    except Exception as e:
        print(e)
        pass


# test_function_call_non_openai_model()

# test_function_call_non_openai_model_llm_mod_set()
