import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';
import Image from '@theme/IdealImage';

# 📈 Prometheus metrics

:::info

✨ Prometheus metrics is on LLM Enterprise

[Enterprise Pricing](https://www.llm.ai/#pricing)

[Get free 7-day trial key](https://www.llm.ai/#trial)

:::

LLM Exposes a `/metrics` endpoint for Prometheus to Poll

## Quick Start

If you're using the LLM CLI with `llm --config proxy_config.yaml` then you need to `pip install prometheus_client==0.20.0`. **This is already pre-installed on the llm Docker image**

Add this to your proxy config.yaml 
```yaml
model_list:
 - model_name: gpt-3.5-turbo
    llm_params:
      model: gpt-3.5-turbo
llm_settings:
  callbacks: ["prometheus"]
```

Start the proxy
```shell
llm --config config.yaml --debug
```

Test Request
```shell
curl --location 'http://0.0.0.0:4000/chat/completions' \
    --header 'Content-Type: application/json' \
    --data '{
    "model": "gpt-3.5-turbo",
    "messages": [
        {
        "role": "user",
        "content": "what llm are you"
        }
    ]
}'
```

View Metrics on `/metrics`, Visit `http://localhost:4000/metrics` 
```shell
http://localhost:4000/metrics

# <proxy_base_url>/metrics
```

## Virtual Keys, Teams, Internal Users

Use this for for tracking per [user, key, team, etc.](virtual_keys)

| Metric Name          | Description                          |
|----------------------|--------------------------------------|
| `llm_spend_metric`                | Total Spend, per `"user", "key", "model", "team", "end-user"`                 |
| `llm_total_tokens`         | input + output tokens per `"end_user", "hashed_api_key", "api_key_alias", "requested_model", "team", "team_alias", "user", "model"`     |
| `llm_input_tokens`         | input tokens per `"end_user", "hashed_api_key", "api_key_alias", "requested_model", "team", "team_alias", "user", "model"`     |
| `llm_output_tokens`        | output tokens per `"end_user", "hashed_api_key", "api_key_alias", "requested_model", "team", "team_alias", "user", "model"`             |

### Team - Budget


| Metric Name          | Description                          |
|----------------------|--------------------------------------|
| `llm_team_max_budget_metric`                    | Max Budget for Team Labels: `"team_id", "team_alias"`|
| `llm_remaining_team_budget_metric`             | Remaining Budget for Team (A team created on LLM) Labels: `"team_id", "team_alias"`|
| `llm_team_budget_remaining_hours_metric`        | Hours before the team budget is reset Labels: `"team_id", "team_alias"`|

### Virtual Key - Budget

| Metric Name          | Description                          |
|----------------------|--------------------------------------|
| `llm_api_key_max_budget_metric`                 | Max Budget for API Key Labels: `"hashed_api_key", "api_key_alias"`|
| `llm_remaining_api_key_budget_metric`                | Remaining Budget for API Key (A key Created on LLM) Labels: `"hashed_api_key", "api_key_alias"`|
| `llm_api_key_budget_remaining_hours_metric`          | Hours before the API Key budget is reset Labels: `"hashed_api_key", "api_key_alias"`|

### Virtual Key - Rate Limit

| Metric Name          | Description                          |
|----------------------|--------------------------------------|
| `llm_remaining_api_key_requests_for_model`                | Remaining Requests for a LLM virtual API key, only if a model-specific rate limit (rpm) has been set for that virtual key. Labels: `"hashed_api_key", "api_key_alias", "model"`|
| `llm_remaining_api_key_tokens_for_model`                | Remaining Tokens for a LLM virtual API key, only if a model-specific token limit (tpm) has been set for that virtual key. Labels: `"hashed_api_key", "api_key_alias", "model"`|


### Initialize Budget Metrics on Startup

If you want to initialize the key/team budget metrics on startup, you can set the `prometheus_initialize_budget_metrics` to `true` in the `config.yaml`

```yaml
llm_settings:
  callbacks: ["prometheus"]
  prometheus_initialize_budget_metrics: true
```


## Proxy Level Tracking Metrics

Use this to track overall LLM Proxy usage.
- Track Actual traffic rate to proxy 
- Number of **client side** requests and failures for requests made to proxy 

| Metric Name          | Description                          |
|----------------------|--------------------------------------|
| `llm_proxy_failed_requests_metric`             | Total number of failed responses from proxy - the client did not get a success response from llm proxy. Labels: `"end_user", "hashed_api_key", "api_key_alias", "requested_model", "team", "team_alias", "user", "exception_status", "exception_class"`          |
| `llm_proxy_total_requests_metric`             | Total number of requests made to the proxy server - track number of client side requests. Labels: `"end_user", "hashed_api_key", "api_key_alias", "requested_model", "team", "team_alias", "user", "status_code"`          |

## LLM Provider Metrics

Use this for LLM API Error monitoring and tracking remaining rate limits and token limits

### Labels Tracked

| Label | Description |
|-------|-------------|
| llm_model_name | The name of the LLM model used by LLM |
| requested_model | The model sent in the request |
| model_id | The model_id of the deployment. Autogenerated by LLM, each deployment has a unique model_id |
| api_base | The API Base of the deployment |
| api_provider | The LLM API provider, used for the provider. Example (azure, openai, vertex_ai) |
| hashed_api_key | The hashed api key of the request |
| api_key_alias | The alias of the api key used |
| team | The team of the request |
| team_alias | The alias of the team used |
| exception_status | The status of the exception, if any |
| exception_class | The class of the exception, if any |

### Success and Failure

| Metric Name          | Description                          |
|----------------------|--------------------------------------|
 `llm_deployment_success_responses`              | Total number of successful LLM API calls for deployment. Labels: `"requested_model", "llm_model_name", "model_id", "api_base", "api_provider", "hashed_api_key", "api_key_alias", "team", "team_alias"` |
| `llm_deployment_failure_responses`              | Total number of failed LLM API calls for a specific LLM deployment. Labels: `"requested_model", "llm_model_name", "model_id", "api_base", "api_provider", "hashed_api_key", "api_key_alias", "team", "team_alias", "exception_status", "exception_class"` |
| `llm_deployment_total_requests`                 | Total number of LLM API calls for deployment - success + failure. Labels: `"requested_model", "llm_model_name", "model_id", "api_base", "api_provider", "hashed_api_key", "api_key_alias", "team", "team_alias"` |

### Remaining Requests and Tokens

| Metric Name          | Description                          |
|----------------------|--------------------------------------|
| `llm_remaining_requests_metric`             | Track `x-ratelimit-remaining-requests` returned from LLM API Deployment. Labels: `"model_group", "api_provider", "api_base", "llm_model_name", "hashed_api_key", "api_key_alias"` |
| `llm_remaining_tokens`                | Track `x-ratelimit-remaining-tokens` return from LLM API Deployment. Labels: `"model_group", "api_provider", "api_base", "llm_model_name", "hashed_api_key", "api_key_alias"` |

### Deployment State 
| Metric Name          | Description                          |
|----------------------|--------------------------------------|
| `llm_deployment_state`             | The state of the deployment: 0 = healthy, 1 = partial outage, 2 = complete outage. Labels: `"llm_model_name", "model_id", "api_base", "api_provider"` |
| `llm_deployment_latency_per_output_token`       | Latency per output token for deployment. Labels: `"llm_model_name", "model_id", "api_base", "api_provider", "hashed_api_key", "api_key_alias", "team", "team_alias"` |

#### Fallback (Failover) Metrics

| Metric Name          | Description                          |
|----------------------|--------------------------------------|
| `llm_deployment_cooled_down`             | Number of times a deployment has been cooled down by LLM load balancing logic. Labels: `"llm_model_name", "model_id", "api_base", "api_provider", "exception_status"` |
| `llm_deployment_successful_fallbacks`           | Number of successful fallback requests from primary model -> fallback model. Labels: `"requested_model", "fallback_model", "hashed_api_key", "api_key_alias", "team", "team_alias", "exception_status", "exception_class"` |
| `llm_deployment_failed_fallbacks`               | Number of failed fallback requests from primary model -> fallback model. Labels: `"requested_model", "fallback_model", "hashed_api_key", "api_key_alias", "team", "team_alias", "exception_status", "exception_class"` |

## Request Latency Metrics 

| Metric Name          | Description                          |
|----------------------|--------------------------------------|
| `llm_request_total_latency_metric`             | Total latency (seconds) for a request to LLM Proxy Server - tracked for labels "end_user", "hashed_api_key", "api_key_alias", "requested_model", "team", "team_alias", "user", "model" |
| `llm_overhead_latency_metric`             | Latency overhead (seconds) added by LLM processing - tracked for labels "end_user", "hashed_api_key", "api_key_alias", "requested_model", "team", "team_alias", "user", "model" |
| `llm_llm_api_latency_metric`  | Latency (seconds) for just the LLM API call - tracked for labels "model", "hashed_api_key", "api_key_alias", "team", "team_alias", "requested_model", "end_user", "user" |
| `llm_llm_api_time_to_first_token_metric`             | Time to first token for LLM API call - tracked for labels `model`, `hashed_api_key`, `api_key_alias`, `team`, `team_alias` [Note: only emitted for streaming requests] |

## [BETA] Custom Metrics

Track custom metrics on prometheus on all events mentioned above. 

1. Define the custom metrics in the `config.yaml`

```yaml
model_list:
  - model_name: openai/gpt-3.5-turbo
    llm_params:
      model: openai/gpt-3.5-turbo
      api_key: os.environ/OPENAI_API_KEY

llm_settings:
  callbacks: ["prometheus"]
  custom_prometheus_metadata_labels: ["metadata.foo", "metadata.bar"]
```

2. Make a request with the custom metadata labels

```bash
curl -L -X POST 'http://0.0.0.0:4000/v1/chat/completions' \
-H 'Content-Type: application/json' \
-H 'Authorization: Bearer <LITELLM_API_KEY>' \
-d '{
    "model": "openai/gpt-3.5-turbo",
    "messages": [
      {
        "role": "user",
        "content": [
          {
            "type": "text",
            "text": "What's in this image?"
          }
        ]
      }
    ],
    "max_tokens": 300,
    "metadata": {
        "foo": "hello world"
    }
}'
```

3. Check your `/metrics` endpoint for the custom metrics  

```
... "metadata_foo": "hello world" ...
```

## Monitor System Health

To monitor the health of llm adjacent services (redis / postgres), do:

```yaml
model_list:
 - model_name: gpt-3.5-turbo
    llm_params:
      model: gpt-3.5-turbo
llm_settings:
  service_callback: ["prometheus_system"]
```

| Metric Name          | Description                          |
|----------------------|--------------------------------------|
| `llm_redis_latency`         | histogram latency for redis calls     |
| `llm_redis_fails`         | Number of failed redis calls    |
| `llm_self_latency`         | Histogram latency for successful llm api call    |


## **🔥 LLM Maintained Grafana Dashboards **

Link to Grafana Dashboards maintained by LLM

https://github.com/BerriAI/llm/tree/main/cookbook/llm_proxy_server/grafana_dashboard

Here is a screenshot of the metrics you can monitor with the LLM Grafana Dashboard


<Image img={require('../../img/grafana_1.png')} />

<Image img={require('../../img/grafana_2.png')} />

<Image img={require('../../img/grafana_3.png')} />


## Deprecated Metrics 

| Metric Name          | Description                          |
|----------------------|--------------------------------------|
| `llm_llm_api_failed_requests_metric`             | **deprecated** use `llm_proxy_failed_requests_metric` |
| `llm_requests_metric`             | **deprecated** use `llm_proxy_total_requests_metric` |



## FAQ 

### What are `_created` vs. `_total` metrics?

- `_created` metrics are metrics that are created when the proxy starts
- `_total` metrics are metrics that are incremented for each request

You should consume the `_total` metrics for your counting purposes