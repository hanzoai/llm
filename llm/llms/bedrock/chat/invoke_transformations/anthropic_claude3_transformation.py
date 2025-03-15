from typing import TYPE_CHECKING, Any, List, Optional

import httpx

from llm.llms.anthropic.chat.transformation import AnthropicConfig
from llm.llms.bedrock.chat.invoke_transformations.base_invoke_transformation import (
    AmazonInvokeConfig,
)
from llm.types.llms.openai import AllMessageValues
from llm.types.utils import ModelResponse

if TYPE_CHECKING:
    from llm.llm_core_utils.llm_logging import Logging as _HanzoLoggingObj

    HanzoLoggingObj = _HanzoLoggingObj
else:
    HanzoLoggingObj = Any


class AmazonAnthropicClaude3Config(AmazonInvokeConfig, AnthropicConfig):
    """
    Reference:
        https://us-west-2.console.aws.amazon.com/bedrock/home?region=us-west-2#/providers?model=claude
        https://docs.anthropic.com/claude/docs/models-overview#model-comparison

    Supported Params for the Amazon / Anthropic Claude 3 models:
    """

    anthropic_version: str = "bedrock-2023-05-31"

    def get_supported_openai_params(self, model: str) -> List[str]:
        return AnthropicConfig.get_supported_openai_params(self, model)

    def map_openai_params(
        self,
        non_default_params: dict,
        optional_params: dict,
        model: str,
        drop_params: bool,
    ) -> dict:
        return AnthropicConfig.map_openai_params(
            self,
            non_default_params,
            optional_params,
            model,
            drop_params,
        )

    def transform_request(
        self,
        model: str,
        messages: List[AllMessageValues],
        optional_params: dict,
        llm_params: dict,
        headers: dict,
    ) -> dict:
        _anthropic_request = AnthropicConfig.transform_request(
            self,
            model=model,
            messages=messages,
            optional_params=optional_params,
            llm_params=llm_params,
            headers=headers,
        )

        _anthropic_request.pop("model", None)
        _anthropic_request.pop("stream", None)
        if "anthropic_version" not in _anthropic_request:
            _anthropic_request["anthropic_version"] = self.anthropic_version

        return _anthropic_request

    def transform_response(
        self,
        model: str,
        raw_response: httpx.Response,
        model_response: ModelResponse,
        logging_obj: HanzoLoggingObj,
        request_data: dict,
        messages: List[AllMessageValues],
        optional_params: dict,
        llm_params: dict,
        encoding: Any,
        api_key: Optional[str] = None,
        json_mode: Optional[bool] = None,
    ) -> ModelResponse:
        return AnthropicConfig.transform_response(
            self,
            model=model,
            raw_response=raw_response,
            model_response=model_response,
            logging_obj=logging_obj,
            request_data=request_data,
            messages=messages,
            optional_params=optional_params,
            llm_params=llm_params,
            encoding=encoding,
            api_key=api_key,
            json_mode=json_mode,
        )
