import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

# Hanzo Proxy (LLM Gateway)


| Property | Details |
|-------|-------|
| Description | Hanzo Proxy is an OpenAI-compatible gateway that allows you to interact with multiple LLM providers through a unified API. Simply use the `llm_proxy/` prefix before the model name to route your requests through the proxy. |
| Provider Route on Hanzo | `llm_proxy/` (add this prefix to the model name, to route any requests to llm_proxy - e.g. `llm_proxy/your-model-name`) |
| Setup Hanzo Gateway | [Hanzo Gateway ↗](../simple_proxy) |
| Supported Endpoints |`/chat/completions`, `/completions`, `/embeddings`, `/audio/speech`, `/audio/transcriptions`, `/images`, `/rerank` |



## Required Variables

```python
os.environ["LLM_PROXY_API_KEY"] = "" # "sk-1234" your llm proxy api key 
os.environ["LLM_PROXY_API_BASE"] = "" # "http://localhost:4000" your llm proxy api base
```


## Usage (Non Streaming)
```python
import os 
import llm
from llm import completion

os.environ["LLM_PROXY_API_KEY"] = ""

# set custom api base to your proxy
# either set .env or llm.api_base
# os.environ["LLM_PROXY_API_BASE"] = ""
llm.api_base = "your-openai-proxy-url"


messages = [{ "content": "Hello, how are you?","role": "user"}]

# llm proxy call
response = completion(model="llm_proxy/your-model-name", messages)
```

## Usage - passing `api_base`, `api_key` per request

If you need to set api_base dynamically, just pass it in completions instead - completions(...,api_base="your-proxy-api-base")

```python
import os 
import llm
from llm import completion

os.environ["LLM_PROXY_API_KEY"] = ""

messages = [{ "content": "Hello, how are you?","role": "user"}]

# llm proxy call
response = completion(
    model="llm_proxy/your-model-name", 
    messages, 
    api_base = "your-llm-proxy-url",
    api_key = "your-llm-proxy-api-key"
)
```
## Usage - Streaming

```python
import os 
import llm
from llm import completion

os.environ["LLM_PROXY_API_KEY"] = ""

messages = [{ "content": "Hello, how are you?","role": "user"}]

# openai call
response = completion(
    model="llm_proxy/your-model-name", 
    messages, 
    api_base = "your-llm-proxy-url", 
    stream=True
)

for chunk in response:
    print(chunk)
```

## Embeddings

```python
import llm

response = llm.embedding(
    model="llm_proxy/your-embedding-model",
    input="Hello world",
    api_base="your-llm-proxy-url",
    api_key="your-llm-proxy-api-key"
)
```

## Image Generation

```python
import llm

response = llm.image_generation(
    model="llm_proxy/dall-e-3",
    prompt="A beautiful sunset over mountains",
    api_base="your-llm-proxy-url",
    api_key="your-llm-proxy-api-key"
)
```

## Audio Transcription

```python
import llm

response = llm.transcription(
    model="llm_proxy/whisper-1",
    file="your-audio-file",
    api_base="your-llm-proxy-url",
    api_key="your-llm-proxy-api-key"
)
```

## Text to Speech

```python
import llm

response = llm.speech(
    model="llm_proxy/tts-1",
    input="Hello world",
    api_base="your-llm-proxy-url",
    api_key="your-llm-proxy-api-key"
)
``` 

## Rerank

```python
import llm

import llm

response = llm.rerank(
    model="llm_proxy/rerank-english-v2.0",
    query="What is machine learning?",
    documents=[
        "Machine learning is a field of study in artificial intelligence",
        "Biology is the study of living organisms"
    ],
    api_base="your-llm-proxy-url",
    api_key="your-llm-proxy-api-key"
)
```
## **Usage with Langchain, LLamaindex, OpenAI Js, Anthropic SDK, Instructor**

#### [Follow this doc to see how to use llm proxy with langchain, llamaindex, anthropic etc](../proxy/user_keys)