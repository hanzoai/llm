# Response Headers

When you make a request to the proxy, the proxy will return the following headers:

## Rate Limit Headers
[OpenAI-compatible headers](https://platform.openai.com/docs/guides/rate-limits/rate-limits-in-headers):

| Header | Type | Description |
|--------|------|-------------|
| `x-ratelimit-remaining-requests` | Optional[int] | The remaining number of requests that are permitted before exhausting the rate limit |
| `x-ratelimit-remaining-tokens` | Optional[int] | The remaining number of tokens that are permitted before exhausting the rate limit |
| `x-ratelimit-limit-requests` | Optional[int] | The maximum number of requests that are permitted before exhausting the rate limit |
| `x-ratelimit-limit-tokens` | Optional[int] | The maximum number of tokens that are permitted before exhausting the rate limit |
| `x-ratelimit-reset-requests` | Optional[int] | The time at which the rate limit will reset |
| `x-ratelimit-reset-tokens` | Optional[int] | The time at which the rate limit will reset |

### How Rate Limit Headers work

**If key has rate limits set**

The proxy will return the [remaining rate limits for that key](https://github.com/hanzoai/llm/blob/bfa95538190575f7f317db2d9598fc9a82275492/llm/proxy/hooks/parallel_request_limiter.py#L778).

**If key does not have rate limits set**

The proxy returns the remaining requests/tokens returned by the backend provider. (LLM will standardize the backend provider's response headers to match the OpenAI format)

If the backend provider does not return these headers, the value will be `None`.

These headers are useful for clients to understand the current rate limit status and adjust their request rate accordingly.


## Latency Headers
| Header | Type | Description |
|--------|------|-------------|
| `x-llm-response-duration-ms` | float | Total duration of the API response in milliseconds |
| `x-llm-overhead-duration-ms` | float | LLM processing overhead in milliseconds |

## Retry, Fallback Headers
| Header | Type | Description |
|--------|------|-------------|
| `x-llm-attempted-retries` | int | Number of retry attempts made |
| `x-llm-attempted-fallbacks` | int | Number of fallback attempts made |
| `x-llm-max-fallbacks` | int | Maximum number of fallback attempts allowed |

## Cost Tracking Headers
| Header | Type | Description | Available on Pass-Through Endpoints |
|--------|------|-------------|-------------|
| `x-llm-response-cost` | float | Cost of the API call | |
| `x-llm-key-spend` | float | Total spend for the API key | ✅ |

## LLM Specific Headers
| Header | Type | Description | Available on Pass-Through Endpoints |
|--------|------|-------------|-------------|
| `x-llm-call-id` | string | Unique identifier for the API call | ✅ |
| `x-llm-model-id` | string | Unique identifier for the model used | |
| `x-llm-model-api-base` | string | Base URL of the API endpoint | ✅ |
| `x-llm-version` | string | Version of LLM being used | |
| `x-llm-model-group` | string | Model group identifier | |

## Response headers from LLM providers

LLM also returns the original response headers from the LLM provider. These headers are prefixed with `llm_provider-` to distinguish them from LLM's headers.

Example response headers:
```
llm_provider-openai-processing-ms: 256
llm_provider-openai-version: 2020-10-01
llm_provider-x-ratelimit-limit-requests: 30000
llm_provider-x-ratelimit-limit-tokens: 150000000
```

