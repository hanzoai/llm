"""
This file handles authentication for the LLM Proxy.

it checks if the user passed a valid API Key to the LLM Proxy

Returns a UserAPIKeyAuth object if the API key is valid

"""

import asyncio
import re
import secrets
from datetime import datetime, timezone
from typing import Optional, cast

import fastapi
from fastapi import HTTPException, Request, WebSocket, status
from fastapi.security.api_key import APIKeyHeader

import llm
from llm._logging import verbose_logger, verbose_proxy_logger
from llm._service_logger import ServiceLogging
from llm.caching import DualCache
from llm.llm_core_utils.dd_tracing import tracer
from llm.proxy._types import *
from llm.proxy.auth.auth_checks import (
    _cache_key_object,
    _get_user_role,
    _handle_failed_db_connection_for_get_key_object,
    _is_user_proxy_admin,
    _virtual_key_max_budget_check,
    _virtual_key_soft_budget_check,
    can_key_call_model,
    common_checks,
    get_end_user_object,
    get_key_object,
    get_team_object,
    get_user_object,
    is_valid_fallback_model,
)
from llm.proxy.auth.auth_utils import (
    _get_request_ip_address,
    get_end_user_id_from_request_body,
    get_request_route,
    is_pass_through_provider_route,
    pre_db_read_auth_checks,
    route_in_additonal_public_routes,
    should_run_auth_on_pass_through_provider_route,
)
from llm.proxy.auth.handle_jwt import JWTAuthManager, JWTHandler
from llm.proxy.auth.oauth2_check import check_oauth2_token
from llm.proxy.auth.oauth2_proxy_hook import handle_oauth2_proxy_request
from llm.proxy.auth.service_account_checks import service_account_checks
from llm.proxy.common_utils.http_parsing_utils import _read_request_body
from llm.proxy.utils import PrismaClient, ProxyLogging
from llm.types.services import ServiceTypes

user_api_key_service_logger_obj = ServiceLogging()  # used for tracking latency on OTEL


api_key_header = APIKeyHeader(
    name=SpecialHeaders.openai_authorization.value,
    auto_error=False,
    description="Bearer token",
)
azure_api_key_header = APIKeyHeader(
    name=SpecialHeaders.azure_authorization.value,
    auto_error=False,
    description="Some older versions of the openai Python package will send an API-Key header with just the API key ",
)
anthropic_api_key_header = APIKeyHeader(
    name=SpecialHeaders.anthropic_authorization.value,
    auto_error=False,
    description="If anthropic client used.",
)
google_ai_studio_api_key_header = APIKeyHeader(
    name=SpecialHeaders.google_ai_studio_authorization.value,
    auto_error=False,
    description="If google ai studio client used.",
)
azure_apim_header = APIKeyHeader(
    name=SpecialHeaders.azure_apim_authorization.value,
    auto_error=False,
    description="The default name of the subscription key header of Azure",
)


def _get_bearer_token(
    api_key: str,
):
    if api_key.startswith("Bearer "):  # ensure Bearer token passed in
        api_key = api_key.replace("Bearer ", "")  # extract the token
    elif api_key.startswith("Basic "):
        api_key = api_key.replace("Basic ", "")  # handle langfuse input
    elif api_key.startswith("bearer "):
        api_key = api_key.replace("bearer ", "")
    else:
        api_key = ""
    return api_key


async def user_api_key_auth_websocket(websocket: WebSocket):
    # Accept the WebSocket connection

    request = Request(scope={"type": "http"})
    request._url = websocket.url

    query_params = websocket.query_params

    model = query_params.get("model")

    async def return_body():
        return_string = f'{{"model": "{model}"}}'
        # return string as bytes
        return return_string.encode()

    request.body = return_body  # type: ignore

    # Extract the Authorization header
    authorization = websocket.headers.get("authorization")

    # If no Authorization header, try the API-key header
    if not authorization:
        api_key = websocket.headers.get("api-key")
        if not api_key:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            raise HTTPException(status_code=403, detail="No API key provided")
    else:
        # Extract the API key from the Bearer token
        if not authorization.startswith("Bearer "):
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            raise HTTPException(
                status_code=403, detail="Invalid Authorization header format"
            )

        api_key = authorization[len("Bearer ") :].strip()

    # Call user_api_key_auth with the extracted API key
    # Note: You'll need to modify this to work with WebSocket context if needed
    try:
        return await user_api_key_auth(request=request, api_key=f"Bearer {api_key}")
    except Exception as e:
        verbose_proxy_logger.exception(e)
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        raise HTTPException(status_code=403, detail=str(e))


def update_valid_token_with_end_user_params(
    valid_token: UserAPIKeyAuth, end_user_params: dict
) -> UserAPIKeyAuth:
    valid_token.end_user_id = end_user_params.get("end_user_id")
    valid_token.end_user_tpm_limit = end_user_params.get("end_user_tpm_limit")
    valid_token.end_user_rpm_limit = end_user_params.get("end_user_rpm_limit")
    valid_token.allowed_model_region = end_user_params.get("allowed_model_region")
    return valid_token


