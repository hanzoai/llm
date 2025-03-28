import Image from '@theme/IdealImage';

# Logfire

Logfire is open Source Observability & Analytics for LLM Apps
Detailed production traces and a granular view on quality, cost and latency

<Image img={require('../../img/logfire.png')} />

:::info
We want to learn how we can make the callbacks better! Meet the LLM [founders](https://calendly.com/d/4mp-gd3-k5k/hanzoai-1-1-onboarding-llm-hosted-version) or
join our [discord](https://discord.gg/XthHQQj)
:::

## Pre-Requisites

Ensure you have installed the following packages to use this integration

```shell
pip install llm

pip install opentelemetry-api==1.25.0
pip install opentelemetry-sdk==1.25.0
pip install opentelemetry-exporter-otlp==1.25.0
```

## Quick Start

Get your Logfire token from [Logfire](https://logfire.pydantic.dev/)

```python
llm.callbacks = ["logfire"]
```

```python
# pip install logfire
import llm
import os

# from https://logfire.pydantic.dev/
os.environ["LOGFIRE_TOKEN"] = ""

# LLM API Keys
os.environ['OPENAI_API_KEY']=""

# set logfire as a callback, llm will send the data to logfire
llm.success_callback = ["logfire"]

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
