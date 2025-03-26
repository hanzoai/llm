import asyncio
from typing import TYPE_CHECKING, Any

from llm.utils import calculate_max_parallel_requests

if TYPE_CHECKING:
    from llm.router import Router as _Router

    LlmRouter = _Router
else:
    LlmRouter = Any


class InitalizeCachedClient:
    @staticmethod
    def set_max_parallel_requests_client(
        llm_router_instance: LlmRouter, model: dict
    ):
        llm_params = model.get("llm_params", {})
        model_id = model["model_info"]["id"]
        rpm = llm_params.get("rpm", None)
        tpm = llm_params.get("tpm", None)
        max_parallel_requests = llm_params.get("max_parallel_requests", None)
        calculated_max_parallel_requests = calculate_max_parallel_requests(
            rpm=rpm,
            max_parallel_requests=max_parallel_requests,
            tpm=tpm,
            default_max_parallel_requests=llm_router_instance.default_max_parallel_requests,
        )
        if calculated_max_parallel_requests:
            semaphore = asyncio.Semaphore(calculated_max_parallel_requests)
            cache_key = f"{model_id}_max_parallel_requests_client"
            llm_router_instance.cache.set_cache(
                key=cache_key,
                value=semaphore,
                local_only=True,
            )
