import Image from '@theme/IdealImage';

# Langsmith - Logging LLM Input/Output



An all-in-one developer platform for every step of the application lifecycle
https://smith.langchain.com/

<Image img={require('../../img/langsmith_new.png')} />

:::info
We want to learn how we can make the callbacks better! Meet the LLM [founders](https://calendly.com/d/4mp-gd3-k5k/hanzoai-1-1-onboarding-llm-hosted-version) or
join our [discord](https://discord.gg/XthHQQj)
::: 

## Pre-Requisites
```shell
pip install llm
```

## Quick Start
Use just 2 lines of code, to instantly log your responses **across all providers** with Langsmith


```python
llm.success_callback = ["langsmith"]
```
```python
import llm
import os

os.environ["LANGSMITH_API_KEY"] = ""
os.environ["LANGSMITH_PROJECT"] = "" # defaults to llm-completion
os.environ["LANGSMITH_DEFAULT_RUN_NAME"] = "" # defaults to LLMRun
# LLM API Keys
os.environ['OPENAI_API_KEY']=""

# set langsmith as a callback, llm will send the data to langsmith
llm.success_callback = ["langsmith"] 
 
# openai call
response = llm.completion(
  model="gpt-3.5-turbo",
  messages=[
    {"role": "user", "content": "Hi 👋 - i'm openai"}
  ]
)
```

## Advanced
### Set Langsmith fields

```python
import llm
import os

os.environ["LANGSMITH_API_KEY"] = ""
# LLM API Keys
os.environ['OPENAI_API_KEY']=""

# set langsmith as a callback, llm will send the data to langsmith
llm.success_callback = ["langsmith"] 
 
response = llm.completion(
    model="gpt-3.5-turbo",
     messages=[
        {"role": "user", "content": "Hi 👋 - i'm openai"}
    ],
    metadata={
        "run_name": "llmRUN",                                   # langsmith run name
        "project_name": "llm-completion",                       # langsmith project name
        "run_id": "497f6eca-6276-4993-bfeb-53cbbbba6f08",           # langsmith run id
        "parent_run_id": "f8faf8c1-9778-49a4-9004-628cdb0047e5",    # langsmith run parent run id
        "trace_id": "df570c03-5a03-4cea-8df0-c162d05127ac",         # langsmith run trace id
        "session_id": "1ffd059c-17ea-40a8-8aef-70fd0307db82",       # langsmith run session id
        "tags": ["model1", "prod-2"],                               # langsmith run tags
        "metadata": {                                               # langsmith run metadata
            "key1": "value1"
        },
        "dotted_order": "20240429T004912090000Z497f6eca-6276-4993-bfeb-53cbbbba6f08"
    }
)
print(response)
```

### Make LLM Proxy use Custom `LANGSMITH_BASE_URL`

If you're using a custom LangSmith instance, you can set the
`LANGSMITH_BASE_URL` environment variable to point to your instance.
For example, you can make LLM Proxy log to a local LangSmith instance with
this config:

```yaml
llm_settings:
  success_callback: ["langsmith"]

environment_variables:
  LANGSMITH_BASE_URL: "http://localhost:1984"
  LANGSMITH_PROJECT: "llm-proxy"
```

## Support & Talk to Founders

- [Schedule Demo 👋](https://calendly.com/d/4mp-gd3-k5k/hanzoai-1-1-onboarding-llm-hosted-version)
- [Community Discord 💭](https://discord.gg/XthHQQj)
- Our numbers 📞 +1 (770) 8783-106 / ‭+1 (412) 618-6238‬
- Our emails ✉️ z@hanzo.ai / dev@hanzo.ai
