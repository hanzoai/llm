# CLI Arguments
Cli arguments,  --host, --port, --num_workers

## --host
   - **Default:** `'0.0.0.0'`
   - The host for the server to listen on.
   - **Usage:** 
     ```shell
     llm --host 127.0.0.1
     ```
   - **Usage - set Environment Variable:** `HOST`
    ```shell
    export HOST=127.0.0.1
    llm
    ```

## --port
   - **Default:** `4000`
   - The port to bind the server to.
   - **Usage:** 
     ```shell
     llm --port 8080
     ```
  - **Usage - set Environment Variable:** `PORT`
    ```shell
    export PORT=8080
    llm
    ```

## --num_workers
   - **Default:** `1`
   - The number of uvicorn workers to spin up.
   - **Usage:** 
     ```shell
     llm --num_workers 4
     ```
  - **Usage - set Environment Variable:** `NUM_WORKERS`
    ```shell
    export NUM_WORKERS=4
    llm
    ```

## --api_base
   - **Default:** `None`
   - The API base for the model llm should call.
   - **Usage:** 
     ```shell
     llm --model huggingface/tinyllama --api_base https://k58ory32yinf1ly0.us-east-1.aws.endpoints.huggingface.cloud
     ```

## --api_version
   - **Default:** `None`
   - For Azure services, specify the API version.
   - **Usage:** 
     ```shell
     llm --model azure/gpt-deployment --api_version 2023-08-01 --api_base https://<your api base>"
     ```

## --model or -m
   - **Default:** `None`
   - The model name to pass to LLM.
   - **Usage:** 
     ```shell
     llm --model gpt-3.5-turbo
     ```

## --test
   - **Type:** `bool` (Flag)
   - Proxy chat completions URL to make a test request.
   - **Usage:** 
     ```shell
     llm --test
     ```

## --health
   - **Type:** `bool` (Flag)
   - Runs a health check on all models in config.yaml
   - **Usage:** 
     ```shell
     llm --health
     ```

## --alias
   - **Default:** `None`
   - An alias for the model, for user-friendly reference.
   - **Usage:** 
     ```shell
     llm --alias my-gpt-model
     ```

## --debug
   - **Default:** `False`
   - **Type:** `bool` (Flag)
   - Enable debugging mode for the input.
   - **Usage:** 
     ```shell
     llm --debug
     ```
  - **Usage - set Environment Variable:** `DEBUG`
    ```shell
    export DEBUG=True
    llm
    ```

## --detailed_debug
   - **Default:** `False`
   - **Type:** `bool` (Flag)
   - Enable debugging mode for the input.
   - **Usage:** 
     ```shell
     llm --detailed_debug
     ```
  - **Usage - set Environment Variable:** `DETAILED_DEBUG`
    ```shell
    export DETAILED_DEBUG=True
    llm
    ```

#### --temperature
   - **Default:** `None`
   - **Type:** `float`
   - Set the temperature for the model.
   - **Usage:** 
     ```shell
     llm --temperature 0.7
     ```

## --max_tokens
   - **Default:** `None`
   - **Type:** `int`
   - Set the maximum number of tokens for the model output.
   - **Usage:** 
     ```shell
     llm --max_tokens 50
     ```

## --request_timeout
   - **Default:** `6000`
   - **Type:** `int`
   - Set the timeout in seconds for completion calls.
   - **Usage:** 
     ```shell
     llm --request_timeout 300
     ```

## --drop_params
   - **Type:** `bool` (Flag)
   - Drop any unmapped params.
   - **Usage:** 
     ```shell
     llm --drop_params
     ```

## --add_function_to_prompt
   - **Type:** `bool` (Flag)
   - If a function passed but unsupported, pass it as a part of the prompt.
   - **Usage:** 
     ```shell
     llm --add_function_to_prompt
     ```

## --config
   - Configure LLM by providing a configuration file path.
   - **Usage:** 
     ```shell
     llm --config path/to/config.yaml
     ```

## --telemetry
   - **Default:** `True`
   - **Type:** `bool`
   - Help track usage of this feature.
   - **Usage:** 
     ```shell
     llm --telemetry False
     ```


## --log_config
   - **Default:** `None`
   - **Type:** `str`
   - Specify a log configuration file for uvicorn.
   - **Usage:** 
     ```shell
     llm --log_config path/to/log_config.conf
     ```
