import Image from '@theme/IdealImage';

# LLM Proxy - Locust Load Test

## Locust Load Test LLM Proxy 

1. Add `fake-openai-endpoint` to your proxy config.yaml and start your llm proxy
llm provides a free hosted `fake-openai-endpoint` you can load test against

```yaml
model_list:
  - model_name: fake-openai-endpoint
    llm_params:
      model: openai/fake
      api_key: fake-key
      api_base: https://exampleopenaiendpoint-production.up.railway.app/
```

2. `pip install locust`

3. Create a file called `locustfile.py` on your local machine. Copy the contents from the llm load test located [here](https://github.com/hanzoai/llm/blob/main/.github/workflows/locustfile.py)

4. Start locust
  Run `locust` in the same directory as your `locustfile.py` from step 2

  ```shell
  locust
  ```

  Output on terminal 
  ```
  [2024-03-15 07:19:58,893] Starting web interface at http://0.0.0.0:8089
  [2024-03-15 07:19:58,898] Starting Locust 2.24.0
  ```

5. Run Load test on locust

  Head to the locust UI on http://0.0.0.0:8089

  Set Users=100, Ramp Up Users=10, Host=Base URL of your LLM Proxy

  <Image img={require('../img/locust_load_test.png')} />

6. Expected Results

  Expect to see the following response times for `/health/readiness` 
  Median → /health/readiness is `150ms`

  Avg →  /health/readiness is `219ms`

  <Image img={require('../img/llm_load_test.png')} />