async def get_global_proxy_spend(
    llm_proxy_admin_name: str,
    user_api_key_cache: DualCache,
    prisma_client: Optional[PrismaClient],
    token: str,
    proxy_logging_obj: ProxyLogging,
) -> Optional[float]:
    global_proxy_spend = None
    if llm.max_budget > 0:  # user set proxy max budget
        # check cache
        global_proxy_spend = await user_api_key_cache.async_get_cache(
            key="{}:spend".format(llm_proxy_admin_name)
        )
        if global_proxy_spend is None and prisma_client is not None:
            # get from db
            sql_query = (
                """SELECT SUM(spend) as total_spend FROM "MonthlyGlobalSpend";"""
            )

            response = await prisma_client.db.query_raw(query=sql_query)

            global_proxy_spend = response[0]["total_spend"]

            await user_api_key_cache.async_set_cache(
                key="{}:spend".format(llm_proxy_admin_name),
                value=global_proxy_spend,
            )
        if global_proxy_spend is not None:
            user_info = CallInfo(
                user_id=llm_proxy_admin_name,
                max_budget=llm.max_budget,
                spend=global_proxy_spend,
                token=token,
            )
            asyncio.create_task(
                proxy_logging_obj.budget_alerts(
                    type="proxy_budget",
                    user_info=user_info,
                )
            )
    return global_proxy_spend


def get_rbac_role(jwt_handler: JWTHandler, scopes: List[str]) -> str:
    is_admin = jwt_handler.is_admin(scopes=scopes)
    if is_admin:
        return LLMUserRoles.PROXY_ADMIN
    else:
        return LLMUserRoles.TEAM


def get_model_from_request(request_data: dict, route: str) -> Optional[str]:

    # First try to get model from request_data
    model = request_data.get("model")

    # If model not in request_data, try to extract from route
    if model is None:
        # Parse model from route that follows the pattern /openai/deployments/{model}/*
        match = re.match(r"/openai/deployments/([^/]+)", route)
        if match:
            model = match.group(1)

    return model


