from typing import List, Optional, Tuple

from llm._logging import verbose_logger
from llm.integrations.custom_prompt_management import CustomPromptManagement
from llm.types.llms.openai import AllMessageValues
from llm.types.utils import StandardCallbackDynamicParams


class X42PromptManagement(CustomPromptManagement):
    def get_chat_completion_prompt(
        self,
        model: str,
        messages: List[AllMessageValues],
        non_default_params: dict,
        prompt_id: str,
        prompt_variables: Optional[dict],
        dynamic_callback_params: StandardCallbackDynamicParams,
    ) -> Tuple[str, List[AllMessageValues], dict]:
        """
        Returns:
        - model: str - the model to use (can be pulled from prompt management tool)
        - messages: List[AllMessageValues] - the messages to use (can be pulled from prompt management tool)
        - non_default_params: dict - update with any optional params (e.g. temperature, max_tokens, etc.) to use (can be pulled from prompt management tool)
        """
        verbose_logger.debug(
            f"in async get chat completion prompt. Prompt ID: {prompt_id}, Prompt Variables: {prompt_variables}, Dynamic Callback Params: {dynamic_callback_params}"
        )

        return model, messages, non_default_params

    @property
    def integration_name(self) -> str:
        return "x42-prompt-management"


x42_prompt_management = X42PromptManagement()
