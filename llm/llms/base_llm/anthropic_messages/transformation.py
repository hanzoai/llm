from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from llm.llm_core_utils.llm_logging import Logging as _HanzoLoggingObj

    HanzoLoggingObj = _HanzoLoggingObj
else:
    HanzoLoggingObj = Any


class BaseAnthropicMessagesConfig(ABC):
    @abstractmethod
    def validate_environment(
        self,
        headers: dict,
        model: str,
        api_key: Optional[str] = None,
    ) -> dict:
        pass

    @abstractmethod
    def get_complete_url(self, api_base: Optional[str], model: str) -> str:
        """
        OPTIONAL

        Get the complete url for the request

        Some providers need `model` in `api_base`
        """
        return api_base or ""

    @abstractmethod
    def get_supported_anthropic_messages_params(self, model: str) -> list:
        pass
