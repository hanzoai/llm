"""
Callbacks triggered on cooling down deployments
"""

import copy
from typing import TYPE_CHECKING, Any, Optional, Union

import llm
from llm._logging import verbose_logger

if TYPE_CHECKING:
    from llm.router import Router as _Router

    LLMRouter = _Router
    from llm.integrations.prometheus import PrometheusLogger
else:
    LLMRouter = Any
    PrometheusLogger = Any


async def router_cooldown_event_callback(
    llm_router_instance: LLMRouter,
    deployment_id: str,
    exception_status: Union[str, int],
    cooldown_time: float,
):
    """
    Callback triggered when a deployment is put into cooldown by llm

    - Updates deployment state on Prometheus
    - Increments cooldown metric for deployment on Prometheus
    """
    verbose_logger.debug("In router_cooldown_event_callback - updating prometheus")
    _deployment = llm_router_instance.get_deployment(model_id=deployment_id)
    if _deployment is None:
        verbose_logger.warning(
            f"in router_cooldown_event_callback but _deployment is None for deployment_id={deployment_id}. Doing nothing"
        )
        return
    _llm_params = _deployment["llm_params"]
    temp_llm_params = copy.deepcopy(_llm_params)
    temp_llm_params = dict(temp_llm_params)
    _model_name = _deployment.get("model_name", None) or ""
    _api_base = (
        llm.get_api_base(model=_model_name, optional_params=temp_llm_params)
        or ""
    )
    model_info = _deployment["model_info"]
    model_id = model_info.id

    llm_model_name = temp_llm_params.get("model") or ""
    llm_provider = ""
    try:
        _, llm_provider, _, _ = llm.get_llm_provider(
            model=llm_model_name,
            custom_llm_provider=temp_llm_params.get("custom_llm_provider"),
        )
    except Exception:
        pass

    # get the prometheus logger from in memory loggers
    prometheusLogger: Optional[PrometheusLogger] = (
        _get_prometheus_logger_from_callbacks()
    )

    if prometheusLogger is not None:
        prometheusLogger.set_deployment_complete_outage(
            llm_model_name=_model_name,
            model_id=model_id,
            api_base=_api_base,
            api_provider=llm_provider,
        )

        prometheusLogger.increment_deployment_cooled_down(
            llm_model_name=_model_name,
            model_id=model_id,
            api_base=_api_base,
            api_provider=llm_provider,
            exception_status=str(exception_status),
        )

    return


def _get_prometheus_logger_from_callbacks() -> Optional[PrometheusLogger]:
    """
    Checks if prometheus is a initalized callback, if yes returns it
    """
    from llm.integrations.prometheus import PrometheusLogger

    for _callback in llm._async_success_callback:
        if isinstance(_callback, PrometheusLogger):
            return _callback
    for global_callback in llm.callbacks:
        if isinstance(global_callback, PrometheusLogger):
            return global_callback

    return None
