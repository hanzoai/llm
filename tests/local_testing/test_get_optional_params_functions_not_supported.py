import llm
from llm import get_optional_params

llm.add_function_to_prompt = True
optional_params = get_optional_params(
    model="",
    tools=[
        {
            "type": "function",
            "function": {
                "description": "Get the current weather in a given location",
                "name": "get_current_weather",
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
            },
        }
    ],
    tool_choice="auto",
)
assert optional_params is not None
