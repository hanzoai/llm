import uuid
from copy import deepcopy

import llm
from llm._logging import verbose_logger

from .asyncify import run_async_function


async def async_completion_with_fallbacks(**kwargs):
    """
    Asynchronously attempts completion with fallback models if the primary model fails.

    Args:
        **kwargs: Keyword arguments for completion, including:
            - model (str): Primary model to use
            - fallbacks (List[Union[str, dict]]): List of fallback models/configs
            - Other completion parameters

    Returns:
        ModelResponse: The completion response from the first successful model

    Raises:
        Exception: If all models fail and no response is generated
    """
    # Extract and prepare parameters
    nested_kwargs = kwargs.pop("kwargs", {})
    original_model = kwargs["model"]
    model = original_model
    fallbacks = [original_model] + nested_kwargs.pop("fallbacks", [])
    kwargs.pop("acompletion", None)  # Remove to prevent keyword conflicts
    llm_call_id = str(uuid.uuid4())
    base_kwargs = {**kwargs, **nested_kwargs, "llm_call_id": llm_call_id}
    base_kwargs.pop("model", None)  # Remove model as it will be set per fallback

    # Try each fallback model
    for fallback in fallbacks:
        try:
            completion_kwargs = deepcopy(base_kwargs)

            # Handle dictionary fallback configurations
            if isinstance(fallback, dict):
                model = fallback.pop("model", original_model)
                completion_kwargs.update(fallback)
            else:
                model = fallback

            response = await llm.acompletion(**completion_kwargs, model=model)

            if response is not None:
                return response

        except Exception as e:
            verbose_logger.exception(
                f"Fallback attempt failed for model {model}: {str(e)}"
            )
            continue

    raise Exception(
        "All fallback attempts failed. Enable verbose logging with `llm.set_verbose=True` for details."
    )


def completion_with_fallbacks(**kwargs):
    return run_async_function(async_function=async_completion_with_fallbacks, **kwargs)
