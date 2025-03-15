from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, List, Optional

import httpx

from llm.llms.base_llm.chat.transformation import BaseConfig
from llm.types.llms.openai import (
    AllMessageValues,
    OpenAIAudioTranscriptionOptionalParams,
)
from llm.types.utils import ModelResponse

if TYPE_CHECKING:
    from llm.llm_core_utils.llm_logging import Logging as _HanzoLoggingObj

    HanzoLoggingObj = _HanzoLoggingObj
else:
    HanzoLoggingObj = Any


class BaseAudioTranscriptionConfig(BaseConfig, ABC):
    @abstractmethod
    def get_supported_openai_params(
        self, model: str
    ) -> List[OpenAIAudioTranscriptionOptionalParams]:
        pass

    def get_complete_url(
        self,
        api_base: Optional[str],
        model: str,
        optional_params: dict,
        llm_params: dict,
        stream: Optional[bool] = None,
    ) -> str:
        """
        OPTIONAL

        Get the complete url for the request

        Some providers need `model` in `api_base`
        """
        return api_base or ""

    def transform_request(
        self,
        model: str,
        messages: List[AllMessageValues],
        optional_params: dict,
        llm_params: dict,
        headers: dict,
    ) -> dict:
        raise NotImplementedError(
            "AudioTranscriptionConfig does not need a request transformation for audio transcription models"
        )

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
        raise NotImplementedError(
            "AudioTranscriptionConfig does not need a response transformation for audio transcription models"
        )
