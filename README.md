<h1 align="center">
        🚅 LLM
    </h1>
    <p align="center">
        <p align="center">
        <a href="https://render.com/deploy?repo=https://github.com/BerriAI/llm" target="_blank" rel="nofollow"><img src="https://render.com/images/deploy-to-render-button.svg" alt="Deploy to Render"></a>
        <a href="https://railway.app/template/HLP0Ub?referralCode=jch2ME">
          <img src="https://railway.app/button.svg" alt="Deploy on Railway">
        </a>
        </p>
        <p align="center">Call all LLM APIs using the OpenAI format [Bedrock, Huggingface, VertexAI, TogetherAI, Azure, OpenAI, Groq etc.]
        <br>
    </p>
<h4 align="center"><a href="https://docs.llm.ai/docs/simple_proxy" target="_blank">LLM Proxy Server (LLM Gateway)</a> | <a href="https://docs.llm.ai/docs/hosted" target="_blank"> Hosted Proxy (Preview)</a> | <a href="https://docs.llm.ai/docs/enterprise"target="_blank">Enterprise Tier</a></h4>
<h4 align="center">
    <a href="https://pypi.org/project/llm/" target="_blank">
        <img src="https://img.shields.io/pypi/v/llm.svg" alt="PyPI Version">
    </a>
    <a href="https://dl.circleci.com/status-badge/redirect/gh/BerriAI/llm/tree/main" target="_blank">
        <img src="https://dl.circleci.com/status-badge/img/gh/BerriAI/llm/tree/main.svg?style=svg" alt="CircleCI">
    </a>
    <a href="https://www.ycombinator.com/companies/berriai">
        <img src="https://img.shields.io/badge/Y%20Combinator-W23-orange?style=flat-square" alt="Y Combinator W23">
    </a>
    <a href="https://wa.link/huol9n">
        <img src="https://img.shields.io/static/v1?label=Chat%20on&message=WhatsApp&color=success&logo=WhatsApp&style=flat-square" alt="Whatsapp">
    </a>
    <a href="https://discord.gg/wuPM9dRgDw">
        <img src="https://img.shields.io/static/v1?label=Chat%20on&message=Discord&color=blue&logo=Discord&style=flat-square" alt="Discord">
    </a>
</h4>

LLM manages:

