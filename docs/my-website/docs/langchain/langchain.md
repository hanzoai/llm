import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

# Using ChatLLM() - Langchain

## Pre-Requisites
```shell
!pip install llm langchain
```
## Quick Start

<Tabs>
<TabItem value="openai" label="OpenAI">

```python
import os
from langchain_community.chat_models import ChatLLM
from langchain_core.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    AIMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

os.environ['OPENAI_API_KEY'] = ""
chat = ChatLLM(model="gpt-3.5-turbo")
messages = [
    HumanMessage(
        content="what model are you"
    )
]
chat.invoke(messages)
```

</TabItem>

<TabItem value="anthropic" label="Anthropic">

```python
import os
from langchain_community.chat_models import ChatLLM
from langchain_core.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    AIMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

os.environ['ANTHROPIC_API_KEY'] = ""
chat = ChatLLM(model="claude-2", temperature=0.3)
messages = [
    HumanMessage(
        content="what model are you"
    )
]
chat.invoke(messages)
```

</TabItem>

<TabItem value="replicate" label="Replicate">

```python
import os
from langchain_community.chat_models import ChatLLM
from langchain_core.prompts.chat import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    AIMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

os.environ['REPLICATE_API_TOKEN'] = ""
chat = ChatLLM(model="replicate/llama-2-70b-chat:2c1608e18606fad2812020dc541930f2d0495ce32eee50074220b87300bc16e1")
messages = [
    HumanMessage(
        content="what model are you?"
    )
]
chat.invoke(messages)
```

</TabItem>

<TabItem value="cohere" label="Cohere">

```python
import os
from langchain_community.chat_models import ChatLLM
from langchain_core.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    AIMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

os.environ['COHERE_API_KEY'] = ""
chat = ChatLLM(model="command-nightly")
messages = [
    HumanMessage(
        content="what model are you?"
    )
]
chat.invoke(messages)
```

</TabItem>
</Tabs>

## Use Langchain ChatLLM with MLflow

MLflow provides open-source observability solution for ChatLLM.

To enable the integration, simply call `mlflow.llm.autolog()` before in your code. No other setup is necessary.

```python
import mlflow

mlflow.llm.autolog()
```

Once the auto-tracing is enabled, you can invoke `ChatLLM` and see recorded traces in MLflow.

```python
import os
from langchain.chat_models import ChatLLM

os.environ['OPENAI_API_KEY']="sk-..."

chat = ChatLLM(model="gpt-4o-mini")
chat.invoke("Hi!")
```

## Use Langchain ChatLLM with Lunary
```python
import os
from langchain.chat_models import ChatLLM
from langchain.schema import HumanMessage
import llm

os.environ["LUNARY_PUBLIC_KEY"] = "" # from https://app.lunary.ai/settings
os.environ['OPENAI_API_KEY']="sk-..."

llm.success_callback = ["lunary"] 
llm.failure_callback = ["lunary"] 

chat = ChatLLM(
  model="gpt-4o"
  messages = [
    HumanMessage(
        content="what model are you"
    )
]
chat(messages)
```

Get more details [here](../observability/lunary_integration.md)

## Use LangChain ChatLLM + Langfuse
Checkout this section [here](../observability/langfuse_integration#use-langchain-chatllm--langfuse) for more details on how to integrate Langfuse with ChatLLM.