async def _user_api_key_auth_builder(  # noqa: PLR0915
    request: Request,
    api_key: str,
    azure_api_key_header: str,
    anthropic_api_key_header: Optional[str],
    google_ai_studio_api_key_header: Optional[str],
    azure_apim_header: Optional[str],
    request_data: dict,
) -> UserAPIKeyAuth:

    from llm.proxy.proxy_server import (
        general_settings,
        jwt_handler,
        llm_proxy_admin_name,
        llm_model_list,
        llm_router,
        master_key,
        model_max_budget_limiter,
        open_telemetry_logger,
        prisma_client,
        proxy_logging_obj,
        user_api_key_cache,
        user_custom_auth,
    )

    parent_otel_span: Optional[Span] = None
    start_time = datetime.now()
    route: str = get_request_route(request=request)
    valid_token: Optional[UserAPIKeyAuth] = None

    try:

        # get the request body

        await pre_db_read_auth_checks(
            request_data=request_data,
            request=request,
            route=route,
        )
        pass_through_endpoints: Optional[List[dict]] = general_settings.get(
            "pass_through_endpoints", None
        )
        passed_in_key: Optional[str] = None
        if isinstance(api_key, str):
            passed_in_key = api_key
            api_key = _get_bearer_token(api_key=api_key)
        elif isinstance(azure_api_key_header, str):
            api_key = azure_api_key_header
        elif isinstance(anthropic_api_key_header, str):
            api_key = anthropic_api_key_header
        elif isinstance(google_ai_studio_api_key_header, str):
            api_key = google_ai_studio_api_key_header
        elif isinstance(azure_apim_header, str):
            api_key = azure_apim_header
        elif pass_through_endpoints is not None:
            for endpoint in pass_through_endpoints:
                if endpoint.get("path", "") == route:
                    headers: Optional[dict] = endpoint.get("headers", None)
                    if headers is not None:
                        header_key: str = headers.get("llm_user_api_key", "")
                        if request.headers.get(key=header_key) is not None:
                            api_key = request.headers.get(key=header_key)

        # if user wants to pass LLM_Master_Key as a custom header, example pass llm keys as X-LLM-Key: Bearer sk-1234
        custom_llm_key_header_name = general_settings.get("llm_key_header_name")
        if custom_llm_key_header_name is not None:
            api_key = get_api_key_from_custom_header(
                request=request,
                custom_llm_key_header_name=custom_llm_key_header_name,
            )

        if open_telemetry_logger is not None:
            parent_otel_span = (
                open_telemetry_logger.create_llm_proxy_request_started_span(
                    start_time=start_time,
                    headers=dict(request.headers),
                )
            )

        ### USER-DEFINED AUTH FUNCTION ###
        if user_custom_auth is not None:
            response = await user_custom_auth(request=request, api_key=api_key)  # type: ignore
            return UserAPIKeyAuth.model_validate(response)

        ### LLM-DEFINED AUTH FUNCTION ###
        #### IF JWT ####
        """
        LLM supports using JWTs.

        Enable this in proxy config, by setting
        ```
        general_settings:
            enable_jwt_auth: true
        ```
        """

        ######## Route Checks Before Reading DB / Cache for "token" ################
        if (
            route in LLMRoutes.public_routes.value  # type: ignore
            or route_in_additonal_public_routes(current_route=route)
        ):
            # check if public endpoint
            return UserAPIKeyAuth(user_role=LLMUserRoles.INTERNAL_USER_VIEW_ONLY)
        elif is_pass_through_provider_route(route=route):
            if should_run_auth_on_pass_through_provider_route(route=route) is False:
                return UserAPIKeyAuth(
                    user_role=LLMUserRoles.INTERNAL_USER_VIEW_ONLY
                )

        ########## End of Route Checks Before Reading DB / Cache for "token" ########

        if general_settings.get("enable_oauth2_auth", False) is True:
            # return UserAPIKeyAuth object
            # helper to check if the api_key is a valid oauth2 token
            from llm.proxy.proxy_server import premium_user

            if premium_user is not True:
                raise ValueError(
                    "Oauth2 token validation is only available for premium users"
                    + CommonProxyErrors.not_premium_user.value
                )

            return await check_oauth2_token(token=api_key)

        if general_settings.get("enable_oauth2_proxy_auth", False) is True:
            return await handle_oauth2_proxy_request(request=request)

        if general_settings.get("enable_jwt_auth", False) is True:
            from llm.proxy.proxy_server import premium_user

            if premium_user is not True:
                raise ValueError(
                    f"JWT Auth is an enterprise only feature. {CommonProxyErrors.not_premium_user.value}"
                )
            is_jwt = jwt_handler.is_jwt(token=api_key)
            verbose_proxy_logger.debug("is_jwt: %s", is_jwt)
            if is_jwt:
                result = await JWTAuthManager.auth_builder(
                    request_data=request_data,
                    general_settings=general_settings,
                    api_key=api_key,
                    jwt_handler=jwt_handler,
                    route=route,
                    prisma_client=prisma_client,
                    user_api_key_cache=user_api_key_cache,
                    proxy_logging_obj=proxy_logging_obj,
                    parent_otel_span=parent_otel_span,
                )

                is_proxy_admin = result["is_proxy_admin"]
                team_id = result["team_id"]
                team_object = result["team_object"]
                user_id = result["user_id"]
                user_object = result["user_object"]
                end_user_id = result["end_user_id"]
                end_user_object = result["end_user_object"]
                org_id = result["org_id"]
                token = result["token"]

                global_proxy_spend = await get_global_proxy_spend(
                    llm_proxy_admin_name=llm_proxy_admin_name,
                    user_api_key_cache=user_api_key_cache,
                    prisma_client=prisma_client,
                    token=token,
                    proxy_logging_obj=proxy_logging_obj,
                )

                if is_proxy_admin:
                    return UserAPIKeyAuth(
                        user_role=LLMUserRoles.PROXY_ADMIN,
                        parent_otel_span=parent_otel_span,
                    )

                valid_token = UserAPIKeyAuth(
                    api_key=None,
                    team_id=team_id,
                    team_tpm_limit=(
                        team_object.tpm_limit if team_object is not None else None
                    ),
                    team_rpm_limit=(
                        team_object.rpm_limit if team_object is not None else None
                    ),
                    team_models=team_object.models if team_object is not None else [],
                    user_role=LLMUserRoles.INTERNAL_USER,
                    user_id=user_id,
                    org_id=org_id,
                    parent_otel_span=parent_otel_span,
                    end_user_id=end_user_id,
                )
                # run through common checks
                _ = await common_checks(
                    request=request,
                    request_body=request_data,
                    team_object=team_object,
                    user_object=user_object,
                    end_user_object=end_user_object,
                    general_settings=general_settings,
                    global_proxy_spend=global_proxy_spend,
                    route=route,
                    llm_router=llm_router,
                    proxy_logging_obj=proxy_logging_obj,
                    valid_token=valid_token,
                )

                # return UserAPIKeyAuth object
                return cast(UserAPIKeyAuth, valid_token)

        #### ELSE ####
        ## CHECK PASS-THROUGH ENDPOINTS ##
        is_mapped_pass_through_route: bool = False
        for mapped_route in LLMRoutes.mapped_pass_through_routes.value:  # type: ignore
            if route.startswith(mapped_route):
                is_mapped_pass_through_route = True
        if is_mapped_pass_through_route:
            if request.headers.get("llm_user_api_key") is not None:
                api_key = request.headers.get("llm_user_api_key") or ""
        if pass_through_endpoints is not None:
            for endpoint in pass_through_endpoints:
                if isinstance(endpoint, dict) and endpoint.get("path", "") == route:
                    ## IF AUTH DISABLED
                    if endpoint.get("auth") is not True:
                        return UserAPIKeyAuth()
                    ## IF AUTH ENABLED
                    ### IF CUSTOM PARSER REQUIRED
                    if (
                        endpoint.get("custom_auth_parser") is not None
                        and endpoint.get("custom_auth_parser") == "langfuse"
                    ):
                        """
                        - langfuse returns {'Authorization': 'Basic YW55dGhpbmc6YW55dGhpbmc'}
                        - check the langfuse public key if it contains the LLM API key
                        """
                        import base64

                        api_key = api_key.replace("Basic ", "").strip()
                        decoded_bytes = base64.b64decode(api_key)
                        decoded_str = decoded_bytes.decode("utf-8")
                        api_key = decoded_str.split(":")[0]
                    else:
                        headers = endpoint.get("headers", None)
                        if headers is not None:
                            header_key = headers.get("llm_user_api_key", "")
                            if (
                                isinstance(request.headers, dict)
                                and request.headers.get(key=header_key) is not None  # type: ignore
                            ):
                                api_key = request.headers.get(key=header_key)  # type: ignore
        if master_key is None:
            if isinstance(api_key, str):
                return UserAPIKeyAuth(
                    api_key=api_key,
                    user_role=LLMUserRoles.PROXY_ADMIN,
                    parent_otel_span=parent_otel_span,
                )
            else:
                return UserAPIKeyAuth(
                    user_role=LLMUserRoles.PROXY_ADMIN,
                    parent_otel_span=parent_otel_span,
                )
        elif api_key is None:  # only require API key if master key is set
            raise Exception("No API key passed in.")
        elif api_key == "":
            # missing 'Bearer ' prefix
            raise Exception(
                f"Malformed API Key passed in. Ensure Key has `Bearer ` prefix. Passed in: {passed_in_key}"
            )

        if route == "/user/auth":
            if general_settings.get("allow_user_auth", False) is True:
                return UserAPIKeyAuth()
            else:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="'allow_user_auth' not set or set to False",
                )

        ## Check END-USER OBJECT
        _end_user_object = None
        end_user_params = {}

        end_user_id = get_end_user_id_from_request_body(request_data)
        if end_user_id:
            try:
                end_user_params["end_user_id"] = end_user_id

                # get end-user object
                _end_user_object = await get_end_user_object(
                    end_user_id=end_user_id,
                    prisma_client=prisma_client,
                    user_api_key_cache=user_api_key_cache,
                    parent_otel_span=parent_otel_span,
                    proxy_logging_obj=proxy_logging_obj,
                )
                if _end_user_object is not None:
                    end_user_params["allowed_model_region"] = (
                        _end_user_object.allowed_model_region
                    )
                    if _end_user_object.llm_budget_table is not None:
                        budget_info = _end_user_object.llm_budget_table
                        if budget_info.tpm_limit is not None:
                            end_user_params["end_user_tpm_limit"] = (
                                budget_info.tpm_limit
                            )
                        if budget_info.rpm_limit is not None:
                            end_user_params["end_user_rpm_limit"] = (
                                budget_info.rpm_limit
                            )
                        if budget_info.max_budget is not None:
                            end_user_params["end_user_max_budget"] = (
                                budget_info.max_budget
                            )
            except Exception as e:
                if isinstance(e, llm.BudgetExceededError):
                    raise e
                verbose_proxy_logger.debug(
                    "Unable to find user in db. Error - {}".format(str(e))
                )
                pass

        ### CHECK IF ADMIN ###
        # note: never string compare API keys, this is vulenerable to a time attack. Use secrets.compare_digest instead
        ### CHECK IF ADMIN ###
        # note: never string compare API keys, this is vulenerable to a time attack. Use secrets.compare_digest instead
        ## Check CACHE
        try:
            valid_token = await get_key_object(
                hashed_token=hash_token(api_key),
                prisma_client=prisma_client,
                user_api_key_cache=user_api_key_cache,
                parent_otel_span=parent_otel_span,
                proxy_logging_obj=proxy_logging_obj,
                check_cache_only=True,
            )
        except Exception:
            verbose_logger.debug("API key not found in cache.")
            valid_token = None

        if (
            valid_token is not None
            and isinstance(valid_token, UserAPIKeyAuth)
            and valid_token.user_role == LLMUserRoles.PROXY_ADMIN
        ):
            # update end-user params on valid token
            valid_token = update_valid_token_with_end_user_params(
                valid_token=valid_token, end_user_params=end_user_params
            )
            valid_token.parent_otel_span = parent_otel_span

            return valid_token

        if (
            valid_token is not None
            and isinstance(valid_token, UserAPIKeyAuth)
            and valid_token.team_id is not None
        ):
            ## UPDATE TEAM VALUES BASED ON CACHED TEAM OBJECT - allows `/team/update` values to work for cached token
            try:
                team_obj: LLM_TeamTableCachedObj = await get_team_object(
                    team_id=valid_token.team_id,
                    prisma_client=prisma_client,
                    user_api_key_cache=user_api_key_cache,
                    parent_otel_span=parent_otel_span,
                    proxy_logging_obj=proxy_logging_obj,
                    check_cache_only=True,
                )

                if (
                    team_obj.last_refreshed_at is not None
                    and valid_token.last_refreshed_at is not None
                    and team_obj.last_refreshed_at > valid_token.last_refreshed_at
                ):
                    team_obj_dict = team_obj.__dict__

                    for k, v in team_obj_dict.items():
                        field_name = f"team_{k}"
                        if field_name in valid_token.__fields__:
                            setattr(valid_token, field_name, v)
            except Exception as e:
                verbose_logger.debug(
                    e
                )  # moving from .warning to .debug as it spams logs when team missing from cache.

        try:
            is_master_key_valid = secrets.compare_digest(api_key, master_key)  # type: ignore
        except Exception:
            is_master_key_valid = False

        ## VALIDATE MASTER KEY ##
        try:
            assert isinstance(master_key, str)
        except Exception:
            raise HTTPException(
                status_code=500,
                detail={
                    "Master key must be a valid string. Current type={}".format(
                        type(master_key)
                    )
                },
            )

        if is_master_key_valid:
            _user_api_key_obj = await _return_user_api_key_auth_obj(
                user_obj=None,
                user_role=LLMUserRoles.PROXY_ADMIN,
                api_key=master_key,
                parent_otel_span=parent_otel_span,
                valid_token_dict={
                    **end_user_params,
                    "user_id": llm_proxy_admin_name,
                },
                route=route,
                start_time=start_time,
            )
            asyncio.create_task(
                _cache_key_object(
                    hashed_token=hash_token(master_key),
                    user_api_key_obj=_user_api_key_obj,
                    user_api_key_cache=user_api_key_cache,
                    proxy_logging_obj=proxy_logging_obj,
                )
            )

            _user_api_key_obj = update_valid_token_with_end_user_params(
                valid_token=_user_api_key_obj, end_user_params=end_user_params
            )

            return _user_api_key_obj

        ## IF it's not a master key
        ## Route should not be in master_key_only_routes
        if route in LLMRoutes.master_key_only_routes.value:  # type: ignore
            raise Exception(
                f"Tried to access route={route}, which is only for MASTER KEY"
            )

        ## Check DB
        if isinstance(
            api_key, str
        ):  # if generated token, make sure it starts with sk-.
            assert api_key.startswith(
                "sk-"
            ), "LLM Virtual Key expected. Received={}, expected to start with 'sk-'.".format(
                api_key
            )  # prevent token hashes from being used
        else:
            verbose_logger.warning(
                "llm.proxy.proxy_server.user_api_key_auth(): Warning - Key={} is not a string.".format(
                    api_key
                )
            )

        if (
            prisma_client is None
        ):  # if both master key + user key submitted, and user key != master key, and no db connected, raise an error
            return await _handle_failed_db_connection_for_get_key_object(
                e=Exception("No connected db.")
            )

        ## check for cache hit (In-Memory Cache)
        _user_role = None
        if api_key.startswith("sk-"):
            api_key = hash_token(token=api_key)

        if valid_token is None:
            try:
                valid_token = await get_key_object(
                    hashed_token=api_key,
                    prisma_client=prisma_client,
                    user_api_key_cache=user_api_key_cache,
                    parent_otel_span=parent_otel_span,
                    proxy_logging_obj=proxy_logging_obj,
                )
                # update end-user params on valid token
                # These can change per request - it's important to update them here
                valid_token.end_user_id = end_user_params.get("end_user_id")
                valid_token.end_user_tpm_limit = end_user_params.get(
                    "end_user_tpm_limit"
                )
                valid_token.end_user_rpm_limit = end_user_params.get(
                    "end_user_rpm_limit"
                )
                valid_token.allowed_model_region = end_user_params.get(
                    "allowed_model_region"
                )
                # update key budget with temp budget increase
                valid_token = _update_key_budget_with_temp_budget_increase(
                    valid_token
                )  # updating it here, allows all downstream reporting / checks to use the updated budget
            except Exception:
                verbose_logger.info(
                    "llm.proxy.auth.user_api_key_auth.py::user_api_key_auth() - Unable to find token={} in cache or `LLM_VerificationTokenTable`. Defaulting 'valid_token' to None'".format(
                        api_key
                    )
                )
                valid_token = None

        if valid_token is None:
            raise Exception(
                "Invalid proxy server token passed. Received API Key (hashed)={}. Unable to find token in cache or `LLM_VerificationTokenTable`".format(
                    api_key
                )
            )

        user_obj: Optional[LLM_UserTable] = None
        valid_token_dict: dict = {}
        if valid_token is not None:
            # Got Valid Token from Cache, DB
            # Run checks for
            # 1. If token can call model
            ## 1a. If token can call fallback models (if client-side fallbacks given)
            # 2. If user_id for this token is in budget
            # 3. If the user spend within their own team is within budget
            # 4. If 'user' passed to /chat/completions, /embeddings endpoint is in budget
            # 5. If token is expired
            # 6. If token spend is under Budget for the token
            # 7. If token spend per model is under budget per model
            # 8. If token spend is under team budget
            # 9. If team spend is under team budget

            ## base case ## key is disabled
            if valid_token.blocked is True:
                raise Exception(
                    "Key is blocked. Update via `/key/unblock` if you're admin."
                )
            config = valid_token.config

            if config != {}:
                model_list = config.get("model_list", [])
                new_model_list = model_list
                verbose_proxy_logger.debug(
                    f"\n new llm router model list {new_model_list}"
                )
            elif (
                isinstance(valid_token.models, list)
                and "all-team-models" in valid_token.models
            ):
                # Do not do any validation at this step
                # the validation will occur when checking the team has access to this model
                pass
            else:
                model = get_model_from_request(request_data, route)
                fallback_models = cast(
                    Optional[List[ALL_FALLBACK_MODEL_VALUES]],
                    request_data.get("fallbacks", None),
                )

                if model is not None:
                    await can_key_call_model(
                        model=model,
                        llm_model_list=llm_model_list,
                        valid_token=valid_token,
                        llm_router=llm_router,
                    )

                if fallback_models is not None:
                    for m in fallback_models:
                        await can_key_call_model(
                            model=m["model"] if isinstance(m, dict) else m,
                            llm_model_list=llm_model_list,
                            valid_token=valid_token,
                            llm_router=llm_router,
                        )
                        await is_valid_fallback_model(
                            model=m["model"] if isinstance(m, dict) else m,
                            llm_router=llm_router,
                            user_model=None,
                        )

            # Check 2. If user_id for this token is in budget - done in common_checks()
            if valid_token.user_id is not None:
                try:
                    user_obj = await get_user_object(
                        user_id=valid_token.user_id,
                        prisma_client=prisma_client,
                        user_api_key_cache=user_api_key_cache,
                        user_id_upsert=False,
                        parent_otel_span=parent_otel_span,
                        proxy_logging_obj=proxy_logging_obj,
                    )
                except Exception as e:
                    verbose_logger.debug(
                        "llm.proxy.auth.user_api_key_auth.py::user_api_key_auth() - Unable to get user from db/cache. Setting user_obj to None. Exception received - {}".format(
                            str(e)
                        )
                    )
                    user_obj = None

            # Check 3. Check if user is in their team budget
            if valid_token.team_member_spend is not None:
                if prisma_client is not None:

                    _cache_key = f"{valid_token.team_id}_{valid_token.user_id}"

                    team_member_info = await user_api_key_cache.async_get_cache(
                        key=_cache_key
                    )
                    if team_member_info is None:
                        # read from DB
                        _user_id = valid_token.user_id
                        _team_id = valid_token.team_id

                        if _user_id is not None and _team_id is not None:
                            team_member_info = await prisma_client.db.llm_teammembership.find_first(
                                where={
                                    "user_id": _user_id,
                                    "team_id": _team_id,
                                },  # type: ignore
                                include={"llm_budget_table": True},
                            )
                            await user_api_key_cache.async_set_cache(
                                key=_cache_key,
                                value=team_member_info,
                            )

                    if (
                        team_member_info is not None
                        and team_member_info.llm_budget_table is not None
                    ):
                        team_member_budget = (
                            team_member_info.llm_budget_table.max_budget
                        )
                        if team_member_budget is not None and team_member_budget > 0:
                            if valid_token.team_member_spend > team_member_budget:
                                raise llm.BudgetExceededError(
                                    current_cost=valid_token.team_member_spend,
                                    max_budget=team_member_budget,
                                )

            # Check 3. If token is expired
            if valid_token.expires is not None:
                current_time = datetime.now(timezone.utc)
                if isinstance(valid_token.expires, datetime):
                    expiry_time = valid_token.expires
                else:
                    expiry_time = datetime.fromisoformat(valid_token.expires)
                if (
                    expiry_time.tzinfo is None
                    or expiry_time.tzinfo.utcoffset(expiry_time) is None
                ):
                    expiry_time = expiry_time.replace(tzinfo=timezone.utc)
                verbose_proxy_logger.debug(
                    f"Checking if token expired, expiry time {expiry_time} and current time {current_time}"
                )
                if expiry_time < current_time:
                    # Token exists but is expired.
                    raise ProxyException(
                        message=f"Authentication Error - Expired Key. Key Expiry time {expiry_time} and current time {current_time}",
                        type=ProxyErrorTypes.expired_key,
                        code=400,
                        param=api_key,
                    )

            # Check 4. Token Spend is under budget
            await _virtual_key_max_budget_check(
                valid_token=valid_token,
                proxy_logging_obj=proxy_logging_obj,
                user_obj=user_obj,
            )

            # Check 5. Soft Budget Check
            await _virtual_key_soft_budget_check(
                valid_token=valid_token,
                proxy_logging_obj=proxy_logging_obj,
            )

            # Check 5. Token Model Spend is under Model budget
            max_budget_per_model = valid_token.model_max_budget
            current_model = request_data.get("model", None)

            if (
                max_budget_per_model is not None
                and isinstance(max_budget_per_model, dict)
                and len(max_budget_per_model) > 0
                and prisma_client is not None
                and current_model is not None
                and valid_token.token is not None
            ):
                ## GET THE SPEND FOR THIS MODEL
                await model_max_budget_limiter.is_key_within_model_budget(
                    user_api_key_dict=valid_token,
                    model=current_model,
                )

            # Check 6: Additional Common Checks across jwt + key auth
            if valid_token.team_id is not None:
                _team_obj: Optional[LLM_TeamTable] = LLM_TeamTable(
                    team_id=valid_token.team_id,
                    max_budget=valid_token.team_max_budget,
                    spend=valid_token.team_spend,
                    tpm_limit=valid_token.team_tpm_limit,
                    rpm_limit=valid_token.team_rpm_limit,
                    blocked=valid_token.team_blocked,
                    models=valid_token.team_models,
                    metadata=valid_token.team_metadata,
                )
            else:
                _team_obj = None

            # Check 7: Check if key is a service account key
            await service_account_checks(
                valid_token=valid_token,
                request_data=request_data,
            )

            user_api_key_cache.set_cache(
                key=valid_token.team_id, value=_team_obj
            )  # save team table in cache - used for tpm/rpm limiting - tpm_rpm_limiter.py

            global_proxy_spend = None
            if (
                llm.max_budget > 0 and prisma_client is not None
            ):  # user set proxy max budget
                # check cache
                global_proxy_spend = await user_api_key_cache.async_get_cache(
                    key="{}:spend".format(llm_proxy_admin_name)
                )
                if global_proxy_spend is None:
                    # get from db
                    sql_query = """SELECT SUM(spend) as total_spend FROM "MonthlyGlobalSpend";"""

                    response = await prisma_client.db.query_raw(query=sql_query)

                    global_proxy_spend = response[0]["total_spend"]
                    await user_api_key_cache.async_set_cache(
                        key="{}:spend".format(llm_proxy_admin_name),
                        value=global_proxy_spend,
                    )

                if global_proxy_spend is not None:
                    call_info = CallInfo(
                        token=valid_token.token,
                        spend=global_proxy_spend,
                        max_budget=llm.max_budget,
                        user_id=llm_proxy_admin_name,
                        team_id=valid_token.team_id,
                    )
                    asyncio.create_task(
                        proxy_logging_obj.budget_alerts(
                            type="proxy_budget",
                            user_info=call_info,
                        )
                    )
            _ = await common_checks(
                request=request,
                request_body=request_data,
                team_object=_team_obj,
                user_object=user_obj,
                end_user_object=_end_user_object,
                general_settings=general_settings,
                global_proxy_spend=global_proxy_spend,
                route=route,
                llm_router=llm_router,
                proxy_logging_obj=proxy_logging_obj,
                valid_token=valid_token,
            )
            # Token passed all checks
            if valid_token is None:
                raise HTTPException(401, detail="Invalid API key")
            if valid_token.token is None:
                raise HTTPException(401, detail="Invalid API key, no token associated")
            api_key = valid_token.token

            # Add hashed token to cache
            asyncio.create_task(
                _cache_key_object(
                    hashed_token=api_key,
                    user_api_key_obj=valid_token,
                    user_api_key_cache=user_api_key_cache,
                    proxy_logging_obj=proxy_logging_obj,
                )
            )

            valid_token_dict = valid_token.model_dump(exclude_none=True)
            valid_token_dict.pop("token", None)

            if _end_user_object is not None:
                valid_token_dict.update(end_user_params)

        # check if token is from llm-ui, llm ui makes keys to allow users to login with sso. These keys can only be used for LLM UI functions
        # sso/login, ui/login, /key functions and /user functions
        # this will never be allowed to call /chat/completions

        if valid_token is None:
            # No token was found when looking up in the DB
            raise Exception("Invalid proxy server token passed")
        if valid_token_dict is not None:
            return await _return_user_api_key_auth_obj(
                user_obj=user_obj,
                api_key=api_key,
                parent_otel_span=parent_otel_span,
                valid_token_dict=valid_token_dict,
                route=route,
                start_time=start_time,
            )
        else:
            raise Exception()
    except Exception as e:
        requester_ip = _get_request_ip_address(
            request=request,
            use_x_forwarded_for=general_settings.get("use_x_forwarded_for", False),
        )
        verbose_proxy_logger.exception(
            "llm.proxy.proxy_server.user_api_key_auth(): Exception occured - {}\nRequester IP Address:{}".format(
                str(e),
                requester_ip,
            ),
            extra={"requester_ip": requester_ip},
        )

        # Log this exception to OTEL, Datadog etc
        user_api_key_dict = UserAPIKeyAuth(
            parent_otel_span=parent_otel_span,
            api_key=api_key,
        )
        asyncio.create_task(
            proxy_logging_obj.post_call_failure_hook(
                request_data=request_data,
                original_exception=e,
                user_api_key_dict=user_api_key_dict,
                error_type=ProxyErrorTypes.auth_error,
                route=route,
            )
        )

        if isinstance(e, llm.BudgetExceededError):
            raise ProxyException(
                message=e.message,
                type=ProxyErrorTypes.budget_exceeded,
                param=None,
                code=400,
            )
        if isinstance(e, HTTPException):
            raise ProxyException(
                message=getattr(e, "detail", f"Authentication Error({str(e)})"),
                type=ProxyErrorTypes.auth_error,
                param=getattr(e, "param", "None"),
                code=getattr(e, "status_code", status.HTTP_401_UNAUTHORIZED),
            )
        elif isinstance(e, ProxyException):
            raise e
        raise ProxyException(
            message="Authentication Error, " + str(e),
            type=ProxyErrorTypes.auth_error,
            param=getattr(e, "param", "None"),
            code=status.HTTP_401_UNAUTHORIZED,
        )


