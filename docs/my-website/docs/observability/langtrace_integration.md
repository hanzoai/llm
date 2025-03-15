import Image from '@theme/IdealImage';

# Langtrace AI

Monitor, evaluate & improve your LLM apps

## Pre-Requisites

Make an account on [Langtrace AI](https://langtrace.ai/login)

## Quick Start

Use just 2 lines of code, to instantly log your responses **across all providers** with langtrace

```python
llm.callbacks = ["langtrace"]
langtrace.init()
```

```python
import llm
import os
from langtrace_python_sdk import langtrace

# Langtrace API Keys
os.environ["LANGTRACE_API_KEY"] = "<your-api-key>"

# LLM API Keys
os.environ['OPENAI_API_KEY']="<openai-api-key>"

# set langtrace as a callback, llm will send the data to langtrace
llm.callbacks = ["langtrace"]

#  init langtrace
langtrace.init()

# openai call
response = completion(
    model="gpt-4o",
    messages=[
        {"content": "respond only in Yoda speak.", "role": "system"},
        {"content": "Hello, how are you?", "role": "user"},
    ],
)
print(response)
```

### Using with Hanzo Proxy

```yaml
model_list:
  - model_name: gpt-4
    llm_params:
      model: openai/fake
      api_key: fake-key
      api_base: https://exampleopenaiendpoint-production.up.railway.app/

llm_settings:
  callbacks: ["langtrace"]

environment_variables:
  LANGTRACE_API_KEY: "141a****"
```
