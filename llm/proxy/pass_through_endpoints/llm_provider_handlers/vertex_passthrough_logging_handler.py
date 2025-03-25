import json
import re
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union
from urllib.parse import urlparse
import httpx

import llm
from llm._logging import verbose_proxy_logger
from llm.llm_core_utils.llm_logging import Logging as LLMLoggingObj
from llm.llms.vertex_ai.gemini.vertex_and_google_ai_studio_gemini import (
    ModelResponseIterator as VertexModelResponseIterator,
)
from llm.proxy._types import PassThroughEndpointLoggingTypedDict
from llm.types.utils import (
    EmbeddingResponse,
    ImageResponse,
    ModelResponse,
    TextCompletionResponse,
)

if TYPE_CHECKING:
    from ..success_handler import PassThroughEndpointLogging
    from ..types import EndpointType
else:
    PassThroughEndpointLogging = Any
    EndpointType = Any


class VertexPassthroughLoggingHandler:
    @staticmethod
    def vertex_passthrough_handler(
        httpx_response: httpx.Response,
        logging_obj: LLMLoggingObj,
        url_route: str,
        result: str,
        start_time: datetime,
        end_time: datetime,
        cache_hit: bool,
        **kwargs,
    ) -> PassThroughEndpointLoggingTypedDict:
        if "generateContent" in url_route:
            model = VertexPassthroughLoggingHandler.extract_model_from_url(url_route)

            instance_of_vertex_llm = llm.VertexGeminiConfig()
            litellm_model_response: ModelResponse = (
                instance_of_vertex_llm.transform_response(
                    model=model,
                    messages=[
                        {"role": "user", "content": "no-message-pass-through-endpoint"}
                    ],
                    raw_response=httpx_response,
                    model_response=llm.ModelResponse(),
                    logging_obj=logging_obj,
                    optional_params={},
                    llm_params={},
                    api_key="",
                    request_data={},
                    encoding=llm.encoding,
                )
            )
            kwargs = VertexPassthroughLoggingHandler._create_vertex_response_logging_payload_for_generate_content(
                litellm_model_response=litellm_model_response,
                model=model,
                kwargs=kwargs,
                start_time=start_time,
                end_time=end_time,
                logging_obj=logging_obj,
                custom_llm_provider=VertexPassthroughLoggingHandler._get_custom_llm_provider_from_url(
                    url_route
                ),
            )

            return {
                "result": litellm_model_response,
                "kwargs": kwargs,
            }

        elif "predict" in url_route:
            from llm.llms.vertex_ai.image_generation.image_generation_handler import (
                VertexImageGeneration,
            )
            from llm.types.utils import PassthroughCallTypes

            vertex_image_generation_class = VertexImageGeneration()

            model = VertexPassthroughLoggingHandler.extract_model_from_url(url_route)
            _json_response = httpx_response.json()

            litellm_prediction_response: Union[
                ModelResponse, EmbeddingResponse, ImageResponse
            ] = ModelResponse()
            if vertex_image_generation_class.is_image_generation_response(
                _json_response
            ):
                litellm_prediction_response = (
                    vertex_image_generation_class.process_image_generation_response(
                        _json_response,
                        model_response=llm.ImageResponse(),
                        model=model,
                    )
                )

                logging_obj.call_type = (
                    PassthroughCallTypes.passthrough_image_generation.value
                )
            else:
                litellm_prediction_response = llm.vertexAITextEmbeddingConfig.transform_vertex_response_to_openai(
                    response=_json_response,
                    model=model,
                    model_response=llm.EmbeddingResponse(),
                )
            if isinstance(litellm_prediction_response, llm.EmbeddingResponse):
                litellm_prediction_response.model = model

            logging_obj.model = model
            logging_obj.model_call_details["model"] = logging_obj.model

            return {
                "result": litellm_prediction_response,
                "kwargs": kwargs,
            }
        else:
            return {
                "result": None,
                "kwargs": kwargs,
            }

    @staticmethod
    def _handle_logging_vertex_collected_chunks(
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
        Takes raw chunks from Vertex passthrough endpoint and logs them in llm callbacks

        - Builds complete response from chunks
        - Creates standard logging object
        - Logs in llm callbacks
        """
        kwargs: Dict[str, Any] = {}
        model = VertexPassthroughLoggingHandler.extract_model_from_url(url_route)
        complete_streaming_response = (
            VertexPassthroughLoggingHandler._build_complete_streaming_response(
                all_chunks=all_chunks,
                llm_logging_obj=llm_logging_obj,
                model=model,
            )
        )

        if complete_streaming_response is None:
            verbose_proxy_logger.error(
                "Unable to build complete streaming response for Vertex passthrough endpoint, not logging..."
            )
            return {
                "result": None,
                "kwargs": kwargs,
            }

        kwargs = VertexPassthroughLoggingHandler._create_vertex_response_logging_payload_for_generate_content(
            litellm_model_response=complete_streaming_response,
            model=model,
            kwargs=kwargs,
            start_time=start_time,
            end_time=end_time,
            logging_obj=llm_logging_obj,
            custom_llm_provider=VertexPassthroughLoggingHandler._get_custom_llm_provider_from_url(
                url_route
            ),
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
        vertex_iterator = VertexModelResponseIterator(
            streaming_response=None,
            sync_stream=False,
        )
        litellm_custom_stream_wrapper = llm.CustomStreamWrapper(
            completion_stream=vertex_iterator,
            model=model,
            logging_obj=llm_logging_obj,
            custom_llm_provider="vertex_ai",
        )
        all_openai_chunks = []
        for chunk in all_chunks:
            generic_chunk = vertex_iterator._common_chunk_parsing_logic(chunk)
            litellm_chunk = litellm_custom_stream_wrapper.chunk_creator(
                chunk=generic_chunk
            )
            if litellm_chunk is not None:
                all_openai_chunks.append(litellm_chunk)

        complete_streaming_response = llm.stream_chunk_builder(
            chunks=all_openai_chunks
        )

        return complete_streaming_response

    @staticmethod
    def extract_model_from_url(url: str) -> str:
        pattern = r"/models/([^:]+)"
        match = re.search(pattern, url)
        if match:
            return match.group(1)
        return "unknown"

    @staticmethod
    def _get_custom_llm_provider_from_url(url: str) -> str:
        parsed_url = urlparse(url)
        if parsed_url.hostname and parsed_url.hostname.endswith("generativelanguage.googleapis.com"):
            return llm.LlmProviders.GEMINI.value
        return llm.LlmProviders.VERTEX_AI.value

    @staticmethod
    def _create_vertex_response_logging_payload_for_generate_content(
        litellm_model_response: Union[ModelResponse, TextCompletionResponse],
        model: str,
        kwargs: dict,
        start_time: datetime,
        end_time: datetime,
        logging_obj: LLMLoggingObj,
        custom_llm_provider: str,
    ):
        """
        Create the standard logging object for Vertex passthrough generateContent (streaming and non-streaming)

        """
        response_cost = llm.completion_cost(
            completion_response=litellm_model_response,
            model=model,
        )
        kwargs["response_cost"] = response_cost
        kwargs["model"] = model

        # pretty print standard logging object
        verbose_proxy_logger.debug("kwargs= %s", json.dumps(kwargs, indent=4))

        # set llm_call_id to logging response object
        litellm_model_response.id = logging_obj.llm_call_id
        logging_obj.model = litellm_model_response.model or model
        logging_obj.model_call_details["model"] = logging_obj.model
        logging_obj.model_call_details["custom_llm_provider"] = custom_llm_provider
        return kwargs
