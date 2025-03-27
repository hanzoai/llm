import Image from '@theme/IdealImage';

# 🌙 Lunary - GenAI Observability 

[Lunary](https://lunary.ai/) is an open-source platform providing [observability](https://lunary.ai/docs/features/observe), [prompt management](https://lunary.ai/docs/features/prompts), and [analytics](https://lunary.ai/docs/features/observe#analytics) to help team manage and improve LLM chatbots.

You can reach out to us anytime by [email](mailto:hello@lunary.ai) or directly [schedule a Demo](https://lunary.ai/schedule).

<video controls width='900' >
  <source src='https://lunary.ai/videos/demo-annotated.mp4'/>
</video>


## Usage with LLM Python SDK
### Pre-Requisites

```shell
pip install llm lunary
```

### Quick Start

First, get your Lunary public key on the [Lunary dashboard](https://app.lunary.ai/).

Use just 2 lines of code, to instantly log your responses **across all providers** with Lunary:

```python
llm.success_callback = ["lunary"]
llm.failure_callback = ["lunary"]
```

Complete code:
```python
from llm import completion

os.environ["LUNARY_PUBLIC_KEY"] = "your-lunary-public-key" # from https://app.lunary.ai/)
os.environ["OPENAI_API_KEY"] = ""

llm.success_callback = ["lunary"]
llm.failure_callback = ["lunary"]

response = completion(
  model="gpt-4o",
  messages=[{"role": "user", "content": "Hi there 👋"}],
  user="z_llm"
)
```

### Usage with LangChain ChatLLM 
```python
import os
from langchain.chat_models import ChatLLM
from langchain.schema import HumanMessage
import llm

os.environ["LUNARY_PUBLIC_KEY"] = "" # from https://app.lunary.ai/settings
os.environ['OPENAI_API_KEY']="sk-..."

llm.success_callback = ["lunary"] 
llm.failure_callback = ["lunary"] 

chat = ChatLLM(
  model="gpt-4o"
  messages = [
    HumanMessage(
        content="what model are you"
    )
]
chat(messages)
```


### Usage with Prompt Templates

You can use Lunary to manage [prompt templates](https://lunary.ai/docs/features/prompts) and use them across all your LLM providers with LLM.

```python
from llm import completion
from lunary

template = lunary.render_template("template-slug", {
  "name": "John", # Inject variables
})

llm.success_callback = ["lunary"]

result = completion(**template)
```

### Usage with custom chains
You can wrap your LLM calls inside custom chains, so that you can visualize them as traces.

```python
import llm
from llm import completion
import lunary

llm.success_callback = ["lunary"]
llm.failure_callback = ["lunary"]

@lunary.chain("My custom chain name")
def my_chain(chain_input):
  chain_run_id = lunary.run_manager.current_run_id
  response = completion(
    model="gpt-4o", 
    messages=[{"role": "user", "content": "Say 1"}],
    metadata={"parent_run_id": chain_run_id},
  )

  response = completion(
    model="gpt-4o", 
    messages=[{"role": "user", "content": "Say 2"}],
    metadata={"parent_run_id": chain_run_id},
  )
  chain_output = response.choices[0].message
  return chain_output

my_chain("Chain input")
```

<Image img={require('../../img/lunary-trace.png')} />

## Usage with LLM Proxy Server
### Step1: Install dependencies and set your environment variables 
Install the dependencies
```shell
pip install llm lunary
```

Get you Lunary public key from from https://app.lunary.ai/settings 
```shell
export LUNARY_PUBLIC_KEY="<your-public-key>"
```

### Step 2: Create a `config.yaml` and set `lunary` callbacks

```yaml
model_list:
  - model_name: "*"
    llm_params:
      model: "*"
llm_settings:
  success_callback: ["lunary"]
  failure_callback: ["lunary"]
```

### Step 3: Start the LLM proxy
```shell
llm --config config.yaml
```

### Step 4: Make a request

```shell
curl -X POST 'http://0.0.0.0:4000/chat/completions' \
-H 'Content-Type: application/json' \
-d '{
    "model": "gpt-4o",
    "messages": [
      {
        "role": "system",
        "content": "You are a helpful math tutor. Guide the user through the solution step by step."
      },
      {
        "role": "user",
        "content": "how can I solve 8x + 7 = -23"
      }
    ]
}'
```

You can find more details about the different ways of making requests to the LLM proxy on [this page](https://docs.hanzo.ai/docs/proxy/user_keys)


## Support & Talk to Founders

- [Schedule Demo 👋](https://calendly.com/d/4mp-gd3-k5k/hanzoai-1-1-onboarding-llm-hosted-version)
- [Community Discord 💭](https://discord.gg/XthHQQj)
- Our numbers 📞 +1 (770) 8783-106 / ‭+1 (412) 618-6238‬
- Our emails ✉️ z@hanzo.ai / dev@hanzo.ai
