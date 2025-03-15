"""
- call /messages on Anthropic API
- Make streaming + non-streaming request - just pass it through direct to Anthropic. No need to do anything special here 
- Ensure requests are logged in the DB - stream + non-stream

"""

import json
from typing import Any, AsyncIterator, Dict, Optional, Union, cast

import httpx

import llm
from llm.llm_core_utils.llm_logging import Logging as HanzoLoggingObj
from llm.llms.base_llm.anthropic_messages.transformation import (
    BaseAnthropicMessagesConfig,
)
from llm.llms.custom_httpx.http_handler import (
    AsyncHTTPHandler,
    get_async_httpx_client,
)
from llm.types.router import GenericHanzoParams
from llm.types.utils import ProviderSpecificHeader
from llm.utils import ProviderConfigManager, client


class AnthropicMessagesHandler:

    @staticmethod
    async def _handle_anthropic_streaming(
        response: httpx.Response,
        request_body: dict,
        llm_logging_obj: HanzoLoggingObj,
    ) -> AsyncIterator:
        """Helper function to handle Anthropic streaming responses using the existing logging handlers"""
        from datetime import datetime

        from llm.proxy.pass_through_endpoints.streaming_handler import (
            PassThroughStreamingHandler,
        )
        from llm.proxy.pass_through_endpoints.success_handler import (
            PassThroughEndpointLogging,
        )
        from llm.proxy.pass_through_endpoints.types import EndpointType

        # Create success handler object
        passthrough_success_handler_obj = PassThroughEndpointLogging()

        # Use the existing streaming handler for Anthropic
        start_time = datetime.now()
        return PassThroughStreamingHandler.chunk_processor(
            response=response,
            request_body=request_body,
            llm_logging_obj=llm_logging_obj,
            endpoint_type=EndpointType.ANTHROPIC,
            start_time=start_time,
            passthrough_success_handler_obj=passthrough_success_handler_obj,
            url_route="/v1/messages",
        )


@client
async def anthropic_messages(
    api_key: str,
    model: str,
    stream: bool = False,
    api_base: Optional[str] = None,
    client: Optional[AsyncHTTPHandler] = None,
    custom_llm_provider: Optional[str] = None,
    **kwargs,
) -> Union[Dict[str, Any], AsyncIterator]:
    """
    Makes Anthropic `/v1/messages` API calls In the Anthropic API Spec
    """
    # Use provided client or create a new one
    optional_params = GenericHanzoParams(**kwargs)
    model, _custom_llm_provider, dynamic_api_key, dynamic_api_base = (
        llm.get_llm_provider(
            model=model,
            custom_llm_provider=custom_llm_provider,
            api_base=optional_params.api_base,
            api_key=optional_params.api_key,
        )
    )
    anthropic_messages_provider_config: Optional[BaseAnthropicMessagesConfig] = (
        ProviderConfigManager.get_provider_anthropic_messages_config(
            model=model,
            provider=llm.LlmProviders(_custom_llm_provider),
        )
    )
    if anthropic_messages_provider_config is None:
        raise ValueError(
            f"Anthropic messages provider config not found for model: {model}"
        )
    if client is None or not isinstance(client, AsyncHTTPHandler):
        async_httpx_client = get_async_httpx_client(
            llm_provider=llm.LlmProviders.ANTHROPIC
        )
    else:
        async_httpx_client = client

    llm_logging_obj: HanzoLoggingObj = kwargs.get("llm_logging_obj", None)

    # Prepare headers
    provider_specific_header = cast(
        Optional[ProviderSpecificHeader], kwargs.get("provider_specific_header", None)
    )
    extra_headers = (
        provider_specific_header.get("extra_headers", {})
        if provider_specific_header
        else {}
    )
    headers = anthropic_messages_provider_config.validate_environment(
        headers=extra_headers or {},
        model=model,
        api_key=api_key,
    )

    llm_logging_obj.update_environment_variables(
        model=model,
        optional_params=dict(optional_params),
        llm_params={
            "metadata": kwargs.get("metadata", {}),
            "preset_cache_key": None,
            "stream_response": {},
            **optional_params.model_dump(exclude_unset=True),
        },
        custom_llm_provider=_custom_llm_provider,
    )
    llm_logging_obj.model_call_details.update(kwargs)

    # Prepare request body
    request_body = kwargs.copy()
    request_body = {
        k: v
        for k, v in request_body.items()
        if k
        in anthropic_messages_provider_config.get_supported_anthropic_messages_params(
            model=model
        )
    }
    request_body["stream"] = stream
    request_body["model"] = model
    llm_logging_obj.stream = stream

    # Make the request
    request_url = anthropic_messages_provider_config.get_complete_url(
        api_base=api_base, model=model
    )

    llm_logging_obj.pre_call(
        input=[{"role": "user", "content": json.dumps(request_body)}],
        api_key="",
        additional_args={
            "complete_input_dict": request_body,
            "api_base": str(request_url),
            "headers": headers,
        },
    )

    response = await async_httpx_client.post(
        url=request_url,
        headers=headers,
        data=json.dumps(request_body),
        stream=stream,
    )
    response.raise_for_status()

    # used for logging + cost tracking
    llm_logging_obj.model_call_details["httpx_response"] = response

    if stream:
        return await AnthropicMessagesHandler._handle_anthropic_streaming(
            response=response,
            request_body=request_body,
            llm_logging_obj=llm_logging_obj,
        )
    else:
        return response.json()
