import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

# Cerebras
https://inference-docs.cerebras.ai/api-reference/chat-completions

:::tip

**We support ALL Cerebras models, just set `model=cerebras/<any-model-on-cerebras>` as a prefix when sending llm requests**

:::

## API Key
```python
# env variable
os.environ['CEREBRAS_API_KEY']
```

## Sample Usage
```python
from llm import completion
import os

os.environ['CEREBRAS_API_KEY'] = ""
response = completion(
    model="cerebras/llama3-70b-instruct",
    messages=[
        {
            "role": "user",
            "content": "What's the weather like in Boston today in Fahrenheit? (Write in JSON)",
        }
    ],
    max_tokens=10,
        
    # The prompt should include JSON if 'json_object' is selected; otherwise, you will get error code 400.
    response_format={ "type": "json_object" },
    seed=123,
    stop=["\n\n"],
    temperature=0.2,
    top_p=0.9,
    tool_choice="auto",
    tools=[],
    user="user",
)
print(response)
```

## Sample Usage - Streaming
```python
from llm import completion
import os

os.environ['CEREBRAS_API_KEY'] = ""
response = completion(
    model="cerebras/llama3-70b-instruct",
    messages=[
        {
            "role": "user",
            "content": "What's the weather like in Boston today in Fahrenheit? (Write in JSON)",
        }
    ],
    stream=True,
    max_tokens=10,

    # The prompt should include JSON if 'json_object' is selected; otherwise, you will get error code 400.
    response_format={ "type": "json_object" }, 
    seed=123,
    stop=["\n\n"],
    temperature=0.2,
    top_p=0.9,
    tool_choice="auto",
    tools=[],
    user="user",
)

for chunk in response:
    print(chunk)
```


## Usage with Hanzo Proxy Server

Here's how to call a Cerebras model with the Hanzo Proxy Server

1. Modify the config.yaml 

  ```yaml
  model_list:
    - model_name: my-model
      llm_params:
        model: cerebras/<your-model-name>  # add cerebras/ prefix to route as Cerebras provider
        api_key: api-key                 # api key to send your model
  ```


2. Start the proxy 

  ```bash
  $ llm --config /path/to/config.yaml
  ```

3. Send Request to Hanzo Proxy Server

  <Tabs>

  <TabItem value="openai" label="OpenAI Python v1.0.0+">

  ```python
  import openai
  client = openai.OpenAI(
      api_key="sk-1234",             # pass llm proxy key, if you're using virtual keys
      base_url="http://0.0.0.0:4000" # llm-proxy-base url
  )

  response = client.chat.completions.create(
      model="my-model",
      messages = [
          {
              "role": "user",
              "content": "what llm are you"
          }
      ],
  )

  print(response)
  ```
  </TabItem>

  <TabItem value="curl" label="curl">

  ```shell
  curl --location 'http://0.0.0.0:4000/chat/completions' \
      --header 'Authorization: Bearer sk-1234' \
      --header 'Content-Type: application/json' \
      --data '{
      "model": "my-model",
      "messages": [
          {
          "role": "user",
          "content": "what llm are you"
          }
      ],
  }'
  ```
  </TabItem>

  </Tabs>


