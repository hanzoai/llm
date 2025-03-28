import Image from '@theme/IdealImage';
import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

# Life of a Request

## High Level architecture

<Image img={require('../../img/llm_gateway.png')} style={{ width: '100%', maxWidth: '4000px' }} />


### Request Flow 

1. **User Sends Request**: The process begins when a user sends a request to the LLM Proxy Server (Gateway).

2. [**Virtual Keys**](../virtual_keys): At this stage the `Bearer` token in the request is checked to ensure it is valid and under it's budget. [Here is the list of checks that run for each request](https://github.com/hanzoai/llm/blob/ba41a72f92a9abf1d659a87ec880e8e319f87481/llm/proxy/auth/auth_checks.py#L43)
    - 2.1 Check if the Virtual Key exists in Redis Cache or In Memory Cache
    - 2.2 **If not in Cache**, Lookup Virtual Key in DB

3. **Rate Limiting**: The [MaxParallelRequestsHandler](https://github.com/hanzoai/llm/blob/main/llm/proxy/hooks/parallel_request_limiter.py) checks the **rate limit (rpm/tpm)** for the the following components:
    - Global Server Rate Limit
    - Virtual Key Rate Limit
    - User Rate Limit
    - Team Limit

4. **LLM `proxy_server.py`**: Contains the `/chat/completions` and `/embeddings` endpoints. Requests to these endpoints are sent through the LLM Router

5. [**LLM Router**](../routing): The LLM Router handles Load balancing, Fallbacks, Retries for LLM API deployments.

6. [**llm.completion() / llm.embedding()**:](../index#llm-python-sdk) The llm Python SDK is used to call the LLM in the OpenAI API format (Translation and parameter mapping)

7. **Post-Request Processing**: After the response is sent back to the client, the following **asynchronous** tasks are performed:
   - [Logging to Lunary, MLflow, LangFuse or other logging destinations](./logging)
   - The [MaxParallelRequestsHandler](https://github.com/hanzoai/llm/blob/main/llm/proxy/hooks/parallel_request_limiter.py) updates the rpm/tpm usage for the 
        - Global Server Rate Limit
        - Virtual Key Rate Limit
        - User Rate Limit
        - Team Limit
    - The `_ProxyDBLogger` updates spend / usage in the LLM database. [Here is everything tracked in the DB per request](https://github.com/hanzoai/llm/blob/ba41a72f92a9abf1d659a87ec880e8e319f87481/schema.prisma#L172)

## Frequently Asked Questions

1. Is a db transaction tied to the lifecycle of request?
    - No, a db transaction is not tied to the lifecycle of a request.
    - The check if a virtual key is valid relies on a DB read if it's not in cache.
    - All other DB transactions are async in background tasks