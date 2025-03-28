# Debugging

2 levels of debugging supported. 

- debug (prints info logs)
- detailed debug (prints debug logs)

The proxy also supports json logs. [See here](#json-logs)

## `debug`

**via cli**

```bash
$ llm --debug
```

**via env**

```python
os.environ["LLM_LOG"] = "INFO"
```

## `detailed debug`

**via cli**

```bash
$ llm --detailed_debug
```

**via env**

```python
os.environ["LLM_LOG"] = "DEBUG"
```

### Debug Logs 

Run the proxy with `--detailed_debug` to view detailed debug logs
```shell
llm --config /path/to/config.yaml --detailed_debug
```

When making requests you should see the POST request sent by LLM to the LLM on the Terminal output
```shell
POST Request Sent from LLM:
curl -X POST \
https://api.openai.com/v1/chat/completions \
-H 'content-type: application/json' -H 'Authorization: Bearer sk-qnWGUIW9****************************************' \
-d '{"model": "gpt-3.5-turbo", "messages": [{"role": "user", "content": "this is a test request, write a short poem"}]}'
```

## JSON LOGS

Set `JSON_LOGS="True"` in your env:

```bash
export JSON_LOGS="True"
```
**OR**

Set `json_logs: true` in your yaml: 

```yaml
llm_settings:
    json_logs: true
```

Start proxy 

```bash
$ llm
```

The proxy will now all logs in json format.

## Control Log Output 

Turn off fastapi's default 'INFO' logs 

1. Turn on 'json logs' 
```yaml
llm_settings:
    json_logs: true
```

2. Set `LLM_LOG` to 'ERROR' 

Only get logs if an error occurs. 

```bash
LLM_LOG="ERROR"
```

3. Start proxy 


```bash
$ llm
```

Expected Output: 

```bash
# no info statements
```

## Common Errors 

1. "No available deployments..."

```
No deployments available for selected model, Try again in 60 seconds. Passed model=claude-3-5-sonnet. pre-call-checks=False, allowed_model_region=n/a.
```

This can be caused due to all your models hitting rate limit errors, causing the cooldown to kick in. 

How to control this? 
- Adjust the cooldown time

```yaml
router_settings:
    cooldown_time: 0 # 👈 KEY CHANGE
```

- Disable Cooldowns [NOT RECOMMENDED]

```yaml
router_settings:
    disable_cooldowns: True
```

This is not recommended, as it will lead to requests being routed to deployments over their tpm/rpm limit.