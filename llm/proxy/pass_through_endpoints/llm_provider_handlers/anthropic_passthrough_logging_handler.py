import json
from datetime import datetime
from typing import TYPE_CHECKING, Any, List, Optional, Union

import httpx

import llm
from llm._logging import verbose_proxy_logger
from llm.llm_core_utils.llm_logging import Logging as LLMLoggingObj
from llm.llms.anthropic.chat.handler import (
    ModelResponseIterator as AnthropicModelResponseIterator,
)
from llm.llms.anthropic.chat.transformation import AnthropicConfig
from llm.proxy._types import PassThroughEndpointLoggingTypedDict
from llm.proxy.auth.auth_utils import get_end_user_id_from_request_body
from llm.proxy.pass_through_endpoints.types import PassthroughStandardLoggingPayload
from llm.types.utils import ModelResponse, TextCompletionResponse

if TYPE_CHECKING:
    from ..success_handler import PassThroughEndpointLogging
    from ..types import EndpointType
else:
    PassThroughEndpointLogging = Any
    EndpointType = Any


class AnthropicPassthroughLoggingHandler:

    @staticmethod
    def anthropic_passthrough_handler(
        httpx_response: httpx.Response,
        response_body: dict,
        logging_obj: LLMLoggingObj,
        url_route: str,
        result: str,
        start_time: datetime,
        end_time: datetime,
        cache_hit: bool,
        **kwargs,
    ) -> PassThroughEndpointLoggingTypedDict:
        """
        Transforms Anthropic response to OpenAI response, generates a standard logging object so downstream logging can be handled
        """
        model = response_body.get("model", "")
        llm_model_response: ModelResponse = AnthropicConfig().transform_response(
            raw_response=httpx_response,
            model_response=llm.ModelResponse(),
            model=model,
            messages=[],
            logging_obj=logging_obj,
            optional_params={},
            api_key="",
            request_data={},
            encoding=llm.encoding,
            json_mode=False,
            llm_params={},
        )

        kwargs = AnthropicPassthroughLoggingHandler._create_anthropic_response_logging_payload(
            llm_model_response=llm_model_response,
            model=model,
            kwargs=kwargs,
            start_time=start_time,
            end_time=end_time,
            logging_obj=logging_obj,
        )

        return {
            "result": llm_model_response,
            "kwargs": kwargs,
        }

    @staticmethod
    def _get_user_from_metadata(
        passthrough_logging_payload: PassthroughStandardLoggingPayload,
    ) -> Optional[str]:
        request_body = passthrough_logging_payload.get("request_body")
        if request_body:
            return get_end_user_id_from_request_body(request_body)
        return None

    @staticmethod
    def _create_anthropic_response_logging_payload(
        llm_model_response: Union[ModelResponse, TextCompletionResponse],
        model: str,
        kwargs: dict,
        start_time: datetime,
        end_time: datetime,
        logging_obj: LLMLoggingObj,
    ):
        """
        Create the standard logging object for Anthropic passthrough

        handles streaming and non-streaming responses
        """
        try:
            response_cost = llm.completion_cost(
                completion_response=llm_model_response,
                model=model,
            )
            kwargs["response_cost"] = response_cost
            kwargs["model"] = model
            passthrough_logging_payload: Optional[PassthroughStandardLoggingPayload] = (  # type: ignore
                kwargs.get("passthrough_logging_payload")
            )
            if passthrough_logging_payload:
                user = AnthropicPassthroughLoggingHandler._get_user_from_metadata(
                    passthrough_logging_payload=passthrough_logging_payload,
                )
                if user:
                    kwargs.setdefault("llm_params", {})
                    kwargs["llm_params"].update(
                        {"proxy_server_request": {"body": {"user": user}}}
                    )

            # pretty print standard logging object
            verbose_proxy_logger.debug(
                "kwargs= %s",
                json.dumps(kwargs, indent=4, default=str),
            )

            # set llm_call_id to logging response object
            llm_model_response.id = logging_obj.llm_call_id
            llm_model_response.model = model
            logging_obj.model_call_details["model"] = model
            logging_obj.model_call_details["custom_llm_provider"] = (
                llm.LLMProviders.ANTHROPIC.value
            )
            return kwargs
        except Exception as e:
            verbose_proxy_logger.exception(
                "Error creating Anthropic response logging payload: %s", e
            )
            return kwargs

    @staticmethod
    def _handle_logging_anthropic_collected_chunks(
        llm_logging_obj: LLMLoggingObj,
        passthrough_success_handler_obj: PassThroughEndpointLogging,
        url_route: str,
        request_body: dict,
        endpoint_type: EndpointType,
        start_time: datetime,
        all_chunks: List[str],
        end_time: datetime,
    ) -> PassThroughEndpointLoggingTypedDict:
        """
        Takes raw chunks from Anthropic passthrough endpoint and logs them in llm callbacks

        - Builds complete response from chunks
        - Creates standard logging object
        - Logs in llm callbacks
        """

        model = request_body.get("model", "")
        complete_streaming_response = (
            AnthropicPassthroughLoggingHandler._build_complete_streaming_response(
                all_chunks=all_chunks,
                llm_logging_obj=llm_logging_obj,
                model=model,
            )
        )
        if complete_streaming_response is None:
            verbose_proxy_logger.error(
                "Unable to build complete streaming response for Anthropic passthrough endpoint, not logging..."
            )
            return {
                "result": None,
                "kwargs": {},
            }
        kwargs = AnthropicPassthroughLoggingHandler._create_anthropic_response_logging_payload(
            llm_model_response=complete_streaming_response,
            model=model,
            kwargs={},
            start_time=start_time,
            end_time=end_time,
            logging_obj=llm_logging_obj,
        )

        return {
            "result": complete_streaming_response,
            "kwargs": kwargs,
        }

    @staticmethod
    def _build_complete_streaming_response(
        all_chunks: List[str],
        llm_logging_obj: LLMLoggingObj,
        model: str,
    ) -> Optional[Union[ModelResponse, TextCompletionResponse]]:
        """
        Builds complete response from raw Anthropic chunks

        - Converts str chunks to generic chunks
        - Converts generic chunks to llm chunks (OpenAI format)
        - Builds complete response from llm chunks
        """
        anthropic_model_response_iterator = AnthropicModelResponseIterator(
            streaming_response=None,
            sync_stream=False,
        )
        all_openai_chunks = []
        for _chunk_str in all_chunks:
            try:
                transformed_openai_chunk = anthropic_model_response_iterator.convert_str_chunk_to_generic_chunk(
                    chunk=_chunk_str
                )
                if transformed_openai_chunk is not None:
                    all_openai_chunks.append(transformed_openai_chunk)

                verbose_proxy_logger.debug(
                    "all openai chunks= %s",
                    json.dumps(all_openai_chunks, indent=4, default=str),
                )
            except (StopIteration, StopAsyncIteration):
                break
        complete_streaming_response = llm.stream_chunk_builder(
            chunks=all_openai_chunks
        )
        return complete_streaming_response