@tracer.wrap()
async def user_api_key_auth(
    request: Request,
    api_key: str = fastapi.Security(api_key_header),
    azure_api_key_header: str = fastapi.Security(azure_api_key_header),
    anthropic_api_key_header: Optional[str] = fastapi.Security(
        anthropic_api_key_header
    ),
    google_ai_studio_api_key_header: Optional[str] = fastapi.Security(
        google_ai_studio_api_key_header
    ),
    azure_apim_header: Optional[str] = fastapi.Security(azure_apim_header),
) -> UserAPIKeyAuth:
    """
    Parent function to authenticate user API key / JWT token.
    """

    request_data = await _read_request_body(request=request)

    user_api_key_auth_obj = await _user_api_key_auth_builder(
        request=request,
        api_key=api_key,
        azure_api_key_header=azure_api_key_header,
        anthropic_api_key_header=anthropic_api_key_header,
        google_ai_studio_api_key_header=google_ai_studio_api_key_header,
        azure_apim_header=azure_apim_header,
        request_data=request_data,
    )

    end_user_id = get_end_user_id_from_request_body(request_data)
    if end_user_id is not None:
        user_api_key_auth_obj.end_user_id = end_user_id

    return user_api_key_auth_obj


async def _return_user_api_key_auth_obj(
    user_obj: Optional[LLM_UserTable],
    api_key: str,
    parent_otel_span: Optional[Span],
    valid_token_dict: dict,
    route: str,
    start_time: datetime,
    user_role: Optional[LLMUserRoles] = None,
) -> UserAPIKeyAuth:
    end_time = datetime.now()

    asyncio.create_task(
        user_api_key_service_logger_obj.async_service_success_hook(
            service=ServiceTypes.AUTH,
            call_type=route,
            start_time=start_time,
            end_time=end_time,
            duration=end_time.timestamp() - start_time.timestamp(),
            parent_otel_span=parent_otel_span,
        )
    )

    retrieved_user_role = (
        user_role or _get_user_role(user_obj=user_obj) or LLMUserRoles.INTERNAL_USER
    )

    user_api_key_kwargs = {
        "api_key": api_key,
        "parent_otel_span": parent_otel_span,
        "user_role": retrieved_user_role,
        **valid_token_dict,
    }
    if user_obj is not None:
        user_api_key_kwargs.update(
            user_tpm_limit=user_obj.tpm_limit,
            user_rpm_limit=user_obj.rpm_limit,
            user_email=user_obj.user_email,
        )
    if user_obj is not None and _is_user_proxy_admin(user_obj=user_obj):
        user_api_key_kwargs.update(
            user_role=LLMUserRoles.PROXY_ADMIN,
        )
        return UserAPIKeyAuth(**user_api_key_kwargs)
    else:
        return UserAPIKeyAuth(**user_api_key_kwargs)


