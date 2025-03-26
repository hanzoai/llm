
import Image from '@theme/IdealImage';
import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

# Arize AI

AI Observability and Evaluation Platform

:::tip

This is community maintained, Please make an issue if you run into a bug
https://github.com/hanzoai/llm

:::

<Image img={require('../../img/arize.png')} />



## Pre-Requisites
Make an account on [Arize AI](https://app.arize.com/auth/login)

## Quick Start
Use just 2 lines of code, to instantly log your responses **across all providers** with arize

You can also use the instrumentor option instead of the callback, which you can find [here](https://docs.arize.com/arize/llm-tracing/tracing-integrations-auto/llm).

```python
llm.callbacks = ["arize"]
```

```python

import llm
import os

os.environ["ARIZE_SPACE_KEY"] = ""
os.environ["ARIZE_API_KEY"] = ""

# LLM API Keys
os.environ['OPENAI_API_KEY']=""

# set arize as a callback, llm will send the data to arize
llm.callbacks = ["arize"]
 
# openai call
response = llm.completion(
  model="gpt-3.5-turbo",
  messages=[
    {"role": "user", "content": "Hi 👋 - i'm openai"}
  ]
)
```

### Using with LLM Proxy

1. Setup config.yaml
```yaml
model_list:
  - model_name: gpt-4
    llm_params:
      model: openai/fake
      api_key: fake-key
      api_base: https://exampleopenaiendpoint-production.up.railway.app/

llm_settings:
  callbacks: ["arize"]

general_settings:
  master_key: "sk-1234" # can also be set as an environment variable

environment_variables:
    ARIZE_SPACE_KEY: "d0*****"
    ARIZE_API_KEY: "141a****"
    ARIZE_ENDPOINT: "https://otlp.arize.com/v1" # OPTIONAL - your custom arize GRPC api endpoint
    ARIZE_HTTP_ENDPOINT: "https://otlp.arize.com/v1" # OPTIONAL - your custom arize HTTP api endpoint. Set either this or ARIZE_ENDPOINT or Neither (defaults to https://otlp.arize.com/v1 on grpc)
```

2. Start the proxy

```bash
llm --config config.yaml
```

3. Test it!

```bash
curl -X POST 'http://0.0.0.0:4000/chat/completions' \
-H 'Content-Type: application/json' \
-H 'Authorization: Bearer sk-1234' \
-d '{ "model": "gpt-4", "messages": [{"role": "user", "content": "Hi 👋 - i'm openai"}]}'
```

## Pass Arize Space/Key per-request

Supported parameters:
- `arize_api_key`
- `arize_space_key`

<Tabs>
<TabItem value="sdk" label="SDK">

```python
import llm
import os

# LLM API Keys
os.environ['OPENAI_API_KEY']=""

# set arize as a callback, llm will send the data to arize
llm.callbacks = ["arize"]
 
# openai call
response = llm.completion(
  model="gpt-3.5-turbo",
  messages=[
    {"role": "user", "content": "Hi 👋 - i'm openai"}
  ],
  arize_api_key=os.getenv("ARIZE_SPACE_2_API_KEY"),
  arize_space_key=os.getenv("ARIZE_SPACE_2_KEY"),
)
```

</TabItem>
<TabItem value="proxy" label="PROXY">

1. Setup config.yaml
```yaml
model_list:
  - model_name: gpt-4
    llm_params:
      model: openai/fake
      api_key: fake-key
      api_base: https://exampleopenaiendpoint-production.up.railway.app/

llm_settings:
  callbacks: ["arize"]

general_settings:
  master_key: "sk-1234" # can also be set as an environment variable
```

2. Start the proxy

```bash
llm --config /path/to/config.yaml
```

3. Test it!

<Tabs>
<TabItem value="curl" label="CURL">

```bash
curl -X POST 'http://0.0.0.0:4000/chat/completions' \
-H 'Content-Type: application/json' \
-H 'Authorization: Bearer sk-1234' \
-d '{
  "model": "gpt-4",
  "messages": [{"role": "user", "content": "Hi 👋 - i'm openai"}],
  "arize_api_key": "ARIZE_SPACE_2_API_KEY",
  "arize_space_key": "ARIZE_SPACE_2_KEY"
}'
```
</TabItem>
<TabItem value="openai_python" label="OpenAI Python">

```python
import openai
client = openai.OpenAI(
    api_key="anything",
    base_url="http://0.0.0.0:4000"
)

# request sent to model set on llm proxy, `llm --model`
response = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages = [
        {
            "role": "user",
            "content": "this is a test request, write a short poem"
        }
    ],
    extra_body={
      "arize_api_key": "ARIZE_SPACE_2_API_KEY",
      "arize_space_key": "ARIZE_SPACE_2_KEY"
    }
)

print(response)
```
</TabItem>
</Tabs>
</TabItem>
</Tabs>

## Support & Talk to Founders

- [Schedule Demo 👋](https://calendly.com/d/4mp-gd3-k5k/hanzoai-1-1-onboarding-llm-hosted-version)
- [Community Discord 💭](https://discord.gg/XthHQQj)
- Our numbers 📞 +1 (770) 8783-106 / ‭+1 (412) 618-6238‬
- Our emails ✉️ z@hanzo.ai / dev@hanzo.ai
