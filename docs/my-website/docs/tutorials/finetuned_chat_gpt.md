# Using Fine-Tuned gpt-3.5-turbo
Hanzo allows you to call `completion` with your fine-tuned gpt-3.5-turbo models
If you're trying to create your custom fine-tuned gpt-3.5-turbo model following along on this tutorial: https://platform.openai.com/docs/guides/fine-tuning/preparing-your-dataset

Once you've created your fine-tuned model, you can call it with `llm.completion()` 

## Usage
```python
import os
from llm import completion

# Hanzo reads from your .env
os.environ["OPENAI_API_KEY"] = "your-api-key"

response = completion(
  model="ft:gpt-3.5-turbo:my-org:custom_suffix:id",
  messages=[
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello!"}
  ]
)

print(response.choices[0].message)
```

## Usage - Setting OpenAI Organization ID
Hanzo allows you to specify your OpenAI Organization when calling OpenAI LLMs. More details here: 
[setting Organization ID](https://docs.llm.ai/docs/providers/openai#setting-organization-id-for-completion-calls)
This can be set in one of the following ways:
- Environment Variable `OPENAI_ORGANIZATION`
- Params to `llm.completion(model=model, organization="your-organization-id")`
- Set as `llm.organization="your-organization-id"`
```python
import os
from llm import completion

# Hanzo reads from your .env
os.environ["OPENAI_API_KEY"] = "your-api-key"
os.environ["OPENAI_ORGANIZATION"] = "your-org-id" # Optional

response = completion(
  model="ft:gpt-3.5-turbo:my-org:custom_suffix:id",
  messages=[
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello!"}
  ]
)

print(response.choices[0].message)
```