def get_api_key_from_custom_header(
    request: Request, custom_llm_key_header_name: str
) -> str:
    """
    Get API key from custom header

    Args:
        request (Request): Request object
        custom_llm_key_header_name (str): Custom header name

    Returns:
        Optional[str]: API key
    """
    api_key: str = ""
    # use this as the virtual key passed to llm proxy
    custom_llm_key_header_name = custom_llm_key_header_name.lower()
    _headers = {k.lower(): v for k, v in request.headers.items()}
    verbose_proxy_logger.debug(
        "searching for custom_llm_key_header_name= %s, in headers=%s",
        custom_llm_key_header_name,
        _headers,
    )
    custom_api_key = _headers.get(custom_llm_key_header_name)
    if custom_api_key:
        api_key = _get_bearer_token(api_key=custom_api_key)
        verbose_proxy_logger.debug(
            "Found custom API key using header: {}, setting api_key={}".format(
                custom_llm_key_header_name, api_key
            )
        )
    else:
        verbose_proxy_logger.exception(
            f"No LLM Virtual Key pass. Please set header={custom_llm_key_header_name}: Bearer <api_key>"
        )
    return api_key


def _get_temp_budget_increase(valid_token: UserAPIKeyAuth):
    valid_token_metadata = valid_token.metadata
    if (
        "temp_budget_increase" in valid_token_metadata
        and "temp_budget_expiry" in valid_token_metadata
    ):
        expiry = datetime.fromisoformat(valid_token_metadata["temp_budget_expiry"])
        if expiry > datetime.now():
            return valid_token_metadata["temp_budget_increase"]
    return None


def _update_key_budget_with_temp_budget_increase(
    valid_token: UserAPIKeyAuth,
) -> UserAPIKeyAuth:
    if valid_token.max_budget is None:
        return valid_token
    temp_budget_increase = _get_temp_budget_increase(valid_token) or 0.0
    valid_token.max_budget = valid_token.max_budget + temp_budget_increase
    return valid_token
