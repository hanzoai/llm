import Image from '@theme/IdealImage';

# Slack - Logging LLM Input/Output, Exceptions

<Image img={require('../../img/slack.png')} />

:::info
We want to learn how we can make the callbacks better! Meet the LLM [founders](https://calendly.com/d/4mp-gd3-k5k/hanzoai-1-1-onboarding-llm-hosted-version) or
join our [discord](https://discord.gg/XthHQQj)
::: 

## Pre-Requisites

### Step 1
```shell
pip install llm
```

### Step 2
Get a slack webhook url from https://api.slack.com/messaging/webhooks



## Quick Start
### Create a custom Callback to log to slack
We create a custom callback, to log to slack webhooks, see [custom callbacks on llm](https://docs.llm.ai/docs/observability/custom_callback)
```python
def send_slack_alert(
        kwargs,
        completion_response,
        start_time,
        end_time,
):
    print(
        "in custom slack callback func"
    )
    import requests
    import json

    # Define the Slack webhook URL
    # get it from https://api.slack.com/messaging/webhooks
    slack_webhook_url = os.environ['SLACK_WEBHOOK_URL']   # "https://hooks.slack.com/services/<>/<>/<>"

    # Remove api_key from kwargs under llm_params
    if kwargs.get('llm_params'):
        kwargs['llm_params'].pop('api_key', None)
        if kwargs['llm_params'].get('metadata'):
            kwargs['llm_params']['metadata'].pop('deployment', None)
    # Remove deployment under metadata
    if kwargs.get('metadata'):
        kwargs['metadata'].pop('deployment', None)
    # Prevent api_key from being logged
    if kwargs.get('api_key'):
        kwargs.pop('api_key', None)

    # Define the text payload, send data available in llm custom_callbacks
    text_payload = f"""LLM Logging: kwargs: {str(kwargs)}\n\n, response: {str(completion_response)}\n\n, start time{str(start_time)} end time: {str(end_time)}
    """
    payload = {
        "text": text_payload
    }

    # Set the headers
    headers = {
        "Content-type": "application/json"
    }

    # Make the POST request
    response = requests.post(slack_webhook_url, json=payload, headers=headers)

    # Check the response status
    if response.status_code == 200:
        print("Message sent successfully to Slack!")
    else:
        print(f"Failed to send message to Slack. Status code: {response.status_code}")
        print(response.json())
```

### Pass callback to LLM
```python
llm.success_callback = [send_slack_alert]
```

```python
import llm
llm.success_callback = [send_slack_alert] # log success
llm.failure_callback = [send_slack_alert] # log exceptions

# this will raise an exception
response = llm.completion(
    model="gpt-2",
    messages=[
        {
            "role": "user",
            "content": "Hi 👋 - i'm openai"
        }
    ]
)
```
## Support & Talk to Founders

- [Schedule Demo 👋](https://calendly.com/d/4mp-gd3-k5k/hanzoai-1-1-onboarding-llm-hosted-version)
- [Community Discord 💭](https://discord.gg/XthHQQj)
- Our numbers 📞 +1 (770) 8783-106 / ‭+1 (412) 618-6238‬
- Our emails ✉️ z@hanzo.ai / dev@hanzo.ai
