# DeepInfra
https://deepinfra.com/

:::tip

**We support ALL DeepInfra models, just set `model=deepinfra/<any-model-on-deepinfra>` as a prefix when sending llm requests**

:::


## API Key
```python
# env variable
os.environ['DEEPINFRA_API_KEY']
```

## Sample Usage
```python
from llm import completion
import os

os.environ['DEEPINFRA_API_KEY'] = ""
response = completion(
    model="deepinfra/meta-llama/Llama-2-70b-chat-hf", 
    messages=[{"role": "user", "content": "write code for saying hi from LLM"}]
)
```

## Sample Usage - Streaming
```python
from llm import completion
import os

os.environ['DEEPINFRA_API_KEY'] = ""
response = completion(
    model="deepinfra/meta-llama/Llama-2-70b-chat-hf", 
    messages=[{"role": "user", "content": "write code for saying hi from LLM"}],
    stream=True
)

for chunk in response:
    print(chunk)
```

## Chat Models
| Model Name       | Function Call                        |
|------------------|--------------------------------------|
| meta-llama/Meta-Llama-3-8B-Instruct  | `completion(model="deepinfra/meta-llama/Meta-Llama-3-8B-Instruct", messages)` | 
| meta-llama/Meta-Llama-3-70B-Instruct  | `completion(model="deepinfra/meta-llama/Meta-Llama-3-70B-Instruct", messages)` | 
| meta-llama/Llama-2-70b-chat-hf  | `completion(model="deepinfra/meta-llama/Llama-2-70b-chat-hf", messages)` | 
| meta-llama/Llama-2-7b-chat-hf  | `completion(model="deepinfra/meta-llama/Llama-2-7b-chat-hf", messages)` | 
| meta-llama/Llama-2-13b-chat-hf | `completion(model="deepinfra/meta-llama/Llama-2-13b-chat-hf", messages)` | 
| codellama/CodeLlama-34b-Instruct-hf | `completion(model="deepinfra/codellama/CodeLlama-34b-Instruct-hf", messages)` |
| mistralai/Mistral-7B-Instruct-v0.1 | `completion(model="deepinfra/mistralai/Mistral-7B-Instruct-v0.1", messages)` | 
| jondurbin/airoboros-l2-70b-gpt4-1.4.1 | `completion(model="deepinfra/jondurbin/airoboros-l2-70b-gpt4-1.4.1", messages)` |
