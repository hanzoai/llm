# Slack Alerting on Hanzo Gateway 

This folder contains the Slack Alerting integration for Hanzo Gateway. 

## Folder Structure 

- `slack_alerting.py`: This is the main file that handles sending different types of alerts
- `batching_handler.py`: Handles Batching + sending Httpx Post requests to slack. Slack alerts are sent every 10s or when events are greater than X events. Done to ensure llm has good performance under high traffic
- `types.py`: This file contains the AlertType enum which is used to define the different types of alerts that can be sent to Slack.
- `utils.py`: This file contains common utils used specifically for slack alerting

## Further Reading
- [Doc setting up Alerting on Hanzo Proxy (Gateway)](https://docs.llm.ai/docs/proxy/alerting)