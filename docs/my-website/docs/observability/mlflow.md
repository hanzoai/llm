import Image from '@theme/IdealImage';

# 🔁 MLflow - OSS LLM Observability and Evaluation

## What is MLflow?

**MLflow** is an end-to-end open source MLOps platform for [experiment tracking](https://www.mlflow.org/docs/latest/tracking.html), [model management](https://www.mlflow.org/docs/latest/models.html), [evaluation](https://www.mlflow.org/docs/latest/llms/llm-evaluate/index.html), [observability (tracing)](https://www.mlflow.org/docs/latest/llms/tracing/index.html), and [deployment](https://www.mlflow.org/docs/latest/deployment/index.html). MLflow empowers teams to collaboratively develop and refine LLM applications efficiently.

MLflow’s integration with LLM supports advanced observability compatible with OpenTelemetry.


<Image img={require('../../img/mlflow_tracing.png')} />


## Getting Started

Install MLflow:

```shell
pip install mlflow
```

To enable MLflow auto tracing for LLM:

```python
import mlflow

mlflow.llm.autolog()

# Alternative, you can set the callback manually in LLM
# llm.callbacks = ["mlflow"]
```

Since MLflow is open-source and free, **no sign-up or API key is needed to log traces!**

```python
import llm
import os

# Set your LLM provider's API key
os.environ["OPENAI_API_KEY"] = ""

# Call LLM as usual
response = llm.completion(
    model="gpt-4o-mini",
    messages=[
      {"role": "user", "content": "Hi 👋 - i'm openai"}
    ]
)
```

Open the MLflow UI and go to the `Traces` tab to view logged traces:

```bash
mlflow ui
```

## Tracing Tool Calls

MLflow integration with LLM support tracking tool calls in addition to the messages.

```python
import mlflow

# Enable MLflow auto-tracing for LLM
mlflow.llm.autolog()

# Define the tool function.
def get_weather(location: str) -> str:
    if location == "Tokyo":
        return "sunny"
    elif location == "Paris":
        return "rainy"
    return "unknown"

# Define function spec
get_weather_tool = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get the current weather in a given location",
        "parameters": {
            "properties": {
                "location": {
                    "description": "The city and state, e.g., San Francisco, CA",
                    "type": "string",
                },
            },
            "required": ["location"],
            "type": "object",
        },
    },
}

# Call LLM as usual
response = llm.completion(
    model="gpt-4o-mini",
    messages=[
      {"role": "user", "content": "What's the weather like in Paris today?"}
    ],
    tools=[get_weather_tool]
)
```

<Image img={require('../../img/mlflow_tool_calling_tracing.png')} />


## Evaluation

MLflow LLM integration allow you to run qualitative assessment against LLM to evaluate or/and monitor your GenAI application.

Visit [Evaluate LLMs Tutorial](../tutorials/eval_suites.md) for the complete guidance on how to run evaluation suite with LLM and MLflow.


## Exporting Traces to OpenTelemetry collectors

MLflow traces are compatible with OpenTelemetry. You can export traces to any OpenTelemetry collector (e.g., Jaeger, Zipkin, Datadog, New Relic) by setting the endpoint URL in the environment variables.

```
# Set the endpoint of the OpenTelemetry Collector
os.environ["OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"] = "http://localhost:4317/v1/traces"
# Optionally, set the service name to group traces
os.environ["OTEL_SERVICE_NAME"] = "<your-service-name>"
```

See [MLflow documentation](https://mlflow.org/docs/latest/llms/tracing/index.html#using-opentelemetry-collector-for-exporting-traces) for more details.

## Combine LLM Trace with Your Application Trace

LLM is often part of larger LLM applications, such as agentic models. MLflow Tracing allows you to instrument custom Python code, which can then be combined with LLM traces.

```python
import llm
import mlflow
from mlflow.entities import SpanType

# Enable MLflow auto-tracing for LLM
mlflow.llm.autolog()


class CustomAgent:
    # Use @mlflow.trace to instrument Python functions.
    @mlflow.trace(span_type=SpanType.AGENT)
    def run(self, query: str):
        # do something

        while i < self.max_turns:
            response = llm.completion(
                model="gpt-4o-mini",
                messages=messages,
            )

            action = self.get_action(response)
            ...

    @mlflow.trace
    def get_action(llm_response):
        ...
```

This approach generates a unified trace, combining your custom Python code with LLM calls.


## Support

* For advanced usage and integrations of tracing, visit the [MLflow Tracing documentation](https://mlflow.org/docs/latest/llms/tracing/index.html).
* For any question or issue with this integration, please [submit an issue](https://github.com/mlflow/mlflow/issues/new/choose) on our [Github](https://github.com/mlflow/mlflow) repository!