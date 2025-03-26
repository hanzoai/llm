from typing import TYPE_CHECKING, Any, Literal, Optional

from fastapi import HTTPException, status

import llm

if TYPE_CHECKING:
    from llm.router import Router as _Router

    LLMRouter = _Router
else:
    LLMRouter = Any


ROUTE_ENDPOINT_MAPPING = {
    "acompletion": "/chat/completions",
    "atext_completion": "/completions",
    "aembedding": "/embeddings",
    "aimage_generation": "/image/generations",
    "aspeech": "/audio/speech",
    "atranscription": "/audio/transcriptions",
    "amoderation": "/moderations",
    "arerank": "/rerank",
    "aresponses": "/responses",
}


class ProxyModelNotFoundError(HTTPException):
    def __init__(self, route: str, model_name: str):
        detail = {
            "error": f"{route}: Invalid model name passed in model={model_name}. Call `/v1/models` to view available models for your key."
        }
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


async def route_request(
    data: dict,
    llm_router: Optional[LLMRouter],
    user_model: Optional[str],
    route_type: Literal[
        "acompletion",
        "atext_completion",
        "aembedding",
        "aimage_generation",
        "aspeech",
        "atranscription",
        "amoderation",
        "arerank",
        "aresponses",
        "_arealtime",  # private function for realtime API
    ],
):
    """
    Common helper to route the request
    """
    router_model_names = llm_router.model_names if llm_router is not None else []
    if "api_key" in data or "api_base" in data:
        return getattr(llm_router, f"{route_type}")(**data)

    elif "user_config" in data:
        router_config = data.pop("user_config")
        user_router = llm.Router(**router_config)
        ret_val = getattr(user_router, f"{route_type}")(**data)
        user_router.discard()
        return ret_val

    elif (
        route_type == "acompletion"
        and data.get("model", "") is not None
        and "," in data.get("model", "")
        and llm_router is not None
    ):
        if data.get("fastest_response", False):
            return llm_router.abatch_completion_fastest_response(**data)
        else:
            models = [model.strip() for model in data.pop("model").split(",")]
            return llm_router.abatch_completion(models=models, **data)
    elif llm_router is not None:
        if (
            data["model"] in router_model_names
            or data["model"] in llm_router.get_model_ids()
        ):
            return getattr(llm_router, f"{route_type}")(**data)

        elif (
            llm_router.model_group_alias is not None
            and data["model"] in llm_router.model_group_alias
        ):
            return getattr(llm_router, f"{route_type}")(**data)

        elif data["model"] in llm_router.deployment_names:
            return getattr(llm_router, f"{route_type}")(
                **data, specific_deployment=True
            )

        elif data["model"] not in router_model_names:
            if llm_router.router_general_settings.pass_through_all_models:
                return getattr(llm, f"{route_type}")(**data)
            elif (
                llm_router.default_deployment is not None
                or len(llm_router.pattern_router.patterns) > 0
            ):
                return getattr(llm_router, f"{route_type}")(**data)
            elif route_type == "amoderation":
                # moderation endpoint does not require `model` parameter
                return getattr(llm_router, f"{route_type}")(**data)

    elif user_model is not None:
        return getattr(llm, f"{route_type}")(**data)

    # if no route found then it's a bad request
    route_name = ROUTE_ENDPOINT_MAPPING.get(route_type, route_type)
    raise ProxyModelNotFoundError(
        route=route_name,
        model_name=data.get("model", ""),
    )