- Translate inputs to provider's `completion`, `embedding`, and `image_generation` endpoints
- [Consistent output](https://docs.llm.ai/docs/completion/output), text responses will always be available at `['choices'][0]['message']['content']`
- Retry/fallback logic across multiple deployments (e.g. Azure/OpenAI) - [Router](https://docs.llm.ai/docs/routing)
- Set Budgets & Rate limits per project, api key, model [LLM Proxy Server (LLM Gateway)](https://docs.llm.ai/docs/simple_proxy)

[**Jump to LLM Proxy (LLM Gateway) Docs**](https://github.com/BerriAI/llm?tab=readme-ov-file#openai-proxy---docs) <br>
[**Jump to Supported LLM Providers**](https://github.com/BerriAI/llm?tab=readme-ov-file#supported-providers-docs)

🚨 **Stable Release:** Use docker images with the `-stable` tag. These have undergone 12 hour load tests, before being published. [More information about the release cycle here](https://docs.llm.ai/docs/proxy/release_cycle)

Support for more providers. Missing a provider or LLM Platform, raise a [feature request](https://github.com/BerriAI/llm/issues/new?assignees=&labels=enhancement&projects=&template=feature_request.yml&title=%5BFeature%5D%3A+).

# Usage ([**Docs**](https://docs.llm.ai/docs/))

> [!IMPORTANT]
> LLM v1.0.0 now requires `openai>=1.0.0`. Migration guide [here](https://docs.llm.ai/docs/migration)  
> LLM v1.40.14+ now requires `pydantic>=2.0.0`. No changes required.

<a target="_blank" href="https://colab.research.google.com/github/BerriAI/llm/blob/main/cookbook/llm_Getting_Started.ipynb">
  <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/>
</a>

```shell
pip install llm
```

```python
from llm import completion
import os

## set ENV variables
os.environ["OPENAI_API_KEY"] = "your-openai-key"
os.environ["ANTHROPIC_API_KEY"] = "your-anthropic-key"

messages = [{ "content": "Hello, how are you?","role": "user"}]

# openai call
response = completion(model="openai/gpt-4o", messages=messages)

# anthropic call
response = completion(model="anthropic/claude-3-sonnet-20240229", messages=messages)
print(response)
```

### Response (OpenAI Format)

```json
{
    "id": "chatcmpl-565d891b-a42e-4c39-8d14-82a1f5208885",
    "created": 1734366691,
    "model": "claude-3-sonnet-20240229",
    "object": "chat.completion",
    "system_fingerprint": null,
    "choices": [
        {
            "finish_reason": "stop",
            "index": 0,
            "message": {
                "content": "Hello! As an AI language model, I don't have feelings, but I'm operating properly and ready to assist you with any questions or tasks you may have. How can I help you today?",
                "role": "assistant",
                "tool_calls": null,
                "function_call": null
            }
        }
    ],
    "usage": {
        "completion_tokens": 43,
        "prompt_tokens": 13,
        "total_tokens": 56,
        "completion_tokens_details": null,
        "prompt_tokens_details": {
            "audio_tokens": null,
            "cached_tokens": 0
        },
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0
    }
}
```

Call any model supported by a provider, with `model=<provider_name>/<model_name>`. There might be provider-specific details here, so refer to [provider docs for more information](https://docs.llm.ai/docs/providers)

## Async ([Docs](https://docs.llm.ai/docs/completion/stream#async-completion))

```python
from llm import acompletion
import asyncio

async def test_get_response():
    user_message = "Hello, how are you?"
    messages = [{"content": user_message, "role": "user"}]
    response = await acompletion(model="openai/gpt-4o", messages=messages)
    return response

response = asyncio.run(test_get_response())
print(response)
```

## Streaming ([Docs](https://docs.llm.ai/docs/completion/stream))

llm supports streaming the model response back, pass `stream=True` to get a streaming iterator in response.  
Streaming is supported for all models (Bedrock, Huggingface, TogetherAI, Azure, OpenAI, etc.)

```python
from llm import completion
response = completion(model="openai/gpt-4o", messages=messages, stream=True)
for part in response:
    print(part.choices[0].delta.content or "")

# claude 2
response = completion('anthropic/claude-3-sonnet-20240229', messages, stream=True)
for part in response:
    print(part)
```

### Response chunk (OpenAI Format)

```json
{
    "id": "chatcmpl-2be06597-eb60-4c70-9ec5-8cd2ab1b4697",
    "created": 1734366925,
    "model": "claude-3-sonnet-20240229",
    "object": "chat.completion.chunk",
    "system_fingerprint": null,
    "choices": [
        {
            "finish_reason": null,
            "index": 0,
            "delta": {
                "content": "Hello",
                "role": "assistant",
                "function_call": null,
                "tool_calls": null,
                "audio": null
            },
            "logprobs": null
        }
    ]
}
```

## Logging Observability ([Docs](https://docs.llm.ai/docs/observability/callbacks))

LLM exposes pre defined callbacks to send data to Lunary, MLflow, Langfuse, DynamoDB, s3 Buckets, Helicone, Promptlayer, Traceloop, Athina, Slack

```python
from llm import completion

## set env variables for logging tools (when using MLflow, no API key set up is required)
os.environ["LUNARY_PUBLIC_KEY"] = "your-lunary-public-key"
os.environ["HELICONE_API_KEY"] = "your-helicone-auth-key"
os.environ["LANGFUSE_PUBLIC_KEY"] = ""
os.environ["LANGFUSE_SECRET_KEY"] = ""
os.environ["ATHINA_API_KEY"] = "your-athina-api-key"

os.environ["OPENAI_API_KEY"] = "your-openai-key"

# set callbacks
llm.success_callback = ["lunary", "mlflow", "langfuse", "athina", "helicone"] # log input/output to lunary, langfuse, supabase, athina, helicone etc

#openai call
response = completion(model="openai/gpt-4o", messages=[{"role": "user", "content": "Hi 👋 - i'm openai"}])
```

# LLM Proxy Server (LLM Gateway) - ([Docs](https://docs.llm.ai/docs/simple_proxy))

Track spend + Load Balance across multiple projects

[Hosted Proxy (Preview)](https://docs.llm.ai/docs/hosted)

The proxy provides:

1. [Hooks for auth](https://docs.llm.ai/docs/proxy/virtual_keys#custom-auth)
2. [Hooks for logging](https://docs.llm.ai/docs/proxy/logging#step-1---create-your-custom-llm-callback-class)
3. [Cost tracking](https://docs.llm.ai/docs/proxy/virtual_keys#tracking-spend)
4. [Rate Limiting](https://docs.llm.ai/docs/proxy/users#set-rate-limits)

## 📖 Proxy Endpoints - [Swagger Docs](https://llm-api.up.railway.app/)


## Quick Start Proxy - CLI

```shell
pip install 'llm[proxy]'
```

### Step 1: Start llm proxy

```shell
$ llm --model huggingface/bigcode/starcoder

#INFO: Proxy running on http://0.0.0.0:4000
```

### Step 2: Make ChatCompletions Request to Proxy


> [!IMPORTANT]
> 💡 [Use LLM Proxy with Langchain (Python, JS), OpenAI SDK (Python, JS) Anthropic SDK, Mistral SDK, LlamaIndex, Instructor, Curl](https://docs.llm.ai/docs/proxy/user_keys)  

```python
import openai # openai v1.0.0+
client = openai.OpenAI(api_key="anything",base_url="http://0.0.0.0:4000") # set proxy to base_url
# request sent to model set on llm proxy, `llm --model`
response = client.chat.completions.create(model="gpt-3.5-turbo", messages = [
    {
        "role": "user",
        "content": "this is a test request, write a short poem"
    }
])

print(response)
```

## Proxy Key Management ([Docs](https://docs.llm.ai/docs/proxy/virtual_keys))

Connect the proxy with a Postgres DB to create proxy keys

```bash
# Get the code
git clone https://github.com/BerriAI/llm

# Go to folder
cd llm

# Add the master key - you can change this after setup
echo 'LLM_MASTER_KEY="sk-1234"' > .env

# Add the llm salt key - you cannot change this after adding a model
# It is used to encrypt / decrypt your LLM API Key credentials
# We recommend - https://1password.com/password-generator/ 
# password generator to get a random hash for llm salt key
echo 'LLM_SALT_KEY="sk-1234"' > .env

source .env

# Start
docker-compose up
```


UI on `/ui` on your proxy server
![ui_3](https://github.com/BerriAI/llm/assets/29436595/47c97d5e-b9be-4839-b28c-43d7f4f10033)

Set budgets and rate limits across multiple projects
`POST /key/generate`

### Request

```shell
curl 'http://0.0.0.0:4000/key/generate' \
--header 'Authorization: Bearer sk-1234' \
--header 'Content-Type: application/json' \
--data-raw '{"models": ["gpt-3.5-turbo", "gpt-4", "claude-2"], "duration": "20m","metadata": {"user": "ishaan@berri.ai", "team": "core-infra"}}'
```

### Expected Response

```shell
{
    "key": "sk-kdEXbIqZRwEeEiHwdg7sFA", # Bearer token
    "expires": "2023-11-19T01:38:25.838000+00:00" # datetime object
}
```

## Supported Providers ([Docs](https://docs.llm.ai/docs/providers))

| Provider                                                                            | [Completion](https://docs.llm.ai/docs/#basic-usage) | [Streaming](https://docs.llm.ai/docs/completion/stream#streaming-responses) | [Async Completion](https://docs.llm.ai/docs/completion/stream#async-completion) | [Async Streaming](https://docs.llm.ai/docs/completion/stream#async-streaming) | [Async Embedding](https://docs.llm.ai/docs/embedding/supported_embedding) | [Async Image Generation](https://docs.llm.ai/docs/image_generation) |
|-------------------------------------------------------------------------------------|---------------------------------------------------------|---------------------------------------------------------------------------------|-------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------|-------------------------------------------------------------------------------|-------------------------------------------------------------------------|
| [openai](https://docs.llm.ai/docs/providers/openai)                             | ✅                                                       | ✅                                                                               | ✅                                                                                   | ✅                                                                                 | ✅                                                                             | ✅                                                                       |
| [azure](https://docs.llm.ai/docs/providers/azure)                               | ✅                                                       | ✅                                                                               | ✅                                                                                   | ✅                                                                                 | ✅                                                                             | ✅                                                                       |
| [AI/ML API](https://docs.llm.ai/docs/providers/aiml)                               | ✅                                                       | ✅                                                                               | ✅                                                                                   | ✅                                                                                 | ✅                                                                             | ✅                                                                       |
| [aws - sagemaker](https://docs.llm.ai/docs/providers/aws_sagemaker)             | ✅                                                       | ✅                                                                               | ✅                                                                                   | ✅                                                                                 | ✅                                                                             |                                                                         |
| [aws - bedrock](https://docs.llm.ai/docs/providers/bedrock)                     | ✅                                                       | ✅                                                                               | ✅                                                                                   | ✅                                                                                 | ✅                                                                             |                                                                         |
| [google - vertex_ai](https://docs.llm.ai/docs/providers/vertex)                 | ✅                                                       | ✅                                                                               | ✅                                                                                   | ✅                                                                                 | ✅                                                                             | ✅                                                                       |
| [google - palm](https://docs.llm.ai/docs/providers/palm)                        | ✅                                                       | ✅                                                                               | ✅                                                                                   | ✅                                                                                 |                                                                               |                                                                         |
| [google AI Studio - gemini](https://docs.llm.ai/docs/providers/gemini)          | ✅                                                       | ✅                                                                               | ✅                                                                                   | ✅                                                                                 |                                                                               |                                                                         |
| [mistral ai api](https://docs.llm.ai/docs/providers/mistral)                    | ✅                                                       | ✅                                                                               | ✅                                                                                   | ✅                                                                                 | ✅                                                                             |                                                                         |
| [cloudflare AI Workers](https://docs.llm.ai/docs/providers/cloudflare_workers)  | ✅                                                       | ✅                                                                               | ✅                                                                                   | ✅                                                                                 |                                                                               |                                                                         |
| [cohere](https://docs.llm.ai/docs/providers/cohere)                             | ✅                                                       | ✅                                                                               | ✅                                                                                   | ✅                                                                                 | ✅                                                                             |                                                                         |
| [anthropic](https://docs.llm.ai/docs/providers/anthropic)                       | ✅                                                       | ✅                                                                               | ✅                                                                                   | ✅                                                                                 |                                                                               |                                                                         |
| [empower](https://docs.llm.ai/docs/providers/empower)                    | ✅                                                      | ✅                                                                              | ✅                                                                                  | ✅                                                                                |
| [huggingface](https://docs.llm.ai/docs/providers/huggingface)                   | ✅                                                       | ✅                                                                               | ✅                                                                                   | ✅                                                                                 | ✅                                                                             |                                                                         |
| [replicate](https://docs.llm.ai/docs/providers/replicate)                       | ✅                                                       | ✅                                                                               | ✅                                                                                   | ✅                                                                                 |                                                                               |                                                                         |
| [together_ai](https://docs.llm.ai/docs/providers/togetherai)                    | ✅                                                       | ✅                                                                               | ✅                                                                                   | ✅                                                                                 |                                                                               |                                                                         |
| [openrouter](https://docs.llm.ai/docs/providers/openrouter)                     | ✅                                                       | ✅                                                                               | ✅                                                                                   | ✅                                                                                 |                                                                               |                                                                         |
| [ai21](https://docs.llm.ai/docs/providers/ai21)                                 | ✅                                                       | ✅                                                                               | ✅                                                                                   | ✅                                                                                 |                                                                               |                                                                         |
| [baseten](https://docs.llm.ai/docs/providers/baseten)                           | ✅                                                       | ✅                                                                               | ✅                                                                                   | ✅                                                                                 |                                                                               |                                                                         |
| [vllm](https://docs.llm.ai/docs/providers/vllm)                                 | ✅                                                       | ✅                                                                               | ✅                                                                                   | ✅                                                                                 |                                                                               |                                                                         |
| [nlp_cloud](https://docs.llm.ai/docs/providers/nlp_cloud)                       | ✅                                                       | ✅                                                                               | ✅                                                                                   | ✅                                                                                 |                                                                               |                                                                         |
| [aleph alpha](https://docs.llm.ai/docs/providers/aleph_alpha)                   | ✅                                                       | ✅                                                                               | ✅                                                                                   | ✅                                                                                 |                                                                               |                                                                         |
| [petals](https://docs.llm.ai/docs/providers/petals)                             | ✅                                                       | ✅                                                                               | ✅                                                                                   | ✅                                                                                 |                                                                               |                                                                         |
| [ollama](https://docs.llm.ai/docs/providers/ollama)                             | ✅                                                       | ✅                                                                               | ✅                                                                                   | ✅                                                                                 | ✅                                                                             |                                                                         |
| [deepinfra](https://docs.llm.ai/docs/providers/deepinfra)                       | ✅                                                       | ✅                                                                               | ✅                                                                                   | ✅                                                                                 |                                                                               |                                                                         |
| [perplexity-ai](https://docs.llm.ai/docs/providers/perplexity)                  | ✅                                                       | ✅                                                                               | ✅                                                                                   | ✅                                                                                 |                                                                               |                                                                         |
| [Groq AI](https://docs.llm.ai/docs/providers/groq)                              | ✅                                                       | ✅                                                                               | ✅                                                                                   | ✅                                                                                 |                                                                               |                                                                         |
| [Deepseek](https://docs.llm.ai/docs/providers/deepseek)                         | ✅                                                       | ✅                                                                               | ✅                                                                                   | ✅                                                                                 |                                                                               |                                                                         |
| [anyscale](https://docs.llm.ai/docs/providers/anyscale)                         | ✅                                                       | ✅                                                                               | ✅                                                                                   | ✅                                                                                 |                                                                               |                                                                         |
| [IBM - watsonx.ai](https://docs.llm.ai/docs/providers/watsonx)                  | ✅                                                       | ✅                                                                               | ✅                                                                                   | ✅                                                                                 | ✅                                                                             |                                                                         |
| [voyage ai](https://docs.llm.ai/docs/providers/voyage)                          |                                                         |                                                                                 |                                                                                     |                                                                                   | ✅                                                                             |                                                                         |
| [xinference [Xorbits Inference]](https://docs.llm.ai/docs/providers/xinference) |                                                         |                                                                                 |                                                                                     |                                                                                   | ✅                                                                             |                                                                         |
| [FriendliAI](https://docs.llm.ai/docs/providers/friendliai)                              | ✅                                                       | ✅                                                                               | ✅                                                                                   | ✅                                                                                 |                                                                               |                                                                         |
| [Galadriel](https://docs.llm.ai/docs/providers/galadriel)                              | ✅                                                       | ✅                                                                               | ✅                                                                                   | ✅                                                                                 |                                                                               |                                                                         |

[**Read the Docs**](https://docs.llm.ai/docs/)

## Contributing

Interested in contributing? Contributions to LLM Python SDK, Proxy Server, and contributing LLM integrations are both accepted and highly encouraged! [See our Contribution Guide for more details](https://docs.llm.ai/docs/extras/contributing_code)

# Enterprise
For companies that need better security, user management and professional support

[Talk to founders](https://calendly.com/d/4mp-gd3-k5k/llm-1-1-onboarding-chat)

This covers: 
- ✅ **Features under the [LLM Commercial License](https://docs.llm.ai/docs/proxy/enterprise):**
- ✅ **Feature Prioritization**
- ✅ **Custom Integrations**
- ✅ **Professional Support - Dedicated discord + slack**
- ✅ **Custom SLAs**
- ✅ **Secure access with Single Sign-On**

# Code Quality / Linting

LLM follows the [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html).

We run: 
- Ruff for [formatting and linting checks](https://github.com/BerriAI/llm/blob/e19bb55e3b4c6a858b6e364302ebbf6633a51de5/.circleci/config.yml#L320)
- Mypy + Pyright for typing [1](https://github.com/BerriAI/llm/blob/e19bb55e3b4c6a858b6e364302ebbf6633a51de5/.circleci/config.yml#L90), [2](https://github.com/BerriAI/llm/blob/e19bb55e3b4c6a858b6e364302ebbf6633a51de5/.pre-commit-config.yaml#L4)
- Black for [formatting](https://github.com/BerriAI/llm/blob/e19bb55e3b4c6a858b6e364302ebbf6633a51de5/.circleci/config.yml#L79)
- isort for [import sorting](https://github.com/BerriAI/llm/blob/e19bb55e3b4c6a858b6e364302ebbf6633a51de5/.pre-commit-config.yaml#L10)


If you have suggestions on how to improve the code quality feel free to open an issue or a PR.


# Support / talk with founders

- [Schedule Demo 👋](https://calendly.com/d/4mp-gd3-k5k/berriai-1-1-onboarding-llm-hosted-version)
- [Community Discord 💭](https://discord.gg/wuPM9dRgDw)
- Our numbers 📞 +1 (770) 8783-106 / ‭+1 (412) 618-6238‬
- Our emails ✉️ ishaan@berri.ai / krrish@berri.ai

# Why did we build this

- **Need for simplicity**: Our code started to get extremely complicated managing & translating calls between Azure, OpenAI and Cohere.

# Contributors

<!-- ALL-CONTRIBUTORS-LIST:START - Do not remove or modify this section -->
<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->

<!-- markdownlint-restore -->
<!-- prettier-ignore-end -->

<!-- ALL-CONTRIBUTORS-LIST:END -->

<a href="https://github.com/BerriAI/llm/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=BerriAI/llm" />
</a>


## Run in Developer mode
### Services
1. Setup .env file in root
2. Run dependant services `docker-compose up db prometheus`

### Backend
1. (In root) create virtual environment `python -m venv .venv`
2. Activate virtual environment `source .venv/bin/activate`
3. Install dependencies `pip install -e ".[all]"`
4. Start proxy backend `uvicorn llm.proxy.proxy_server:app --host localhost --port 4000 --reload`

### Frontend
1. Navigate to `ui/llm-dashboard`
2. Install dependencies `npm install`
3. Run `npm run dev` to start the dashboard
