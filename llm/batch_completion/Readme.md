# Implementation of `llm.batch_completion`, `llm.batch_completion_models`, `llm.batch_completion_models_all_responses`

Doc: https://docs.llm.ai/docs/completion/batching


LLM Python SDK allows you to:
1. `llm.batch_completion` Batch llm.completion function for a given model.
2. `llm.batch_completion_models` Send a request to multiple language models concurrently and return the response
    as soon as one of the models responds.
3. `llm.batch_completion_models_all_responses` Send a request to multiple language models concurrently and return a list of responses
    from all models that respond.