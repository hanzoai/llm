import Image from '@theme/IdealImage';
import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

# 💥 LLM Proxy Server

LLM Server manages:

* **Unified Interface**: Calling 100+ LLMs [Huggingface/Bedrock/TogetherAI/etc.](#other-supported-models) in the OpenAI `ChatCompletions` & `Completions` format
* **Load Balancing**: between [Multiple Models](#multiple-models---quick-start) + [Deployments of the same model](#multiple-instances-of-1-model) - LLM proxy can handle 1.5k+ requests/second during load tests.
* **Cost tracking**: Authentication & Spend Tracking [Virtual Keys](#managing-auth---virtual-keys)

[**See LLM Proxy code**](https://github.com/BerriAI/llm/tree/main/llm/proxy)

## Quick Start
View all the supported args for the Proxy CLI [here](https://docs.llm.ai/docs/simple_proxy#proxy-cli-arguments)

```shell
$ pip install 'llm[proxy]'
```

```shell
$ llm --model huggingface/bigcode/starcoder

#INFO: Proxy running on http://0.0.0.0:4000
```

### Test
In a new shell, run, this will make an `openai.chat.completions` request. Ensure you're using openai v1.0.0+
```shell
llm --test
```

This will now automatically route any requests for gpt-3.5-turbo to bigcode starcoder, hosted on huggingface inference endpoints.

### Using LLM Proxy - Curl Request, OpenAI Package

<Tabs>
<TabItem value="Curl" label="Curl Request">

```shell
curl --location 'http://0.0.0.0:4000/chat/completions' \
--header 'Content-Type: application/json' \
--data ' {
      "model": "gpt-3.5-turbo",
      "messages": [
        {
          "role": "user",
          "content": "what llm are you"
        }
      ],
    }
'
```
</TabItem>
<TabItem value="openai" label="OpenAI v1.0.0+">

```python
import openai
client = openai.OpenAI(
    api_key="anything",
    base_url="http://0.0.0.0:4000"
)

# request sent to model set on llm proxy, `llm --model`
response = client.chat.completions.create(model="gpt-3.5-turbo", messages = [
    {
        "role": "user",
        "content": "this is a test request, write a short poem"
    }
])

print(response)

```
</TabItem>

</Tabs>

### Server Endpoints
- POST `/chat/completions` - chat completions endpoint to call 100+ LLMs
- POST `/completions` - completions endpoint
- POST `/embeddings` - embedding endpoint for Azure, OpenAI, Huggingface endpoints
- GET `/models` - available models on server
- POST `/key/generate` - generate a key to access the proxy

### Supported LLMs
All LLM supported LLMs are supported on the Proxy. Seel all [supported llms](https://docs.llm.ai/docs/providers)
<Tabs>
<TabItem value="bedrock" label="AWS Bedrock">

```shell
$ export AWS_ACCESS_KEY_ID=
$ export AWS_REGION_NAME=
$ export AWS_SECRET_ACCESS_KEY=
```

```shell
$ llm --model bedrock/anthropic.claude-v2
```
</TabItem>
<TabItem value="azure" label="Azure OpenAI">

```shell
$ export AZURE_API_KEY=my-api-key
$ export AZURE_API_BASE=my-api-base
```
```
$ llm --model azure/my-deployment-name
```

</TabItem>
<TabItem value="openai-proxy" label="OpenAI">

```shell
$ export OPENAI_API_KEY=my-api-key
```

```shell
$ llm --model gpt-3.5-turbo
```
</TabItem>
<TabItem value="huggingface" label="Huggingface (TGI) Deployed">

```shell
$ export HUGGINGFACE_API_KEY=my-api-key #[OPTIONAL]
```
```shell
$ llm --model huggingface/<your model name> --api_base https://k58ory32yinf1ly0.us-east-1.aws.endpoints.huggingface.cloud
```

</TabItem>
<TabItem value="huggingface-local" label="Huggingface (TGI) Local">

```shell
$ llm --model huggingface/<your model name> --api_base http://0.0.0.0:8001
```

</TabItem>
<TabItem value="aws-sagemaker" label="AWS Sagemaker">

```shell
export AWS_ACCESS_KEY_ID=
export AWS_REGION_NAME=
export AWS_SECRET_ACCESS_KEY=
```

```shell
$ llm --model sagemaker/jumpstart-dft-meta-textgeneration-llama-2-7b
```

</TabItem>
<TabItem value="anthropic" label="Anthropic">

```shell
$ export ANTHROPIC_API_KEY=my-api-key
```
```shell
$ llm --model claude-instant-1
```

</TabItem>
<TabItem value="vllm-local" label="VLLM">
Assuming you're running vllm locally

```shell
$ llm --model vllm/facebook/opt-125m
```
</TabItem>
<TabItem value="together_ai" label="TogetherAI">

```shell
$ export TOGETHERAI_API_KEY=my-api-key
```
```shell
$ llm --model together_ai/lmsys/vicuna-13b-v1.5-16k
```

</TabItem>

<TabItem value="replicate" label="Replicate">

```shell
$ export REPLICATE_API_KEY=my-api-key
```
```shell
$ llm \
  --model replicate/meta/llama-2-70b-chat:02e509c789964a7ea8736978a43525956ef40397be9033abf9fd2badfe68c9e3
```

</TabItem>

<TabItem value="petals" label="Petals">

```shell
$ llm --model petals/meta-llama/Llama-2-70b-chat-hf
```

</TabItem>

<TabItem value="palm" label="Palm">

```shell
$ export PALM_API_KEY=my-palm-key
```
```shell
$ llm --model palm/chat-bison
```

</TabItem>

<TabItem value="ai21" label="AI21">

```shell
$ export AI21_API_KEY=my-api-key
```

```shell
$ llm --model j2-light
```

</TabItem>

<TabItem value="cohere" label="Cohere">

```shell
$ export COHERE_API_KEY=my-api-key
```

```shell
$ llm --model command-nightly
```

</TabItem>

</Tabs>


## Using with OpenAI compatible projects
Set `base_url` to the LLM Proxy server

<Tabs>
<TabItem value="openai" label="OpenAI v1.0.0+">

```python
import openai
client = openai.OpenAI(
    api_key="anything",
    base_url="http://0.0.0.0:4000"
)

# request sent to model set on llm proxy, `llm --model`
response = client.chat.completions.create(model="gpt-3.5-turbo", messages = [
    {
        "role": "user",
        "content": "this is a test request, write a short poem"
    }
])

print(response)

```
</TabItem>
<TabItem value="librechat" label="LibreChat">

#### Start the LLM proxy
```shell
llm --model gpt-3.5-turbo

#INFO: Proxy running on http://0.0.0.0:4000
```

#### 1. Clone the repo

```shell
git clone https://github.com/danny-avila/LibreChat.git
```


#### 2. Modify Librechat's `docker-compose.yml`
LLM Proxy is running on port `4000`, set `4000` as the proxy below
```yaml
OPENAI_REVERSE_PROXY=http://host.docker.internal:4000/v1/chat/completions
```

#### 3. Save fake OpenAI key in Librechat's `.env`

Copy Librechat's `.env.example` to `.env` and overwrite the default OPENAI_API_KEY (by default it requires the user to pass a key).
```env
OPENAI_API_KEY=sk-1234
```

#### 4. Run LibreChat:
```shell
docker compose up
```
</TabItem>

<TabItem value="continue-dev" label="ContinueDev">

Continue-Dev brings ChatGPT to VSCode. See how to [install it here](https://continue.dev/docs/quickstart).

In the [config.py](https://continue.dev/docs/reference/Models/openai) set this as your default model.
```python
  default=OpenAI(
      api_key="IGNORED",
      model="fake-model-name",
      context_length=2048, # customize if needed for your model
      api_base="http://localhost:4000" # your proxy server url
  ),
```

Credits [@vividfog](https://github.com/ollama/ollama/issues/305#issuecomment-1751848077) for this tutorial.
</TabItem>

<TabItem value="aider" label="Aider">

```shell
$ pip install aider

$ aider --openai-api-base http://0.0.0.0:4000 --openai-api-key fake-key
```
</TabItem>
<TabItem value="autogen" label="AutoGen">

```python
pip install pyautogen
```

```python
from autogen import AssistantAgent, UserProxyAgent, oai
config_list=[
    {
        "model": "my-fake-model",
        "api_base": "http://localhost:4000",  #llm compatible endpoint
        "api_type": "open_ai",
        "api_key": "NULL", # just a placeholder
    }
]

response = oai.Completion.create(config_list=config_list, prompt="Hi")
print(response) # works fine

llm_config={
    "config_list": config_list,
}

assistant = AssistantAgent("assistant", llm_config=llm_config)
user_proxy = UserProxyAgent("user_proxy")
user_proxy.initiate_chat(assistant, message="Plot a chart of META and TESLA stock price change YTD.", config_list=config_list)
```

Credits [@victordibia](https://github.com/microsoft/autogen/issues/45#issuecomment-1749921972) for this tutorial.
</TabItem>

<TabItem value="guidance" label="guidance">
A guidance language for controlling large language models.
https://github.com/guidance-ai/guidance

**NOTE:** Guidance sends additional params like `stop_sequences` which can cause some models to fail if they don't support it.

**Fix**: Start your proxy using the `--drop_params` flag

```shell
llm --model ollama/codellama --temperature 0.3 --max_tokens 2048 --drop_params
```

```python
import guidance

# set api_base to your proxy
# set api_key to anything
gpt4 = guidance.llms.OpenAI("gpt-4", api_base="http://0.0.0.0:4000", api_key="anything")

experts = guidance('''
{{#system~}}
You are a helpful and terse assistant.
{{~/system}}

{{#user~}}
I want a response to the following question:
{{query}}
Name 3 world-class experts (past or present) who would be great at answering this?
Don't answer the question yet.
{{~/user}}

{{#assistant~}}
{{gen 'expert_names' temperature=0 max_tokens=300}}
{{~/assistant}}
''', llm=gpt4)

result = experts(query='How can I be more productive?')
print(result)
```
</TabItem>
</Tabs>

## Proxy Configs
The Config allows you to set the following params

| Param Name           | Description                                                   |
|----------------------|---------------------------------------------------------------|
| `model_list`         | List of supported models on the server, with model-specific configs |
| `llm_settings`   | llm Module settings, example `llm.drop_params=True`, `llm.set_verbose=True`, `llm.api_base`, `llm.cache` |
| `general_settings`   | Server settings, example setting `master_key: sk-my_special_key` |
| `environment_variables`   | Environment Variables example, `REDIS_HOST`, `REDIS_PORT` |

#### Example Config
```yaml
model_list:
  - model_name: gpt-3.5-turbo
    llm_params:
      model: azure/gpt-turbo-small-eu
      api_base: https://my-endpoint-europe-berri-992.openai.azure.com/
      api_key:
      rpm: 6      # Rate limit for this deployment: in requests per minute (rpm)
  - model_name: gpt-3.5-turbo
    llm_params:
      model: azure/gpt-turbo-small-ca
      api_base: https://my-endpoint-canada-berri992.openai.azure.com/
      api_key:
      rpm: 6
  - model_name: gpt-3.5-turbo
    llm_params:
      model: azure/gpt-turbo-large
      api_base: https://openai-france-1234.openai.azure.com/
      api_key:
      rpm: 1440

llm_settings:
  drop_params: True
  set_verbose: True

general_settings:
  master_key: sk-1234 # [OPTIONAL] Only use this if you to require all calls to contain this key (Authorization: Bearer sk-1234)


environment_variables:
  OPENAI_API_KEY: sk-123
  REPLICATE_API_KEY: sk-cohere-is-okay
  REDIS_HOST: redis-16337.c322.us-east-1-2.ec2.cloud.redislabs.com
  REDIS_PORT: "16337"
  REDIS_PASSWORD:
```

### Config for Multiple Models - GPT-4, Claude-2

Here's how you can use multiple llms with one proxy `config.yaml`.

#### Step 1: Setup Config
```yaml
model_list:
  - model_name: zephyr-alpha # the 1st model is the default on the proxy
    llm_params: # params for llm.completion() - https://docs.llm.ai/docs/completion/input#input---request-body
      model: huggingface/HuggingFaceH4/zephyr-7b-alpha
      api_base: http://0.0.0.0:8001
  - model_name: gpt-4
    llm_params:
      model: gpt-4
      api_key: sk-1233
  - model_name: claude-2
    llm_params:
      model: claude-2
      api_key: sk-claude
```

:::info

The proxy uses the first model in the config as the default model - in this config the default model is `zephyr-alpha`
:::


#### Step 2: Start Proxy with config

```shell
$ llm --config /path/to/config.yaml
```

#### Step 3: Use proxy
Curl Command
```shell
curl --location 'http://0.0.0.0:4000/chat/completions' \
--header 'Content-Type: application/json' \
--data ' {
      "model": "zephyr-alpha",
      "messages": [
        {
          "role": "user",
          "content": "what llm are you"
        }
      ],
    }
'
```

### Load Balancing - Multiple Instances of 1 model
Use this config to load balance between multiple instances of the same model. The proxy will handle routing requests (using LLM's Router). **Set `rpm` in the config if you want maximize throughput**

#### Example config
requests with `model=gpt-3.5-turbo` will be routed across multiple instances of `azure/gpt-3.5-turbo`
```yaml
model_list:
  - model_name: gpt-3.5-turbo
    llm_params:
      model: azure/gpt-turbo-small-eu
      api_base: https://my-endpoint-europe-berri-992.openai.azure.com/
      api_key:
      rpm: 6      # Rate limit for this deployment: in requests per minute (rpm)
  - model_name: gpt-3.5-turbo
    llm_params:
      model: azure/gpt-turbo-small-ca
      api_base: https://my-endpoint-canada-berri992.openai.azure.com/
      api_key:
      rpm: 6
  - model_name: gpt-3.5-turbo
    llm_params:
      model: azure/gpt-turbo-large
      api_base: https://openai-france-1234.openai.azure.com/
      api_key:
      rpm: 1440
```

#### Step 2: Start Proxy with config

```shell
$ llm --config /path/to/config.yaml
```

#### Step 3: Use proxy
Curl Command
```shell
curl --location 'http://0.0.0.0:4000/chat/completions' \
--header 'Content-Type: application/json' \
--data ' {
      "model": "gpt-3.5-turbo",
      "messages": [
        {
          "role": "user",
          "content": "what llm are you"
        }
      ],
    }
'
```

### Fallbacks + Cooldowns + Retries + Timeouts

If a call fails after num_retries, fall back to another model group.

If the error is a context window exceeded error, fall back to a larger model group (if given).

[**See Code**](https://github.com/BerriAI/llm/blob/main/llm/router.py)

**Set via config**
```yaml
model_list:
  - model_name: zephyr-beta
    llm_params:
        model: huggingface/HuggingFaceH4/zephyr-7b-beta
        api_base: http://0.0.0.0:8001
  - model_name: zephyr-beta
    llm_params:
        model: huggingface/HuggingFaceH4/zephyr-7b-beta
        api_base: http://0.0.0.0:8002
  - model_name: zephyr-beta
    llm_params:
        model: huggingface/HuggingFaceH4/zephyr-7b-beta
        api_base: http://0.0.0.0:8003
  - model_name: gpt-3.5-turbo
    llm_params:
        model: gpt-3.5-turbo
        api_key: <my-openai-key>
  - model_name: gpt-3.5-turbo-16k
    llm_params:
        model: gpt-3.5-turbo-16k
        api_key: <my-openai-key>

llm_settings:
  num_retries: 3 # retry call 3 times on each model_name (e.g. zephyr-beta)
  request_timeout: 10 # raise Timeout error if call takes longer than 10s
  fallbacks: [{"zephyr-beta": ["gpt-3.5-turbo"]}] # fallback to gpt-3.5-turbo if call fails num_retries
  context_window_fallbacks: [{"zephyr-beta": ["gpt-3.5-turbo-16k"]}, {"gpt-3.5-turbo": ["gpt-3.5-turbo-16k"]}] # fallback to gpt-3.5-turbo-16k if context window error
  allowed_fails: 3 # cooldown model if it fails > 1 call in a minute.
```

**Set dynamically**

```bash
curl --location 'http://0.0.0.0:4000/chat/completions' \
--header 'Content-Type: application/json' \
--data ' {
      "model": "zephyr-beta",
      "messages": [
        {
          "role": "user",
          "content": "what llm are you"
        }
      ],
      "fallbacks": [{"zephyr-beta": ["gpt-3.5-turbo"]}],
      "context_window_fallbacks": [{"zephyr-beta": ["gpt-3.5-turbo"]}],
      "num_retries": 2,
      "request_timeout": 10
    }
'
```

### Config for Embedding Models - xorbitsai/inference

Here's how you can use multiple llms with one proxy `config.yaml`.
Here is how [LLM calls OpenAI Compatible Embedding models](https://docs.llm.ai/docs/embedding/supported_embedding#openai-compatible-embedding-models)

#### Config
```yaml
model_list:
  - model_name: custom_embedding_model
    llm_params:
      model: openai/custom_embedding  # the `openai/` prefix tells llm it's openai compatible
      api_base: http://0.0.0.0:4000/
  - model_name: custom_embedding_model
    llm_params:
      model: openai/custom_embedding  # the `openai/` prefix tells llm it's openai compatible
      api_base: http://0.0.0.0:8001/
```

Run the proxy using this config
```shell
$ llm --config /path/to/config.yaml
```


### Managing Auth - Virtual Keys

Grant other's temporary access to your proxy, with keys that expire after a set duration.

Requirements:

- Need to a postgres database (e.g. [Supabase](https://supabase.com/), [Neon](https://neon.tech/), etc)

You can then generate temporary keys by hitting the `/key/generate` endpoint.

[**See code**](https://github.com/BerriAI/llm/blob/7a669a36d2689c7f7890bc9c93e04ff3c2641299/llm/proxy/proxy_server.py#L672)

**Step 1: Save postgres db url**

```yaml
model_list:
  - model_name: gpt-4
    llm_params:
        model: ollama/llama2
  - model_name: gpt-3.5-turbo
    llm_params:
        model: ollama/llama2

general_settings:
  master_key: sk-1234 # [OPTIONAL] if set all calls to proxy will require either this key or a valid generated token
  database_url: "postgresql://<user>:<password>@<host>:<port>/<dbname>"
```

**Step 2: Start llm**

```shell
llm --config /path/to/config.yaml
```

**Step 3: Generate temporary keys**

```shell
curl 'http://0.0.0.0:4000/key/generate' \
--h 'Authorization: Bearer sk-1234' \
--d '{"models": ["gpt-3.5-turbo", "gpt-4", "claude-2"], "duration": "20m"}'
```

- `models`: *list or null (optional)* - Specify the models a token has access too. If null, then token has access to all models on server.

- `duration`: *str or null (optional)* Specify the length of time the token is valid for. If null, default is set to 1 hour. You can set duration as seconds ("30s"), minutes ("30m"), hours ("30h"), days ("30d").

Expected response:

```python
{
    "key": "sk-kdEXbIqZRwEeEiHwdg7sFA", # Bearer token
    "expires": "2023-11-19T01:38:25.838000+00:00" # datetime object
}
```

### Managing Auth - Upgrade/Downgrade Models

If a user is expected to use a given model (i.e. gpt3-5), and you want to:

- try to upgrade the request (i.e. GPT4)
- or downgrade it (i.e. Mistral)
- OR rotate the API KEY (i.e. open AI)
- OR access the same model through different end points (i.e. openAI vs openrouter vs Azure)

Here's how you can do that:

**Step 1: Create a model group in config.yaml (save model name, api keys, etc.)**

```yaml
model_list:
  - model_name: my-free-tier
    llm_params:
        model: huggingface/HuggingFaceH4/zephyr-7b-beta
        api_base: http://0.0.0.0:8001
  - model_name: my-free-tier
    llm_params:
        model: huggingface/HuggingFaceH4/zephyr-7b-beta
        api_base: http://0.0.0.0:8002
  - model_name: my-free-tier
    llm_params:
        model: huggingface/HuggingFaceH4/zephyr-7b-beta
        api_base: http://0.0.0.0:8003
	- model_name: my-paid-tier
    llm_params:
        model: gpt-4
        api_key: my-api-key
```

**Step 2: Generate a user key - enabling them access to specific models, custom model aliases, etc.**

```bash
curl -X POST "https://0.0.0.0:4000/key/generate" \
-H "Authorization: Bearer sk-1234" \
-H "Content-Type: application/json" \
-d '{
	"models": ["my-free-tier"],
	"aliases": {"gpt-3.5-turbo": "my-free-tier"},
	"duration": "30min"
}'
```

- **How to upgrade / downgrade request?** Change the alias mapping
- **How are routing between diff keys/api bases done?** llm handles this by shuffling between different models in the model list with the same model_name. [**See Code**](https://github.com/BerriAI/llm/blob/main/llm/router.py)

### Managing Auth - Tracking Spend

You can get spend for a key by using the `/key/info` endpoint.

```bash
curl 'http://0.0.0.0:4000/key/info?key=<user-key>' \
     -X GET \
     -H 'Authorization: Bearer <your-master-key>'
```

This is automatically updated (in USD) when calls are made to /completions, /chat/completions, /embeddings using llm's completion_cost() function. [**See Code**](https://github.com/BerriAI/llm/blob/1a6ea20a0bb66491968907c2bfaabb7fe45fc064/llm/utils.py#L1654).

**Sample response**

```python
{
    "key": "sk-tXL0wt5-lOOVK9sfY2UacA",
    "info": {
        "token": "sk-tXL0wt5-lOOVK9sfY2UacA",
        "spend": 0.0001065,
        "expires": "2023-11-24T23:19:11.131000Z",
        "models": [
            "gpt-3.5-turbo",
            "gpt-4",
            "claude-2"
        ],
        "aliases": {
            "mistral-7b": "gpt-3.5-turbo"
        },
        "config": {}
    }
}
```

### Save Model-specific params (API Base, API Keys, Temperature, Headers etc.)
You can use the config to save model-specific information like api_base, api_key, temperature, max_tokens, etc.

**Step 1**: Create a `config.yaml` file
```yaml
model_list:
  - model_name: gpt-4-team1
    llm_params: # params for llm.completion() - https://docs.llm.ai/docs/completion/input#input---request-body
      model: azure/chatgpt-v-2
      api_base: https://openai-gpt-4-test-v-1.openai.azure.com/
      api_version: "2023-05-15"
      azure_ad_token: eyJ0eXAiOiJ
  - model_name: gpt-4-team2
    llm_params:
      model: azure/gpt-4
      api_key: sk-123
      api_base: https://openai-gpt-4-test-v-2.openai.azure.com/
  - model_name: mistral-7b
    llm_params:
      model: ollama/mistral
      api_base: your_ollama_api_base
```

**Step 2**: Start server with config

```shell
$ llm --config /path/to/config.yaml
```

### Load API Keys from Vault

If you have secrets saved in Azure Vault, etc. and don't want to expose them in the config.yaml, here's how to load model-specific keys from the environment.

```python
os.environ["AZURE_NORTH_AMERICA_API_KEY"] = "your-azure-api-key"
```

```yaml
model_list:
  - model_name: gpt-4-team1
    llm_params: # params for llm.completion() - https://docs.llm.ai/docs/completion/input#input---request-body
      model: azure/chatgpt-v-2
      api_base: https://openai-gpt-4-test-v-1.openai.azure.com/
      api_version: "2023-05-15"
      api_key: os.environ/AZURE_NORTH_AMERICA_API_KEY
```

[**See Code**](https://github.com/BerriAI/llm/blob/c12d6c3fe80e1b5e704d9846b246c059defadce7/llm/utils.py#L2366)

s/o to [@David Manouchehri](https://www.linkedin.com/in/davidmanouchehri/) for helping with this.

### Config for setting Model Aliases

Set a model alias for your deployments.

In the `config.yaml` the model_name parameter is the user-facing name to use for your deployment.

In the config below requests with `model=gpt-4` will route to `ollama/llama2`

```yaml
model_list:
  - model_name: text-davinci-003
    llm_params:
        model: ollama/zephyr
  - model_name: gpt-4
    llm_params:
        model: ollama/llama2
  - model_name: gpt-3.5-turbo
    llm_params:
        model: ollama/llama2
```
### Caching Responses
Caching can be enabled by adding the `cache` key in the `config.yaml`
#### Step 1: Add `cache` to the config.yaml
```yaml
model_list:
  - model_name: gpt-3.5-turbo
    llm_params:
      model: gpt-3.5-turbo

llm_settings:
  set_verbose: True
  cache:          # init cache
    type: redis   # tell llm to use redis caching
```

#### Step 2: Add Redis Credentials to .env
LLM requires the following REDIS credentials in your env to enable caching

  ```shell
  REDIS_HOST = ""       # REDIS_HOST='redis-18841.c274.us-east-1-3.ec2.cloud.redislabs.com'
  REDIS_PORT = ""       # REDIS_PORT='18841'
  REDIS_PASSWORD = ""   # REDIS_PASSWORD='LLMIsAmazing'
  ```
#### Step 3: Run proxy with config
```shell
$ llm --config /path/to/config.yaml
```

#### Using Caching
Send the same request twice:
```shell
curl http://0.0.0.0:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
     "model": "gpt-3.5-turbo",
     "messages": [{"role": "user", "content": "write a poem about llm!"}],
     "temperature": 0.7
   }'

curl http://0.0.0.0:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
     "model": "gpt-3.5-turbo",
     "messages": [{"role": "user", "content": "write a poem about llm!"}],
     "temperature": 0.7
   }'
```

#### Control caching per completion request
Caching can be switched on/off per `/chat/completions` request
- Caching **on** for completion - pass `caching=True`:
  ```shell
  curl http://0.0.0.0:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
     "model": "gpt-3.5-turbo",
     "messages": [{"role": "user", "content": "write a poem about llm!"}],
     "temperature": 0.7,
     "caching": true
   }'
  ```
- Caching **off** for completion - pass `caching=False`:
  ```shell
  curl http://0.0.0.0:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
     "model": "gpt-3.5-turbo",
     "messages": [{"role": "user", "content": "write a poem about llm!"}],
     "temperature": 0.7,
     "caching": false
   }'
  ```

### Set Custom Prompt Templates

LLM by default checks if a model has a [prompt template and applies it](./completion/prompt_formatting.md) (e.g. if a huggingface model has a saved chat template in it's tokenizer_config.json). However, you can also set a custom prompt template on your proxy in the `config.yaml`:

**Step 1**: Save your prompt template in a `config.yaml`
```yaml
# Model-specific parameters
model_list:
  - model_name: mistral-7b # model alias
    llm_params: # actual params for llm.completion()
      model: "huggingface/mistralai/Mistral-7B-Instruct-v0.1"
      api_base: "<your-api-base>"
      api_key: "<your-api-key>" # [OPTIONAL] for hf inference endpoints
      initial_prompt_value: "\n"
      roles: {"system":{"pre_message":"<|im_start|>system\n", "post_message":"<|im_end|>"}, "assistant":{"pre_message":"<|im_start|>assistant\n","post_message":"<|im_end|>"}, "user":{"pre_message":"<|im_start|>user\n","post_message":"<|im_end|>"}}
      final_prompt_value: "\n"
      bos_token: "<s>"
      eos_token: "</s>"
      max_tokens: 4096
```

**Step 2**: Start server with config

```shell
$ llm --config /path/to/config.yaml
```

## Debugging Proxy
Run the proxy with `--debug` to easily view debug logs
```shell
llm --model gpt-3.5-turbo --debug
```

### Detailed Debug Logs

Run the proxy with `--detailed_debug` to view detailed debug logs
```shell
llm --model gpt-3.5-turbo --detailed_debug
```

When making requests you should see the POST request sent by LLM to the LLM on the Terminal output
```shell
POST Request Sent from LLM:
curl -X POST \
https://api.openai.com/v1/chat/completions \
-H 'content-type: application/json' -H 'Authorization: Bearer sk-qnWGUIW9****************************************' \
-d '{"model": "gpt-3.5-turbo", "messages": [{"role": "user", "content": "this is a test request, write a short poem"}]}'
```

## Health Check LLMs on Proxy
Use this to health check all LLMs defined in your config.yaml
#### Request
```shell
curl --location 'http://0.0.0.0:4000/health'
```

You can also run `llm -health` it makes a `get` request to `http://0.0.0.0:4000/health` for you
```
llm --health
```
#### Response
```shell
{
    "healthy_endpoints": [
        {
            "model": "azure/gpt-35-turbo",
            "api_base": "https://my-endpoint-canada-berri992.openai.azure.com/"
        },
        {
            "model": "azure/gpt-35-turbo",
            "api_base": "https://my-endpoint-europe-berri-992.openai.azure.com/"
        }
    ],
    "unhealthy_endpoints": [
        {
            "model": "azure/gpt-35-turbo",
            "api_base": "https://openai-france-1234.openai.azure.com/"
        }
    ]
}
```

## Logging Proxy Input/Output - OpenTelemetry

### Step 1 Start OpenTelemetry Collecter Docker Container
This container sends logs to your selected destination

#### Install OpenTelemetry Collecter Docker Image
```shell
docker pull otel/opentelemetry-collector:0.90.0
docker run -p 127.0.0.1:4317:4317 -p 127.0.0.1:55679:55679 otel/opentelemetry-collector:0.90.0
```

#### Set Destination paths on OpenTelemetry Collecter

Here's the OpenTelemetry yaml config to use with Elastic Search
```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317

processors:
  batch:
    timeout: 1s
    send_batch_size: 1024

exporters:
  logging:
    loglevel: debug
  otlphttp/elastic:
    endpoint: "<your elastic endpoint>"
    headers:
      Authorization: "Bearer <elastic api key>"

service:
  pipelines:
    metrics:
      receivers: [otlp]
      exporters: [logging, otlphttp/elastic]
    traces:
      receivers: [otlp]
      exporters: [logging, otlphttp/elastic]
    logs:
      receivers: [otlp]
      exporters: [logging,otlphttp/elastic]
```

#### Start the OpenTelemetry container with config
Run the following command to start your docker container. We pass `otel_config.yaml` from the previous step

```shell
docker run -p 4317:4317 \
    -v $(pwd)/otel_config.yaml:/etc/otel-collector-config.yaml \
    otel/opentelemetry-collector:latest \
    --config=/etc/otel-collector-config.yaml
```

### Step 2 Configure LLM proxy to log on OpenTelemetry

#### Pip install opentelemetry
```shell
pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp -U
```

#### Set (OpenTelemetry) `otel=True` on the proxy `config.yaml`
**Example config.yaml**

```yaml
model_list:
  - model_name: gpt-3.5-turbo
    llm_params:
      model: azure/gpt-turbo-small-eu
      api_base: https://my-endpoint-europe-berri-992.openai.azure.com/
      api_key:
      rpm: 6      # Rate limit for this deployment: in requests per minute (rpm)

general_settings:
  otel: True      # set OpenTelemetry=True, on llm Proxy

```

#### Set OTEL collector endpoint
LLM will read the `OTEL_ENDPOINT` environment variable to send data to your OTEL collector

```python
os.environ['OTEL_ENDPOINT'] # defauls to 127.0.0.1:4317 if not provided
```

#### Start LLM Proxy
```shell
llm -config config.yaml
```

#### Run a test request to Proxy
```shell
curl --location 'http://0.0.0.0:4000/chat/completions' \
    --header 'Authorization: Bearer sk-1244' \
    --data ' {
    "model": "gpt-3.5-turbo",
    "messages": [
        {
        "role": "user",
        "content": "request from LLM testing"
        }
    ]
    }'
```


#### Test & View Logs on OpenTelemetry Collecter
On successfull logging you should be able to see this log on your `OpenTelemetry Collecter` Docker Container
```shell
Events:
SpanEvent #0
     -> Name: LLM: Request Input
     -> Timestamp: 2023-12-02 05:05:53.71063 +0000 UTC
     -> DroppedAttributesCount: 0
     -> Attributes::
          -> type: Str(http)
          -> asgi: Str({'version': '3.0', 'spec_version': '2.3'})
          -> http_version: Str(1.1)
          -> server: Str(('127.0.0.1', 8000))
          -> client: Str(('127.0.0.1', 62796))
          -> scheme: Str(http)
          -> method: Str(POST)
          -> root_path: Str()
          -> path: Str(/chat/completions)
          -> raw_path: Str(b'/chat/completions')
          -> query_string: Str(b'')
          -> headers: Str([(b'host', b'0.0.0.0:8000'), (b'user-agent', b'curl/7.88.1'), (b'accept', b'*/*'), (b'authorization', b'Bearer sk-1244'), (b'content-length', b'147'), (b'content-type', b'application/x-www-form-urlencoded')])
          -> state: Str({})
          -> app: Str(<fastapi.applications.FastAPI object at 0x1253dd960>)
          -> fastapi_astack: Str(<contextlib.AsyncExitStack object at 0x127c8b7c0>)
          -> router: Str(<fastapi.routing.APIRouter object at 0x1253dda50>)
          -> endpoint: Str(<function chat_completion at 0x1254383a0>)
          -> path_params: Str({})
          -> route: Str(APIRoute(path='/chat/completions', name='chat_completion', methods=['POST']))
SpanEvent #1
     -> Name: LLM: Request Headers
     -> Timestamp: 2023-12-02 05:05:53.710652 +0000 UTC
     -> DroppedAttributesCount: 0
     -> Attributes::
          -> host: Str(0.0.0.0:8000)
          -> user-agent: Str(curl/7.88.1)
          -> accept: Str(*/*)
          -> authorization: Str(Bearer sk-1244)
          -> content-length: Str(147)
          -> content-type: Str(application/x-www-form-urlencoded)
SpanEvent #2
```

### View Log on Elastic Search
Here's the log view on Elastic Search. You can see the request `input`, `output` and `headers`

<Image img={require('../img/elastic_otel.png')} />

## Logging Proxy Input/Output - Langfuse
We will use the `--config` to set `llm.success_callback = ["langfuse"]` this will log all successfull LLM calls to langfuse

**Step 1** Install langfuse

```shell
pip install langfuse
```

**Step 2**: Create a `config.yaml` file and set `llm_settings`: `success_callback`
```yaml
model_list:
 - model_name: gpt-3.5-turbo
    llm_params:
      model: gpt-3.5-turbo
llm_settings:
  success_callback: ["langfuse"]
```

**Step 3**: Start the proxy, make a test request

Start proxy
```shell
llm --config config.yaml --debug
```

Test Request
```
llm --test
```

Expected output on Langfuse

<Image img={require('../img/langfuse_small.png')} />

## Deploying LLM Proxy

### Deploy on Render https://render.com/

<iframe width="840" height="500" src="https://www.loom.com/embed/805964b3c8384b41be180a61442389a3" frameborder="0" webkitallowfullscreen mozallowfullscreen allowfullscreen></iframe>

## LLM Proxy Performance

### Throughput - 30% Increase
LLM proxy + Load Balancer gives **30% increase** in throughput compared to Raw OpenAI API
<Image img={require('../img/throughput.png')} />

### Latency Added - 0.00325 seconds
LLM proxy adds **0.00325 seconds** latency as compared to using the Raw OpenAI API
<Image img={require('../img/latency.png')} />




## Proxy CLI Arguments

#### --host
   - **Default:** `'0.0.0.0'`
   - The host for the server to listen on.
   - **Usage:**
     ```shell
     llm --host 127.0.0.1
     ```

#### --port
   - **Default:** `4000`
   - The port to bind the server to.
   - **Usage:**
     ```shell
     llm --port 8080
     ```

#### --num_workers
   - **Default:** `1`
   - The number of uvicorn workers to spin up.
   - **Usage:**
     ```shell
     llm --num_workers 4
     ```

#### --api_base
   - **Default:** `None`
   - The API base for the model llm should call.
   - **Usage:**
     ```shell
     llm --model huggingface/tinyllama --api_base https://k58ory32yinf1ly0.us-east-1.aws.endpoints.huggingface.cloud
     ```

#### --api_version
   - **Default:** `None`
   - For Azure services, specify the API version.
   - **Usage:**
     ```shell
     llm --model azure/gpt-deployment --api_version 2023-08-01 --api_base https://<your api base>"
     ```

#### --model or -m
   - **Default:** `None`
   - The model name to pass to LLM.
   - **Usage:**
     ```shell
     llm --model gpt-3.5-turbo
     ```

#### --test
   - **Type:** `bool` (Flag)
   - Proxy chat completions URL to make a test request.
   - **Usage:**
     ```shell
     llm --test
     ```

#### --health
   - **Type:** `bool` (Flag)
   - Runs a health check on all models in config.yaml
   - **Usage:**
     ```shell
     llm --health
     ```

#### --alias
   - **Default:** `None`
   - An alias for the model, for user-friendly reference.
   - **Usage:**
     ```shell
     llm --alias my-gpt-model
     ```

#### --debug
   - **Default:** `False`
   - **Type:** `bool` (Flag)
   - Enable debugging mode for the input.
   - **Usage:**
     ```shell
     llm --debug
     ```
#### --detailed_debug
   - **Default:** `False`
   - **Type:** `bool` (Flag)
   - Enable debugging mode for the input.
   - **Usage:**
     ```shell
     llm --detailed_debug
     ```

#### --temperature
   - **Default:** `None`
   - **Type:** `float`
   - Set the temperature for the model.
   - **Usage:**
     ```shell
     llm --temperature 0.7
     ```

#### --max_tokens
   - **Default:** `None`
   - **Type:** `int`
   - Set the maximum number of tokens for the model output.
   - **Usage:**
     ```shell
     llm --max_tokens 50
     ```

#### --request_timeout
   - **Default:** `6000`
   - **Type:** `int`
   - Set the timeout in seconds for completion calls.
   - **Usage:**
     ```shell
     llm --request_timeout 300
     ```

#### --drop_params
   - **Type:** `bool` (Flag)
   - Drop any unmapped params.
   - **Usage:**
     ```shell
     llm --drop_params
     ```

#### --add_function_to_prompt
   - **Type:** `bool` (Flag)
   - If a function passed but unsupported, pass it as a part of the prompt.
   - **Usage:**
     ```shell
     llm --add_function_to_prompt
     ```

#### --config
   - Configure LLM by providing a configuration file path.
   - **Usage:**
     ```shell
     llm --config path/to/config.yaml
     ```

#### --telemetry
   - **Default:** `True`
   - **Type:** `bool`
   - Help track usage of this feature.
   - **Usage:**
     ```shell
     llm --telemetry False
     ```
