import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

# /responses [Beta]

Hanzo provides a BETA endpoint in the spec of [OpenAI's `/responses` API](https://platform.openai.com/docs/api-reference/responses)

| Feature | Supported | Notes |
|---------|-----------|--------|
| Cost Tracking | ✅ | Works with all supported models |
| Logging | ✅ | Works across all integrations |
| End-user Tracking | ✅ | |
| Streaming | ✅ | |
| Fallbacks | ✅ | Works between supported models |
| Loadbalancing | ✅ | Works between supported models |
| Supported Hanzo Versions | 1.63.8+ | |
| Supported LLM providers | `openai` | |

## Usage

## Create a model response

<Tabs>
<TabItem value="llm-sdk" label="Hanzo SDK">

#### Non-streaming
```python
import llm

# Non-streaming response
response = llm.responses(
    model="gpt-4o",
    input="Tell me a three sentence bedtime story about a unicorn.",
    max_output_tokens=100
)

print(response)
```

#### Streaming
```python
import llm

# Streaming response
response = llm.responses(
    model="gpt-4o",
    input="Tell me a three sentence bedtime story about a unicorn.",
    stream=True
)

for event in response:
    print(event)
```

</TabItem>
<TabItem value="proxy" label="OpenAI SDK with Hanzo Proxy">

First, add this to your llm proxy config.yaml:
```yaml
model_list:
  - model_name: gpt-4o
    llm_params:
      model: openai/gpt-4o
      api_key: os.environ/OPENAI_API_KEY
```

Start your Hanzo proxy:
```bash
llm --config /path/to/config.yaml

# RUNNING on http://0.0.0.0:4000
```

Then use the OpenAI SDK pointed to your proxy:

#### Non-streaming
```python
from openai import OpenAI

# Initialize client with your proxy URL
client = OpenAI(
    base_url="http://localhost:4000",  # Your proxy URL
    api_key="your-api-key"             # Your proxy API key
)

# Non-streaming response
response = client.responses.create(
    model="gpt-4o",
    input="Tell me a three sentence bedtime story about a unicorn."
)

print(response)
```

#### Streaming
```python
from openai import OpenAI

# Initialize client with your proxy URL
client = OpenAI(
    base_url="http://localhost:4000",  # Your proxy URL
    api_key="your-api-key"             # Your proxy API key
)

# Streaming response
response = client.responses.create(
    model="gpt-4o",
    input="Tell me a three sentence bedtime story about a unicorn.",
    stream=True
)

for event in response:
    print(event)
```

</TabItem>
</Tabs>
