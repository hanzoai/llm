# Using at Scale (1M+ rows in DB)

This document is a guide for using LLM Proxy once you have crossed 1M+ rows in the LLM Spend Logs Database.

<iframe width="840" height="500" src="https://www.loom.com/embed/eafd90d5374d4633b99c441fb04df351" frameborder="0" webkitallowfullscreen mozallowfullscreen allowfullscreen></iframe>

## Why is UI Usage Tracking disabled?
- Heavy database queries on `LLM_Spend_Logs` (once it has 1M+ rows) can slow down your LLM API requests. **We do not want this happening**

## Solutions for Usage Tracking

Step 1. **Export Logs to Cloud Storage**
   - [Send logs to S3, GCS, or Azure Blob Storage](https://docs.hanzo.ai/docs/proxy/logging)
   - [Log format specification](https://docs.hanzo.ai/docs/proxy/logging_spec)

Step 2. **Analyze Data**
   - Use tools like [Redash](https://redash.io/), [Databricks](https://www.databricks.com/), [Snowflake](https://www.snowflake.com/en/) to analyze exported logs

[Optional] Step 3. **Disable Spend + Error Logs to LLM DB**

[See Instructions Here](./prod#6-disable-spend_logs--error_logs-if-not-using-the-llm-ui)

Disabling this will prevent your LLM DB from growing in size, which will help with performance (prevent health checks from failing).

## Need an Integration? Get in Touch

- Request a logging integration on [Github Issues](https://github.com/hanzoai/llm/issues)
- Get in [touch with LLM Founders](https://calendly.com/d/4mp-gd3-k5k/llm-1-1-onboarding-chat)
- Get a 7-day free trial of LLM [here](https://hanzo.ai#trial)



