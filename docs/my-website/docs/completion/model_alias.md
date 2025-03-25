# Model Alias

The model name you show an end-user might be different from the one you pass to LLM - e.g. Displaying `GPT-3.5` while calling `gpt-3.5-turbo-16k` on the backend. 

LLM simplifies this by letting you pass in a model alias mapping. 

# expected format

```python
llm.model_alias_map = {
    # a dictionary containing a mapping of the alias string to the actual llm model name string
    "model_alias": "llm_model_name"
}
```

# usage 

### Relevant Code
```python
model_alias_map = {
    "GPT-3.5": "gpt-3.5-turbo-16k",
    "llama2": "replicate/llama-2-70b-chat:2796ee9483c3fd7aa2e171d38f4ca12251a30609463dcfd4cd76703f22e96cdf"
}

llm.model_alias_map = model_alias_map
```

### Complete Code
```python
import llm 
from llm import completion 


## set ENV variables
os.environ["OPENAI_API_KEY"] = "openai key"
os.environ["REPLICATE_API_KEY"] = "cohere key"

## set model alias map
model_alias_map = {
    "GPT-3.5": "gpt-3.5-turbo-16k",
    "llama2": "replicate/llama-2-70b-chat:2796ee9483c3fd7aa2e171d38f4ca12251a30609463dcfd4cd76703f22e96cdf"
}

llm.model_alias_map = model_alias_map

messages = [{ "content": "Hello, how are you?","role": "user"}]

# call "gpt-3.5-turbo-16k"
response = completion(model="GPT-3.5", messages=messages)

# call replicate/llama-2-70b-chat:2796ee9483c3fd7aa2e171d38f4ca1...
response = completion("llama2", messages)
```
