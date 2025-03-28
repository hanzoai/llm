# Hosted Cache - api.hanzo.ai

Use api.hanzo.ai for caching `completion()` and `embedding()` responses

## Quick Start Usage - Completion
```python
import llm
from llm import completion
from llm.caching.caching import Cache
llm.cache = Cache(type="hosted") # init cache to use api.hanzo.ai

# Make completion calls
response1 = completion(
    model="gpt-3.5-turbo", 
    messages=[{"role": "user", "content": "Tell me a joke."}]
    caching=True
)

response2 = completion(
    model="gpt-3.5-turbo", 
    messages=[{"role": "user", "content": "Tell me a joke."}],
    caching=True
)
# response1 == response2, response 1 is cached
```


## Usage - Embedding()

```python
import time
import llm
from llm import completion, embedding
from llm.caching.caching import Cache
llm.cache = Cache(type="hosted")

start_time = time.time()
embedding1 = embedding(model="text-embedding-ada-002", input=["hello from llm"*5], caching=True)
end_time = time.time()
print(f"Embedding 1 response time: {end_time - start_time} seconds")

start_time = time.time()
embedding2 = embedding(model="text-embedding-ada-002", input=["hello from llm"*5], caching=True)
end_time = time.time()
print(f"Embedding 2 response time: {end_time - start_time} seconds")
```

## Caching with Streaming 
LLM can cache your streamed responses for you

### Usage
```python
import llm
import time
from llm import completion
from llm.caching.caching import Cache

llm.cache = Cache(type="hosted")

# Make completion calls
response1 = completion(
    model="gpt-3.5-turbo", 
    messages=[{"role": "user", "content": "Tell me a joke."}], 
    stream=True,
    caching=True)
for chunk in response1:
    print(chunk)

time.sleep(1) # cache is updated asynchronously

response2 = completion(
    model="gpt-3.5-turbo", 
    messages=[{"role": "user", "content": "Tell me a joke."}], 
    stream=True,
    caching=True)
for chunk in response2:
    print(chunk)
```
