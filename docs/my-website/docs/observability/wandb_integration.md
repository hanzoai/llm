import Image from '@theme/IdealImage';

# Weights & Biases - Logging LLM Input/Output


:::tip

This is community maintained, Please make an issue if you run into a bug
https://github.com/hanzoai/llm

:::


Weights & Biases helps AI developers build better models faster https://wandb.ai

<Image img={require('../../img/wandb.png')} />

:::info
We want to learn how we can make the callbacks better! Meet the LLM [founders](https://calendly.com/d/4mp-gd3-k5k/hanzoai-1-1-onboarding-llm-hosted-version) or
join our [discord](https://discord.gg/XthHQQj)
::: 

## Pre-Requisites
Ensure you have run `pip install wandb` for this integration
```shell
pip install wandb llm
```

## Quick Start
Use just 2 lines of code, to instantly log your responses **across all providers** with Weights & Biases

```python
llm.success_callback = ["wandb"]
```
```python
# pip install wandb 
import llm
import os

os.environ["WANDB_API_KEY"] = ""
# LLM API Keys
os.environ['OPENAI_API_KEY']=""

# set wandb as a callback, llm will send the data to Weights & Biases
llm.success_callback = ["wandb"] 
 
# openai call
response = llm.completion(
  model="gpt-3.5-turbo",
  messages=[
    {"role": "user", "content": "Hi 👋 - i'm openai"}
  ]
)
```

## Support & Talk to Founders

- [Schedule Demo 👋](https://calendly.com/d/4mp-gd3-k5k/hanzoai-1-1-onboarding-llm-hosted-version)
- [Community Discord 💭](https://discord.gg/XthHQQj)
- Our numbers 📞 +1 (770) 8783-106 / ‭+1 (412) 618-6238‬
- Our emails ✉️ z@hanzo.ai / dev@hanzo.ai