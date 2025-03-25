from typing import Literal, Optional

import llm
from llm import LlmProviders
from llm.exceptions import BadRequestError


def get_supported_openai_params(  # noqa: PLR0915
    model: str,
    custom_llm_provider: Optional[str] = None,
    request_type: Literal[
        "chat_completion", "embeddings", "transcription"
    ] = "chat_completion",
) -> Optional[list]:
    """
    Returns the supported openai params for a given model + provider

    Example:
    ```
    get_supported_openai_params(model="anthropic.claude-3", custom_llm_provider="bedrock")
    ```

    Returns:
    - List if custom_llm_provider is mapped
    - None if unmapped
    """
    if not custom_llm_provider:
        try:
            custom_llm_provider = llm.get_llm_provider(model=model)[1]
        except BadRequestError:
            return None

    if custom_llm_provider == "bedrock":
        return llm.AmazonConverseConfig().get_supported_openai_params(model=model)
    elif custom_llm_provider == "ollama":
        return llm.OllamaConfig().get_supported_openai_params(model=model)
    elif custom_llm_provider == "ollama_chat":
        return llm.OllamaChatConfig().get_supported_openai_params(model=model)
    elif custom_llm_provider == "anthropic":
        return llm.AnthropicConfig().get_supported_openai_params(model=model)
    elif custom_llm_provider == "anthropic_text":
        return llm.AnthropicTextConfig().get_supported_openai_params(model=model)
    elif custom_llm_provider == "fireworks_ai":
        if request_type == "embeddings":
            return llm.FireworksAIEmbeddingConfig().get_supported_openai_params(
                model=model
            )
        elif request_type == "transcription":
            return llm.FireworksAIAudioTranscriptionConfig().get_supported_openai_params(
                model=model
            )
        else:
            return llm.FireworksAIConfig().get_supported_openai_params(model=model)
    elif custom_llm_provider == "nvidia_nim":
        if request_type == "chat_completion":
            return llm.nvidiaNimConfig.get_supported_openai_params(model=model)
        elif request_type == "embeddings":
            return llm.nvidiaNimEmbeddingConfig.get_supported_openai_params()
    elif custom_llm_provider == "cerebras":
        return llm.CerebrasConfig().get_supported_openai_params(model=model)
    elif custom_llm_provider == "xai":
        return llm.XAIChatConfig().get_supported_openai_params(model=model)
    elif custom_llm_provider == "ai21_chat" or custom_llm_provider == "ai21":
        return llm.AI21ChatConfig().get_supported_openai_params(model=model)
    elif custom_llm_provider == "volcengine":
        return llm.VolcEngineConfig().get_supported_openai_params(model=model)
    elif custom_llm_provider == "groq":
        return llm.GroqChatConfig().get_supported_openai_params(model=model)
    elif custom_llm_provider == "hosted_vllm":
        return llm.HostedVLLMChatConfig().get_supported_openai_params(model=model)
    elif custom_llm_provider == "vllm":
        return llm.VLLMConfig().get_supported_openai_params(model=model)
    elif custom_llm_provider == "deepseek":
        return llm.DeepSeekChatConfig().get_supported_openai_params(model=model)
    elif custom_llm_provider == "cohere":
        return llm.CohereConfig().get_supported_openai_params(model=model)
    elif custom_llm_provider == "cohere_chat":
        return llm.CohereChatConfig().get_supported_openai_params(model=model)
    elif custom_llm_provider == "maritalk":
        return llm.MaritalkConfig().get_supported_openai_params(model=model)
    elif custom_llm_provider == "openai":
        return llm.OpenAIConfig().get_supported_openai_params(model=model)
    elif custom_llm_provider == "azure":
        if llm.AzureOpenAIO1Config().is_o_series_model(model=model):
            return llm.AzureOpenAIO1Config().get_supported_openai_params(
                model=model
            )
        else:
            return llm.AzureOpenAIConfig().get_supported_openai_params(model=model)
    elif custom_llm_provider == "openrouter":
        return llm.OpenrouterConfig().get_supported_openai_params(model=model)
    elif custom_llm_provider == "mistral" or custom_llm_provider == "codestral":
        # mistal and codestral api have the exact same params
        if request_type == "chat_completion":
            return llm.MistralConfig().get_supported_openai_params(model=model)
        elif request_type == "embeddings":
            return llm.MistralEmbeddingConfig().get_supported_openai_params()
    elif custom_llm_provider == "text-completion-codestral":
        return llm.CodestralTextCompletionConfig().get_supported_openai_params(
            model=model
        )
    elif custom_llm_provider == "sambanova":
        return llm.SambanovaConfig().get_supported_openai_params(model=model)
    elif custom_llm_provider == "replicate":
        return llm.ReplicateConfig().get_supported_openai_params(model=model)
    elif custom_llm_provider == "huggingface":
        return llm.HuggingfaceConfig().get_supported_openai_params(model=model)
    elif custom_llm_provider == "jina_ai":
        if request_type == "embeddings":
            return llm.JinaAIEmbeddingConfig().get_supported_openai_params()
    elif custom_llm_provider == "together_ai":
        return llm.TogetherAIConfig().get_supported_openai_params(model=model)
    elif custom_llm_provider == "databricks":
        if request_type == "chat_completion":
            return llm.DatabricksConfig().get_supported_openai_params(model=model)
        elif request_type == "embeddings":
            return llm.DatabricksEmbeddingConfig().get_supported_openai_params()
    elif custom_llm_provider == "palm" or custom_llm_provider == "gemini":
        return llm.GoogleAIStudioGeminiConfig().get_supported_openai_params(
            model=model
        )
    elif custom_llm_provider == "vertex_ai" or custom_llm_provider == "vertex_ai_beta":
        if request_type == "chat_completion":
            if model.startswith("mistral"):
                return llm.MistralConfig().get_supported_openai_params(model=model)
            elif model.startswith("codestral"):
                return (
                    llm.CodestralTextCompletionConfig().get_supported_openai_params(
                        model=model
                    )
                )
            elif model.startswith("claude"):
                return llm.VertexAIAnthropicConfig().get_supported_openai_params(
                    model=model
                )
            elif model.startswith("gemini"):
                return llm.VertexGeminiConfig().get_supported_openai_params(
                    model=model
                )
            else:
                return llm.VertexAILlama3Config().get_supported_openai_params(
                    model=model
                )
        elif request_type == "embeddings":
            return llm.VertexAITextEmbeddingConfig().get_supported_openai_params()
    elif custom_llm_provider == "sagemaker":
        return llm.SagemakerConfig().get_supported_openai_params(model=model)
    elif custom_llm_provider == "aleph_alpha":
        return [
            "max_tokens",
            "stream",
            "top_p",
            "temperature",
            "presence_penalty",
            "frequency_penalty",
            "n",
            "stop",
        ]
    elif custom_llm_provider == "cloudflare":
        return llm.CloudflareChatConfig().get_supported_openai_params(model=model)
    elif custom_llm_provider == "nlp_cloud":
        return llm.NLPCloudConfig().get_supported_openai_params(model=model)
    elif custom_llm_provider == "petals":
        return llm.PetalsConfig().get_supported_openai_params(model=model)
    elif custom_llm_provider == "deepinfra":
        return llm.DeepInfraConfig().get_supported_openai_params(model=model)
    elif custom_llm_provider == "perplexity":
        return llm.PerplexityChatConfig().get_supported_openai_params(model=model)
    elif custom_llm_provider == "anyscale":
        return [
            "temperature",
            "top_p",
            "stream",
            "max_tokens",
            "stop",
            "frequency_penalty",
            "presence_penalty",
        ]
    elif custom_llm_provider == "watsonx":
        return llm.IBMWatsonXChatConfig().get_supported_openai_params(model=model)
    elif custom_llm_provider == "watsonx_text":
        return llm.IBMWatsonXAIConfig().get_supported_openai_params(model=model)
    elif (
        custom_llm_provider == "custom_openai"
        or custom_llm_provider == "text-completion-openai"
    ):
        return llm.OpenAITextCompletionConfig().get_supported_openai_params(
            model=model
        )
    elif custom_llm_provider == "predibase":
        return llm.PredibaseConfig().get_supported_openai_params(model=model)
    elif custom_llm_provider == "voyage":
        return llm.VoyageEmbeddingConfig().get_supported_openai_params(model=model)
    elif custom_llm_provider == "triton":
        if request_type == "embeddings":
            return llm.TritonEmbeddingConfig().get_supported_openai_params(
                model=model
            )
        else:
            return llm.TritonConfig().get_supported_openai_params(model=model)
    elif custom_llm_provider == "deepgram":
        if request_type == "transcription":
            return (
                llm.DeepgramAudioTranscriptionConfig().get_supported_openai_params(
                    model=model
                )
            )
    elif custom_llm_provider in llm._custom_providers:
        if request_type == "chat_completion":
            provider_config = llm.ProviderConfigManager.get_provider_chat_config(
                model=model, provider=LlmProviders.CUSTOM
            )
            return provider_config.get_supported_openai_params(model=model)
        elif request_type == "embeddings":
            return None
        elif request_type == "transcription":
            return None

    return None
