import asyncio
import copy
import inspect
import io
import os
import random
import secrets
import subprocess
import sys
import time
import traceback
import uuid
import warnings
from datetime import datetime, timedelta
from typing import (
    TYPE_CHECKING,
    Any,
    List,
    Optional,
    Tuple,
    cast,
    get_args,
    get_origin,
    get_type_hints,
)

from llm.types.utils import (
    ModelResponse,
    ModelResponseStream,
    TextCompletionResponse,
)

if TYPE_CHECKING:
    from opentelemetry.trace import Span as _Span

    from llm.integrations.opentelemetry import OpenTelemetry

    Span = _Span
else:
    Span = Any
    OpenTelemetry = Any


def showwarning(message, category, filename, lineno, file=None, line=None):
    traceback_info = f"{filename}:{lineno}: {category.__name__}: {message}\n"
    if file is not None:
        file.write(traceback_info)


warnings.showwarning = showwarning
warnings.filterwarnings("default", category=UserWarning)

# Your client code here


messages: list = []
sys.path.insert(
    0, os.path.abspath("../..")
)  # Adds the parent directory to the system path - for llm local dev

try:
    import logging

    import backoff
    import fastapi
    import orjson
    import yaml  # type: ignore
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
except ImportError as e:
    raise ImportError(f"Missing dependency {e}. Run `pip install 'llm[proxy]'`")

from collections import defaultdict
from contextlib import asynccontextmanager

import llm
from llm import Router
from llm._logging import verbose_proxy_logger, verbose_router_logger
from llm.caching.caching import DualCache, RedisCache
from llm.constants import LLM_PROXY_ADMIN_NAME
from llm.exceptions import RejectedRequestError
from llm.integrations.SlackAlerting.slack_alerting import SlackAlerting
from llm.llm_core_utils.core_helpers import (
    _get_parent_otel_span_from_kwargs,
    get_llm_metadata_from_kwargs,
)
from llm.llm_core_utils.credential_accessor import CredentialAccessor
from llm.llm_core_utils.llm_logging import Logging as LLMLoggingObj
from llm.llms.custom_httpx.http_handler import AsyncHTTPHandler, HTTPHandler
from llm.proxy._experimental.mcp_server.server import router as mcp_router
from llm.proxy._experimental.mcp_server.admin_routes import router as mcp_admin_router, public_router as mcp_public_router
# Removed admin_ui_routes import to use Next.js UI instead
from llm.proxy._experimental.mcp_server.openai_agents_integration import router as mcp_openai_agents_router
from llm.proxy._experimental.mcp_server.tool_registry import (
    global_mcp_tool_registry,
)
from llm.proxy._experimental.mcp_server.config_mapping import load_mcp_server_configs_on_startup
from llm.proxy._types import *
from llm.proxy.analytics_endpoints.analytics_endpoints import (
    router as analytics_router,
)
from llm.proxy.anthropic_endpoints.endpoints import router as anthropic_router
from llm.proxy.auth.auth_checks import get_team_object, log_db_metrics
from llm.proxy.auth.auth_utils import check_response_size_is_safe
from llm.proxy.auth.handle_jwt import JWTHandler
from llm.proxy.auth.llm_license import LicenseCheck
from llm.proxy.auth.model_checks import (
    get_complete_model_list,
    get_key_models,
    get_team_models,
)
from llm.proxy.auth.user_api_key_auth import (
    user_api_key_auth,
    user_api_key_auth_websocket,
)
from llm.proxy.batches_endpoints.endpoints import router as batches_router

## Import All Misc routes here ##
from llm.proxy.caching_routes import router as caching_router
from llm.proxy.common_request_processing import ProxyBaseLLMRequestProcessing
from llm.proxy.common_utils.admin_ui_utils import html_form
from llm.proxy.common_utils.callback_utils import initialize_callbacks_on_proxy
from llm.proxy.common_utils.debug_utils import init_verbose_loggers
from llm.proxy.common_utils.debug_utils import router as debugging_endpoints_router
from llm.proxy.common_utils.encrypt_decrypt_utils import (
    decrypt_value_helper,
    encrypt_value_helper,
)
from llm.proxy.common_utils.http_parsing_utils import (
    _read_request_body,
    check_file_size_under_limit,
)
from llm.proxy.common_utils.load_config_utils import (
    get_config_file_contents_from_gcs,
    get_file_contents_from_s3,
)
from llm.proxy.common_utils.openai_endpoint_utils import (
    remove_sensitive_info_from_deployment,
)
from llm.proxy.common_utils.proxy_state import ProxyState
from llm.proxy.common_utils.reset_budget_job import ResetBudgetJob
from llm.proxy.common_utils.swagger_utils import ERROR_RESPONSES
from llm.proxy.credential_endpoints.endpoints import router as credential_router
from llm.proxy.fine_tuning_endpoints.endpoints import router as fine_tuning_router
from llm.proxy.fine_tuning_endpoints.endpoints import set_fine_tuning_config
from llm.proxy.guardrails.guardrail_endpoints import router as guardrails_router
from llm.proxy.guardrails.init_guardrails import (
    init_guardrails_v2,
    initialize_guardrails,
)
from llm.proxy.health_check import perform_health_check
from llm.proxy.health_endpoints._health_endpoints import router as health_router
from llm.proxy.hooks.model_max_budget_limiter import (
    _PROXY_VirtualKeyModelMaxBudgetLimiter,
)
from llm.proxy.hooks.prompt_injection_detection import (
    _OPTIONAL_PromptInjectionDetection,
)
from llm.proxy.hooks.proxy_track_cost_callback import _ProxyDBLogger
from llm.proxy.llm_pre_call_utils import add_llm_data_to_request
from llm.proxy.management_endpoints.budget_management_endpoints import (
    router as budget_management_router,
)
from llm.proxy.management_endpoints.customer_endpoints import (
    router as customer_router,
)
from llm.proxy.management_endpoints.internal_user_endpoints import (
    router as internal_user_router,
)
from llm.proxy.management_endpoints.internal_user_endpoints import user_update
from llm.proxy.management_endpoints.key_management_endpoints import (
    delete_verification_tokens,
    duration_in_seconds,
    generate_key_helper_fn,
)
from llm.proxy.management_endpoints.key_management_endpoints import (
    router as key_management_router,
)
from llm.proxy.management_endpoints.model_management_endpoints import (
    _add_model_to_db,
    _add_team_model_to_db,
    check_if_team_id_matches_key,
)
from llm.proxy.management_endpoints.model_management_endpoints import (
    router as model_management_router,
)
from llm.proxy.management_endpoints.organization_endpoints import (
    router as organization_router,
)
from llm.proxy.management_endpoints.team_callback_endpoints import (
    router as team_callback_router,
)
from llm.proxy.management_endpoints.team_endpoints import router as team_router
from llm.proxy.management_endpoints.team_endpoints import (
    update_team,
    validate_membership,
)
from llm.proxy.management_endpoints.ui_sso import (
    get_disabled_non_admin_personal_key_creation,
)
from llm.proxy.management_endpoints.ui_sso import router as ui_sso_router
from llm.proxy.management_helpers.audit_logs import create_audit_log_for_update
from llm.proxy.openai_files_endpoints.files_endpoints import (
    router as openai_files_router,
)
from llm.proxy.openai_files_endpoints.files_endpoints import set_files_config
from llm.proxy.pass_through_endpoints.llm_passthrough_endpoints import (
    passthrough_endpoint_router,
)
from llm.proxy.pass_through_endpoints.llm_passthrough_endpoints import (
    router as llm_passthrough_router,
)
from llm.proxy.pass_through_endpoints.pass_through_endpoints import (
    initialize_pass_through_endpoints,
)
from llm.proxy.pass_through_endpoints.pass_through_endpoints import (
    router as pass_through_router,
)
from llm.proxy.rerank_endpoints.endpoints import router as rerank_router
from llm.proxy.response_api_endpoints.endpoints import router as response_router
from llm.proxy.route_llm_request import route_request
from llm.proxy.spend_tracking.spend_management_endpoints import (
    router as spend_management_router,
)
from llm.proxy.spend_tracking.spend_tracking_utils import get_logging_payload
from llm.proxy.types_utils.utils import get_instance_fn
from llm.proxy.ui_crud_endpoints.proxy_setting_endpoints import (
    router as ui_crud_endpoints_router,
)
from llm.proxy.utils import (
    PrismaClient,
    ProxyLogging,
    ProxyUpdateSpend,
    _cache_user_row,
    _get_docs_url,
    _get_projected_spend_over_limit,
    _get_redoc_url,
    _is_projected_spend_over_limit,
    _is_valid_team_configs,
    get_error_message_str,
    hash_token,
    update_spend,
)
from llm.proxy.vertex_ai_endpoints.langfuse_endpoints import (
    router as langfuse_router,
)
from llm.router import (
    AssistantsTypedDict,
    Deployment,
    LLM_Params,
    ModelGroupInfo,
)
from llm.scheduler import DefaultPriorities, FlowItem, Scheduler
from llm.secret_managers.aws_secret_manager import load_aws_kms
from llm.secret_managers.google_kms import load_google_kms
from llm.secret_managers.main import (
    get_secret,
    get_secret_bool,
    get_secret_str,
    str_to_bool,
)
from llm.types.integrations.slack_alerting import SlackAlertingArgs
from llm.types.llms.anthropic import (
    AnthropicMessagesRequest,
    AnthropicResponse,
    AnthropicResponseContentBlockText,
    AnthropicResponseUsageBlock,
)
from llm.types.llms.openai import HttpxBinaryResponseContent
from llm.types.router import DeploymentTypedDict
from llm.types.router import ModelInfo as RouterModelInfo
from llm.types.router import RouterGeneralSettings, updateDeployment
from llm.types.utils import CredentialItem, CustomHuggingfaceTokenizer
from llm.types.utils import ModelInfo as ModelMapInfo
from llm.types.utils import RawRequestTypedDict, StandardLoggingPayload
from llm.utils import _add_custom_logger_callback_to_specific_event

try:
    from llm._version import version
except Exception:
    version = "0.0.0"
llm.suppress_debug_info = True
import json
from typing import Union

from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    Header,
    HTTPException,
    Path,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import (
    FileResponse,
    JSONResponse,
    ORJSONResponse,
    RedirectResponse,
    StreamingResponse,
)
from fastapi.routing import APIRouter
from fastapi.security import OAuth2PasswordBearer
from fastapi.security.api_key import APIKeyHeader
from fastapi.staticfiles import StaticFiles

# import enterprise folder
try:
    # when using llm cli
    import llm.proxy.enterprise as enterprise
except Exception:
    # when using llm docker image
    try:
        import enterprise  # type: ignore
    except Exception:
        pass

server_root_path = os.getenv("SERVER_ROOT_PATH", "")
_license_check = LicenseCheck()
premium_user: bool = _license_check.is_premium()
global_max_parallel_request_retries_env: Optional[str] = os.getenv(
    "LLM_GLOBAL_MAX_PARALLEL_REQUEST_RETRIES"
)
proxy_state = ProxyState()
if global_max_parallel_request_retries_env is None:
    global_max_parallel_request_retries: int = 3
else:
    global_max_parallel_request_retries = int(global_max_parallel_request_retries_env)

global_max_parallel_request_retry_timeout_env: Optional[str] = os.getenv(
    "LLM_GLOBAL_MAX_PARALLEL_REQUEST_RETRY_TIMEOUT"
)
if global_max_parallel_request_retry_timeout_env is None:
    global_max_parallel_request_retry_timeout: float = 60.0
else:
    global_max_parallel_request_retry_timeout = float(
        global_max_parallel_request_retry_timeout_env
    )

ui_link = "https://cloud.hanzo.ai"
ui_message = ""  # Removed the console and models links

custom_swagger_message = ""  # Removed the docs link

### CUSTOM BRANDING [ENTERPRISE FEATURE] ###
_title = os.getenv("DOCS_TITLE", "Hanzo API") if premium_user else "Hanzo API"
_description = (
    os.getenv(
        "DOCS_DESCRIPTION",
        f"Enterprise Edition \n\nAPI documentation for Hanzo",
    )
    if premium_user
    else f"API documentation for Hanzo"
)


def cleanup_router_config_variables():
    global master_key, user_config_file_path, otel_logging, user_custom_auth, user_custom_auth_path, user_custom_key_generate, user_custom_sso, use_background_health_checks, health_check_interval, prisma_client

    # Set all variables to None
    master_key = None
    user_config_file_path = None
    otel_logging = None
    user_custom_auth = None
    user_custom_auth_path = None
    user_custom_key_generate = None
    user_custom_sso = None
    use_background_health_checks = None
    health_check_interval = None
    prisma_client = None


async def proxy_shutdown_event():
    global prisma_client, master_key, user_custom_auth, user_custom_key_generate
    verbose_proxy_logger.info("Shutting down LLM Proxy Server")
    if prisma_client:
        verbose_proxy_logger.debug("Disconnecting from Prisma")
        await prisma_client.disconnect()

    if llm.cache is not None:
        await llm.cache.disconnect()

    await jwt_handler.close()

    if db_writer_client is not None:
        await db_writer_client.close()

    # flush remaining langfuse logs
    if "langfuse" in llm.success_callback:
        try:
            # flush langfuse logs on shutdow
            from llm.utils import langFuseLogger

            if langFuseLogger is not None:
                langFuseLogger.Langfuse.flush()
        except Exception:
            # [DO NOT BLOCK shutdown events for this]
            pass

    ## RESET CUSTOM VARIABLES ##
    cleanup_router_config_variables()


@asynccontextmanager
async def proxy_startup_event(app: FastAPI):
    global prisma_client, master_key, use_background_health_checks, llm_router, llm_model_list, general_settings, proxy_budget_rescheduler_min_time, proxy_budget_rescheduler_max_time, llm_proxy_admin_name, db_writer_client, store_model_in_db, premium_user, _license_check
    import json

    init_verbose_loggers()
    ### LOAD MASTER KEY ###
    # check if master key set in environment - load from there
    master_key = get_secret("LLM_MASTER_KEY", None)  # type: ignore
    # check if DATABASE_URL in environment - load from there
    if prisma_client is None:
        _db_url: Optional[str] = get_secret("DATABASE_URL", None)  # type: ignore
        prisma_client = await ProxyStartupEvent._setup_prisma_client(
            database_url=_db_url,
            proxy_logging_obj=proxy_logging_obj,
            user_api_key_cache=user_api_key_cache,
        )

    ## CHECK PREMIUM USER
    verbose_proxy_logger.debug(
        "llm.proxy.proxy_server.py::startup() - CHECKING PREMIUM USER - {}".format(
            premium_user
        )
    )
    if premium_user is False:
        premium_user = _license_check.is_premium()

    ### LOAD CONFIG ###
    worker_config: Optional[Union[str, dict]] = get_secret("WORKER_CONFIG")  # type: ignore
    env_config_yaml: Optional[str] = get_secret_str("CONFIG_FILE_PATH")
    verbose_proxy_logger.debug("worker_config: %s", worker_config)
    # check if it's a valid file path
    if env_config_yaml is not None:
        if os.path.isfile(env_config_yaml) and proxy_config.is_yaml(
            config_file_path=env_config_yaml
        ):
            (
                llm_router,
                llm_model_list,
                general_settings,
            ) = await proxy_config.load_config(
                router=llm_router, config_file_path=env_config_yaml
            )
    elif worker_config is not None:
        if (
            isinstance(worker_config, str)
            and os.path.isfile(worker_config)
            and proxy_config.is_yaml(config_file_path=worker_config)
        ):
            (
                llm_router,
                llm_model_list,
                general_settings,
            ) = await proxy_config.load_config(
                router=llm_router, config_file_path=worker_config
            )
        elif os.environ.get("LLM_CONFIG_BUCKET_NAME") is not None and isinstance(
            worker_config, str
        ):
            (
                llm_router,
                llm_model_list,
                general_settings,
            ) = await proxy_config.load_config(
                router=llm_router, config_file_path=worker_config
            )
        elif isinstance(worker_config, dict):
            await initialize(**worker_config)
        else:
            # if not, assume it's a json string
            worker_config = json.loads(worker_config)
            if isinstance(worker_config, dict):
                await initialize(**worker_config)

    # Load MCP server configurations from config
    load_mcp_server_configs_on_startup(general_settings)
    
    ProxyStartupEvent._initialize_startup_logging(
        llm_router=llm_router,
        proxy_logging_obj=proxy_logging_obj,
        redis_usage_cache=redis_usage_cache,
    )

    ## JWT AUTH ##
    ProxyStartupEvent._initialize_jwt_auth(
        general_settings=general_settings,
        prisma_client=prisma_client,
        user_api_key_cache=user_api_key_cache,
    )

    if use_background_health_checks:
        asyncio.create_task(
            _run_background_health_check()
        )  # start the background health check coroutine.

    if prompt_injection_detection_obj is not None:  # [TODO] - REFACTOR THIS
        prompt_injection_detection_obj.update_environment(router=llm_router)

    verbose_proxy_logger.debug("prisma_client: %s", prisma_client)
    if prisma_client is not None and llm.max_budget > 0:
        ProxyStartupEvent._add_proxy_budget_to_db(
            llm_proxy_budget_name=llm_proxy_admin_name
        )

    ### START BATCH WRITING DB + CHECKING NEW MODELS###
    if prisma_client is not None:
        await ProxyStartupEvent.initialize_scheduled_background_jobs(
            general_settings=general_settings,
            prisma_client=prisma_client,
            proxy_budget_rescheduler_min_time=proxy_budget_rescheduler_min_time,
            proxy_budget_rescheduler_max_time=proxy_budget_rescheduler_max_time,
            proxy_batch_write_at=proxy_batch_write_at,
            proxy_logging_obj=proxy_logging_obj,
        )
    ## [Optional] Initialize dd tracer
    ProxyStartupEvent._init_dd_tracer()

    # End of startup event
    yield

    # Shutdown event
    await proxy_shutdown_event()


from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse

app = FastAPI(
    docs_url=None,  # Disable automatic docs
    redoc_url=_get_redoc_url(),
    title=_title,
    description=_description,
    version=version,
    root_path=server_root_path,  # check if user passed root path, FastAPI defaults this value to ""
    lifespan=proxy_startup_event,
)

# Define custom docs endpoint with our own favicon and dark theme
@app.get("/", include_in_schema=False)
async def custom_swagger_ui_html():
    # Create a simple HTML response with dark theme and custom favicon
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <link type="text/css" rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css">
        <link rel="shortcut icon" href="/favicon.ico">
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@100..900&display=swap" rel="stylesheet">
        <link href="https://fonts.googleapis.com/css2?family=Geist+Mono:wght@300..700&display=swap" rel="stylesheet">
        <title>Hanzo API</title>
        <style>
        /* Navigation bar */
        .nav-container {
            display: flex;
            justify-content: space-between;
            align-items: center;
            background-color: #000;
            padding: 12px 20px;
            margin-bottom: 20px;
            width: calc(100% - 40px);
            position: fixed;
            top: 0;
            left: 0;
            z-index: 1000;
            box-shadow: 0 2px 4px rgba(0,0,0,0.3);
        }
        .nav-logo {
            height: 32px;
        }
        .nav-links a {
            color: #fff;
            text-decoration: none;
            margin-left: 20px;
            font-family: 'Inter', system-ui, sans-serif;
            font-size: 14px;
            font-weight: 500;
        }
        .nav-links a:hover {
            color: #0070f3;
        }
        .swagger-content {
            margin-top: 70px;
        }
        
        /* Vercel-like Dark Theme for Swagger UI with Inter and Geist Mono fonts */
        body {
            background-color: #000; /* Pure black background */
            color: #fff;
            margin: 0;
            padding: 0;
            font-family: 'Inter', system-ui, sans-serif;
        }
        .swagger-ui {
            color: #fff;
            font-family: 'Inter', system-ui, sans-serif;
        }
        /* Force slightly less dark black background everywhere - make it very minimal */
        body, 
        .swagger-ui,
        .swagger-ui .wrapper,
        .swagger-ui section:not(.models),
        .swagger-ui .auth-wrapper,
        .swagger-ui .auth-container,
        .swagger-ui .authorization__btn,
        .swagger-ui .opblock-body,
        .swagger-ui .opblock-section-header,
        .swagger-ui .parameters,
        .swagger-ui .table-container,
        .swagger-ui .responses-wrapper,
        .swagger-ui .responses-inner,
        .swagger-ui .response-col_description__inner,
        .swagger-ui .renderedMarkdown,
        .swagger-ui .highlight-code,
        .swagger-ui .response,
        .swagger-ui .model {
            background-color: #0f0f0f;
        }
        
        /* Fix text colors for better contrast */
        .swagger-ui, 
        .swagger-ui p, 
        .swagger-ui span:not(.arrow), /* Exclude arrow spans for dropdown toggles */
        .swagger-ui label, 
        .swagger-ui .parameter__name, 
        .swagger-ui .parameter__type, 
        .swagger-ui .parameter__deprecated, 
        .swagger-ui .parameter__in,
        .swagger-ui table thead tr th,
        .swagger-ui .parameter__name.required:after,
        .swagger-ui .parameters-col_description p,
        .swagger-ui .tab li,
        .swagger-ui .opblock-description-wrapper p, 
        .swagger-ui .opblock-external-docs-wrapper p {
            color: #aaa !important;
        }
        
        /* Fix dropdown arrows and icons to be white instead of black */
        .swagger-ui .opblock-tag svg,
        .swagger-ui .expand-operation svg,
        .swagger-ui .arrow,
        .swagger-ui .authorization__btn svg,
        .swagger-ui .authorization__btn.locked,
        .swagger-ui .authorization__btn.unlocked,
        .swagger-ui .lock-icon {
            fill: white !important;
            color: white !important;
        }
        
        /* Ensure SVG icons in buttons are white */
        .swagger-ui .btn svg {
            fill: white !important;
        }
        
        /* Make some text brighter for better readability */
        .swagger-ui h1, 
        .swagger-ui h2, 
        .swagger-ui h3, 
        .swagger-ui h4, 
        .swagger-ui h5,
        .swagger-ui .opblock-summary-method,
        .swagger-ui .tab a,
        .swagger-ui .response-col_status,
        .swagger-ui .opblock-summary-path {
            color: #fff !important;
            font-weight: 600 !important;
        }
        /* Hide the information container and clean up UI */
        .swagger-ui .information-container {
            display: none;
        }
        
        /* Remove background from highlighted areas */
        .swagger-ui .highlight-code {
            background: none;
        }
        
        /* Make border on operation blocks more subtle */
        .swagger-ui .opblock {
            margin: 0 0 15px;
            border-radius: 4px;
            box-shadow: none;
        }
        
        /* Fix the opblock section header styling */
        .swagger-ui .opblock .opblock-section-header {
            background: transparent;
            border-bottom: 1px solid #333;
            box-shadow: none;
        }
        
        /* Clean up expanded content style */
        .swagger-ui .parameters-container, 
        .swagger-ui .response-col_description, 
        .swagger-ui .opblock-description-wrapper, 
        .swagger-ui .responses-inner {
            background: transparent;
            box-shadow: none;
        }
        
        /* Make tables more minimal */
        .swagger-ui table tbody tr td {
            border-bottom: 1px solid #333;
            padding: 10px 0;
        }
        
        /* Remove borders from responses */
        .swagger-ui .responses-table .response {
            border: none;
        }
        /* Additional overrides for the authorize section */
        .swagger-ui .dialog-ux .modal-ux {
            background: #0f0f0f;
            border: 1px solid #333;
        }
        .swagger-ui .dialog-ux .modal-ux-header,
        .swagger-ui .dialog-ux .modal-ux-content {
            background: #0f0f0f;
            border-bottom: 1px solid #333;
        }
        .swagger-ui .auth-container .authorize {
            color: #fff;
            border-color: #333;
        }
        .swagger-ui .auth-container .scopes {
            border-color: #333;
        }
        /* Fix auth wrapper text */
        .swagger-ui .auth-wrapper .auth-container h4,
        .swagger-ui .auth-wrapper .auth-container p {
            color: #fff !important;
        }
        /* Enhance the auth input field */
        .swagger-ui .auth-wrapper .auth-container input {
            background: #0f0f0f;
            color: #fff;
            border: 1px solid #333;
            padding: 8px 10px;
            font-family: 'Geist Mono', monospace;
        }
        /* Move swagger UI content up since we hid the info container */
        .swagger-ui .wrapper {
            padding-top: 0;
        }
        /* Custom header with Hanzo logo and navigation */
        .hanzo-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 20px;
            background-color: #000;
            border-bottom: 1px solid #333;
        }
        .hanzo-logo {
            display: flex;
            align-items: center;
            text-decoration: none; /* Remove underline */
        }
        .hanzo-logo img {
            height: 32px;
            margin-right: 10px;
        }
        .hanzo-nav {
            display: flex;
            align-items: center;
            gap: 20px;
        }
        .hanzo-nav a {
            color: white;
            text-decoration: none;
            font-weight: 500;
            padding: 8px 16px;
            border-radius: 4px;
            transition: all 0.2s ease;
        }
        .hanzo-nav a:not(.signup) {
            border: 1px solid white;
        }
        .hanzo-nav a:not(.signup):hover {
            background-color: rgba(255, 255, 255, 0.1);
        }
        .hanzo-nav a.signup {
            background-color: white;
            color: black;
            font-weight: 600;
        }
        .hanzo-nav a.signup:hover {
            background-color: #f0f0f0;
        }
        .hanzo-logo h1 {
            font-family: 'Inter', system-ui, sans-serif;
            font-weight: 600;
            font-size: 24px;
            color: #fff;
            margin: 0;
        }
        .hanzo-nav {
            display: flex;
            gap: 20px;
        }
        .hanzo-nav a {
            color: #fff;
            text-decoration: none;
            font-family: 'Inter', system-ui, sans-serif;
            font-size: 14px;
            padding: 8px 16px;
            border-radius: 4px;
            transition: background-color 0.2s;
        }
        .hanzo-nav a:hover {
            background-color: rgba(255, 255, 255, 0.1);
        }
        .hanzo-nav a.signup {
            background-color: #0070f3;
        }
        .hanzo-nav a.signup:hover {
            background-color: #0060df;
        }
        /* Code formatting with Geist Mono */
        .swagger-ui .markdown code, 
        .swagger-ui .renderedMarkdown code,
        .swagger-ui textarea,
        .swagger-ui .model,
        .swagger-ui code,
        .swagger-ui pre {
            font-family: 'Geist Mono', monospace !important;
        }
        /* General styling */
        .swagger-ui .info .title,
        .swagger-ui .info h1, 
        .swagger-ui .info h2, 
        .swagger-ui .info h3, 
        .swagger-ui .info h4, 
        .swagger-ui .info h5 {
            color: #fff;
            font-family: 'Inter', system-ui, sans-serif;
        }
        .swagger-ui .scheme-container {
            background-color: #0f0f0f;
            box-shadow: none;
            border-bottom: 1px solid #333;
            margin-top: 0;
        }
        .swagger-ui .opblock-tag {
            border-bottom: 1px solid #333;
            color: #fff;
            font-family: 'Inter', system-ui, sans-serif;
        }
        .swagger-ui .opblock {
            background: #0f0f0f;
            border: 1px solid #333;
            box-shadow: none;
        }
        .swagger-ui .opblock .opblock-summary-operation-id {
            color: #aaa;
            font-family: 'Inter', system-ui, sans-serif;
        }
        .swagger-ui .opblock .opblock-summary-path,
        .swagger-ui .opblock .opblock-summary-path__deprecated {
            color: #fff;
            font-family: 'Inter', system-ui, sans-serif;
            font-weight: 500;
        }
        .swagger-ui .opblock .opblock-summary-description {
            color: #aaa;
            font-family: 'Inter', system-ui, sans-serif;
        }
        .swagger-ui .opblock-description-wrapper, 
        .swagger-ui .opblock-external-docs-wrapper, 
        .swagger-ui .opblock-title_normal {
            color: #aaa;
            font-family: 'Inter', system-ui, sans-serif;
        }
        /* Minimal styling for HTTP method blocks with only border colors */
        .swagger-ui .opblock.opblock-get {
            background: #0f0f0f;
            border-color: #007fff;
        }
        .swagger-ui .opblock.opblock-post {
            background: #0f0f0f;
            border-color: #49cc90;
        }
        .swagger-ui .opblock.opblock-delete {
            background: #0f0f0f;
            border-color: #f93e3e;
        }
        .swagger-ui .opblock.opblock-put {
            background: #0f0f0f;
            border-color: #fca130;
        }
        .swagger-ui .opblock.opblock-patch {
            background: #0f0f0f;
            border-color: #50e3c2;
        }
        .swagger-ui .opblock.opblock-head {
            background: #0f0f0f;
            border-color: #9012fe;
        }
        
        /* Ensure method labels are bright white and fully opaque */
        .swagger-ui .opblock-summary-method {
            color: #ffffff !important;
            opacity: 1 !important;
            font-weight: 600 !important;
        }
        .swagger-ui section.models {
            border: 1px solid #333;
        }
        .swagger-ui section.models .model-container {
            background: #0f0f0f;
        }
        .swagger-ui .model-box {
            background: #0f0f0f;
        }
        .swagger-ui .btn {
            background: #333;
            color: #fff;
            border: 1px solid #444;
            font-family: 'Inter', system-ui, sans-serif;
        }
        .swagger-ui select {
            background: #0f0f0f;
            color: #fff;
            border: 1px solid #444;
            font-family: 'Inter', system-ui, sans-serif;
        }
        .swagger-ui input[type="text"], 
        .swagger-ui input[type="password"], 
        .swagger-ui input[type="search"], 
        .swagger-ui input[type="email"] {
            background: #0f0f0f;
            color: #fff;
            border: 1px solid #444;
            font-family: 'Inter', system-ui, sans-serif;
        }
        .swagger-ui textarea {
            background: #0f0f0f;
            color: #fff;
            border: 1px solid #444;
        }
        .swagger-ui .markdown code, 
        .swagger-ui .renderedMarkdown code {
            background: #111;
            color: #eee;
            padding: 3px 5px;
            border-radius: 3px;
            font-size: 13px;
        }
        .swagger-ui .model {
            color: #ccc;
        }
        .swagger-ui .model-title {
            color: #fff;
            font-family: 'Inter', system-ui, sans-serif;
        }
        .swagger-ui table tbody tr td {
            border-bottom: 1px solid #333;
            font-family: 'Inter', system-ui, sans-serif;
        }
        .swagger-ui .response-col_status {
            color: #fff;
        }
        .swagger-ui .responses-table .response {
            color: #ccc;
        }
        .swagger-ui .topbar {
            background-color: #000;
            border-bottom: 1px solid #333;
            display: none; /* Hide default topbar */
        }
        .swagger-ui .info a {
            color: #0070f3;
        }
        .swagger-ui .info a:hover {
            color: #3291ff;
        }
        /* Make scrollbars dark themed */
        ::-webkit-scrollbar {
            width: 10px;
            height: 10px;
        }
        ::-webkit-scrollbar-track {
            background: #111;
        }
        ::-webkit-scrollbar-thumb {
            background: #333;
            border-radius: 5px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: #444;
        }
        /* Hide some Swagger UI elements */
        .swagger-ui .info .title small {
            display: none;
        }
        </style>
    </head>
    <body>
    <div class="nav-container">
        <div>
            <img src="/get_image" alt="Hanzo AI Logo" class="nav-logo">
        </div>
        <div class="nav-links">
            <a href="/docs">API</a>
            <a href="/models.html">Models</a>
            <a href="/mcps.html">MCP Servers</a>
            <a href="/ui/tool-hub">Tool Hub</a>
            <a href="https://github.com/hanzoai/llm" target="_blank">GitHub</a>
        </div>
    </div>
    <div class="swagger-content">
        <div id="swagger-ui"></div>
    <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    <!-- `SwaggerUIBundle` is now available on the page -->
    <script>
    const ui = SwaggerUIBundle({
        url: '/openapi.json',
        dom_id: '#swagger-ui',
        presets: [
            SwaggerUIBundle.presets.apis,
            SwaggerUIBundle.SwaggerUIStandalonePreset
        ],
        layout: "BaseLayout",
        deepLinking: true,
        showExtensions: true,
        showCommonExtensions: true,
        docExpansion: 'list',
        securityDefinitions: {
            apiKey: {
                type: "apiKey",
                name: "Authorization",
                in: "header",
                description: "Enter your API key with the format: 'Bearer &lt;HANZO_API_KEY&gt;'"
            }
        },
        requestInterceptor: function(request) {
            // Ensure Authorization header is in the correct format if it exists
            if (request.headers.Authorization && !request.headers.Authorization.startsWith('Bearer ')) {
                request.headers.Authorization = 'Bearer ' + request.headers.Authorization;
            }
            return request;
        }
    });
    </script>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)


# Add a metrics endpoint to fix the 404 issue
@app.get("/metrics", include_in_schema=False)
async def metrics():
    """Endpoint for Prometheus metrics"""
    # Simple empty response for now
    return HTMLResponse(content="# Metrics endpoint - Enterprise Feature\n")


### CUSTOM API DOCS [ENTERPRISE FEATURE] ###
# Custom OpenAPI schema generator to include only selected routes
from fastapi.routing import APIWebSocketRoute


def get_openapi_schema():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # Find all WebSocket routes
    websocket_routes = [
        route for route in app.routes if isinstance(route, APIWebSocketRoute)
    ]

    # Add each WebSocket route to the schema
    for route in websocket_routes:
        # Get the base path without query parameters
        base_path = route.path.split("{")[0].rstrip("?")

        # Extract parameters from the route
        parameters = []
        if hasattr(route, "dependant"):
            for param in route.dependant.query_params:
                parameters.append(
                    {
                        "name": param.name,
                        "in": "query",
                        "required": param.required,
                        "schema": {
                            "type": "string"
                        },  # You can make this more specific if needed
                    }
                )

        openapi_schema["paths"][base_path] = {
            "get": {
                "summary": f"WebSocket: {route.name or base_path}",
                "description": "WebSocket connection endpoint",
                "operationId": f"websocket_{route.name or base_path.replace('/', '_')}",
                "parameters": parameters,
                "responses": {"101": {"description": "WebSocket Protocol Switched"}},
                "tags": ["WebSocket"],
            }
        }

    app.openapi_schema = openapi_schema
    return app.openapi_schema


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi_schema()

    # Filter routes to include only specific ones
    openai_routes = LLMRoutes.openai_routes.value
    paths_to_include: dict = {}
    for route in openai_routes:
        if route in openapi_schema["paths"]:
            paths_to_include[route] = openapi_schema["paths"][route]
    openapi_schema["paths"] = paths_to_include
    app.openapi_schema = openapi_schema
    return app.openapi_schema


if os.getenv("DOCS_FILTERED", "False") == "True" and premium_user:
    app.openapi = custom_openapi  # type: ignore


class UserAPIKeyCacheTTLEnum(enum.Enum):
    in_memory_cache_ttl = 60  # 1 min ttl ## configure via `general_settings::user_api_key_cache_ttl: <your-value>`


@app.exception_handler(ProxyException)
async def openai_exception_handler(request: Request, exc: ProxyException):
    # NOTE: DO NOT MODIFY THIS, its crucial to map to Openai exceptions
    headers = exc.headers
    return JSONResponse(
        status_code=(
            int(exc.code) if exc.code else status.HTTP_500_INTERNAL_SERVER_ERROR
        ),
        content={
            "error": {
                "message": exc.message,
                "type": exc.type,
                "param": exc.param,
                "code": exc.code,
            }
        },
        headers=headers,
    )


router = APIRouter()
origins = ["*"]

# get current directory
try:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    ui_path = os.path.join(current_dir, "_experimental", "out")
    app.mount("/ui", StaticFiles(directory=ui_path, html=True), name="ui")
    # Iterate through files in the UI directory
    for filename in os.listdir(ui_path):
        if filename.endswith(".html") and filename != "index.html":
            # Create a folder with the same name as the HTML file
            folder_name = os.path.splitext(filename)[0]
            folder_path = os.path.join(ui_path, folder_name)
            os.makedirs(folder_path, exist_ok=True)

            # Move the HTML file into the folder and rename it to 'index.html'
            src = os.path.join(ui_path, filename)
            dst = os.path.join(folder_path, "index.html")
            os.rename(src, dst)

    if server_root_path != "":
        print(  # noqa
            f"server_root_path is set, forwarding any /ui requests to {server_root_path}/ui"
        )  # noqa
        if os.getenv("PROXY_BASE_URL") is None:
            os.environ["PROXY_BASE_URL"] = server_root_path

        @app.middleware("http")
        async def redirect_ui_middleware(request: Request, call_next):
            if request.url.path.startswith("/ui"):
                new_url = str(request.url).replace("/ui", f"{server_root_path}/ui", 1)
                return RedirectResponse(new_url)
            return await call_next(request)

except Exception:
    pass
# current_dir = os.path.dirname(os.path.abspath(__file__))
# ui_path = os.path.join(current_dir, "_experimental", "out")
# # Mount this test directory instead
# app.mount("/ui", StaticFiles(directory=ui_path, html=True), name="ui")


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


from typing import Dict

user_api_base = None
user_model = None
user_debug = False
user_max_tokens = None
user_request_timeout = None
user_temperature = None
user_telemetry = True
user_config = None
user_headers = None
user_config_file_path: Optional[str] = None
local_logging = True  # writes logs to a local api_log.json file for debugging
experimental = False
#### GLOBAL VARIABLES ####
llm_router: Optional[Router] = None
llm_model_list: Optional[list] = None
general_settings: dict = {}
callback_settings: dict = {}
log_file = "api_log.json"
worker_config = None
master_key: Optional[str] = None
otel_logging = False
prisma_client: Optional[PrismaClient] = None
user_api_key_cache = DualCache(
    default_in_memory_ttl=UserAPIKeyCacheTTLEnum.in_memory_cache_ttl.value
)
model_max_budget_limiter = _PROXY_VirtualKeyModelMaxBudgetLimiter(
    dual_cache=user_api_key_cache
)
llm.logging_callback_manager.add_llm_callback(model_max_budget_limiter)
redis_usage_cache: Optional[RedisCache] = (
    None  # redis cache used for tracking spend, tpm/rpm limits
)
user_custom_auth = None
user_custom_key_generate = None
user_custom_sso = None
use_background_health_checks = None
use_queue = False
health_check_interval = None
health_check_details = None
health_check_results = {}
queue: List = []
llm_proxy_budget_name = "llm-proxy-budget"
llm_proxy_admin_name = LLM_PROXY_ADMIN_NAME
ui_access_mode: Literal["admin", "all"] = "all"
proxy_budget_rescheduler_min_time = 597
proxy_budget_rescheduler_max_time = 605
proxy_batch_write_at = 10  # in seconds
llm_master_key_hash = None
disable_spend_logs = False
jwt_handler = JWTHandler()
prompt_injection_detection_obj: Optional[_OPTIONAL_PromptInjectionDetection] = None
store_model_in_db: bool = False
open_telemetry_logger: Optional[OpenTelemetry] = None
### INITIALIZE GLOBAL LOGGING OBJECT ###
proxy_logging_obj = ProxyLogging(
    user_api_key_cache=user_api_key_cache, premium_user=premium_user
)
### REDIS QUEUE ###
async_result = None
celery_app_conn = None
celery_fn = None  # Redis Queue for handling requests
### DB WRITER ###
db_writer_client: Optional[AsyncHTTPHandler] = None
### logger ###


async def check_request_disconnection(request: Request, llm_api_call_task):
    """
    Asynchronously checks if the request is disconnected at regular intervals.
    If the request is disconnected
    - cancel the llm.router task
    - raises an HTTPException with status code 499 and detail "Client disconnected the request".

    Parameters:
    - request: Request: The request object to check for disconnection.
    Returns:
    - None
    """

    # only run this function for 10 mins -> if these don't get cancelled -> we don't want the server to have many while loops
    start_time = time.time()
    while time.time() - start_time < 600:
        await asyncio.sleep(1)
        if await request.is_disconnected():

            # cancel the LLM API Call task if any passed - this is passed from individual providers
            # Example OpenAI, Azure, VertexAI etc
            llm_api_call_task.cancel()

            raise HTTPException(
                status_code=499,
                detail="Client disconnected the request",
            )


def _resolve_typed_dict_type(typ):
    """Resolve the actual TypedDict class from a potentially wrapped type."""
    from typing_extensions import _TypedDictMeta  # type: ignore

    origin = get_origin(typ)
    if origin is Union:  # Check if it's a Union (like Optional)
        for arg in get_args(typ):
            if isinstance(arg, _TypedDictMeta):
                return arg
    elif isinstance(typ, type) and isinstance(typ, dict):
        return typ
    return None


def _resolve_pydantic_type(typ) -> List:
    """Resolve the actual TypedDict class from a potentially wrapped type."""
    origin = get_origin(typ)
    typs = []
    if origin is Union:  # Check if it's a Union (like Optional)
        for arg in get_args(typ):
            if (
                arg is not None
                and not isinstance(arg, type(None))
                and "NoneType" not in str(arg)
            ):
                typs.append(arg)
    elif isinstance(typ, type) and isinstance(typ, BaseModel):
        return [typ]
    return typs


def load_from_azure_key_vault(use_azure_key_vault: bool = False):
    if use_azure_key_vault is False:
        return

    try:
        from azure.identity import DefaultAzureCredential
        from azure.keyvault.secrets import SecretClient

        # Set your Azure Key Vault URI
        KVUri = os.getenv("AZURE_KEY_VAULT_URI", None)

        if KVUri is None:
            raise Exception(
                "Error when loading keys from Azure Key Vault: AZURE_KEY_VAULT_URI is not set."
            )

        credential = DefaultAzureCredential()

        # Create the SecretClient using the credential
        client = SecretClient(vault_url=KVUri, credential=credential)

        llm.secret_manager_client = client
        llm._key_management_system = KeyManagementSystem.AZURE_KEY_VAULT
    except Exception as e:
        _error_str = str(e)
        verbose_proxy_logger.exception(
            "Error when loading keys from Azure Key Vault: %s .Ensure you run `pip install azure-identity azure-keyvault-secrets`",
            _error_str,
        )


def cost_tracking():
    global prisma_client
    if prisma_client is not None:
        llm.logging_callback_manager.add_llm_callback(_ProxyDBLogger())


def _set_spend_logs_payload(
    payload: Union[dict, SpendLogsPayload],
    prisma_client: PrismaClient,
    spend_logs_url: Optional[str] = None,
):
    verbose_proxy_logger.info(
        "Writing spend log to db - request_id: {}, spend: {}".format(
            payload.get("request_id"), payload.get("spend")
        )
    )
    if prisma_client is not None and spend_logs_url is not None:
        if isinstance(payload["startTime"], datetime):
            payload["startTime"] = payload["startTime"].isoformat()
        if isinstance(payload["endTime"], datetime):
            payload["endTime"] = payload["endTime"].isoformat()
        prisma_client.spend_log_transactions.append(payload)
    elif prisma_client is not None:
        prisma_client.spend_log_transactions.append(payload)
    return prisma_client


async def update_database(  # noqa: PLR0915
    token,
    response_cost,
    user_id=None,
    end_user_id=None,
    team_id=None,
    kwargs=None,
    completion_response=None,
    start_time=None,
    end_time=None,
    org_id=None,
):
    try:
        global prisma_client
        verbose_proxy_logger.debug(
            f"Enters prisma db call, response_cost: {response_cost}, token: {token}; user_id: {user_id}; team_id: {team_id}"
        )
        if ProxyUpdateSpend.disable_spend_updates() is True:
            return
        if token is not None and isinstance(token, str) and token.startswith("sk-"):
            hashed_token = hash_token(token=token)
        else:
            hashed_token = token

        ### UPDATE USER SPEND ###
        async def _update_user_db():
            """
            - Update that user's row
            - Update llm-proxy-budget row (global proxy spend)
            """
            ## if an end-user is passed in, do an upsert - we can't guarantee they already exist in db
            existing_user_obj = await user_api_key_cache.async_get_cache(key=user_id)
            if existing_user_obj is not None and isinstance(existing_user_obj, dict):
                existing_user_obj = LLM_UserTable(**existing_user_obj)
            try:
                if prisma_client is not None:  # update
                    user_ids = [user_id]
                    if (
                        llm.max_budget > 0
                    ):  # track global proxy budget, if user set max budget
                        user_ids.append(llm_proxy_budget_name)
                    ### KEY CHANGE ###
                    for _id in user_ids:
                        if _id is not None:
                            prisma_client.user_list_transactons[_id] = (
                                response_cost
                                + prisma_client.user_list_transactons.get(_id, 0)
                            )
                    if end_user_id is not None:
                        prisma_client.end_user_list_transactons[end_user_id] = (
                            response_cost
                            + prisma_client.end_user_list_transactons.get(
                                end_user_id, 0
                            )
                        )
            except Exception as e:
                verbose_proxy_logger.info(
                    "\033[91m"
                    + f"Update User DB call failed to execute {str(e)}\n{traceback.format_exc()}"
                )

        ### UPDATE KEY SPEND ###
        async def _update_key_db():
            try:
                verbose_proxy_logger.debug(
                    f"adding spend to key db. Response cost: {response_cost}. Token: {hashed_token}."
                )
                if hashed_token is None:
                    return
                if prisma_client is not None:
                    prisma_client.key_list_transactons[hashed_token] = (
                        response_cost
                        + prisma_client.key_list_transactons.get(hashed_token, 0)
                    )
            except Exception as e:
                verbose_proxy_logger.exception(
                    f"Update Key DB Call failed to execute - {str(e)}"
                )
                raise e

        ### UPDATE SPEND LOGS ###
        async def _insert_spend_log_to_db():
            try:
                global prisma_client
                if prisma_client is not None:
                    # Helper to generate payload to log
                    payload = get_logging_payload(
                        kwargs=kwargs,
                        response_obj=completion_response,
                        start_time=start_time,
                        end_time=end_time,
                    )
                    payload["spend"] = response_cost
                    prisma_client = _set_spend_logs_payload(
                        payload=payload,
                        spend_logs_url=os.getenv("SPEND_LOGS_URL"),
                        prisma_client=prisma_client,
                    )
            except Exception as e:
                verbose_proxy_logger.debug(
                    f"Update Spend Logs DB failed to execute - {str(e)}\n{traceback.format_exc()}"
                )
                raise e

        ### UPDATE TEAM SPEND ###
        async def _update_team_db():
            try:
                verbose_proxy_logger.debug(
                    f"adding spend to team db. Response cost: {response_cost}. team_id: {team_id}."
                )
                if team_id is None:
                    verbose_proxy_logger.debug(
                        "track_cost_callback: team_id is None. Not tracking spend for team"
                    )
                    return
                if prisma_client is not None:
                    prisma_client.team_list_transactons[team_id] = (
                        response_cost
                        + prisma_client.team_list_transactons.get(team_id, 0)
                    )

                    try:
                        # Track spend of the team member within this team
                        # key is "team_id::<value>::user_id::<value>"
                        team_member_key = f"team_id::{team_id}::user_id::{user_id}"
                        prisma_client.team_member_list_transactons[team_member_key] = (
                            response_cost
                            + prisma_client.team_member_list_transactons.get(
                                team_member_key, 0
                            )
                        )
                    except Exception:
                        pass
            except Exception as e:
                verbose_proxy_logger.info(
                    f"Update Team DB failed to execute - {str(e)}\n{traceback.format_exc()}"
                )
                raise e

        ### UPDATE ORG SPEND ###
        async def _update_org_db():
            try:
                verbose_proxy_logger.debug(
                    "adding spend to org db. Response cost: {}. org_id: {}.".format(
                        response_cost, org_id
                    )
                )
                if org_id is None:
                    verbose_proxy_logger.debug(
                        "track_cost_callback: org_id is None. Not tracking spend for org"
                    )
                    return
                if prisma_client is not None:
                    prisma_client.org_list_transactons[org_id] = (
                        response_cost
                        + prisma_client.org_list_transactons.get(org_id, 0)
                    )
            except Exception as e:
                verbose_proxy_logger.info(
                    f"Update Org DB failed to execute - {str(e)}\n{traceback.format_exc()}"
                )
                raise e

        asyncio.create_task(_update_user_db())
        asyncio.create_task(_update_key_db())
        asyncio.create_task(_update_team_db())
        asyncio.create_task(_update_org_db())
        # asyncio.create_task(_insert_spend_log_to_db())
        if disable_spend_logs is False:
            await _insert_spend_log_to_db()
        else:
            verbose_proxy_logger.info(
                "disable_spend_logs=True. Skipping writing spend logs to db. Other spend updates - Key/User/Team table will still occur."
            )

        verbose_proxy_logger.debug("Runs spend update on all tables")
    except Exception:
        verbose_proxy_logger.debug(
            f"Error updating Prisma database: {traceback.format_exc()}"
        )


async def update_cache(  # noqa: PLR0915
    token: Optional[str],
    user_id: Optional[str],
    end_user_id: Optional[str],
    team_id: Optional[str],
    response_cost: Optional[float],
    parent_otel_span: Optional[Span],  # type: ignore
):
    """
    Use this to update the cache with new user spend.

    Put any alerting logic in here.
    """

    values_to_update_in_cache: List[Tuple[Any, Any]] = []

    ### UPDATE KEY SPEND ###
    async def _update_key_cache(token: str, response_cost: float):
        # Fetch the existing cost for the given token
        if isinstance(token, str) and token.startswith("sk-"):
            hashed_token = hash_token(token=token)
        else:
            hashed_token = token
        verbose_proxy_logger.debug("_update_key_cache: hashed_token=%s", hashed_token)
        existing_spend_obj: LLM_VerificationTokenView = await user_api_key_cache.async_get_cache(key=hashed_token)  # type: ignore
        verbose_proxy_logger.debug(
            f"_update_key_cache: existing_spend_obj={existing_spend_obj}"
        )
        verbose_proxy_logger.debug(
            f"_update_key_cache: existing spend: {existing_spend_obj}"
        )
        if existing_spend_obj is None:
            return
        else:
            existing_spend = existing_spend_obj.spend
        # Calculate the new cost by adding the existing cost and response_cost
        new_spend = existing_spend + response_cost

        ## CHECK IF USER PROJECTED SPEND > SOFT LIMIT
        if (
            existing_spend_obj.soft_budget_cooldown is False
            and existing_spend_obj.llm_budget_table is not None
            and (
                _is_projected_spend_over_limit(
                    current_spend=new_spend,
                    soft_budget_limit=existing_spend_obj.llm_budget_table[
                        "soft_budget"
                    ],
                )
                is True
            )
        ):
            projected_spend, projected_exceeded_date = _get_projected_spend_over_limit(
                current_spend=new_spend,
                soft_budget_limit=existing_spend_obj.llm_budget_table.get(
                    "soft_budget", None
                ),
            )  # type: ignore
            soft_limit = existing_spend_obj.llm_budget_table.get(
                "soft_budget", float("inf")
            )
            call_info = CallInfo(
                token=existing_spend_obj.token or "",
                spend=new_spend,
                key_alias=existing_spend_obj.key_alias,
                max_budget=soft_limit,
                user_id=existing_spend_obj.user_id,
                projected_spend=projected_spend,
                projected_exceeded_date=projected_exceeded_date,
            )
            # alert user
            asyncio.create_task(
                proxy_logging_obj.budget_alerts(
                    type="projected_limit_exceeded",
                    user_info=call_info,
                )
            )
            # set cooldown on alert

        if (
            existing_spend_obj is not None
            and getattr(existing_spend_obj, "team_spend", None) is not None
        ):
            existing_team_spend = existing_spend_obj.team_spend or 0
            # Calculate the new cost by adding the existing cost and response_cost
            existing_spend_obj.team_spend = existing_team_spend + response_cost

        if (
            existing_spend_obj is not None
            and getattr(existing_spend_obj, "team_member_spend", None) is not None
        ):
            existing_team_member_spend = existing_spend_obj.team_member_spend or 0
            # Calculate the new cost by adding the existing cost and response_cost
            existing_spend_obj.team_member_spend = (
                existing_team_member_spend + response_cost
            )

        # Update the cost column for the given token
        existing_spend_obj.spend = new_spend
        values_to_update_in_cache.append((hashed_token, existing_spend_obj))

    ### UPDATE USER SPEND ###
    async def _update_user_cache():
        ## UPDATE CACHE FOR USER ID + GLOBAL PROXY
        user_ids = [user_id]
        try:
            for _id in user_ids:
                # Fetch the existing cost for the given user
                if _id is None:
                    continue
                existing_spend_obj = await user_api_key_cache.async_get_cache(key=_id)
                if existing_spend_obj is None:
                    # do nothing if there is no cache value
                    return
                verbose_proxy_logger.debug(
                    f"_update_user_db: existing spend: {existing_spend_obj}; response_cost: {response_cost}"
                )

                if isinstance(existing_spend_obj, dict):
                    existing_spend = existing_spend_obj["spend"]
                else:
                    existing_spend = existing_spend_obj.spend
                # Calculate the new cost by adding the existing cost and response_cost
                new_spend = existing_spend + response_cost

                # Update the cost column for the given user
                if isinstance(existing_spend_obj, dict):
                    existing_spend_obj["spend"] = new_spend
                    values_to_update_in_cache.append((_id, existing_spend_obj))
                else:
                    existing_spend_obj.spend = new_spend
                    values_to_update_in_cache.append((_id, existing_spend_obj.json()))
            ## UPDATE GLOBAL PROXY ##
            global_proxy_spend = await user_api_key_cache.async_get_cache(
                key="{}:spend".format(llm_proxy_admin_name)
            )
            if global_proxy_spend is None:
                # do nothing if not in cache
                return
            elif response_cost is not None and global_proxy_spend is not None:
                increment = global_proxy_spend + response_cost
                values_to_update_in_cache.append(
                    ("{}:spend".format(llm_proxy_admin_name), increment)
                )
        except Exception as e:
            verbose_proxy_logger.debug(
                f"An error occurred updating user cache: {str(e)}\n\n{traceback.format_exc()}"
            )

    ### UPDATE END-USER SPEND ###
    async def _update_end_user_cache():
        if end_user_id is None or response_cost is None:
            return

        _id = "end_user_id:{}".format(end_user_id)
        try:
            # Fetch the existing cost for the given user
            existing_spend_obj = await user_api_key_cache.async_get_cache(key=_id)
            if existing_spend_obj is None:
                # if user does not exist in LLM_UserTable, create a new user
                # do nothing if end-user not in api key cache
                return
            verbose_proxy_logger.debug(
                f"_update_end_user_db: existing spend: {existing_spend_obj}; response_cost: {response_cost}"
            )
            if existing_spend_obj is None:
                existing_spend = 0
            else:
                if isinstance(existing_spend_obj, dict):
                    existing_spend = existing_spend_obj["spend"]
                else:
                    existing_spend = existing_spend_obj.spend
            # Calculate the new cost by adding the existing cost and response_cost
            new_spend = existing_spend + response_cost

            # Update the cost column for the given user
            if isinstance(existing_spend_obj, dict):
                existing_spend_obj["spend"] = new_spend
                values_to_update_in_cache.append((_id, existing_spend_obj))
            else:
                existing_spend_obj.spend = new_spend
                values_to_update_in_cache.append((_id, existing_spend_obj.json()))
        except Exception as e:
            verbose_proxy_logger.exception(
                f"An error occurred updating end user cache: {str(e)}"
            )

    ### UPDATE TEAM SPEND ###
    async def _update_team_cache():
        if team_id is None or response_cost is None:
            return

        _id = "team_id:{}".format(team_id)
        try:
            # Fetch the existing cost for the given user
            existing_spend_obj: Optional[LLM_TeamTable] = (
                await user_api_key_cache.async_get_cache(key=_id)
            )
            if existing_spend_obj is None:
                # do nothing if team not in api key cache
                return
            verbose_proxy_logger.debug(
                f"_update_team_db: existing spend: {existing_spend_obj}; response_cost: {response_cost}"
            )
            if existing_spend_obj is None:
                existing_spend: Optional[float] = 0.0
            else:
                if isinstance(existing_spend_obj, dict):
                    existing_spend = existing_spend_obj["spend"]
                else:
                    existing_spend = existing_spend_obj.spend

            if existing_spend is None:
                existing_spend = 0.0
            # Calculate the new cost by adding the existing cost and response_cost
            new_spend = existing_spend + response_cost

            # Update the cost column for the given user
            if isinstance(existing_spend_obj, dict):
                existing_spend_obj["spend"] = new_spend
                values_to_update_in_cache.append((_id, existing_spend_obj))
            else:
                existing_spend_obj.spend = new_spend
                values_to_update_in_cache.append((_id, existing_spend_obj))
        except Exception as e:
            verbose_proxy_logger.exception(
                f"An error occurred updating end user cache: {str(e)}"
            )

    if token is not None and response_cost is not None:
        await _update_key_cache(token=token, response_cost=response_cost)

    if user_id is not None:
        await _update_user_cache()

    if end_user_id is not None:
        await _update_end_user_cache()

    if team_id is not None:
        await _update_team_cache()

    asyncio.create_task(
        user_api_key_cache.async_set_cache_pipeline(
            cache_list=values_to_update_in_cache,
            ttl=60,
            llm_parent_otel_span=parent_otel_span,
        )
    )


def run_ollama_serve():
    try:
        command = ["ollama", "serve"]

        with open(os.devnull, "w") as devnull:
            subprocess.Popen(command, stdout=devnull, stderr=devnull)
    except Exception as e:
        verbose_proxy_logger.debug(
            f"""
            LLM Warning: proxy started with `ollama` model\n`ollama serve` failed with Exception{e}. \nEnsure you run `ollama serve`
        """
        )


async def _run_background_health_check():
    """
    Periodically run health checks in the background on the endpoints.

    Update health_check_results, based on this.
    """
    global health_check_results, llm_model_list, health_check_interval, health_check_details

    # make 1 deep copy of llm_model_list -> use this for all background health checks
    _llm_model_list = copy.deepcopy(llm_model_list)

    if _llm_model_list is None:
        return

    while True:
        healthy_endpoints, unhealthy_endpoints = await perform_health_check(
            model_list=_llm_model_list, details=health_check_details
        )

        # Update the global variable with the health check results
        health_check_results["healthy_endpoints"] = healthy_endpoints
        health_check_results["unhealthy_endpoints"] = unhealthy_endpoints
        health_check_results["healthy_count"] = len(healthy_endpoints)
        health_check_results["unhealthy_count"] = len(unhealthy_endpoints)

        if health_check_interval is not None and isinstance(
            health_check_interval, float
        ):
            await asyncio.sleep(health_check_interval)


class StreamingCallbackError(Exception):
    pass


class ProxyConfig:
    """
    Abstraction class on top of config loading/updating logic. Gives us one place to control all config updating logic.
    """

    def __init__(self) -> None:
        self.config: Dict[str, Any] = {}

    def is_yaml(self, config_file_path: str) -> bool:
        if not os.path.isfile(config_file_path):
            return False

        _, file_extension = os.path.splitext(config_file_path)
        return file_extension.lower() == ".yaml" or file_extension.lower() == ".yml"

    def _load_yaml_file(self, file_path: str) -> dict:
        """
        Load and parse a YAML file
        """
        try:
            with open(file_path, "r") as file:
                return yaml.safe_load(file) or {}
        except Exception as e:
            raise Exception(f"Error loading yaml file {file_path}: {str(e)}")

    async def _get_config_from_file(
        self, config_file_path: Optional[str] = None
    ) -> dict:
        """
        Given a config file path, load the config from the file.
        Args:
            config_file_path (str): path to the config file
        Returns:
            dict: config
        """
        global prisma_client, user_config_file_path

        file_path = config_file_path or user_config_file_path
        if config_file_path is not None:
            user_config_file_path = config_file_path
        # Load existing config
        ## Yaml
        if os.path.exists(f"{file_path}"):
            with open(f"{file_path}", "r") as config_file:
                config = yaml.safe_load(config_file)
        elif file_path is not None:
            raise Exception(f"Config file not found: {file_path}")
        else:
            config = {
                "model_list": [],
                "general_settings": {},
                "router_settings": {},
                "llm_settings": {},
            }

        # Process includes
        config = self._process_includes(
            config=config, base_dir=os.path.dirname(os.path.abspath(file_path or ""))
        )

        verbose_proxy_logger.debug(f"loaded config={json.dumps(config, indent=4)}")
        return config

    def _process_includes(self, config: dict, base_dir: str) -> dict:
        """
        Process includes by appending their contents to the main config

        Handles nested config.yamls with `include` section

        Example config: This will get the contents from files in `include` and append it
        ```yaml
        include:
            - model_config.yaml

        llm_settings:
            callbacks: ["prometheus"]
        ```
        """
        if "include" not in config:
            return config

        if not isinstance(config["include"], list):
            raise ValueError("'include' must be a list of file paths")

        # Load and append all included files
        for include_file in config["include"]:
            file_path = os.path.join(base_dir, include_file)
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Included file not found: {file_path}")

            included_config = self._load_yaml_file(file_path)
            # Simply update/extend the main config with included config
            for key, value in included_config.items():
                if isinstance(value, list) and key in config:
                    config[key].extend(value)
                else:
                    config[key] = value

        # Remove the include directive
        del config["include"]
        return config

    async def save_config(self, new_config: dict):
        global prisma_client, general_settings, user_config_file_path, store_model_in_db
        # Load existing config
        ## DB - writes valid config to db
        """
        - Do not write restricted params like 'api_key' to the database
        - if api_key is passed, save that to the local environment or connected secret manage (maybe expose `llm.save_secret()`)
        """
        if prisma_client is not None and (
            general_settings.get("store_model_in_db", False) is True
            or store_model_in_db
        ):
            # if using - db for config - models are in ModelTable
            new_config.pop("model_list", None)
            await prisma_client.insert_data(data=new_config, table_name="config")
        else:
            # Save the updated config - if user is not using a dB
            ## YAML
            with open(f"{user_config_file_path}", "w") as config_file:
                yaml.dump(new_config, config_file, default_flow_style=False)

    def _check_for_os_environ_vars(
        self, config: dict, depth: int = 0, max_depth: int = 10
    ) -> dict:
        """
        Check for os.environ/ variables in the config and replace them with the actual values.
        Includes a depth limit to prevent infinite recursion.

        Args:
            config (dict): The configuration dictionary to process.
            depth (int): Current recursion depth.
            max_depth (int): Maximum allowed recursion depth.

        Returns:
            dict: Processed configuration dictionary.
        """
        if depth > max_depth:
            verbose_proxy_logger.warning(
                f"Maximum recursion depth ({max_depth}) reached while processing config."
            )
            return config

        for key, value in config.items():
            if isinstance(value, dict):
                config[key] = self._check_for_os_environ_vars(
                    config=value, depth=depth + 1, max_depth=max_depth
                )
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        item = self._check_for_os_environ_vars(
                            config=item, depth=depth + 1, max_depth=max_depth
                        )
            # if the value is a string and starts with "os.environ/" - then it's an environment variable
            elif isinstance(value, str) and value.startswith("os.environ/"):
                config[key] = get_secret(value)
        return config

    def _get_team_config(self, team_id: str, all_teams_config: List[Dict]) -> Dict:
        team_config: dict = {}
        for team in all_teams_config:
            if "team_id" not in team:
                raise Exception(f"team_id missing from team: {team}")
            if team_id == team["team_id"]:
                team_config = team
                break
        for k, v in team_config.items():
            if isinstance(v, str) and v.startswith("os.environ/"):
                team_config[k] = get_secret(v)
        return team_config

    def load_team_config(self, team_id: str):
        """
        - for a given team id
        - return the relevant completion() call params
        """

        # load existing config
        config = self.get_config_state()

        ## LLM MODULE SETTINGS (e.g. llm.drop_params=True,..)
        llm_settings = config.get("llm_settings", {})
        all_teams_config = llm_settings.get("default_team_settings", None)
        if all_teams_config is None:
            return {}
        team_config = self._get_team_config(
            team_id=team_id, all_teams_config=all_teams_config
        )
        return team_config

    def _init_cache(
        self,
        cache_params: dict,
    ):
        global redis_usage_cache, llm_router
        from llm import Cache

        if "default_in_memory_ttl" in cache_params:
            llm.default_in_memory_ttl = cache_params["default_in_memory_ttl"]

        if "default_redis_ttl" in cache_params:
            llm.default_redis_ttl = cache_params["default_in_redis_ttl"]

        llm.cache = Cache(**cache_params)

        if llm.cache is not None and isinstance(llm.cache.cache, RedisCache):
            ## INIT PROXY REDIS USAGE CLIENT ##
            redis_usage_cache = llm.cache.cache

    async def get_config(self, config_file_path: Optional[str] = None) -> dict:
        """
        Load config file
        Supports reading from:
        - .yaml file paths
        - LLM connected DB
        - GCS
        - S3

        Args:
            config_file_path (str): path to the config file
        Returns:
            dict: config

        """
        global prisma_client, store_model_in_db
        # Load existing config

        if os.environ.get("LLM_CONFIG_BUCKET_NAME") is not None:
            bucket_name = os.environ.get("LLM_CONFIG_BUCKET_NAME")
            object_key = os.environ.get("LLM_CONFIG_BUCKET_OBJECT_KEY")
            bucket_type = os.environ.get("LLM_CONFIG_BUCKET_TYPE")
            verbose_proxy_logger.debug(
                "bucket_name: %s, object_key: %s", bucket_name, object_key
            )
            if bucket_type == "gcs":
                config = await get_config_file_contents_from_gcs(
                    bucket_name=bucket_name, object_key=object_key
                )
            else:
                config = get_file_contents_from_s3(
                    bucket_name=bucket_name, object_key=object_key
                )

            if config is None:
                raise Exception("Unable to load config from given source.")
        else:
            # default to file
            config = await self._get_config_from_file(config_file_path=config_file_path)
        ## UPDATE CONFIG WITH DB
        if prisma_client is not None and store_model_in_db is True:
            config = await self._update_config_from_db(
                config=config,
                prisma_client=prisma_client,
                store_model_in_db=store_model_in_db,
            )

        ## PRINT YAML FOR CONFIRMING IT WORKS
        printed_yaml = copy.deepcopy(config)
        printed_yaml.pop("environment_variables", None)

        config = self._check_for_os_environ_vars(config=config)

        self.update_config_state(config=config)
        return config

    def update_config_state(self, config: dict):
        self.config = config

    def get_config_state(self):
        """
        Returns a deep copy of the config,

        Do this, to avoid mutating the config state outside of allowed methods
        """
        try:
            return copy.deepcopy(self.config)
        except Exception as e:
            verbose_proxy_logger.debug(
                "ProxyConfig:get_config_state(): Error returning copy of config state. self.config={}\nError: {}".format(
                    self.config, e
                )
            )
            return {}

    def load_credential_list(self, config: dict) -> List[CredentialItem]:
        """
        Load the credential list from the database
        """
        credential_list_dict = config.get("credential_list")
        credential_list = []
        if credential_list_dict:
            credential_list = [CredentialItem(**cred) for cred in credential_list_dict]
        return credential_list

    async def load_config(  # noqa: PLR0915
        self, router: Optional[llm.Router], config_file_path: str
    ):
        """
        Load config values into proxy global state
        """
        global master_key, user_config_file_path, otel_logging, user_custom_auth, user_custom_auth_path, user_custom_key_generate, user_custom_sso, use_background_health_checks, health_check_interval, use_queue, proxy_budget_rescheduler_max_time, proxy_budget_rescheduler_min_time, ui_access_mode, llm_master_key_hash, proxy_batch_write_at, disable_spend_logs, prompt_injection_detection_obj, redis_usage_cache, store_model_in_db, premium_user, open_telemetry_logger, health_check_details, callback_settings

        config: dict = await self.get_config(config_file_path=config_file_path)

        ## ENVIRONMENT VARIABLES
        environment_variables = config.get("environment_variables", None)
        if environment_variables:
            for key, value in environment_variables.items():
                os.environ[key] = str(get_secret(secret_name=key, default_value=value))

            # check if llm_license in general_settings
            if "LLM_LICENSE" in environment_variables:
                _license_check.license_str = os.getenv("LLM_LICENSE", None)
                premium_user = _license_check.is_premium()

        ## Callback settings
        callback_settings = config.get("callback_settings", None)

        ## LLM MODULE SETTINGS (e.g. llm.drop_params=True,..)
        llm_settings = config.get("llm_settings", None)
        if llm_settings is None:
            llm_settings = {}
        if llm_settings:
            # ANSI escape code for blue text
            blue_color_code = "\033[94m"
            reset_color_code = "\033[0m"
            for key, value in llm_settings.items():
                if key == "cache" and value is True:
                    print(f"{blue_color_code}\nSetting Cache on Proxy")  # noqa
                    from llm.caching.caching import Cache

                    cache_params = {}
                    if "cache_params" in llm_settings:
                        cache_params_in_config = llm_settings["cache_params"]
                        # overwrie cache_params with cache_params_in_config
                        cache_params.update(cache_params_in_config)

                    cache_type = cache_params.get("type", "redis")

                    verbose_proxy_logger.debug("passed cache type=%s", cache_type)

                    if (
                        cache_type == "redis" or cache_type == "redis-semantic"
                    ) and len(cache_params.keys()) == 0:
                        cache_host = get_secret("REDIS_HOST", None)
                        cache_port = get_secret("REDIS_PORT", None)
                        cache_password = None
                        cache_params.update(
                            {
                                "type": cache_type,
                                "host": cache_host,
                                "port": cache_port,
                            }
                        )

                        if get_secret("REDIS_PASSWORD", None) is not None:
                            cache_password = get_secret("REDIS_PASSWORD", None)
                            cache_params.update(
                                {
                                    "password": cache_password,
                                }
                            )

                        # Assuming cache_type, cache_host, cache_port, and cache_password are strings
                        verbose_proxy_logger.debug(
                            "%sCache Type:%s %s",
                            blue_color_code,
                            reset_color_code,
                            cache_type,
                        )
                        verbose_proxy_logger.debug(
                            "%sCache Host:%s %s",
                            blue_color_code,
                            reset_color_code,
                            cache_host,
                        )
                        verbose_proxy_logger.debug(
                            "%sCache Port:%s %s",
                            blue_color_code,
                            reset_color_code,
                            cache_port,
                        )
                        verbose_proxy_logger.debug(
                            "%sCache Password:%s %s",
                            blue_color_code,
                            reset_color_code,
                            cache_password,
                        )

                    # users can pass os.environ/ variables on the proxy - we should read them from the env
                    for key, value in cache_params.items():
                        if type(value) is str and value.startswith("os.environ/"):
                            cache_params[key] = get_secret(value)

                    ## to pass a complete url, or set ssl=True, etc. just set it as `os.environ[REDIS_URL] = <your-redis-url>`, _redis.py checks for REDIS specific environment variables
                    self._init_cache(cache_params=cache_params)
                    if llm.cache is not None:
                        verbose_proxy_logger.debug(
                            f"{blue_color_code}Set Cache on LLM Proxy{reset_color_code}"
                        )
                elif key == "cache" and value is False:
                    pass
                elif key == "guardrails":
                    guardrail_name_config_map = initialize_guardrails(
                        guardrails_config=value,
                        premium_user=premium_user,
                        config_file_path=config_file_path,
                        llm_settings=llm_settings,
                    )

                    llm.guardrail_name_config_map = guardrail_name_config_map
                elif key == "callbacks":

                    initialize_callbacks_on_proxy(
                        value=value,
                        premium_user=premium_user,
                        config_file_path=config_file_path,
                        llm_settings=llm_settings,
                    )

                elif key == "post_call_rules":
                    llm.post_call_rules = [
                        get_instance_fn(value=value, config_file_path=config_file_path)
                    ]
                    verbose_proxy_logger.debug(
                        f"llm.post_call_rules: {llm.post_call_rules}"
                    )
                elif key == "max_internal_user_budget":
                    llm.max_internal_user_budget = float(value)  # type: ignore
                elif key == "default_max_internal_user_budget":
                    llm.default_max_internal_user_budget = float(value)
                    if llm.max_internal_user_budget is None:
                        llm.max_internal_user_budget = (
                            llm.default_max_internal_user_budget
                        )
                elif key == "custom_provider_map":
                    from llm.utils import custom_llm_setup

                    llm.custom_provider_map = [
                        {
                            "provider": item["provider"],
                            "custom_handler": get_instance_fn(
                                value=item["custom_handler"],
                                config_file_path=config_file_path,
                            ),
                        }
                        for item in value
                    ]

                    custom_llm_setup()
                elif key == "success_callback":
                    llm.success_callback = []

                    # initialize success callbacks
                    for callback in value:
                        # user passed custom_callbacks.async_on_succes_logger. They need us to import a function
                        if "." in callback:
                            llm.logging_callback_manager.add_llm_success_callback(
                                get_instance_fn(value=callback)
                            )
                        # these are llm callbacks - "langfuse", "sentry", "wandb"
                        else:
                            llm.logging_callback_manager.add_llm_success_callback(
                                callback
                            )
                            if "prometheus" in callback:
                                verbose_proxy_logger.debug(
                                    "Starting Prometheus Metrics on /metrics"
                                )
                                from prometheus_client import make_asgi_app

                                # Add prometheus asgi middleware to route /metrics requests
                                metrics_app = make_asgi_app()
                                app.mount("/metrics", metrics_app)
                    print(  # noqa
                        f"{blue_color_code} Initialized Success Callbacks - {llm.success_callback} {reset_color_code}"
                    )  # noqa
                elif key == "failure_callback":
                    llm.failure_callback = []

                    # initialize success callbacks
                    for callback in value:
                        # user passed custom_callbacks.async_on_succes_logger. They need us to import a function
                        if "." in callback:
                            llm.logging_callback_manager.add_llm_failure_callback(
                                get_instance_fn(value=callback)
                            )
                        # these are llm callbacks - "langfuse", "sentry", "wandb"
                        else:
                            llm.logging_callback_manager.add_llm_failure_callback(
                                callback
                            )
                    print(  # noqa
                        f"{blue_color_code} Initialized Failure Callbacks - {llm.failure_callback} {reset_color_code}"
                    )  # noqa
                elif key == "cache_params":
                    # this is set in the cache branch
                    # see usage here: https://docs.hanzo.ai/docs/proxy/caching
                    pass
                elif key == "default_team_settings":
                    for idx, team_setting in enumerate(
                        value
                    ):  # run through pydantic validation
                        try:
                            TeamDefaultSettings(**team_setting)
                        except Exception:
                            if isinstance(team_setting, dict):
                                raise Exception(
                                    f"team_id missing from default_team_settings at index={idx}\npassed in value={team_setting.keys()}"
                                )
                            raise Exception(
                                f"team_id missing from default_team_settings at index={idx}\npassed in value={type(team_setting)}"
                            )
                    verbose_proxy_logger.debug(
                        f"{blue_color_code} setting llm.{key}={value}{reset_color_code}"
                    )
                    setattr(llm, key, value)
                elif key == "upperbound_key_generate_params":
                    if value is not None and isinstance(value, dict):
                        for _k, _v in value.items():
                            if isinstance(_v, str) and _v.startswith("os.environ/"):
                                value[_k] = get_secret(_v)
                        llm.upperbound_key_generate_params = (
                            LLM_UpperboundKeyGenerateParams(**value)
                        )
                    else:
                        raise Exception(
                            f"Invalid value set for upperbound_key_generate_params - value={value}"
                        )
                else:
                    verbose_proxy_logger.debug(
                        f"{blue_color_code} setting llm.{key}={value}{reset_color_code}"
                    )
                    setattr(llm, key, value)

        ## GENERAL SERVER SETTINGS (e.g. master key,..) # do this after initializing llm, to ensure sentry logging works for proxylogging
        general_settings = config.get("general_settings", {})
        if general_settings is None:
            general_settings = {}
        if general_settings:
            ### LOAD SECRET MANAGER ###
            key_management_system = general_settings.get("key_management_system", None)
            self.initialize_secret_manager(key_management_system=key_management_system)
            key_management_settings = general_settings.get(
                "key_management_settings", None
            )
            if key_management_settings is not None:
                llm._key_management_settings = KeyManagementSettings(
                    **key_management_settings
                )
            ### [DEPRECATED] LOAD FROM GOOGLE KMS ### old way of loading from google kms
            use_google_kms = general_settings.get("use_google_kms", False)
            load_google_kms(use_google_kms=use_google_kms)
            ### [DEPRECATED] LOAD FROM AZURE KEY VAULT ### old way of loading from azure secret manager
            use_azure_key_vault = general_settings.get("use_azure_key_vault", False)
            load_from_azure_key_vault(use_azure_key_vault=use_azure_key_vault)
            ### ALERTING ###
            self._load_alerting_settings(general_settings=general_settings)
            ### CONNECT TO DATABASE ###
            database_url = general_settings.get("database_url", None)
            if database_url and database_url.startswith("os.environ/"):
                verbose_proxy_logger.debug("GOING INTO LLM.GET_SECRET!")
                database_url = get_secret(database_url)
                verbose_proxy_logger.debug("RETRIEVED DB URL: %s", database_url)
            ### MASTER KEY ###
            master_key = general_settings.get(
                "master_key", get_secret("LLM_MASTER_KEY", None)
            )

            if master_key and master_key.startswith("os.environ/"):
                master_key = get_secret(master_key)  # type: ignore
                if not isinstance(master_key, str):
                    raise Exception(
                        "Master key must be a string. Current type - {}".format(
                            type(master_key)
                        )
                    )

            if master_key is not None and isinstance(master_key, str):
                llm_master_key_hash = hash_token(master_key)
            ### USER API KEY CACHE IN-MEMORY TTL ###
            user_api_key_cache_ttl = general_settings.get(
                "user_api_key_cache_ttl", None
            )
            if user_api_key_cache_ttl is not None:
                user_api_key_cache.update_cache_ttl(
                    default_in_memory_ttl=float(user_api_key_cache_ttl),
                    default_redis_ttl=None,  # user_api_key_cache is an in-memory cache
                )
            ### STORE MODEL IN DB ### feature flag for `/model/new`
            store_model_in_db = general_settings.get("store_model_in_db", False)
            if store_model_in_db is None:
                store_model_in_db = False
            ### CUSTOM API KEY AUTH ###
            ## pass filepath
            custom_auth = general_settings.get("custom_auth", None)
            if custom_auth is not None:
                user_custom_auth = get_instance_fn(
                    value=custom_auth, config_file_path=config_file_path
                )

            custom_key_generate = general_settings.get("custom_key_generate", None)
            if custom_key_generate is not None:
                user_custom_key_generate = get_instance_fn(
                    value=custom_key_generate, config_file_path=config_file_path
                )

            custom_sso = general_settings.get("custom_sso", None)
            if custom_sso is not None:
                user_custom_sso = get_instance_fn(
                    value=custom_sso, config_file_path=config_file_path
                )

            ## pass through endpoints
            if general_settings.get("pass_through_endpoints", None) is not None:
                await initialize_pass_through_endpoints(
                    pass_through_endpoints=general_settings["pass_through_endpoints"]
                )
            ## ADMIN UI ACCESS ##
            ui_access_mode = general_settings.get(
                "ui_access_mode", "all"
            )  # can be either ["admin_only" or "all"]
            ### ALLOWED IP ###
            allowed_ips = general_settings.get("allowed_ips", None)
            if allowed_ips is not None and premium_user is False:
                raise ValueError(
                    "allowed_ips is an Enterprise Feature. Please add a valid LLM_LICENSE to your envionment."
                )
            ## BUDGET RESCHEDULER ##
            proxy_budget_rescheduler_min_time = general_settings.get(
                "proxy_budget_rescheduler_min_time", proxy_budget_rescheduler_min_time
            )
            proxy_budget_rescheduler_max_time = general_settings.get(
                "proxy_budget_rescheduler_max_time", proxy_budget_rescheduler_max_time
            )
            ## BATCH WRITER ##
            proxy_batch_write_at = general_settings.get(
                "proxy_batch_write_at", proxy_batch_write_at
            )
            ## DISABLE SPEND LOGS ## - gives a perf improvement
            disable_spend_logs = general_settings.get(
                "disable_spend_logs", disable_spend_logs
            )
            ### BACKGROUND HEALTH CHECKS ###
            # Enable background health checks
            use_background_health_checks = general_settings.get(
                "background_health_checks", False
            )
            health_check_interval = general_settings.get("health_check_interval", 300)
            health_check_details = general_settings.get("health_check_details", True)

            ### RBAC ###
            rbac_role_permissions = general_settings.get("role_permissions", None)
            if rbac_role_permissions is not None:
                general_settings["role_permissions"] = [  # validate role permissions
                    RoleBasedPermissions(**role_permission)
                    for role_permission in rbac_role_permissions
                ]

            ## check if user has set a premium feature in general_settings
            if (
                general_settings.get("enforced_params") is not None
                and premium_user is not True
            ):
                raise ValueError(
                    "Trying to use `enforced_params`"
                    + CommonProxyErrors.not_premium_user.value
                )

            # check if llm_license in general_settings
            if "llm_license" in general_settings:
                _license_check.license_str = general_settings["llm_license"]
                premium_user = _license_check.is_premium()

        router_params: dict = {
            "cache_responses": llm.cache
            is not None,  # cache if user passed in cache values
        }
        ## MODEL LIST
        model_list = config.get("model_list", None)
        if model_list:
            router_params["model_list"] = model_list
            print(  # noqa
                "\033[32mLLM: Proxy initialized with Config, Set models:\033[0m"
            )  # noqa
            for model in model_list:
                ### LOAD FROM os.environ/ ###
                for k, v in model["llm_params"].items():
                    if isinstance(v, str) and v.startswith("os.environ/"):
                        model["llm_params"][k] = get_secret(v)
                print(f"\033[32m    {model.get('model_name', '')}\033[0m")  # noqa
                llm_model_name = model["llm_params"]["model"]
                llm_model_api_base = model["llm_params"].get("api_base", None)
                if "ollama" in llm_model_name and llm_model_api_base is None:
                    run_ollama_serve()

        ## ASSISTANT SETTINGS
        assistants_config: Optional[AssistantsTypedDict] = None
        assistant_settings = config.get("assistant_settings", None)
        if assistant_settings:
            for k, v in assistant_settings["llm_params"].items():
                if isinstance(v, str) and v.startswith("os.environ/"):
                    _v = v.replace("os.environ/", "")
                    v = os.getenv(_v)
                    assistant_settings["llm_params"][k] = v
            assistants_config = AssistantsTypedDict(**assistant_settings)  # type: ignore

        ## /fine_tuning/jobs endpoints config
        finetuning_config = config.get("finetune_settings", None)
        set_fine_tuning_config(config=finetuning_config)

        ## /files endpoint config
        files_config = config.get("files_settings", None)
        set_files_config(config=files_config)

        ## default config for vertex ai routes
        default_vertex_config = config.get("default_vertex_config", None)
        passthrough_endpoint_router.set_default_vertex_config(
            config=default_vertex_config
        )

        ## ROUTER SETTINGS (e.g. routing_strategy, ...)
        router_settings = config.get("router_settings", None)
        if router_settings and isinstance(router_settings, dict):
            arg_spec = inspect.getfullargspec(llm.Router)
            # model list already set
            exclude_args = {
                "self",
                "model_list",
            }

            available_args = [x for x in arg_spec.args if x not in exclude_args]

            for k, v in router_settings.items():
                if k in available_args:
                    router_params[k] = v
        router = llm.Router(
            **router_params,
            assistants_config=assistants_config,
            router_general_settings=RouterGeneralSettings(
                async_only_mode=True  # only init async clients
            ),
        )  # type:ignore

        if redis_usage_cache is not None and router.cache.redis_cache is None:
            router._update_redis_cache(cache=redis_usage_cache)

        # Guardrail settings
        guardrails_v2: Optional[List[Dict]] = None

        if config is not None:
            guardrails_v2 = config.get("guardrails", None)
        if guardrails_v2:
            init_guardrails_v2(
                all_guardrails=guardrails_v2, config_file_path=config_file_path
            )

        ## MCP TOOLS
        mcp_tools_config = config.get("mcp_tools", None)
        if mcp_tools_config:
            global_mcp_tool_registry.load_tools_from_config(mcp_tools_config)

        ## CREDENTIALS
        credential_list_dict = self.load_credential_list(config=config)
        llm.credential_list = credential_list_dict
        return router, router.get_model_list(), general_settings

    def _load_alerting_settings(self, general_settings: dict):
        """
        Initialize alerting settings
        """
        from llm.llm_core_utils.llm_logging import (
            _init_custom_logger_compatible_class,
        )

        _alerting_callbacks = general_settings.get("alerting", None)
        verbose_proxy_logger.debug(f"_alerting_callbacks: {general_settings}")
        if _alerting_callbacks is None:
            return
        for _alert in _alerting_callbacks:
            if _alert == "slack":
                # [OLD] v0 implementation
                proxy_logging_obj.update_values(
                    alerting=general_settings.get("alerting", None),
                    alerting_threshold=general_settings.get("alerting_threshold", 600),
                    alert_types=general_settings.get("alert_types", None),
                    alert_to_webhook_url=general_settings.get(
                        "alert_to_webhook_url", None
                    ),
                    alerting_args=general_settings.get("alerting_args", None),
                    redis_cache=redis_usage_cache,
                )
            else:
                # [NEW] v1 implementation - init as a custom logger
                if _alert in llm._known_custom_logger_compatible_callbacks:
                    _logger = _init_custom_logger_compatible_class(
                        logging_integration=_alert,
                        internal_usage_cache=None,
                        llm_router=None,
                        custom_logger_init_args={
                            "alerting_args": general_settings.get("alerting_args", None)
                        },
                    )
                    if _logger is not None:
                        llm.logging_callback_manager.add_llm_callback(_logger)
        pass

    def initialize_secret_manager(self, key_management_system: Optional[str]):
        """
        Initialize the relevant secret manager if `key_management_system` is provided
        """
        if key_management_system is not None:
            if key_management_system == KeyManagementSystem.AZURE_KEY_VAULT.value:
                ### LOAD FROM AZURE KEY VAULT ###
                load_from_azure_key_vault(use_azure_key_vault=True)
            elif key_management_system == KeyManagementSystem.GOOGLE_KMS.value:
                ### LOAD FROM GOOGLE KMS ###
                load_google_kms(use_google_kms=True)
            elif (
                key_management_system
                == KeyManagementSystem.AWS_SECRET_MANAGER.value  # noqa: F405
            ):
                from llm.secret_managers.aws_secret_manager_v2 import (
                    AWSSecretsManagerV2,
                )

                AWSSecretsManagerV2.load_aws_secret_manager(use_aws_secret_manager=True)
            elif key_management_system == KeyManagementSystem.AWS_KMS.value:
                load_aws_kms(use_aws_kms=True)
            elif (
                key_management_system == KeyManagementSystem.GOOGLE_SECRET_MANAGER.value
            ):
                from llm.secret_managers.google_secret_manager import (
                    GoogleSecretManager,
                )

                GoogleSecretManager()
            elif key_management_system == KeyManagementSystem.HASHICORP_VAULT.value:
                from llm.secret_managers.hashicorp_secret_manager import (
                    HashicorpSecretManager,
                )

                HashicorpSecretManager()
            else:
                raise ValueError("Invalid Key Management System selected")

    def get_model_info_with_id(self, model, db_model=False) -> RouterModelInfo:
        """
        Common logic across add + delete router models
        Parameters:
        - deployment
        - db_model -> flag for differentiating model stored in db vs. config -> used on UI

        Return model info w/ id
        """
        _id: Optional[str] = getattr(model, "model_id", None)
        if _id is not None:
            model.model_info["id"] = _id
            model.model_info["db_model"] = True

        if premium_user is True:
            # seeing "created_at", "updated_at", "created_by", "updated_by" is a LLM Enterprise Feature
            model.model_info["created_at"] = getattr(model, "created_at", None)
            model.model_info["updated_at"] = getattr(model, "updated_at", None)
            model.model_info["created_by"] = getattr(model, "created_by", None)
            model.model_info["updated_by"] = getattr(model, "updated_by", None)

        if model.model_info is not None and isinstance(model.model_info, dict):
            if "id" not in model.model_info:
                model.model_info["id"] = model.model_id
            if "db_model" in model.model_info and model.model_info["db_model"] is False:
                model.model_info["db_model"] = db_model
            _model_info = RouterModelInfo(**model.model_info)

        else:
            _model_info = RouterModelInfo(id=model.model_id, db_model=db_model)
        return _model_info

    async def _delete_deployment(self, db_models: list) -> int:
        """
        (Helper function of add deployment) -> combined to reduce prisma db calls

        - Create all up list of model id's (db + config)
        - Compare all up list to router model id's
        - Remove any that are missing

        Return:
        - int - returns number of deleted deployments
        """
        global user_config_file_path, llm_router
        combined_id_list = []

        ## BASE CASES ##
        # if llm_router is None or db_models is empty, return 0
        if llm_router is None or len(db_models) == 0:
            return 0

        ## DB MODELS ##
        for m in db_models:
            model_info = self.get_model_info_with_id(model=m)
            if model_info.id is not None:
                combined_id_list.append(model_info.id)

        ## CONFIG MODELS ##
        config = await self.get_config(config_file_path=user_config_file_path)
        model_list = config.get("model_list", None)
        if model_list:
            for model in model_list:
                ### LOAD FROM os.environ/ ###
                for k, v in model["llm_params"].items():
                    if isinstance(v, str) and v.startswith("os.environ/"):
                        model["llm_params"][k] = get_secret(v)

                ## check if they have model-id's ##
                model_id = model.get("model_info", {}).get("id", None)
                if model_id is None:
                    ## else - generate stable id's ##
                    model_id = llm_router._generate_model_id(
                        model_group=model["model_name"],
                        llm_params=model["llm_params"],
                    )
                combined_id_list.append(model_id)  # ADD CONFIG MODEL TO COMBINED LIST

        router_model_ids = llm_router.get_model_ids()
        # Check for model IDs in llm_router not present in combined_id_list and delete them

        deleted_deployments = 0
        for model_id in router_model_ids:
            if model_id not in combined_id_list:
                is_deleted = llm_router.delete_deployment(id=model_id)
                if is_deleted is not None:
                    deleted_deployments += 1
        return deleted_deployments

    def _add_deployment(self, db_models: list) -> int:
        """
        Iterate through db models

        for any not in router - add them.

        Return - number of deployments added
        """
        import base64

        if master_key is None or not isinstance(master_key, str):
            raise Exception(
                f"Master key is not initialized or formatted. master_key={master_key}"
            )

        if llm_router is None:
            return 0

        added_models = 0
        ## ADD MODEL LOGIC
        for m in db_models:
            _llm_params = m.llm_params
            if isinstance(_llm_params, dict):
                # decrypt values
                for k, v in _llm_params.items():
                    if isinstance(v, str):
                        # decrypt value
                        _value = decrypt_value_helper(value=v)
                        if _value is None:
                            raise Exception("Unable to decrypt value={}".format(v))
                        # sanity check if string > size 0
                        if len(_value) > 0:
                            _llm_params[k] = _value
                _llm_params = LLM_Params(**_llm_params)

            else:
                verbose_proxy_logger.error(
                    f"Invalid model added to proxy db. Invalid llm params. llm_params={_llm_params}"
                )
                continue  # skip to next model
            _model_info = self.get_model_info_with_id(
                model=m, db_model=True
            )  ## 👈 FLAG = True for db_models

            added = llm_router.upsert_deployment(
                deployment=Deployment(
                    model_name=m.model_name,
                    llm_params=_llm_params,
                    model_info=_model_info,
                )
            )

            if added is not None:
                added_models += 1
        return added_models

    def decrypt_model_list_from_db(self, new_models: list) -> list:
        _model_list: list = []
        for m in new_models:
            _llm_params = m.llm_params
            if isinstance(_llm_params, dict):
                # decrypt values
                for k, v in _llm_params.items():
                    decrypted_value = decrypt_value_helper(value=v)
                    _llm_params[k] = decrypted_value
                _llm_params = LLM_Params(**_llm_params)
            else:
                verbose_proxy_logger.error(
                    f"Invalid model added to proxy db. Invalid llm params. llm_params={_llm_params}"
                )
                continue  # skip to next model

            _model_info = self.get_model_info_with_id(model=m)
            _model_list.append(
                Deployment(
                    model_name=m.model_name,
                    llm_params=_llm_params,
                    model_info=_model_info,
                ).to_json(exclude_none=True)
            )

        return _model_list

    async def _update_llm_router(
        self,
        new_models: list,
        proxy_logging_obj: ProxyLogging,
    ):
        global llm_router, llm_model_list, master_key, general_settings

        try:
            if llm_router is None and master_key is not None:
                verbose_proxy_logger.debug(f"len new_models: {len(new_models)}")

                _model_list: list = self.decrypt_model_list_from_db(
                    new_models=new_models
                )
                if len(_model_list) > 0:
                    verbose_proxy_logger.debug(f"_model_list: {_model_list}")
                    llm_router = llm.Router(
                        model_list=_model_list,
                        router_general_settings=RouterGeneralSettings(
                            async_only_mode=True  # only init async clients
                        ),
                    )
                    verbose_proxy_logger.debug(f"updated llm_router: {llm_router}")
            else:
                verbose_proxy_logger.debug(f"len new_models: {len(new_models)}")
                ## DELETE MODEL LOGIC
                await self._delete_deployment(db_models=new_models)

                ## ADD MODEL LOGIC
                self._add_deployment(db_models=new_models)

        except Exception as e:
            verbose_proxy_logger.exception(
                f"Error adding/deleting model to llm_router: {str(e)}"
            )

        if llm_router is not None:
            llm_model_list = llm_router.get_model_list()

        # check if user set any callbacks in Config Table
        config_data = await proxy_config.get_config()
        self._add_callbacks_from_db_config(config_data)

        # we need to set env variables too
        self._add_environment_variables_from_db_config(config_data)

        # router settings
        await self._add_router_settings_from_db_config(
            config_data=config_data, llm_router=llm_router, prisma_client=prisma_client
        )

        # general settings
        self._add_general_settings_from_db_config(
            config_data=config_data,
            general_settings=general_settings,
            proxy_logging_obj=proxy_logging_obj,
        )

    def _add_callbacks_from_db_config(self, config_data: dict) -> None:
        """
        Adds callbacks from DB config to llm
        """
        llm_settings = config_data.get("llm_settings", {}) or {}
        success_callbacks = llm_settings.get("success_callback", None)
        failure_callbacks = llm_settings.get("failure_callback", None)

        if success_callbacks is not None and isinstance(success_callbacks, list):
            for success_callback in success_callbacks:
                if (
                    success_callback
                    in llm._known_custom_logger_compatible_callbacks
                ):
                    _add_custom_logger_callback_to_specific_event(
                        success_callback, "success"
                    )
                elif success_callback not in llm.success_callback:
                    llm.logging_callback_manager.add_llm_success_callback(
                        success_callback
                    )

        # Add failure callbacks from DB to llm
        if failure_callbacks is not None and isinstance(failure_callbacks, list):
            for failure_callback in failure_callbacks:
                if (
                    failure_callback
                    in llm._known_custom_logger_compatible_callbacks
                ):
                    _add_custom_logger_callback_to_specific_event(
                        failure_callback, "failure"
                    )
                elif failure_callback not in llm.failure_callback:
                    llm.logging_callback_manager.add_llm_failure_callback(
                        failure_callback
                    )

    def _add_environment_variables_from_db_config(self, config_data: dict) -> None:
        """
        Adds environment variables from DB config to llm
        """
        environment_variables = config_data.get("environment_variables", {})
        self._decrypt_and_set_db_env_variables(environment_variables)

    def _encrypt_env_variables(
        self, environment_variables: dict, new_encryption_key: Optional[str] = None
    ) -> dict:
        """
        Encrypts a dictionary of environment variables and returns them.
        """
        encrypted_env_vars = {}
        for k, v in environment_variables.items():
            encrypted_value = encrypt_value_helper(
                value=v, new_encryption_key=new_encryption_key
            )
            encrypted_env_vars[k] = encrypted_value
        return encrypted_env_vars

    def _decrypt_and_set_db_env_variables(self, environment_variables: dict) -> dict:
        """
        Decrypts a dictionary of environment variables and then sets them in the environment

        Args:
            environment_variables: dict - dictionary of environment variables to decrypt and set
            eg. `{"LANGFUSE_PUBLIC_KEY": "kFiKa1VZukMmD8RB6WXB9F......."}`
        """
        decrypted_env_vars = {}
        for k, v in environment_variables.items():
            try:
                decrypted_value = decrypt_value_helper(value=v)
                if decrypted_value is not None:
                    os.environ[k] = decrypted_value
                    decrypted_env_vars[k] = decrypted_value
            except Exception as e:
                verbose_proxy_logger.error(
                    "Error setting env variable: %s - %s", k, str(e)
                )
        return decrypted_env_vars

    async def _add_router_settings_from_db_config(
        self,
        config_data: dict,
        llm_router: Optional[Router],
        prisma_client: Optional[PrismaClient],
    ) -> None:
        """
        Adds router settings from DB config to llm proxy
        """
        if llm_router is not None and prisma_client is not None:
            db_router_settings = await prisma_client.db.llm_config.find_first(
                where={"param_name": "router_settings"}
            )
            if (
                db_router_settings is not None
                and db_router_settings.param_value is not None
            ):
                _router_settings = db_router_settings.param_value
                llm_router.update_settings(**_router_settings)

    def _add_general_settings_from_db_config(
        self, config_data: dict, general_settings: dict, proxy_logging_obj: ProxyLogging
    ) -> None:
        """
        Adds general settings from DB config to llm proxy

        Args:
            config_data: dict
            general_settings: dict - global general_settings currently in use
            proxy_logging_obj: ProxyLogging
        """
        _general_settings = config_data.get("general_settings", {})
        if "alerting" in _general_settings:
            if (
                general_settings is not None
                and general_settings.get("alerting", None) is not None
                and isinstance(general_settings["alerting"], list)
                and _general_settings.get("alerting", None) is not None
                and isinstance(_general_settings["alerting"], list)
            ):
                verbose_proxy_logger.debug(
                    "Overriding Default 'alerting' values with db 'alerting' values."
                )
                general_settings["alerting"] = _general_settings[
                    "alerting"
                ]  # override yaml values with db
                proxy_logging_obj.alerting = general_settings["alerting"]
                proxy_logging_obj.slack_alerting_instance.alerting = general_settings[
                    "alerting"
                ]
            elif general_settings is None:
                general_settings = {}
                general_settings["alerting"] = _general_settings["alerting"]
                proxy_logging_obj.alerting = general_settings["alerting"]
                proxy_logging_obj.slack_alerting_instance.alerting = general_settings[
                    "alerting"
                ]
            elif isinstance(general_settings, dict):
                general_settings["alerting"] = _general_settings["alerting"]
                proxy_logging_obj.alerting = general_settings["alerting"]
                proxy_logging_obj.slack_alerting_instance.alerting = general_settings[
                    "alerting"
                ]

        if "alert_types" in _general_settings:
            general_settings["alert_types"] = _general_settings["alert_types"]
            proxy_logging_obj.alert_types = general_settings["alert_types"]
            proxy_logging_obj.slack_alerting_instance.update_values(
                alert_types=general_settings["alert_types"], llm_router=llm_router
            )

        if "alert_to_webhook_url" in _general_settings:
            general_settings["alert_to_webhook_url"] = _general_settings[
                "alert_to_webhook_url"
            ]
            proxy_logging_obj.slack_alerting_instance.update_values(
                alert_to_webhook_url=general_settings["alert_to_webhook_url"],
                llm_router=llm_router,
            )

    async def _update_general_settings(self, db_general_settings: Optional[Json]):
        """
        Pull from DB, read general settings value
        """
        global general_settings
        if db_general_settings is None:
            return
        _general_settings = dict(db_general_settings)
        ## MAX PARALLEL REQUESTS ##
        if "max_parallel_requests" in _general_settings:
            general_settings["max_parallel_requests"] = _general_settings[
                "max_parallel_requests"
            ]

        if "global_max_parallel_requests" in _general_settings:
            general_settings["global_max_parallel_requests"] = _general_settings[
                "global_max_parallel_requests"
            ]

        ## ALERTING ARGS ##
        if "alerting_args" in _general_settings:
            general_settings["alerting_args"] = _general_settings["alerting_args"]
            proxy_logging_obj.slack_alerting_instance.update_values(
                alerting_args=general_settings["alerting_args"],
            )

        ## PASS-THROUGH ENDPOINTS ##
        if "pass_through_endpoints" in _general_settings:
            general_settings["pass_through_endpoints"] = _general_settings[
                "pass_through_endpoints"
            ]
            await initialize_pass_through_endpoints(
                pass_through_endpoints=general_settings["pass_through_endpoints"]
            )

    def _update_config_fields(
        self,
        current_config: dict,
        param_name: Literal[
            "general_settings",
            "router_settings",
            "llm_settings",
            "environment_variables",
        ],
        db_param_value: Any,
    ) -> dict:
        """
        Updates the config fields with the new values from the DB

        Args:
            current_config (dict): Current configuration dictionary to update
            param_name (Literal): Name of the parameter to update
            db_param_value (Any): New value from the database

        Returns:
            dict: Updated configuration dictionary
        """
        if param_name == "environment_variables":
            self._decrypt_and_set_db_env_variables(db_param_value)
            return current_config

        # If param doesn't exist in config, add it
        if param_name not in current_config:
            current_config[param_name] = db_param_value
            return current_config

        # For dictionary values, update only non-empty values
        if isinstance(current_config[param_name], dict):
            # Only keep non None values from db_param_value
            non_empty_values = {k: v for k, v in db_param_value.items() if v}

            # Update the config with non-empty values
            current_config[param_name].update(non_empty_values)
        else:
            current_config[param_name] = db_param_value
        return current_config

    async def _update_config_from_db(
        self,
        prisma_client: PrismaClient,
        config: dict,
        store_model_in_db: Optional[bool],
    ):
        if store_model_in_db is not True:
            verbose_proxy_logger.info(
                "'store_model_in_db' is not True, skipping db updates"
            )
            return config

        _tasks = []
        keys = [
            "general_settings",
            "router_settings",
            "llm_settings",
            "environment_variables",
        ]
        for k in keys:
            response = prisma_client.get_generic_data(
                key="param_name", value=k, table_name="config"
            )
            _tasks.append(response)

        responses = await asyncio.gather(*_tasks)
        for response in responses:
            if response is None:
                continue

            param_name = getattr(response, "param_name", None)
            param_value = getattr(response, "param_value", None)
            verbose_proxy_logger.debug(
                f"param_name={param_name}, param_value={param_value}"
            )

            if param_name is not None and param_value is not None:
                config = self._update_config_fields(
                    current_config=config,
                    param_name=param_name,
                    db_param_value=param_value,
                )

        return config

    async def _get_models_from_db(self, prisma_client: PrismaClient) -> list:
        try:
            new_models = await prisma_client.db.llm_proxymodeltable.find_many()
        except Exception as e:
            verbose_proxy_logger.exception(
                "llm.proxy_server.py::add_deployment() - Error getting new models from DB - {}".format(
                    str(e)
                )
            )
            new_models = []

        return new_models

    async def add_deployment(
        self,
        prisma_client: PrismaClient,
        proxy_logging_obj: ProxyLogging,
    ):
        """
        - Check db for new models
        - Check if model id's in router already
        - If not, add to router
        """
        global llm_router, llm_model_list, master_key, general_settings

        try:
            if master_key is None or not isinstance(master_key, str):
                raise ValueError(
                    f"Master key is not initialized or formatted. master_key={master_key}"
                )

            new_models = await self._get_models_from_db(prisma_client=prisma_client)

            # update llm router
            await self._update_llm_router(
                new_models=new_models, proxy_logging_obj=proxy_logging_obj
            )

            db_general_settings = await prisma_client.db.llm_config.find_first(
                where={"param_name": "general_settings"}
            )

            # update general settings
            if db_general_settings is not None:
                await self._update_general_settings(
                    db_general_settings=db_general_settings.param_value,
                )

        except Exception as e:
            verbose_proxy_logger.exception(
                "llm.proxy.proxy_server.py::ProxyConfig:add_deployment - {}".format(
                    str(e)
                )
            )

    def decrypt_credentials(self, credential: Union[dict, BaseModel]) -> CredentialItem:
        if isinstance(credential, dict):
            credential_object = CredentialItem(**credential)
        elif isinstance(credential, BaseModel):
            credential_object = CredentialItem(**credential.model_dump())

        decrypted_credential_values = {}
        for k, v in credential_object.credential_values.items():
            decrypted_credential_values[k] = decrypt_value_helper(v) or v

        credential_object.credential_values = decrypted_credential_values
        return credential_object

    async def delete_credentials(self, db_credentials: List[CredentialItem]):
        """
        Create all-up list of db credentials + local credentials
        Compare to the llm.credential_list
        Delete any from llm.credential_list that are not in the all-up list
        """
        ## CONFIG credentials ##
        config = await self.get_config(config_file_path=user_config_file_path)
        credential_list = self.load_credential_list(config=config)

        ## COMBINED LIST ##
        combined_list = db_credentials + credential_list

        ## DELETE ##
        idx_to_delete = []
        for idx, credential in enumerate(llm.credential_list):
            if credential.credential_name not in [
                cred.credential_name for cred in combined_list
            ]:
                idx_to_delete.append(idx)
        for idx in sorted(idx_to_delete, reverse=True):
            llm.credential_list.pop(idx)

    async def get_credentials(self, prisma_client: PrismaClient):
        try:
            credentials = await prisma_client.db.llm_credentialstable.find_many()
            credentials = [self.decrypt_credentials(cred) for cred in credentials]
            await self.delete_credentials(
                credentials
            )  # delete credentials that are not in the all-up list
            CredentialAccessor.upsert_credentials(
                credentials
            )  # upsert credentials that are in the all-up list
        except Exception as e:
            verbose_proxy_logger.exception(
                "llm.proxy_server.py::get_credentials() - Error getting credentials from DB - {}".format(
                    str(e)
                )
            )
            return []


proxy_config = ProxyConfig()


def save_worker_config(**data):
    import json

    os.environ["WORKER_CONFIG"] = json.dumps(data)


async def initialize(  # noqa: PLR0915
    model=None,
    alias=None,
    api_base=None,
    api_version=None,
    debug=False,
    detailed_debug=False,
    temperature=None,
    max_tokens=None,
    request_timeout=600,
    max_budget=None,
    telemetry=False,
    drop_params=True,
    add_function_to_prompt=True,
    headers=None,
    save=False,
    use_queue=False,
    config=None,
):
    global user_model, user_api_base, user_debug, user_detailed_debug, user_user_max_tokens, user_request_timeout, user_temperature, user_telemetry, user_headers, experimental, llm_model_list, llm_router, general_settings, master_key, user_custom_auth, prisma_client
    user_model = model
    user_debug = debug
    if debug is True:  # this needs to be first, so users can see Router init debugg
        import logging

        from llm._logging import (
            verbose_logger,
            verbose_proxy_logger,
            verbose_router_logger,
        )

        # this must ALWAYS remain logging.INFO, DO NOT MODIFY THIS
        verbose_logger.setLevel(level=logging.INFO)  # sets package logs to info
        verbose_router_logger.setLevel(level=logging.INFO)  # set router logs to info
        verbose_proxy_logger.setLevel(level=logging.INFO)  # set proxy logs to info
    if detailed_debug is True:
        import logging

        from llm._logging import (
            verbose_logger,
            verbose_proxy_logger,
            verbose_router_logger,
        )

        verbose_logger.setLevel(level=logging.DEBUG)  # set package log to debug
        verbose_router_logger.setLevel(level=logging.DEBUG)  # set router logs to debug
        verbose_proxy_logger.setLevel(level=logging.DEBUG)  # set proxy logs to debug
    elif debug is False and detailed_debug is False:
        # users can control proxy debugging using env variable = 'LLM_LOG'
        llm_log_setting = os.environ.get("LLM_LOG", "")
        if llm_log_setting is not None:
            if llm_log_setting.upper() == "INFO":
                import logging

                from llm._logging import verbose_proxy_logger, verbose_router_logger

                # this must ALWAYS remain logging.INFO, DO NOT MODIFY THIS

                verbose_router_logger.setLevel(
                    level=logging.INFO
                )  # set router logs to info
                verbose_proxy_logger.setLevel(
                    level=logging.INFO
                )  # set proxy logs to info
            elif llm_log_setting.upper() == "DEBUG":
                import logging

                from llm._logging import verbose_proxy_logger, verbose_router_logger

                verbose_router_logger.setLevel(
                    level=logging.DEBUG
                )  # set router logs to info
                verbose_proxy_logger.setLevel(
                    level=logging.DEBUG
                )  # set proxy logs to debug
    dynamic_config = {"general": {}, user_model: {}}
    if config:
        (
            llm_router,
            llm_model_list,
            general_settings,
        ) = await proxy_config.load_config(router=llm_router, config_file_path=config)
    if headers:  # model-specific param
        user_headers = headers
        dynamic_config[user_model]["headers"] = headers
    if api_base:  # model-specific param
        user_api_base = api_base
        dynamic_config[user_model]["api_base"] = api_base
    if api_version:
        os.environ["AZURE_API_VERSION"] = (
            api_version  # set this for azure - llm can read this from the env
        )
    if max_tokens:  # model-specific param
        dynamic_config[user_model]["max_tokens"] = max_tokens
    if temperature:  # model-specific param
        user_temperature = temperature
        dynamic_config[user_model]["temperature"] = temperature
    if request_timeout:
        user_request_timeout = request_timeout
        dynamic_config[user_model]["request_timeout"] = request_timeout
    if alias:  # model-specific param
        dynamic_config[user_model]["alias"] = alias
    if drop_params is True:  # llm-specific param
        llm.drop_params = True
        dynamic_config["general"]["drop_params"] = True
    if add_function_to_prompt is True:  # llm-specific param
        llm.add_function_to_prompt = True
        dynamic_config["general"]["add_function_to_prompt"] = True
    if max_budget:  # llm-specific param
        llm.max_budget = max_budget
        dynamic_config["general"]["max_budget"] = max_budget
    if experimental:
        pass
    user_telemetry = telemetry


# for streaming
def data_generator(response):
    verbose_proxy_logger.debug("inside generator")
    for chunk in response:
        verbose_proxy_logger.debug("returned chunk: %s", chunk)
        try:
            yield f"data: {json.dumps(chunk.dict())}\n\n"
        except Exception:
            yield f"data: {json.dumps(chunk)}\n\n"


async def async_assistants_data_generator(
    response, user_api_key_dict: UserAPIKeyAuth, request_data: dict
):
    verbose_proxy_logger.debug("inside generator")
    try:
        time.time()
        async with response as chunk:

            ### CALL HOOKS ### - modify outgoing data
            chunk = await proxy_logging_obj.async_post_call_streaming_hook(
                user_api_key_dict=user_api_key_dict, response=chunk
            )

            # chunk = chunk.model_dump_json(exclude_none=True)
            async for c in chunk:  # type: ignore
                c = c.model_dump_json(exclude_none=True)
                try:
                    yield f"data: {c}\n\n"
                except Exception as e:
                    yield f"data: {str(e)}\n\n"

        # Streaming is done, yield the [DONE] chunk
        done_message = "[DONE]"
        yield f"data: {done_message}\n\n"
    except Exception as e:
        verbose_proxy_logger.exception(
            "llm.proxy.proxy_server.async_assistants_data_generator(): Exception occured - {}".format(
                str(e)
            )
        )
        await proxy_logging_obj.post_call_failure_hook(
            user_api_key_dict=user_api_key_dict,
            original_exception=e,
            request_data=request_data,
        )
        verbose_proxy_logger.debug(
            f"\033[1;31mAn error occurred: {e}\n\n Debug this by setting `--debug`, e.g. `llm --model gpt-3.5-turbo --debug`"
        )
        if isinstance(e, HTTPException):
            raise e
        else:
            error_traceback = traceback.format_exc()
            error_msg = f"{str(e)}\n\n{error_traceback}"

        proxy_exception = ProxyException(
            message=getattr(e, "message", error_msg),
            type=getattr(e, "type", "None"),
            param=getattr(e, "param", "None"),
            code=getattr(e, "status_code", 500),
        )
        error_returned = json.dumps({"error": proxy_exception.to_dict()})
        yield f"data: {error_returned}\n\n"


async def async_data_generator(
    response, user_api_key_dict: UserAPIKeyAuth, request_data: dict
):
    verbose_proxy_logger.debug("inside generator")
    try:
        async for chunk in proxy_logging_obj.async_post_call_streaming_iterator_hook(
            user_api_key_dict=user_api_key_dict,
            response=response,
            request_data=request_data,
        ):
            verbose_proxy_logger.debug(
                "async_data_generator: received streaming chunk - {}".format(chunk)
            )
            ### CALL HOOKS ### - modify outgoing data
            chunk = await proxy_logging_obj.async_post_call_streaming_hook(
                user_api_key_dict=user_api_key_dict, response=chunk
            )

            if isinstance(chunk, BaseModel):
                chunk = chunk.model_dump_json(exclude_none=True, exclude_unset=True)

            try:
                yield f"data: {chunk}\n\n"
            except Exception as e:
                yield f"data: {str(e)}\n\n"

        # Streaming is done, yield the [DONE] chunk
        done_message = "[DONE]"
        yield f"data: {done_message}\n\n"
    except Exception as e:
        verbose_proxy_logger.exception(
            "llm.proxy.proxy_server.async_data_generator(): Exception occured - {}".format(
                str(e)
            )
        )
        await proxy_logging_obj.post_call_failure_hook(
            user_api_key_dict=user_api_key_dict,
            original_exception=e,
            request_data=request_data,
        )
        verbose_proxy_logger.debug(
            f"\033[1;31mAn error occurred: {e}\n\n Debug this by setting `--debug`, e.g. `llm --model gpt-3.5-turbo --debug`"
        )

        if isinstance(e, HTTPException):
            raise e
        elif isinstance(e, StreamingCallbackError):
            error_msg = str(e)
        else:
            error_traceback = traceback.format_exc()
            error_msg = f"{str(e)}\n\n{error_traceback}"

        proxy_exception = ProxyException(
            message=getattr(e, "message", error_msg),
            type=getattr(e, "type", "None"),
            param=getattr(e, "param", "None"),
            code=getattr(e, "status_code", 500),
        )
        error_returned = json.dumps({"error": proxy_exception.to_dict()})
        yield f"data: {error_returned}\n\n"


def select_data_generator(
    response, user_api_key_dict: UserAPIKeyAuth, request_data: dict
):
    return async_data_generator(
        response=response,
        user_api_key_dict=user_api_key_dict,
        request_data=request_data,
    )


def get_llm_model_info(model: dict = {}):
    model_info = model.get("model_info", {})
    model_to_lookup = model.get("llm_params", {}).get("model", None)
    try:
        if "azure" in model_to_lookup:
            model_to_lookup = model_info.get("base_model", None)
        llm_model_info = llm.get_model_info(model_to_lookup)
        return llm_model_info
    except Exception:
        # this should not block returning on /model/info
        # if llm does not have info on the model it should return {}
        return {}


def on_backoff(details):
    # The 'tries' key in the details dictionary contains the number of completed tries
    verbose_proxy_logger.debug("Backing off... this was attempt # %s", details["tries"])


def giveup(e):
    result = not (
        isinstance(e, ProxyException)
        and getattr(e, "message", None) is not None
        and isinstance(e.message, str)
        and "Max parallel request limit reached" in e.message
    )

    if (
        general_settings.get("disable_retry_on_max_parallel_request_limit_error")
        is True
    ):
        return True  # giveup if queuing max parallel request limits is disabled

    if result:
        verbose_proxy_logger.info(json.dumps({"event": "giveup", "exception": str(e)}))
    return result


class ProxyStartupEvent:
    @classmethod
    def _initialize_startup_logging(
        cls,
        llm_router: Optional[Router],
        proxy_logging_obj: ProxyLogging,
        redis_usage_cache: Optional[RedisCache],
    ):
        """Initialize logging and alerting on startup"""
        ## COST TRACKING ##
        cost_tracking()

        proxy_logging_obj.startup_event(
            llm_router=llm_router, redis_usage_cache=redis_usage_cache
        )

    @classmethod
    def _initialize_jwt_auth(
        cls,
        general_settings: dict,
        prisma_client: Optional[PrismaClient],
        user_api_key_cache: DualCache,
    ):
        """Initialize JWT auth on startup"""
        if general_settings.get("llm_jwtauth", None) is not None:
            for k, v in general_settings["llm_jwtauth"].items():
                if isinstance(v, str) and v.startswith("os.environ/"):
                    general_settings["llm_jwtauth"][k] = get_secret(v)
            llm_jwtauth = LLM_JWTAuth(**general_settings["llm_jwtauth"])
        else:
            llm_jwtauth = LLM_JWTAuth()
        jwt_handler.update_environment(
            prisma_client=prisma_client,
            user_api_key_cache=user_api_key_cache,
            llm_jwtauth=llm_jwtauth,
        )

    @classmethod
    def _add_proxy_budget_to_db(cls, llm_proxy_budget_name: str):
        """Adds a global proxy budget to db"""
        if llm.budget_duration is None:
            raise Exception(
                "budget_duration not set on Proxy. budget_duration is required to use max_budget."
            )

        # add proxy budget to db in the user table
        asyncio.create_task(
            generate_key_helper_fn(  # type: ignore
                request_type="user",
                user_id=llm_proxy_budget_name,
                duration=None,
                models=[],
                aliases={},
                config={},
                spend=0,
                max_budget=llm.max_budget,
                budget_duration=llm.budget_duration,
                query_type="update_data",
                update_key_values={
                    "max_budget": llm.max_budget,
                    "budget_duration": llm.budget_duration,
                },
            )
        )

    @classmethod
    async def initialize_scheduled_background_jobs(
        cls,
        general_settings: dict,
        prisma_client: PrismaClient,
        proxy_budget_rescheduler_min_time: int,
        proxy_budget_rescheduler_max_time: int,
        proxy_batch_write_at: int,
        proxy_logging_obj: ProxyLogging,
    ):
        """Initializes scheduled background jobs"""
        global store_model_in_db
        scheduler = AsyncIOScheduler()
        interval = random.randint(
            proxy_budget_rescheduler_min_time, proxy_budget_rescheduler_max_time
        )  # random interval, so multiple workers avoid resetting budget at the same time
        batch_writing_interval = random.randint(
            proxy_batch_write_at - 3, proxy_batch_write_at + 3
        )  # random interval, so multiple workers avoid batch writing at the same time

        ### RESET BUDGET ###
        if general_settings.get("disable_reset_budget", False) is False:
            budget_reset_job = ResetBudgetJob(
                proxy_logging_obj=proxy_logging_obj,
                prisma_client=prisma_client,
            )
            scheduler.add_job(
                budget_reset_job.reset_budget,
                "interval",
                seconds=interval,
            )

        ### UPDATE SPEND ###
        scheduler.add_job(
            update_spend,
            "interval",
            seconds=batch_writing_interval,
            args=[prisma_client, db_writer_client, proxy_logging_obj],
        )

        ### ADD NEW MODELS ###
        store_model_in_db = (
            get_secret_bool("STORE_MODEL_IN_DB", store_model_in_db) or store_model_in_db
        )

        if store_model_in_db is True:
            scheduler.add_job(
                proxy_config.add_deployment,
                "interval",
                seconds=10,
                args=[prisma_client, proxy_logging_obj],
            )

            # this will load all existing models on proxy startup
            await proxy_config.add_deployment(
                prisma_client=prisma_client, proxy_logging_obj=proxy_logging_obj
            )

            ### GET STORED CREDENTIALS ###
            scheduler.add_job(
                proxy_config.get_credentials,
                "interval",
                seconds=10,
                args=[prisma_client],
            )
            await proxy_config.get_credentials(prisma_client=prisma_client)
        if (
            proxy_logging_obj is not None
            and proxy_logging_obj.slack_alerting_instance.alerting is not None
            and prisma_client is not None
        ):
            print("Alerting: Initializing Weekly/Monthly Spend Reports")  # noqa
            ### Schedule weekly/monthly spend reports ###
            ### Schedule spend reports ###
            spend_report_frequency: str = (
                general_settings.get("spend_report_frequency", "7d") or "7d"
            )

            # Parse the frequency
            days = int(spend_report_frequency[:-1])
            if spend_report_frequency[-1].lower() != "d":
                raise ValueError(
                    "spend_report_frequency must be specified in days, e.g., '1d', '7d'"
                )

            scheduler.add_job(
                proxy_logging_obj.slack_alerting_instance.send_weekly_spend_report,
                "interval",
                days=days,
                next_run_time=datetime.now()
                + timedelta(seconds=10),  # Start 10 seconds from now
                args=[spend_report_frequency],
            )

            scheduler.add_job(
                proxy_logging_obj.slack_alerting_instance.send_monthly_spend_report,
                "cron",
                day=1,
            )

            # Beta Feature - only used when prometheus api is in .env
            if os.getenv("PROMETHEUS_URL"):
                from zoneinfo import ZoneInfo

                scheduler.add_job(
                    proxy_logging_obj.slack_alerting_instance.send_fallback_stats_from_prometheus,
                    "cron",
                    hour=9,
                    minute=0,
                    timezone=ZoneInfo("America/Los_Angeles"),  # Pacific Time
                )
                await proxy_logging_obj.slack_alerting_instance.send_fallback_stats_from_prometheus()

        scheduler.start()

    @classmethod
    async def _setup_prisma_client(
        cls,
        database_url: Optional[str],
        proxy_logging_obj: ProxyLogging,
        user_api_key_cache: DualCache,
    ) -> Optional[PrismaClient]:
        """
        - Sets up prisma client
        - Adds necessary views to proxy
        """
        prisma_client: Optional[PrismaClient] = None
        if database_url is not None:
            try:
                prisma_client = PrismaClient(
                    database_url=database_url, proxy_logging_obj=proxy_logging_obj
                )
            except Exception as e:
                raise e

            await prisma_client.connect()

            ## Add necessary views to proxy ##
            asyncio.create_task(
                prisma_client.check_view_exists()
            )  # check if all necessary views exist. Don't block execution

            asyncio.create_task(
                prisma_client._set_spend_logs_row_count_in_proxy_state()
            )  # set the spend logs row count in proxy state. Don't block execution

            # run a health check to ensure the DB is ready
            if (
                get_secret_bool("DISABLE_PRISMA_HEALTH_CHECK_ON_STARTUP", False)
                is not True
            ):
                await prisma_client.health_check()
        return prisma_client

    @classmethod
    def _init_dd_tracer(cls):
        """
        Initialize dd tracer - if `USE_DDTRACE=true` in .env

        DD tracer is used to trace Python applications.
        Doc: https://docs.datadoghq.com/tracing/trace_collection/automatic_instrumentation/dd_libraries/python/
        """
        from llm.llm_core_utils.dd_tracing import _should_use_dd_tracer

        if _should_use_dd_tracer():
            import ddtrace

            ddtrace.patch_all(logging=True, openai=False)


#### API ENDPOINTS ####
@router.get(
    "/v1/models", dependencies=[Depends(user_api_key_auth)], tags=["model management"]
)
@router.get(
    "/models", dependencies=[Depends(user_api_key_auth)], tags=["model management"]
)  # if project requires model list
async def model_list(
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
    return_wildcard_routes: Optional[bool] = False,
    team_id: Optional[str] = None,
):
    """
    Use `/model/info` - to get detailed model information, example - pricing, mode, etc.

    This is just for compatibility with openai projects like aider.
    """
    global llm_model_list, general_settings, llm_router, prisma_client, user_api_key_cache, proxy_logging_obj
    all_models = []
    model_access_groups: Dict[str, List[str]] = defaultdict(list)
    ## CHECK IF MODEL RESTRICTIONS ARE SET AT KEY/TEAM LEVEL ##
    if llm_router is None:
        proxy_model_list = []
    else:
        proxy_model_list = llm_router.get_model_names()
        model_access_groups = llm_router.get_model_access_groups()
    key_models = get_key_models(
        user_api_key_dict=user_api_key_dict,
        proxy_model_list=proxy_model_list,
        model_access_groups=model_access_groups,
    )

    team_models: List[str] = user_api_key_dict.team_models

    if team_id:
        team_object = await get_team_object(
            team_id=team_id,
            prisma_client=prisma_client,
            user_api_key_cache=user_api_key_cache,
            proxy_logging_obj=proxy_logging_obj,
        )
        validate_membership(user_api_key_dict=user_api_key_dict, team_table=team_object)
        team_models = team_object.models

    team_models = get_team_models(
        team_models=team_models,
        proxy_model_list=proxy_model_list,
        model_access_groups=model_access_groups,
    )

    all_models = get_complete_model_list(
        key_models=key_models if not team_models else [],
        team_models=team_models,
        proxy_model_list=proxy_model_list,
        user_model=user_model,
        infer_model_from_keys=general_settings.get("infer_model_from_keys", False),
        return_wildcard_routes=return_wildcard_routes,
    )

    return dict(
        data=[
            {
                "id": model,
                "object": "model",
                "created": 1677610602,
                "owned_by": "openai",
            }
            for model in all_models
        ],
        object="list",
    )


@router.post(
    "/v1/chat/completions",
    dependencies=[Depends(user_api_key_auth)],
    tags=["chat/completions"],
)
@router.post(
    "/chat/completions",
    dependencies=[Depends(user_api_key_auth)],
    tags=["chat/completions"],
)
@router.post(
    "/engines/{model:path}/chat/completions",
    dependencies=[Depends(user_api_key_auth)],
    tags=["chat/completions"],
)
@router.post(
    "/openai/deployments/{model:path}/chat/completions",
    dependencies=[Depends(user_api_key_auth)],
    tags=["chat/completions"],
    responses={200: {"description": "Successful response"}, **ERROR_RESPONSES},
)  # azure compatible endpoint
@backoff.on_exception(
    backoff.expo,
    Exception,  # base exception to catch for the backoff
    max_tries=global_max_parallel_request_retries,  # maximum number of retries
    max_time=global_max_parallel_request_retry_timeout,  # maximum total time to retry for
    on_backoff=on_backoff,  # specifying the function to call on backoff
    giveup=giveup,
    logger=verbose_proxy_logger,
)
async def chat_completion(  # noqa: PLR0915
    request: Request,
    fastapi_response: Response,
    model: Optional[str] = None,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """

    Follows the exact same API spec as `OpenAI's Chat API https://platform.openai.com/docs/api-reference/chat`

    ```bash
    curl -X POST http://localhost:4000/v1/chat/completions \

    -H "Content-Type: application/json" \

    -H "Authorization: Bearer sk-1234" \

    -d '{
        "model": "gpt-4o",
        "messages": [
            {
                "role": "user",
                "content": "Hello!"
            }
        ]
    }'
    ```

    """
    global general_settings, user_debug, proxy_logging_obj, llm_model_list
    global user_temperature, user_request_timeout, user_max_tokens, user_api_base
    data = await _read_request_body(request=request)
    base_llm_response_processor = ProxyBaseLLMRequestProcessing(data=data)
    try:
        return await base_llm_response_processor.base_process_llm_request(
            request=request,
            fastapi_response=fastapi_response,
            user_api_key_dict=user_api_key_dict,
            route_type="acompletion",
            proxy_logging_obj=proxy_logging_obj,
            llm_router=llm_router,
            general_settings=general_settings,
            proxy_config=proxy_config,
            select_data_generator=select_data_generator,
            model=model,
            user_model=user_model,
            user_temperature=user_temperature,
            user_request_timeout=user_request_timeout,
            user_max_tokens=user_max_tokens,
            user_api_base=user_api_base,
            version=version,
        )
    except RejectedRequestError as e:
        _data = e.request_data
        await proxy_logging_obj.post_call_failure_hook(
            user_api_key_dict=user_api_key_dict,
            original_exception=e,
            request_data=_data,
        )
        _chat_response = llm.ModelResponse()
        _chat_response.choices[0].message.content = e.message  # type: ignore

        if data.get("stream", None) is not None and data["stream"] is True:
            _iterator = llm.utils.ModelResponseIterator(
                model_response=_chat_response, convert_to_delta=True
            )
            _streaming_response = llm.CustomStreamWrapper(
                completion_stream=_iterator,
                model=data.get("model", ""),
                custom_llm_provider="cached_response",
                logging_obj=data.get("llm_logging_obj", None),
            )
            selected_data_generator = select_data_generator(
                response=_streaming_response,
                user_api_key_dict=user_api_key_dict,
                request_data=_data,
            )

            return StreamingResponse(
                selected_data_generator,
                media_type="text/event-stream",
            )
        _usage = llm.Usage(prompt_tokens=0, completion_tokens=0, total_tokens=0)
        _chat_response.usage = _usage  # type: ignore
        return _chat_response
    except Exception as e:
        raise await base_llm_response_processor._handle_llm_api_exception(
            e=e,
            user_api_key_dict=user_api_key_dict,
            proxy_logging_obj=proxy_logging_obj,
        )


@router.post(
    "/v1/completions", dependencies=[Depends(user_api_key_auth)], tags=["completions"]
)
@router.post(
    "/completions", dependencies=[Depends(user_api_key_auth)], tags=["completions"]
)
@router.post(
    "/engines/{model:path}/completions",
    dependencies=[Depends(user_api_key_auth)],
    tags=["completions"],
)
@router.post(
    "/openai/deployments/{model:path}/completions",
    dependencies=[Depends(user_api_key_auth)],
    tags=["completions"],
)
async def completion(  # noqa: PLR0915
    request: Request,
    fastapi_response: Response,
    model: Optional[str] = None,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Follows the exact same API spec as `OpenAI's Completions API https://platform.openai.com/docs/api-reference/completions`

    ```bash
    curl -X POST http://localhost:4000/v1/completions \

    -H "Content-Type: application/json" \

    -H "Authorization: Bearer sk-1234" \

    -d '{
        "model": "gpt-3.5-turbo-instruct",
        "prompt": "Once upon a time",
        "max_tokens": 50,
        "temperature": 0.7
    }'
    ```
    """
    global user_temperature, user_request_timeout, user_max_tokens, user_api_base
    data = {}
    try:
        data = await _read_request_body(request=request)

        data["model"] = (
            general_settings.get("completion_model", None)  # server default
            or user_model  # model name passed via cli args
            or model  # for azure deployments
            or data.get("model", None)
        )
        if user_model:
            data["model"] = user_model

        data = await add_llm_data_to_request(
            data=data,
            request=request,
            general_settings=general_settings,
            user_api_key_dict=user_api_key_dict,
            version=version,
            proxy_config=proxy_config,
        )

        # override with user settings, these are params passed via cli
        if user_temperature:
            data["temperature"] = user_temperature
        if user_request_timeout:
            data["request_timeout"] = user_request_timeout
        if user_max_tokens:
            data["max_tokens"] = user_max_tokens
        if user_api_base:
            data["api_base"] = user_api_base

        ### MODEL ALIAS MAPPING ###
        # check if model name in model alias map
        # get the actual model name
        if data["model"] in llm.model_alias_map:
            data["model"] = llm.model_alias_map[data["model"]]

        ### CALL HOOKS ### - modify incoming data before calling the model
        data = await proxy_logging_obj.pre_call_hook(  # type: ignore
            user_api_key_dict=user_api_key_dict, data=data, call_type="text_completion"
        )

        ### ROUTE THE REQUESTs ###
        llm_call = await route_request(
            data=data,
            route_type="atext_completion",
            llm_router=llm_router,
            user_model=user_model,
        )

        # Await the llm_response task
        response = await llm_call

        hidden_params = getattr(response, "_hidden_params", {}) or {}
        model_id = hidden_params.get("model_id", None) or ""
        cache_key = hidden_params.get("cache_key", None) or ""
        api_base = hidden_params.get("api_base", None) or ""
        response_cost = hidden_params.get("response_cost", None) or ""
        llm_call_id = hidden_params.get("llm_call_id", None) or ""

        ### ALERTING ###
        asyncio.create_task(
            proxy_logging_obj.update_request_status(
                llm_call_id=data.get("llm_call_id", ""), status="success"
            )
        )

        verbose_proxy_logger.debug("final response: %s", response)
        if (
            "stream" in data and data["stream"] is True
        ):  # use generate_responses to stream responses
            custom_headers = ProxyBaseLLMRequestProcessing.get_custom_headers(
                user_api_key_dict=user_api_key_dict,
                call_id=llm_call_id,
                model_id=model_id,
                cache_key=cache_key,
                api_base=api_base,
                version=version,
                response_cost=response_cost,
                hidden_params=hidden_params,
                request_data=data,
            )
            selected_data_generator = select_data_generator(
                response=response,
                user_api_key_dict=user_api_key_dict,
                request_data=data,
            )

            return StreamingResponse(
                selected_data_generator,
                media_type="text/event-stream",
                headers=custom_headers,
            )
        ### CALL HOOKS ### - modify outgoing data
        response = await proxy_logging_obj.post_call_success_hook(
            data=data, user_api_key_dict=user_api_key_dict, response=response  # type: ignore
        )

        fastapi_response.headers.update(
            ProxyBaseLLMRequestProcessing.get_custom_headers(
                user_api_key_dict=user_api_key_dict,
                call_id=llm_call_id,
                model_id=model_id,
                cache_key=cache_key,
                api_base=api_base,
                version=version,
                response_cost=response_cost,
                request_data=data,
                hidden_params=hidden_params,
            )
        )
        await check_response_size_is_safe(response=response)
        return response
    except RejectedRequestError as e:
        _data = e.request_data
        await proxy_logging_obj.post_call_failure_hook(
            user_api_key_dict=user_api_key_dict,
            original_exception=e,
            request_data=_data,
        )
        if _data.get("stream", None) is not None and _data["stream"] is True:
            _chat_response = llm.ModelResponse()
            _usage = llm.Usage(
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
            )
            _chat_response.usage = _usage  # type: ignore
            _chat_response.choices[0].message.content = e.message  # type: ignore
            _iterator = llm.utils.ModelResponseIterator(
                model_response=_chat_response, convert_to_delta=True
            )
            _streaming_response = llm.TextCompletionStreamWrapper(
                completion_stream=_iterator,
                model=_data.get("model", ""),
            )

            selected_data_generator = select_data_generator(
                response=_streaming_response,
                user_api_key_dict=user_api_key_dict,
                request_data=data,
            )

            return StreamingResponse(
                selected_data_generator,
                media_type="text/event-stream",
                headers={},
            )
        else:
            _response = llm.TextCompletionResponse()
            _response.choices[0].text = e.message
            return _response
    except Exception as e:
        await proxy_logging_obj.post_call_failure_hook(
            user_api_key_dict=user_api_key_dict, original_exception=e, request_data=data
        )
        verbose_proxy_logger.exception(
            "llm.proxy.proxy_server.completion(): Exception occured - {}".format(
                str(e)
            )
        )
        error_msg = f"{str(e)}"
        raise ProxyException(
            message=getattr(e, "message", error_msg),
            type=getattr(e, "type", "None"),
            param=getattr(e, "param", "None"),
            openai_code=getattr(e, "code", None),
            code=getattr(e, "status_code", 500),
        )


@router.post(
    "/v1/embeddings",
    dependencies=[Depends(user_api_key_auth)],
    response_class=ORJSONResponse,
    tags=["embeddings"],
)
@router.post(
    "/embeddings",
    dependencies=[Depends(user_api_key_auth)],
    response_class=ORJSONResponse,
    tags=["embeddings"],
)
@router.post(
    "/engines/{model:path}/embeddings",
    dependencies=[Depends(user_api_key_auth)],
    response_class=ORJSONResponse,
    tags=["embeddings"],
)  # azure compatible endpoint
@router.post(
    "/openai/deployments/{model:path}/embeddings",
    dependencies=[Depends(user_api_key_auth)],
    response_class=ORJSONResponse,
    tags=["embeddings"],
)  # azure compatible endpoint
async def embeddings(  # noqa: PLR0915
    request: Request,
    fastapi_response: Response,
    model: Optional[str] = None,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Follows the exact same API spec as `OpenAI's Embeddings API https://platform.openai.com/docs/api-reference/embeddings`

    ```bash
    curl -X POST http://localhost:4000/v1/embeddings \

    -H "Content-Type: application/json" \

    -H "Authorization: Bearer sk-1234" \

    -d '{
        "model": "text-embedding-ada-002",
        "input": "The quick brown fox jumps over the lazy dog"
    }'
    ```

"""
    global proxy_logging_obj
    data: Any = {}
    try:
        # Use orjson to parse JSON data, orjson speeds up requests significantly
        body = await request.body()
        data = orjson.loads(body)

        verbose_proxy_logger.debug(
            "Request received by LLM:\n%s",
            json.dumps(data, indent=4),
        )

        # Include original request and headers in the data
        data = await add_llm_data_to_request(
            data=data,
            request=request,
            general_settings=general_settings,
            user_api_key_dict=user_api_key_dict,
            version=version,
            proxy_config=proxy_config,
        )

        data["model"] = (
            general_settings.get("embedding_model", None)  # server default
            or user_model  # model name passed via cli args
            or model  # for azure deployments
            or data.get("model", None)  # default passed in http request
        )
        if user_model:
            data["model"] = user_model

        ### MODEL ALIAS MAPPING ###
        # check if model name in model alias map
        # get the actual model name
        if data["model"] in llm.model_alias_map:
            data["model"] = llm.model_alias_map[data["model"]]

        router_model_names = llm_router.model_names if llm_router is not None else []
        if (
            "input" in data
            and isinstance(data["input"], list)
            and len(data["input"]) > 0
            and isinstance(data["input"][0], list)
            and isinstance(data["input"][0][0], int)
        ):  # check if array of tokens passed in
            # check if non-openai/azure model called - e.g. for langchain integration
            if llm_model_list is not None and data["model"] in router_model_names:
                for m in llm_model_list:
                    if m["model_name"] == data["model"] and (
                        m["llm_params"]["model"] in llm.open_ai_embedding_models
                        or m["llm_params"]["model"].startswith("azure/")
                    ):
                        pass
                    else:
                        # non-openai/azure embedding model called with token input
                        input_list = []
                        for i in data["input"]:
                            input_list.append(
                                llm.decode(model="gpt-3.5-turbo", tokens=i)
                            )
                        data["input"] = input_list
                        break

        ### CALL HOOKS ### - modify incoming data / reject request before calling the model
        data = await proxy_logging_obj.pre_call_hook(
            user_api_key_dict=user_api_key_dict, data=data, call_type="embeddings"
        )

        tasks = []
        tasks.append(
            proxy_logging_obj.during_call_hook(
                data=data,
                user_api_key_dict=user_api_key_dict,
                call_type="embeddings",
            )
        )

        ## ROUTE TO CORRECT ENDPOINT ##
        llm_call = await route_request(
            data=data,
            route_type="aembedding",
            llm_router=llm_router,
            user_model=user_model,
        )
        tasks.append(llm_call)

        # wait for call to end
        llm_responses = asyncio.gather(
            *tasks
        )  # run the moderation check in parallel to the actual llm api call

        responses = await llm_responses

        response = responses[1]

        ### ALERTING ###
        asyncio.create_task(
            proxy_logging_obj.update_request_status(
                llm_call_id=data.get("llm_call_id", ""), status="success"
            )
        )

        ### RESPONSE HEADERS ###
        hidden_params = getattr(response, "_hidden_params", {}) or {}
        model_id = hidden_params.get("model_id", None) or ""
        cache_key = hidden_params.get("cache_key", None) or ""
        api_base = hidden_params.get("api_base", None) or ""
        response_cost = hidden_params.get("response_cost", None) or ""
        llm_call_id = hidden_params.get("llm_call_id", None) or ""
        additional_headers: dict = hidden_params.get("additional_headers", {}) or {}

        fastapi_response.headers.update(
            ProxyBaseLLMRequestProcessing.get_custom_headers(
                user_api_key_dict=user_api_key_dict,
                model_id=model_id,
                cache_key=cache_key,
                api_base=api_base,
                version=version,
                response_cost=response_cost,
                model_region=getattr(user_api_key_dict, "allowed_model_region", ""),
                call_id=llm_call_id,
                request_data=data,
                hidden_params=hidden_params,
                **additional_headers,
            )
        )
        await check_response_size_is_safe(response=response)

        return response
    except Exception as e:
        await proxy_logging_obj.post_call_failure_hook(
            user_api_key_dict=user_api_key_dict, original_exception=e, request_data=data
        )
        llm_debug_info = getattr(e, "llm_debug_info", "")
        verbose_proxy_logger.debug(
            "\033[1;31mAn error occurred: %s %s\n\n Debug this by setting `--debug`, e.g. `llm --model gpt-3.5-turbo --debug`",
            e,
            llm_debug_info,
        )
        verbose_proxy_logger.exception(
            "llm.proxy.proxy_server.embeddings(): Exception occured - {}".format(
                str(e)
            )
        )
        if isinstance(e, HTTPException):
            message = get_error_message_str(e)
            raise ProxyException(
                message=message,
                type=getattr(e, "type", "None"),
                param=getattr(e, "param", "None"),
                code=getattr(e, "status_code", status.HTTP_400_BAD_REQUEST),
            )
        else:
            error_msg = f"{str(e)}"
            raise ProxyException(
                message=getattr(e, "message", error_msg),
                type=getattr(e, "type", "None"),
                param=getattr(e, "param", "None"),
                openai_code=getattr(e, "code", None),
                code=getattr(e, "status_code", 500),
            )


@router.post(
    "/v1/images/generations",
    dependencies=[Depends(user_api_key_auth)],
    response_class=ORJSONResponse,
    tags=["images"],
)
@router.post(
    "/images/generations",
    dependencies=[Depends(user_api_key_auth)],
    response_class=ORJSONResponse,
    tags=["images"],
)
async def image_generation(
    request: Request,
    fastapi_response: Response,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    global proxy_logging_obj
    data = {}
    try:
        # Use orjson to parse JSON data, orjson speeds up requests significantly
        body = await request.body()
        data = orjson.loads(body)

        # Include original request and headers in the data
        data = await add_llm_data_to_request(
            data=data,
            request=request,
            general_settings=general_settings,
            user_api_key_dict=user_api_key_dict,
            version=version,
            proxy_config=proxy_config,
        )

        data["model"] = (
            general_settings.get("image_generation_model", None)  # server default
            or user_model  # model name passed via cli args
            or data.get("model", None)  # default passed in http request
        )
        if user_model:
            data["model"] = user_model

        ### MODEL ALIAS MAPPING ###
        # check if model name in model alias map
        # get the actual model name
        if data["model"] in llm.model_alias_map:
            data["model"] = llm.model_alias_map[data["model"]]

        ### CALL HOOKS ### - modify incoming data / reject request before calling the model
        data = await proxy_logging_obj.pre_call_hook(
            user_api_key_dict=user_api_key_dict, data=data, call_type="image_generation"
        )

        ## ROUTE TO CORRECT ENDPOINT ##
        llm_call = await route_request(
            data=data,
            route_type="aimage_generation",
            llm_router=llm_router,
            user_model=user_model,
        )
        response = await llm_call

        ### ALERTING ###
        asyncio.create_task(
            proxy_logging_obj.update_request_status(
                llm_call_id=data.get("llm_call_id", ""), status="success"
            )
        )
        ### RESPONSE HEADERS ###
        hidden_params = getattr(response, "_hidden_params", {}) or {}
        model_id = hidden_params.get("model_id", None) or ""
        cache_key = hidden_params.get("cache_key", None) or ""
        api_base = hidden_params.get("api_base", None) or ""
        response_cost = hidden_params.get("response_cost", None) or ""
        llm_call_id = hidden_params.get("llm_call_id", None) or ""

        fastapi_response.headers.update(
            ProxyBaseLLMRequestProcessing.get_custom_headers(
                user_api_key_dict=user_api_key_dict,
                model_id=model_id,
                cache_key=cache_key,
                api_base=api_base,
                version=version,
                response_cost=response_cost,
                model_region=getattr(user_api_key_dict, "allowed_model_region", ""),
                call_id=llm_call_id,
                request_data=data,
                hidden_params=hidden_params,
            )
        )

        return response
    except Exception as e:
        await proxy_logging_obj.post_call_failure_hook(
            user_api_key_dict=user_api_key_dict, original_exception=e, request_data=data
        )
        verbose_proxy_logger.error(
            "llm.proxy.proxy_server.image_generation(): Exception occured - {}".format(
                str(e)
            )
        )
        verbose_proxy_logger.debug(traceback.format_exc())
        if isinstance(e, HTTPException):
            raise ProxyException(
                message=getattr(e, "message", str(e)),
                type=getattr(e, "type", "None"),
                param=getattr(e, "param", "None"),
                code=getattr(e, "status_code", status.HTTP_400_BAD_REQUEST),
            )
        else:
            error_msg = f"{str(e)}"
            raise ProxyException(
                message=getattr(e, "message", error_msg),
                type=getattr(e, "type", "None"),
                param=getattr(e, "param", "None"),
                openai_code=getattr(e, "code", None),
                code=getattr(e, "status_code", 500),
            )


@router.post(
    "/v1/audio/speech",
    dependencies=[Depends(user_api_key_auth)],
    tags=["audio"],
)
@router.post(
    "/audio/speech",
    dependencies=[Depends(user_api_key_auth)],
    tags=["audio"],
)
async def audio_speech(
    request: Request,
    fastapi_response: Response,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Same params as:

    https://platform.openai.com/docs/api-reference/audio/createSpeech
    """
    global proxy_logging_obj
    data: Dict = {}
    try:
        # Use orjson to parse JSON data, orjson speeds up requests significantly
        body = await request.body()
        data = orjson.loads(body)

        # Include original request and headers in the data
        data = await add_llm_data_to_request(
            data=data,
            request=request,
            general_settings=general_settings,
            user_api_key_dict=user_api_key_dict,
            version=version,
            proxy_config=proxy_config,
        )

        if data.get("user", None) is None and user_api_key_dict.user_id is not None:
            data["user"] = user_api_key_dict.user_id

        if user_model:
            data["model"] = user_model

        ### CALL HOOKS ### - modify incoming data / reject request before calling the model
        data = await proxy_logging_obj.pre_call_hook(
            user_api_key_dict=user_api_key_dict, data=data, call_type="image_generation"
        )

        ## ROUTE TO CORRECT ENDPOINT ##
        llm_call = await route_request(
            data=data,
            route_type="aspeech",
            llm_router=llm_router,
            user_model=user_model,
        )
        response = await llm_call

        ### ALERTING ###
        asyncio.create_task(
            proxy_logging_obj.update_request_status(
                llm_call_id=data.get("llm_call_id", ""), status="success"
            )
        )

        ### RESPONSE HEADERS ###
        hidden_params = getattr(response, "_hidden_params", {}) or {}
        model_id = hidden_params.get("model_id", None) or ""
        cache_key = hidden_params.get("cache_key", None) or ""
        api_base = hidden_params.get("api_base", None) or ""
        response_cost = hidden_params.get("response_cost", None) or ""
        llm_call_id = hidden_params.get("llm_call_id", None) or ""

        # Printing each chunk size
        async def generate(_response: HttpxBinaryResponseContent):
            _generator = await _response.aiter_bytes(chunk_size=1024)
            async for chunk in _generator:
                yield chunk

        custom_headers = ProxyBaseLLMRequestProcessing.get_custom_headers(
            user_api_key_dict=user_api_key_dict,
            model_id=model_id,
            cache_key=cache_key,
            api_base=api_base,
            version=version,
            response_cost=response_cost,
            model_region=getattr(user_api_key_dict, "allowed_model_region", ""),
            fastest_response_batch_completion=None,
            call_id=llm_call_id,
            request_data=data,
            hidden_params=hidden_params,
        )

        select_data_generator(
            response=response,
            user_api_key_dict=user_api_key_dict,
            request_data=data,
        )
        return StreamingResponse(
            generate(response), media_type="audio/mpeg", headers=custom_headers  # type: ignore
        )

    except Exception as e:
        verbose_proxy_logger.error(
            "llm.proxy.proxy_server.audio_speech(): Exception occured - {}".format(
                str(e)
            )
        )
        verbose_proxy_logger.debug(traceback.format_exc())
        raise e


@router.post(
    "/v1/audio/transcriptions",
    dependencies=[Depends(user_api_key_auth)],
    tags=["audio"],
)
@router.post(
    "/audio/transcriptions",
    dependencies=[Depends(user_api_key_auth)],
    tags=["audio"],
)
async def audio_transcriptions(
    request: Request,
    fastapi_response: Response,
    file: UploadFile = File(...),
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Same params as:

    https://platform.openai.com/docs/api-reference/audio/createTranscription?lang=curl
    """
    global proxy_logging_obj
    data: Dict = {}
    try:
        # Use orjson to parse JSON data, orjson speeds up requests significantly
        form_data = await request.form()
        data = {key: value for key, value in form_data.items() if key != "file"}

        # Include original request and headers in the data
        data = await add_llm_data_to_request(
            data=data,
            request=request,
            general_settings=general_settings,
            user_api_key_dict=user_api_key_dict,
            version=version,
            proxy_config=proxy_config,
        )

        if data.get("user", None) is None and user_api_key_dict.user_id is not None:
            data["user"] = user_api_key_dict.user_id

        data["model"] = (
            general_settings.get("moderation_model", None)  # server default
            or user_model  # model name passed via cli args
            or data.get("model", None)  # default passed in http request
        )
        if user_model:
            data["model"] = user_model

        router_model_names = llm_router.model_names if llm_router is not None else []

        if file.filename is None:
            raise ProxyException(
                message="File name is None. Please check your file name",
                code=status.HTTP_400_BAD_REQUEST,
                type="bad_request",
                param="file",
            )

        # Check if File can be read in memory before reading
        check_file_size_under_limit(
            request_data=data,
            file=file,
            router_model_names=router_model_names,
        )

        file_content = await file.read()
        file_object = io.BytesIO(file_content)
        file_object.name = file.filename
        data["file"] = file_object
        try:
            ### CALL HOOKS ### - modify incoming data / reject request before calling the model
            data = await proxy_logging_obj.pre_call_hook(
                user_api_key_dict=user_api_key_dict,
                data=data,
                call_type="audio_transcription",
            )

            ## ROUTE TO CORRECT ENDPOINT ##
            llm_call = await route_request(
                data=data,
                route_type="atranscription",
                llm_router=llm_router,
                user_model=user_model,
            )
            response = await llm_call
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            file_object.close()  # close the file read in by io library

        ### ALERTING ###
        asyncio.create_task(
            proxy_logging_obj.update_request_status(
                llm_call_id=data.get("llm_call_id", ""), status="success"
            )
        )

        ### RESPONSE HEADERS ###
        hidden_params = getattr(response, "_hidden_params", {}) or {}
        model_id = hidden_params.get("model_id", None) or ""
        cache_key = hidden_params.get("cache_key", None) or ""
        api_base = hidden_params.get("api_base", None) or ""
        response_cost = hidden_params.get("response_cost", None) or ""
        llm_call_id = hidden_params.get("llm_call_id", None) or ""
        additional_headers: dict = hidden_params.get("additional_headers", {}) or {}

        fastapi_response.headers.update(
            ProxyBaseLLMRequestProcessing.get_custom_headers(
                user_api_key_dict=user_api_key_dict,
                model_id=model_id,
                cache_key=cache_key,
                api_base=api_base,
                version=version,
                response_cost=response_cost,
                model_region=getattr(user_api_key_dict, "allowed_model_region", ""),
                call_id=llm_call_id,
                request_data=data,
                hidden_params=hidden_params,
                **additional_headers,
            )
        )

        return response
    except Exception as e:
        await proxy_logging_obj.post_call_failure_hook(
            user_api_key_dict=user_api_key_dict, original_exception=e, request_data=data
        )
        verbose_proxy_logger.exception(
            "llm.proxy.proxy_server.audio_transcription(): Exception occured - {}".format(
                str(e)
            )
        )
        if isinstance(e, HTTPException):
            raise ProxyException(
                message=getattr(e, "message", str(e.detail)),
                type=getattr(e, "type", "None"),
                param=getattr(e, "param", "None"),
                code=getattr(e, "status_code", status.HTTP_400_BAD_REQUEST),
            )
        else:
            error_msg = f"{str(e)}"
            raise ProxyException(
                message=getattr(e, "message", error_msg),
                type=getattr(e, "type", "None"),
                param=getattr(e, "param", "None"),
                openai_code=getattr(e, "code", None),
                code=getattr(e, "status_code", 500),
            )


######################################################################

#                          /v1/realtime Endpoints

######################################################################
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from llm import _arealtime


@app.websocket("/v1/realtime")
@app.websocket("/realtime")
async def websocket_endpoint(
    websocket: WebSocket,
    model: str,
    user_api_key_dict=Depends(user_api_key_auth_websocket),
):
    import websockets

    await websocket.accept()

    data = {
        "model": model,
        "websocket": websocket,
    }

    ### ROUTE THE REQUEST ###
    try:
        llm_call = await route_request(
            data=data,
            route_type="_arealtime",
            llm_router=llm_router,
            user_model=user_model,
        )

        await llm_call
    except websockets.exceptions.InvalidStatusCode as e:  # type: ignore
        verbose_proxy_logger.exception("Invalid status code")
        await websocket.close(code=e.status_code, reason="Invalid status code")
    except Exception:
        verbose_proxy_logger.exception("Internal server error")
        await websocket.close(code=1011, reason="Internal server error")


######################################################################

#                          /v1/assistant Endpoints


######################################################################


@router.get(
    "/v1/assistants",
    dependencies=[Depends(user_api_key_auth)],
    tags=["assistants"],
)
@router.get(
    "/assistants",
    dependencies=[Depends(user_api_key_auth)],
    tags=["assistants"],
)
async def get_assistants(
    request: Request,
    fastapi_response: Response,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Returns a list of assistants.

    API Reference docs - https://platform.openai.com/docs/api-reference/assistants/listAssistants
    """
    global proxy_logging_obj
    data: Dict = {}
    try:
        # Use orjson to parse JSON data, orjson speeds up requests significantly
        await request.body()

        # Include original request and headers in the data
        data = await add_llm_data_to_request(
            data=data,
            request=request,
            general_settings=general_settings,
            user_api_key_dict=user_api_key_dict,
            version=version,
            proxy_config=proxy_config,
        )

        # for now use custom_llm_provider=="openai" -> this will change as LLM adds more providers for acreate_batch
        if llm_router is None:
            raise HTTPException(
                status_code=500, detail={"error": CommonProxyErrors.no_llm_router.value}
            )
        response = await llm_router.aget_assistants(**data)

        ### ALERTING ###
        asyncio.create_task(
            proxy_logging_obj.update_request_status(
                llm_call_id=data.get("llm_call_id", ""), status="success"
            )
        )

        ### RESPONSE HEADERS ###
        hidden_params = getattr(response, "_hidden_params", {}) or {}
        model_id = hidden_params.get("model_id", None) or ""
        cache_key = hidden_params.get("cache_key", None) or ""
        api_base = hidden_params.get("api_base", None) or ""

        fastapi_response.headers.update(
            ProxyBaseLLMRequestProcessing.get_custom_headers(
                user_api_key_dict=user_api_key_dict,
                model_id=model_id,
                cache_key=cache_key,
                api_base=api_base,
                version=version,
                model_region=getattr(user_api_key_dict, "allowed_model_region", ""),
                request_data=data,
                hidden_params=hidden_params,
            )
        )

        return response
    except Exception as e:
        await proxy_logging_obj.post_call_failure_hook(
            user_api_key_dict=user_api_key_dict, original_exception=e, request_data=data
        )
        verbose_proxy_logger.error(
            "llm.proxy.proxy_server.get_assistants(): Exception occured - {}".format(
                str(e)
            )
        )
        verbose_proxy_logger.debug(traceback.format_exc())
        if isinstance(e, HTTPException):
            raise ProxyException(
                message=getattr(e, "message", str(e.detail)),
                type=getattr(e, "type", "None"),
                param=getattr(e, "param", "None"),
                code=getattr(e, "status_code", status.HTTP_400_BAD_REQUEST),
            )
        else:
            error_msg = f"{str(e)}"
            raise ProxyException(
                message=getattr(e, "message", error_msg),
                type=getattr(e, "type", "None"),
                param=getattr(e, "param", "None"),
                openai_code=getattr(e, "code", None),
                code=getattr(e, "status_code", 500),
            )


@router.post(
    "/v1/assistants",
    dependencies=[Depends(user_api_key_auth)],
    tags=["assistants"],
)
@router.post(
    "/assistants",
    dependencies=[Depends(user_api_key_auth)],
    tags=["assistants"],
)
async def create_assistant(
    request: Request,
    fastapi_response: Response,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Create assistant

    API Reference docs - https://platform.openai.com/docs/api-reference/assistants/createAssistant
    """
    global proxy_logging_obj
    data = {}  # ensure data always dict
    try:
        # Use orjson to parse JSON data, orjson speeds up requests significantly
        body = await request.body()
        data = orjson.loads(body)

        # Include original request and headers in the data
        data = await add_llm_data_to_request(
            data=data,
            request=request,
            general_settings=general_settings,
            user_api_key_dict=user_api_key_dict,
            version=version,
            proxy_config=proxy_config,
        )

        # for now use custom_llm_provider=="openai" -> this will change as LLM adds more providers for acreate_batch
        if llm_router is None:
            raise HTTPException(
                status_code=500, detail={"error": CommonProxyErrors.no_llm_router.value}
            )
        response = await llm_router.acreate_assistants(**data)

        ### ALERTING ###
        asyncio.create_task(
            proxy_logging_obj.update_request_status(
                llm_call_id=data.get("llm_call_id", ""), status="success"
            )
        )

        ### RESPONSE HEADERS ###
        hidden_params = getattr(response, "_hidden_params", {}) or {}
        model_id = hidden_params.get("model_id", None) or ""
        cache_key = hidden_params.get("cache_key", None) or ""
        api_base = hidden_params.get("api_base", None) or ""

        fastapi_response.headers.update(
            ProxyBaseLLMRequestProcessing.get_custom_headers(
                user_api_key_dict=user_api_key_dict,
                model_id=model_id,
                cache_key=cache_key,
                api_base=api_base,
                version=version,
                model_region=getattr(user_api_key_dict, "allowed_model_region", ""),
                request_data=data,
                hidden_params=hidden_params,
            )
        )

        return response
    except Exception as e:
        await proxy_logging_obj.post_call_failure_hook(
            user_api_key_dict=user_api_key_dict, original_exception=e, request_data=data
        )
        verbose_proxy_logger.error(
            "llm.proxy.proxy_server.create_assistant(): Exception occured - {}".format(
                str(e)
            )
        )
        verbose_proxy_logger.debug(traceback.format_exc())
        if isinstance(e, HTTPException):
            raise ProxyException(
                message=getattr(e, "message", str(e.detail)),
                type=getattr(e, "type", "None"),
                param=getattr(e, "param", "None"),
                code=getattr(e, "status_code", status.HTTP_400_BAD_REQUEST),
            )
        else:
            error_msg = f"{str(e)}"
            raise ProxyException(
                message=getattr(e, "message", error_msg),
                type=getattr(e, "type", "None"),
                param=getattr(e, "param", "None"),
                code=getattr(e, "code", getattr(e, "status_code", 500)),
            )


@router.delete(
    "/v1/assistants/{assistant_id:path}",
    dependencies=[Depends(user_api_key_auth)],
    tags=["assistants"],
)
@router.delete(
    "/assistants/{assistant_id:path}",
    dependencies=[Depends(user_api_key_auth)],
    tags=["assistants"],
)
async def delete_assistant(
    request: Request,
    assistant_id: str,
    fastapi_response: Response,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Delete assistant

    API Reference docs - https://platform.openai.com/docs/api-reference/assistants/createAssistant
    """
    global proxy_logging_obj
    data: Dict = {}
    try:
        # Use orjson to parse JSON data, orjson speeds up requests significantly

        # Include original request and headers in the data
        data = await add_llm_data_to_request(
            data=data,
            request=request,
            general_settings=general_settings,
            user_api_key_dict=user_api_key_dict,
            version=version,
            proxy_config=proxy_config,
        )

        # for now use custom_llm_provider=="openai" -> this will change as LLM adds more providers for acreate_batch
        if llm_router is None:
            raise HTTPException(
                status_code=500, detail={"error": CommonProxyErrors.no_llm_router.value}
            )
        response = await llm_router.adelete_assistant(assistant_id=assistant_id, **data)

        ### ALERTING ###
        asyncio.create_task(
            proxy_logging_obj.update_request_status(
                llm_call_id=data.get("llm_call_id", ""), status="success"
            )
        )

        ### RESPONSE HEADERS ###
        hidden_params = getattr(response, "_hidden_params", {}) or {}
        model_id = hidden_params.get("model_id", None) or ""
        cache_key = hidden_params.get("cache_key", None) or ""
        api_base = hidden_params.get("api_base", None) or ""

        fastapi_response.headers.update(
            ProxyBaseLLMRequestProcessing.get_custom_headers(
                user_api_key_dict=user_api_key_dict,
                model_id=model_id,
                cache_key=cache_key,
                api_base=api_base,
                version=version,
                model_region=getattr(user_api_key_dict, "allowed_model_region", ""),
                request_data=data,
                hidden_params=hidden_params,
            )
        )

        return response
    except Exception as e:
        await proxy_logging_obj.post_call_failure_hook(
            user_api_key_dict=user_api_key_dict, original_exception=e, request_data=data
        )
        verbose_proxy_logger.error(
            "llm.proxy.proxy_server.delete_assistant(): Exception occured - {}".format(
                str(e)
            )
        )
        verbose_proxy_logger.debug(traceback.format_exc())
        if isinstance(e, HTTPException):
            raise ProxyException(
                message=getattr(e, "message", str(e.detail)),
                type=getattr(e, "type", "None"),
                param=getattr(e, "param", "None"),
                code=getattr(e, "status_code", status.HTTP_400_BAD_REQUEST),
            )
        else:
            error_msg = f"{str(e)}"
            raise ProxyException(
                message=getattr(e, "message", error_msg),
                type=getattr(e, "type", "None"),
                param=getattr(e, "param", "None"),
                code=getattr(e, "code", getattr(e, "status_code", 500)),
            )


@router.post(
    "/v1/threads",
    dependencies=[Depends(user_api_key_auth)],
    tags=["assistants"],
)
@router.post(
    "/threads",
    dependencies=[Depends(user_api_key_auth)],
    tags=["assistants"],
)
async def create_threads(
    request: Request,
    fastapi_response: Response,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Create a thread.

    API Reference - https://platform.openai.com/docs/api-reference/threads/createThread
    """
    global proxy_logging_obj
    data: Dict = {}
    try:
        # Use orjson to parse JSON data, orjson speeds up requests significantly
        await request.body()

        # Include original request and headers in the data
        data = await add_llm_data_to_request(
            data=data,
            request=request,
            general_settings=general_settings,
            user_api_key_dict=user_api_key_dict,
            version=version,
            proxy_config=proxy_config,
        )

        # for now use custom_llm_provider=="openai" -> this will change as LLM adds more providers for acreate_batch
        if llm_router is None:
            raise HTTPException(
                status_code=500, detail={"error": CommonProxyErrors.no_llm_router.value}
            )
        response = await llm_router.acreate_thread(**data)

        ### ALERTING ###
        asyncio.create_task(
            proxy_logging_obj.update_request_status(
                llm_call_id=data.get("llm_call_id", ""), status="success"
            )
        )

        ### RESPONSE HEADERS ###
        hidden_params = getattr(response, "_hidden_params", {}) or {}
        model_id = hidden_params.get("model_id", None) or ""
        cache_key = hidden_params.get("cache_key", None) or ""
        api_base = hidden_params.get("api_base", None) or ""

        fastapi_response.headers.update(
            ProxyBaseLLMRequestProcessing.get_custom_headers(
                user_api_key_dict=user_api_key_dict,
                model_id=model_id,
                cache_key=cache_key,
                api_base=api_base,
                version=version,
                model_region=getattr(user_api_key_dict, "allowed_model_region", ""),
                request_data=data,
                hidden_params=hidden_params,
            )
        )

        return response
    except Exception as e:
        await proxy_logging_obj.post_call_failure_hook(
            user_api_key_dict=user_api_key_dict, original_exception=e, request_data=data
        )
        verbose_proxy_logger.error(
            "llm.proxy.proxy_server.create_threads(): Exception occured - {}".format(
                str(e)
            )
        )
        verbose_proxy_logger.debug(traceback.format_exc())
        if isinstance(e, HTTPException):
            raise ProxyException(
                message=getattr(e, "message", str(e.detail)),
                type=getattr(e, "type", "None"),
                param=getattr(e, "param", "None"),
                code=getattr(e, "status_code", status.HTTP_400_BAD_REQUEST),
            )
        else:
            error_msg = f"{str(e)}"
            raise ProxyException(
                message=getattr(e, "message", error_msg),
                type=getattr(e, "type", "None"),
                param=getattr(e, "param", "None"),
                code=getattr(e, "code", getattr(e, "status_code", 500)),
            )


@router.get(
    "/v1/threads/{thread_id}",
    dependencies=[Depends(user_api_key_auth)],
    tags=["assistants"],
)
@router.get(
    "/threads/{thread_id}",
    dependencies=[Depends(user_api_key_auth)],
    tags=["assistants"],
)
async def get_thread(
    request: Request,
    thread_id: str,
    fastapi_response: Response,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Retrieves a thread.

    API Reference - https://platform.openai.com/docs/api-reference/threads/getThread
    """
    global proxy_logging_obj
    data: Dict = {}
    try:

        # Include original request and headers in the data
        data = await add_llm_data_to_request(
            data=data,
            request=request,
            general_settings=general_settings,
            user_api_key_dict=user_api_key_dict,
            version=version,
            proxy_config=proxy_config,
        )

        # for now use custom_llm_provider=="openai" -> this will change as LLM adds more providers for acreate_batch
        if llm_router is None:
            raise HTTPException(
                status_code=500, detail={"error": CommonProxyErrors.no_llm_router.value}
            )
        response = await llm_router.aget_thread(thread_id=thread_id, **data)

        ### ALERTING ###
        asyncio.create_task(
            proxy_logging_obj.update_request_status(
                llm_call_id=data.get("llm_call_id", ""), status="success"
            )
        )

        ### RESPONSE HEADERS ###
        hidden_params = getattr(response, "_hidden_params", {}) or {}
        model_id = hidden_params.get("model_id", None) or ""
        cache_key = hidden_params.get("cache_key", None) or ""
        api_base = hidden_params.get("api_base", None) or ""

        fastapi_response.headers.update(
            ProxyBaseLLMRequestProcessing.get_custom_headers(
                user_api_key_dict=user_api_key_dict,
                model_id=model_id,
                cache_key=cache_key,
                api_base=api_base,
                version=version,
                model_region=getattr(user_api_key_dict, "allowed_model_region", ""),
                request_data=data,
                hidden_params=hidden_params,
            )
        )

        return response
    except Exception as e:
        await proxy_logging_obj.post_call_failure_hook(
            user_api_key_dict=user_api_key_dict, original_exception=e, request_data=data
        )
        verbose_proxy_logger.error(
            "llm.proxy.proxy_server.get_thread(): Exception occured - {}".format(
                str(e)
            )
        )
        verbose_proxy_logger.debug(traceback.format_exc())
        if isinstance(e, HTTPException):
            raise ProxyException(
                message=getattr(e, "message", str(e.detail)),
                type=getattr(e, "type", "None"),
                param=getattr(e, "param", "None"),
                code=getattr(e, "status_code", status.HTTP_400_BAD_REQUEST),
            )
        else:
            error_msg = f"{str(e)}"
            raise ProxyException(
                message=getattr(e, "message", error_msg),
                type=getattr(e, "type", "None"),
                param=getattr(e, "param", "None"),
                code=getattr(e, "code", getattr(e, "status_code", 500)),
            )


@router.post(
    "/v1/threads/{thread_id}/messages",
    dependencies=[Depends(user_api_key_auth)],
    tags=["assistants"],
)
@router.post(
    "/threads/{thread_id}/messages",
    dependencies=[Depends(user_api_key_auth)],
    tags=["assistants"],
)
async def add_messages(
    request: Request,
    thread_id: str,
    fastapi_response: Response,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Create a message.

    API Reference - https://platform.openai.com/docs/api-reference/messages/createMessage
    """
    global proxy_logging_obj
    data: Dict = {}
    try:
        # Use orjson to parse JSON data, orjson speeds up requests significantly
        body = await request.body()
        data = orjson.loads(body)

        # Include original request and headers in the data
        data = await add_llm_data_to_request(
            data=data,
            request=request,
            general_settings=general_settings,
            user_api_key_dict=user_api_key_dict,
            version=version,
            proxy_config=proxy_config,
        )

        # for now use custom_llm_provider=="openai" -> this will change as LLM adds more providers for acreate_batch
        if llm_router is None:
            raise HTTPException(
                status_code=500, detail={"error": CommonProxyErrors.no_llm_router.value}
            )
        response = await llm_router.a_add_message(thread_id=thread_id, **data)

        ### ALERTING ###
        asyncio.create_task(
            proxy_logging_obj.update_request_status(
                llm_call_id=data.get("llm_call_id", ""), status="success"
            )
        )

        ### RESPONSE HEADERS ###
        hidden_params = getattr(response, "_hidden_params", {}) or {}
        model_id = hidden_params.get("model_id", None) or ""
        cache_key = hidden_params.get("cache_key", None) or ""
        api_base = hidden_params.get("api_base", None) or ""

        fastapi_response.headers.update(
            ProxyBaseLLMRequestProcessing.get_custom_headers(
                user_api_key_dict=user_api_key_dict,
                model_id=model_id,
                cache_key=cache_key,
                api_base=api_base,
                version=version,
                model_region=getattr(user_api_key_dict, "allowed_model_region", ""),
                request_data=data,
                hidden_params=hidden_params,
            )
        )

        return response
    except Exception as e:
        await proxy_logging_obj.post_call_failure_hook(
            user_api_key_dict=user_api_key_dict, original_exception=e, request_data=data
        )
        verbose_proxy_logger.error(
            "llm.proxy.proxy_server.add_messages(): Exception occured - {}".format(
                str(e)
            )
        )
        verbose_proxy_logger.debug(traceback.format_exc())
        if isinstance(e, HTTPException):
            raise ProxyException(
                message=getattr(e, "message", str(e.detail)),
                type=getattr(e, "type", "None"),
                param=getattr(e, "param", "None"),
                code=getattr(e, "status_code", status.HTTP_400_BAD_REQUEST),
            )
        else:
            error_msg = f"{str(e)}"
            raise ProxyException(
                message=getattr(e, "message", error_msg),
                type=getattr(e, "type", "None"),
                param=getattr(e, "param", "None"),
                code=getattr(e, "code", getattr(e, "status_code", 500)),
            )


@router.get(
    "/v1/threads/{thread_id}/messages",
    dependencies=[Depends(user_api_key_auth)],
    tags=["assistants"],
)
@router.get(
    "/threads/{thread_id}/messages",
    dependencies=[Depends(user_api_key_auth)],
    tags=["assistants"],
)
async def get_messages(
    request: Request,
    thread_id: str,
    fastapi_response: Response,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Returns a list of messages for a given thread.

    API Reference - https://platform.openai.com/docs/api-reference/messages/listMessages
    """
    global proxy_logging_obj
    data: Dict = {}
    try:
        # Include original request and headers in the data
        data = await add_llm_data_to_request(
            data=data,
            request=request,
            general_settings=general_settings,
            user_api_key_dict=user_api_key_dict,
            version=version,
            proxy_config=proxy_config,
        )

        # for now use custom_llm_provider=="openai" -> this will change as LLM adds more providers for acreate_batch
        if llm_router is None:
            raise HTTPException(
                status_code=500, detail={"error": CommonProxyErrors.no_llm_router.value}
            )
        response = await llm_router.aget_messages(thread_id=thread_id, **data)

        ### ALERTING ###
        asyncio.create_task(
            proxy_logging_obj.update_request_status(
                llm_call_id=data.get("llm_call_id", ""), status="success"
            )
        )

        ### RESPONSE HEADERS ###
        hidden_params = getattr(response, "_hidden_params", {}) or {}
        model_id = hidden_params.get("model_id", None) or ""
        cache_key = hidden_params.get("cache_key", None) or ""
        api_base = hidden_params.get("api_base", None) or ""

        fastapi_response.headers.update(
            ProxyBaseLLMRequestProcessing.get_custom_headers(
                user_api_key_dict=user_api_key_dict,
                model_id=model_id,
                cache_key=cache_key,
                api_base=api_base,
                version=version,
                model_region=getattr(user_api_key_dict, "allowed_model_region", ""),
                request_data=data,
                hidden_params=hidden_params,
            )
        )

        return response
    except Exception as e:
        await proxy_logging_obj.post_call_failure_hook(
            user_api_key_dict=user_api_key_dict, original_exception=e, request_data=data
        )
        verbose_proxy_logger.error(
            "llm.proxy.proxy_server.get_messages(): Exception occured - {}".format(
                str(e)
            )
        )
        verbose_proxy_logger.debug(traceback.format_exc())
        if isinstance(e, HTTPException):
            raise ProxyException(
                message=getattr(e, "message", str(e.detail)),
                type=getattr(e, "type", "None"),
                param=getattr(e, "param", "None"),
                code=getattr(e, "status_code", status.HTTP_400_BAD_REQUEST),
            )
        else:
            error_msg = f"{str(e)}"
            raise ProxyException(
                message=getattr(e, "message", error_msg),
                type=getattr(e, "type", "None"),
                param=getattr(e, "param", "None"),
                code=getattr(e, "code", getattr(e, "status_code", 500)),
            )


@router.post(
    "/v1/threads/{thread_id}/runs",
    dependencies=[Depends(user_api_key_auth)],
    tags=["assistants"],
)
@router.post(
    "/threads/{thread_id}/runs",
    dependencies=[Depends(user_api_key_auth)],
    tags=["assistants"],
)
async def run_thread(
    request: Request,
    thread_id: str,
    fastapi_response: Response,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Create a run.

    API Reference: https://platform.openai.com/docs/api-reference/runs/createRun
    """
    global proxy_logging_obj
    data: Dict = {}
    try:
        body = await request.body()
        data = orjson.loads(body)
        # Include original request and headers in the data
        data = await add_llm_data_to_request(
            data=data,
            request=request,
            general_settings=general_settings,
            user_api_key_dict=user_api_key_dict,
            version=version,
            proxy_config=proxy_config,
        )

        # for now use custom_llm_provider=="openai" -> this will change as LLM adds more providers for acreate_batch
        if llm_router is None:
            raise HTTPException(
                status_code=500, detail={"error": CommonProxyErrors.no_llm_router.value}
            )
        response = await llm_router.arun_thread(thread_id=thread_id, **data)

        if (
            "stream" in data and data["stream"] is True
        ):  # use generate_responses to stream responses
            return StreamingResponse(
                async_assistants_data_generator(
                    user_api_key_dict=user_api_key_dict,
                    response=response,
                    request_data=data,
                ),
                media_type="text/event-stream",
            )

        ### ALERTING ###
        asyncio.create_task(
            proxy_logging_obj.update_request_status(
                llm_call_id=data.get("llm_call_id", ""), status="success"
            )
        )

        ### RESPONSE HEADERS ###
        hidden_params = getattr(response, "_hidden_params", {}) or {}
        model_id = hidden_params.get("model_id", None) or ""
        cache_key = hidden_params.get("cache_key", None) or ""
        api_base = hidden_params.get("api_base", None) or ""

        fastapi_response.headers.update(
            ProxyBaseLLMRequestProcessing.get_custom_headers(
                user_api_key_dict=user_api_key_dict,
                model_id=model_id,
                cache_key=cache_key,
                api_base=api_base,
                version=version,
                model_region=getattr(user_api_key_dict, "allowed_model_region", ""),
                request_data=data,
                hidden_params=hidden_params,
            )
        )

        return response
    except Exception as e:
        await proxy_logging_obj.post_call_failure_hook(
            user_api_key_dict=user_api_key_dict, original_exception=e, request_data=data
        )
        verbose_proxy_logger.error(
            "llm.proxy.proxy_server.run_thread(): Exception occured - {}".format(
                str(e)
            )
        )
        verbose_proxy_logger.debug(traceback.format_exc())
        if isinstance(e, HTTPException):
            raise ProxyException(
                message=getattr(e, "message", str(e.detail)),
                type=getattr(e, "type", "None"),
                param=getattr(e, "param", "None"),
                code=getattr(e, "status_code", status.HTTP_400_BAD_REQUEST),
            )
        else:
            error_msg = f"{str(e)}"
            raise ProxyException(
                message=getattr(e, "message", error_msg),
                type=getattr(e, "type", "None"),
                param=getattr(e, "param", "None"),
                code=getattr(e, "code", getattr(e, "status_code", 500)),
            )


@router.post(
    "/v1/moderations",
    dependencies=[Depends(user_api_key_auth)],
    response_class=ORJSONResponse,
    tags=["moderations"],
)
@router.post(
    "/moderations",
    dependencies=[Depends(user_api_key_auth)],
    response_class=ORJSONResponse,
    tags=["moderations"],
)
async def moderations(
    request: Request,
    fastapi_response: Response,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    The moderations endpoint is a tool you can use to check whether content complies with an LLM Providers policies.

    Quick Start
    ```
    curl --location 'http://0.0.0.0:4000/moderations' \
    --header 'Content-Type: application/json' \
    --header 'Authorization: Bearer sk-1234' \
    --data '{"input": "Sample text goes here", "model": "text-moderation-stable"}'
    ```
    """
    global proxy_logging_obj
    data: Dict = {}
    try:
        # Use orjson to parse JSON data, orjson speeds up requests significantly
        body = await request.body()
        data = orjson.loads(body)

        # Include original request and headers in the data
        data = await add_llm_data_to_request(
            data=data,
            request=request,
            general_settings=general_settings,
            user_api_key_dict=user_api_key_dict,
            version=version,
            proxy_config=proxy_config,
        )

        data["model"] = (
            general_settings.get("moderation_model", None)  # server default
            or user_model  # model name passed via cli args
            or data.get("model")  # default passed in http request
        )
        if user_model:
            data["model"] = user_model

        ### CALL HOOKS ### - modify incoming data / reject request before calling the model
        data = await proxy_logging_obj.pre_call_hook(
            user_api_key_dict=user_api_key_dict, data=data, call_type="moderation"
        )

        time.time()

        ## ROUTE TO CORRECT ENDPOINT ##
        llm_call = await route_request(
            data=data,
            route_type="amoderation",
            llm_router=llm_router,
            user_model=user_model,
        )
        response = await llm_call

        ### ALERTING ###
        asyncio.create_task(
            proxy_logging_obj.update_request_status(
                llm_call_id=data.get("llm_call_id", ""), status="success"
            )
        )

        ### RESPONSE HEADERS ###
        hidden_params = getattr(response, "_hidden_params", {}) or {}
        model_id = hidden_params.get("model_id", None) or ""
        cache_key = hidden_params.get("cache_key", None) or ""
        api_base = hidden_params.get("api_base", None) or ""

        fastapi_response.headers.update(
            ProxyBaseLLMRequestProcessing.get_custom_headers(
                user_api_key_dict=user_api_key_dict,
                model_id=model_id,
                cache_key=cache_key,
                api_base=api_base,
                version=version,
                model_region=getattr(user_api_key_dict, "allowed_model_region", ""),
                request_data=data,
                hidden_params=hidden_params,
            )
        )

        return response
    except Exception as e:
        await proxy_logging_obj.post_call_failure_hook(
            user_api_key_dict=user_api_key_dict, original_exception=e, request_data=data
        )
        verbose_proxy_logger.exception(
            "llm.proxy.proxy_server.moderations(): Exception occured - {}".format(
                str(e)
            )
        )
        if isinstance(e, HTTPException):
            raise ProxyException(
                message=getattr(e, "message", str(e)),
                type=getattr(e, "type", "None"),
                param=getattr(e, "param", "None"),
                code=getattr(e, "status_code", status.HTTP_400_BAD_REQUEST),
            )
        else:
            error_msg = f"{str(e)}"
            raise ProxyException(
                message=getattr(e, "message", error_msg),
                type=getattr(e, "type", "None"),
                param=getattr(e, "param", "None"),
                code=getattr(e, "status_code", 500),
            )


#### DEV UTILS ####

# @router.get(
#     "/utils/available_routes",
#     tags=["llm utils"],
#     dependencies=[Depends(user_api_key_auth)],
# )
# async def get_available_routes(user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth)):


@router.post(
    "/utils/token_counter",
    tags=["llm utils"],
    dependencies=[Depends(user_api_key_auth)],
    response_model=TokenCountResponse,
)
async def token_counter(request: TokenCountRequest):
    """ """
    from llm import token_counter

    global llm_router

    prompt = request.prompt
    messages = request.messages
    if prompt is None and messages is None:
        raise HTTPException(
            status_code=400, detail="prompt or messages must be provided"
        )

    deployment = None
    llm_model_name = None
    model_info: Optional[ModelMapInfo] = None
    if llm_router is not None:
        # get 1 deployment corresponding to the model
        for _model in llm_router.model_list:
            if _model["model_name"] == request.model:
                deployment = _model
                model_info = llm_router.get_router_model_info(
                    deployment=deployment,
                    received_model_name=request.model,
                )
                break
    if deployment is not None:
        llm_model_name = deployment.get("llm_params", {}).get("model")
        # remove the custom_llm_provider_prefix in the llm_model_name
        if "/" in llm_model_name:
            llm_model_name = llm_model_name.split("/", 1)[1]

    model_to_use = (
        llm_model_name or request.model
    )  # use llm model name, if it's not avalable then fallback to request.model

    custom_tokenizer: Optional[CustomHuggingfaceTokenizer] = None
    if model_info is not None:
        custom_tokenizer = cast(
            Optional[CustomHuggingfaceTokenizer],
            model_info.get("custom_tokenizer", None),
        )
    _tokenizer_used = llm.utils._select_tokenizer(
        model=model_to_use, custom_tokenizer=custom_tokenizer
    )

    tokenizer_used = str(_tokenizer_used["type"])
    total_tokens = token_counter(
        model=model_to_use,
        text=prompt,
        messages=messages,
        custom_tokenizer=_tokenizer_used,  # type: ignore
    )
    return TokenCountResponse(
        total_tokens=total_tokens,
        request_model=request.model,
        model_used=model_to_use,
        tokenizer_type=tokenizer_used,
    )


@router.get(
    "/utils/supported_openai_params",
    tags=["llm utils"],
    dependencies=[Depends(user_api_key_auth)],
)
async def supported_openai_params(model: str):
    """
    Returns supported openai params for a given llm model name

    e.g. `gpt-4` vs `gpt-3.5-turbo`

    Example curl:
    ```
    curl -X GET --location 'http://localhost:4000/utils/supported_openai_params?model=gpt-3.5-turbo-16k' \
        --header 'Authorization: Bearer sk-1234'
    ```
    """
    try:
        model, custom_llm_provider, _, _ = llm.get_llm_provider(model=model)
        return {
            "supported_openai_params": llm.get_supported_openai_params(
                model=model, custom_llm_provider=custom_llm_provider
            )
        }
    except Exception:
        raise HTTPException(
            status_code=400, detail={"error": "Could not map model={}".format(model)}
        )


@router.post(
    "/utils/transform_request",
    tags=["llm utils"],
    dependencies=[Depends(user_api_key_auth)],
    response_model=RawRequestTypedDict,
)
async def transform_request(request: TransformRequestBody):
    from llm.utils import return_raw_request

    return return_raw_request(endpoint=request.call_type, kwargs=request.request_body)


@router.get(
    "/v2/model/info",
    description="v2 - returns all the models set on the config.yaml, shows 'user_access' = True if the user has access to the model. Provides more info about each model in /models, including config.yaml descriptions (except api key and api base)",
    tags=["model management"],
    dependencies=[Depends(user_api_key_auth)],
    include_in_schema=False,
)
async def model_info_v2(
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
    model: Optional[str] = fastapi.Query(
        None, description="Specify the model name (optional)"
    ),
    debug: Optional[bool] = False,
):
    """
    BETA ENDPOINT. Might change unexpectedly. Use `/v1/model/info` for now.
    """
    global llm_model_list, general_settings, user_config_file_path, proxy_config, llm_router

    if llm_router is None:
        raise HTTPException(
            status_code=500,
            detail={
                "error": f"No model list passed, models router={llm_router}. You can add a model through the config.yaml or on the LLM Admin UI."
            },
        )

    # Load existing config
    await proxy_config.get_config()
    all_models = copy.deepcopy(llm_router.model_list)

    if user_model is not None:
        # if user does not use a config.yaml, https://github.com/hanzoai/llm/issues/2061
        all_models += [user_model]

    # check all models user has access to in user_api_key_dict
    if len(user_api_key_dict.models) > 0:
        pass

    if model is not None:
        all_models = [m for m in all_models if m["model_name"] == model]

    # fill in model info based on config.yaml and llm model_prices_and_context_window.json
    for _model in all_models:
        # provided model_info in config.yaml
        model_info = _model.get("model_info", {})
        if debug is True:
            _openai_client = "None"
            if llm_router is not None:
                _openai_client = (
                    llm_router._get_client(
                        deployment=_model, kwargs={}, client_type="async"
                    )
                    or "None"
                )
            else:
                _openai_client = "llm_router_is_None"
            openai_client = str(_openai_client)
            _model["openai_client"] = openai_client

        # read llm model_prices_and_context_window.json to get the following:
        # input_cost_per_token, output_cost_per_token, max_tokens
        llm_model_info = get_llm_model_info(model=_model)

        # 2nd pass on the model, try seeing if we can find model in llm model_cost map
        if llm_model_info == {}:
            # use llm_param model_name to get model_info
            llm_params = _model.get("llm_params", {})
            llm_model = llm_params.get("model", None)
            try:
                llm_model_info = llm.get_model_info(model=llm_model)
            except Exception:
                llm_model_info = {}
        # 3rd pass on the model, try seeing if we can find model but without the "/" in model cost map
        if llm_model_info == {}:
            # use llm_param model_name to get model_info
            llm_params = _model.get("llm_params", {})
            llm_model = llm_params.get("model", None)
            split_model = llm_model.split("/")
            if len(split_model) > 0:
                llm_model = split_model[-1]
            try:
                llm_model_info = llm.get_model_info(
                    model=llm_model, custom_llm_provider=split_model[0]
                )
            except Exception:
                llm_model_info = {}
        for k, v in llm_model_info.items():
            if k not in model_info:
                model_info[k] = v
        _model["model_info"] = model_info
        # don't return the api key / vertex credentials
        # don't return the llm credentials
        _model["llm_params"].pop("api_key", None)
        _model["llm_params"].pop("vertex_credentials", None)
        _model["llm_params"].pop("aws_access_key_id", None)
        _model["llm_params"].pop("aws_secret_access_key", None)

    verbose_proxy_logger.debug("all_models: %s", all_models)
    return {"data": all_models}


@router.get(
    "/model/streaming_metrics",
    description="View time to first token for models in spend logs",
    tags=["model management"],
    include_in_schema=False,
    dependencies=[Depends(user_api_key_auth)],
)
async def model_streaming_metrics(
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
    _selected_model_group: Optional[str] = None,
    startTime: Optional[datetime] = None,
    endTime: Optional[datetime] = None,
):
    global prisma_client, llm_router
    if prisma_client is None:
        raise ProxyException(
            message=CommonProxyErrors.db_not_connected_error.value,
            type="internal_error",
            param="None",
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    startTime = startTime or datetime.now() - timedelta(days=7)  # show over past week
    endTime = endTime or datetime.now()

    is_same_day = startTime.date() == endTime.date()
    if is_same_day:
        sql_query = """
            SELECT
                api_base,
                model_group,
                model,
                "startTime",
                request_id,
                EXTRACT(epoch FROM ("completionStartTime" - "startTime")) AS time_to_first_token
            FROM
                "LLM_SpendLogs"
            WHERE
                "model_group" = $1 AND "cache_hit" != 'True'
                AND "completionStartTime" IS NOT NULL
                AND "completionStartTime" != "endTime"
                AND DATE("startTime") = DATE($2::timestamp)
            GROUP BY
                api_base,
                model_group,
                model,
                request_id
            ORDER BY
                time_to_first_token DESC;
        """
    else:
        sql_query = """
            SELECT
                api_base,
                model_group,
                model,
                DATE_TRUNC('day', "startTime")::DATE AS day,
                AVG(EXTRACT(epoch FROM ("completionStartTime" - "startTime"))) AS time_to_first_token
            FROM
                "LLM_SpendLogs"
            WHERE
                "startTime" BETWEEN $2::timestamp AND $3::timestamp
                AND "model_group" = $1 AND "cache_hit" != 'True'
                AND "completionStartTime" IS NOT NULL
                AND "completionStartTime" != "endTime"
            GROUP BY
                api_base,
                model_group,
                model,
                day
            ORDER BY
                time_to_first_token DESC;
        """

    _all_api_bases = set()
    db_response = await prisma_client.db.query_raw(
        sql_query, _selected_model_group, startTime, endTime
    )
    _daily_entries: dict = {}  # {"Jun 23": {"model1": 0.002, "model2": 0.003}}
    if db_response is not None:
        for model_data in db_response:
            _api_base = model_data["api_base"]
            _model = model_data["model"]
            time_to_first_token = model_data["time_to_first_token"]
            unique_key = ""
            if is_same_day:
                _request_id = model_data["request_id"]
                unique_key = _request_id
                if _request_id not in _daily_entries:
                    _daily_entries[_request_id] = {}
            else:
                _day = model_data["day"]
                unique_key = _day
                time_to_first_token = model_data["time_to_first_token"]
                if _day not in _daily_entries:
                    _daily_entries[_day] = {}
            _combined_model_name = str(_model)
            if "https://" in _api_base:
                _combined_model_name = str(_api_base)
            if "/openai/" in _combined_model_name:
                _combined_model_name = _combined_model_name.split("/openai/")[0]

            _all_api_bases.add(_combined_model_name)

            _daily_entries[unique_key][_combined_model_name] = time_to_first_token

        """
        each entry needs to be like this:
        {
            date: 'Jun 23',
            'gpt-4-https://api.openai.com/v1/': 0.002,
            'gpt-43-https://api.openai.com-12/v1/': 0.002,
        }
        """
        # convert daily entries to list of dicts

        response: List[dict] = []

        # sort daily entries by date
        _daily_entries = dict(sorted(_daily_entries.items(), key=lambda item: item[0]))
        for day in _daily_entries:
            entry = {"date": str(day)}
            for model_key, latency in _daily_entries[day].items():
                entry[model_key] = latency
            response.append(entry)

        return {
            "data": response,
            "all_api_bases": list(_all_api_bases),
        }


@router.get(
    "/model/metrics",
    description="View number of requests & avg latency per model on config.yaml",
    tags=["model management"],
    include_in_schema=False,
    dependencies=[Depends(user_api_key_auth)],
)
async def model_metrics(
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
    _selected_model_group: Optional[str] = "gpt-4-32k",
    startTime: Optional[datetime] = None,
    endTime: Optional[datetime] = None,
    api_key: Optional[str] = None,
    customer: Optional[str] = None,
):
    global prisma_client, llm_router
    if prisma_client is None:
        raise ProxyException(
            message="Prisma Client is not initialized",
            type="internal_error",
            param="None",
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    startTime = startTime or datetime.now() - timedelta(days=30)
    endTime = endTime or datetime.now()

    if api_key is None or api_key == "undefined":
        api_key = "null"

    if customer is None or customer == "undefined":
        customer = "null"

    sql_query = """
        SELECT
            api_base,
            model_group,
            model,
            DATE_TRUNC('day', "startTime")::DATE AS day,
            AVG(EXTRACT(epoch FROM ("endTime" - "startTime")) / NULLIF("completion_tokens", 0)) AS avg_latency_per_token
        FROM
            "LLM_SpendLogs"
        WHERE
            "startTime" >= $2::timestamp AND "startTime" <= $3::timestamp
            AND "model_group" = $1 AND "cache_hit" != 'True'
            AND (
                CASE
                    WHEN $4 != 'null' THEN "api_key" = $4
                    ELSE TRUE
                END
            )
            AND (
                CASE
                    WHEN $5 != 'null' THEN "end_user" = $5
                    ELSE TRUE
                END
            )
        GROUP BY
            api_base,
            model_group,
            model,
            day
        HAVING
            SUM(completion_tokens) > 0
        ORDER BY
            avg_latency_per_token DESC;
    """
    _all_api_bases = set()
    db_response = await prisma_client.db.query_raw(
        sql_query, _selected_model_group, startTime, endTime, api_key, customer
    )
    _daily_entries: dict = {}  # {"Jun 23": {"model1": 0.002, "model2": 0.003}}

    if db_response is not None:
        for model_data in db_response:
            _api_base = model_data["api_base"]
            _model = model_data["model"]
            _day = model_data["day"]
            _avg_latency_per_token = model_data["avg_latency_per_token"]
            if _day not in _daily_entries:
                _daily_entries[_day] = {}
            _combined_model_name = str(_model)
            if _api_base is not None and "https://" in _api_base:
                _combined_model_name = str(_api_base)
            if _combined_model_name is not None and "/openai/" in _combined_model_name:
                _combined_model_name = _combined_model_name.split("/openai/")[0]

            _all_api_bases.add(_combined_model_name)
            _daily_entries[_day][_combined_model_name] = _avg_latency_per_token

        """
        each entry needs to be like this:
        {
            date: 'Jun 23',
            'gpt-4-https://api.openai.com/v1/': 0.002,
            'gpt-43-https://api.openai.com-12/v1/': 0.002,
        }
        """
        # convert daily entries to list of dicts

        response: List[dict] = []

        # sort daily entries by date
        _daily_entries = dict(sorted(_daily_entries.items(), key=lambda item: item[0]))
        for day in _daily_entries:
            entry = {"date": str(day)}
            for model_key, latency in _daily_entries[day].items():
                entry[model_key] = latency
            response.append(entry)

        return {
            "data": response,
            "all_api_bases": list(_all_api_bases),
        }


@router.get(
    "/model/metrics/slow_responses",
    description="View number of hanging requests per model_group",
    tags=["model management"],
    include_in_schema=False,
    dependencies=[Depends(user_api_key_auth)],
)
async def model_metrics_slow_responses(
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
    _selected_model_group: Optional[str] = "gpt-4-32k",
    startTime: Optional[datetime] = None,
    endTime: Optional[datetime] = None,
    api_key: Optional[str] = None,
    customer: Optional[str] = None,
):
    global prisma_client, llm_router, proxy_logging_obj
    if prisma_client is None:
        raise ProxyException(
            message="Prisma Client is not initialized",
            type="internal_error",
            param="None",
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    if api_key is None or api_key == "undefined":
        api_key = "null"

    if customer is None or customer == "undefined":
        customer = "null"

    startTime = startTime or datetime.now() - timedelta(days=30)
    endTime = endTime or datetime.now()

    alerting_threshold = (
        proxy_logging_obj.slack_alerting_instance.alerting_threshold or 300
    )
    alerting_threshold = int(alerting_threshold)

    sql_query = """
SELECT
    api_base,
    COUNT(*) AS total_count,
    SUM(CASE
        WHEN ("endTime" - "startTime") >= (INTERVAL '1 SECOND' * CAST($1 AS INTEGER)) THEN 1
        ELSE 0
    END) AS slow_count
FROM
    "LLM_SpendLogs"
WHERE
    "model_group" = $2
    AND "cache_hit" != 'True'
    AND "startTime" >= $3::timestamp
    AND "startTime" <= $4::timestamp
    AND (
        CASE
            WHEN $5 != 'null' THEN "api_key" = $5
            ELSE TRUE
        END
    )
    AND (
        CASE
            WHEN $6 != 'null' THEN "end_user" = $6
            ELSE TRUE
        END
    )
GROUP BY
    api_base
ORDER BY
    slow_count DESC;
    """

    db_response = await prisma_client.db.query_raw(
        sql_query,
        alerting_threshold,
        _selected_model_group,
        startTime,
        endTime,
        api_key,
        customer,
    )

    if db_response is not None:
        for row in db_response:
            _api_base = row.get("api_base") or ""
            if "/openai/" in _api_base:
                _api_base = _api_base.split("/openai/")[0]
            row["api_base"] = _api_base
    return db_response


@router.get(
    "/model/metrics/exceptions",
    description="View number of failed requests per model on config.yaml",
    tags=["model management"],
    include_in_schema=False,
    dependencies=[Depends(user_api_key_auth)],
)
async def model_metrics_exceptions(
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
    _selected_model_group: Optional[str] = None,
    startTime: Optional[datetime] = None,
    endTime: Optional[datetime] = None,
    api_key: Optional[str] = None,
    customer: Optional[str] = None,
):
    global prisma_client, llm_router
    if prisma_client is None:
        raise ProxyException(
            message="Prisma Client is not initialized",
            type="internal_error",
            param="None",
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    startTime = startTime or datetime.now() - timedelta(days=30)
    endTime = endTime or datetime.now()

    if api_key is None or api_key == "undefined":
        api_key = "null"

    """
    """
    sql_query = """
        WITH cte AS (
            SELECT
                CASE WHEN api_base = '' THEN llm_model_name ELSE CONCAT(llm_model_name, '-', api_base) END AS combined_model_api_base,
                exception_type,
                COUNT(*) AS num_rate_limit_exceptions
            FROM "LLM_ErrorLogs"
            WHERE
                "startTime" >= $1::timestamp
                AND "endTime" <= $2::timestamp
                AND model_group = $3
            GROUP BY combined_model_api_base, exception_type
        )
        SELECT
            combined_model_api_base,
            COUNT(*) AS total_exceptions,
            json_object_agg(exception_type, num_rate_limit_exceptions) AS exception_counts
        FROM cte
        GROUP BY combined_model_api_base
        ORDER BY total_exceptions DESC
        LIMIT 200;
    """
    db_response = await prisma_client.db.query_raw(
        sql_query, startTime, endTime, _selected_model_group, api_key
    )
    response: List[dict] = []
    exception_types = set()

    """
    Return Data
    {
        "combined_model_api_base": "gpt-3.5-turbo-https://api.openai.com/v1/,
        "total_exceptions": 5,
        "BadRequestException": 5,
        "TimeoutException": 2
    }
    """

    if db_response is not None:
        # loop through all models
        for model_data in db_response:
            model = model_data.get("combined_model_api_base", "")
            total_exceptions = model_data.get("total_exceptions", 0)
            exception_counts = model_data.get("exception_counts", {})
            curr_row = {
                "model": model,
                "total_exceptions": total_exceptions,
            }
            curr_row.update(exception_counts)
            response.append(curr_row)
            for k, v in exception_counts.items():
                exception_types.add(k)

    return {"data": response, "exception_types": list(exception_types)}


def _get_proxy_model_info(model: dict) -> dict:
    # provided model_info in config.yaml
    model_info = model.get("model_info", {})

    # read llm model_prices_and_context_window.json to get the following:
    # input_cost_per_token, output_cost_per_token, max_tokens
    llm_model_info = get_llm_model_info(model=model)

    # 2nd pass on the model, try seeing if we can find model in llm model_cost map
    if llm_model_info == {}:
        # use llm_param model_name to get model_info
        llm_params = model.get("llm_params", {})
        llm_model = llm_params.get("model", None)
        try:
            llm_model_info = llm.get_model_info(model=llm_model)
        except Exception:
            llm_model_info = {}
    # 3rd pass on the model, try seeing if we can find model but without the "/" in model cost map
    if llm_model_info == {}:
        # use llm_param model_name to get model_info
        llm_params = model.get("llm_params", {})
        llm_model = llm_params.get("model", None)
        split_model = llm_model.split("/")
        if len(split_model) > 0:
            llm_model = split_model[-1]
        try:
            llm_model_info = llm.get_model_info(
                model=llm_model, custom_llm_provider=split_model[0]
            )
        except Exception:
            llm_model_info = {}
    for k, v in llm_model_info.items():
        if k not in model_info:
            model_info[k] = v
    model["model_info"] = model_info
    # don't return the llm credentials
    model = remove_sensitive_info_from_deployment(deployment_dict=model)

    return model


@router.get(
    "/model/info",
    tags=["model management"],
    dependencies=[Depends(user_api_key_auth)],
)
@router.get(
    "/v1/model/info",
    tags=["model management"],
    dependencies=[Depends(user_api_key_auth)],
)
async def model_info_v1(  # noqa: PLR0915
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
    llm_model_id: Optional[str] = None,
):
    """
    Provides more info about each model in /models, including config.yaml descriptions (except api key and api base)

    Parameters:
        llm_model_id: Optional[str] = None (this is the value of `x-llm-model-id` returned in response headers)

        - When llm_model_id is passed, it will return the info for that specific model
        - When llm_model_id is not passed, it will return the info for all models

    Returns:
        Returns a dictionary containing information about each model.

    Example Response:
    ```json
    {
        "data": [
                    {
                        "model_name": "fake-openai-endpoint",
                        "llm_params": {
                            "api_base": "https://exampleopenaiendpoint-production.up.railway.app/",
                            "model": "openai/fake"
                        },
                        "model_info": {
                            "id": "112f74fab24a7a5245d2ced3536dd8f5f9192c57ee6e332af0f0512e08bed5af",
                            "db_model": false
                        }
                    }
                ]
    }

    ```
    """
    global llm_model_list, general_settings, user_config_file_path, proxy_config, llm_router, user_model

    if user_model is not None:
        # user is trying to get specific model from llm router
        try:
            model_info: Dict = cast(Dict, llm.get_model_info(model=user_model))
        except Exception:
            model_info = {}
        _deployment_info = Deployment(
            model_name="*",
            llm_params=LLM_Params(
                model=user_model,
            ),
            model_info=model_info,
        )
        _deployment_info_dict = _deployment_info.model_dump()
        _deployment_info_dict = remove_sensitive_info_from_deployment(
            deployment_dict=_deployment_info_dict
        )
        return {"data": _deployment_info_dict}

    if llm_model_list is None:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "LLM Model List not loaded in. Make sure you passed models in your config.yaml or on the LLM Admin UI. - https://docs.hanzo.ai/docs/proxy/configs"
            },
        )

    if llm_router is None:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "LLM Router is not loaded in. Make sure you passed models in your config.yaml or on the LLM Admin UI. - https://docs.hanzo.ai/docs/proxy/configs"
            },
        )

    if llm_model_id is not None:
        # user is trying to get specific model from llm router
        deployment_info = llm_router.get_deployment(model_id=llm_model_id)
        if deployment_info is None:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": f"Model id = {llm_model_id} not found on llm proxy"
                },
            )
        _deployment_info_dict = _get_proxy_model_info(
            model=deployment_info.model_dump(exclude_none=True)
        )
        return {"data": [_deployment_info_dict]}

    all_models: List[dict] = []
    model_access_groups: Dict[str, List[str]] = defaultdict(list)
    ## CHECK IF MODEL RESTRICTIONS ARE SET AT KEY/TEAM LEVEL ##
    if llm_router is None:
        proxy_model_list = []
    else:
        proxy_model_list = llm_router.get_model_names()
        model_access_groups = llm_router.get_model_access_groups()
    key_models = get_key_models(
        user_api_key_dict=user_api_key_dict,
        proxy_model_list=proxy_model_list,
        model_access_groups=model_access_groups,
    )
    team_models = get_team_models(
        team_models=user_api_key_dict.team_models,
        proxy_model_list=proxy_model_list,
        model_access_groups=model_access_groups,
    )
    all_models_str = get_complete_model_list(
        key_models=key_models,
        team_models=team_models,
        proxy_model_list=proxy_model_list,
        user_model=user_model,
        infer_model_from_keys=general_settings.get("infer_model_from_keys", False),
    )

    if len(all_models_str) > 0:
        _relevant_models = []
        for model in all_models_str:
            router_models = llm_router.get_model_list(model_name=model)
            if router_models is not None:
                _relevant_models.extend(router_models)
        if llm_model_list is not None:
            all_models = copy.deepcopy(_relevant_models)  # type: ignore
        else:
            all_models = []

    for in_place_model in all_models:
        in_place_model = _get_proxy_model_info(model=in_place_model)

    verbose_proxy_logger.debug("all_models: %s", all_models)
    return {"data": all_models}


def _get_model_group_info(
    llm_router: Router, all_models_str: List[str], model_group: Optional[str]
) -> List[ModelGroupInfo]:
    model_groups: List[ModelGroupInfo] = []
    for model in all_models_str:
        if model_group is not None and model_group != model:
            continue

        _model_group_info = llm_router.get_model_group_info(model_group=model)
        if _model_group_info is not None:
            model_groups.append(_model_group_info)
    return model_groups


@router.get(
    "/model_group/info",
    tags=["model management"],
    dependencies=[Depends(user_api_key_auth)],
)
async def model_group_info(
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
    model_group: Optional[str] = None,
):
    """
    Get information about all the deployments on llm proxy, including config.yaml descriptions (except api key and api base)

    - /model_group/info returns all model groups. End users of proxy should use /model_group/info since those models will be used for /chat/completions, /embeddings, etc.
    - /model_group/info?model_group=rerank-english-v3.0 returns all model groups for a specific model group (`model_name` in config.yaml)



    Example Request (All Models):
    ```shell
    curl -X 'GET' \
    'http://localhost:4000/model_group/info' \
    -H 'accept: application/json' \
    -H 'x-api-key: sk-1234'
    ```

    Example Request (Specific Model Group):
    ```shell
    curl -X 'GET' \
    'http://localhost:4000/model_group/info?model_group=rerank-english-v3.0' \
    -H 'accept: application/json' \
    -H 'Authorization: Bearer sk-1234'
    ```

    Example Request (Specific Wildcard Model Group): (e.g. `model_name: openai/*` on config.yaml)
    ```shell
    curl -X 'GET' \
    'http://localhost:4000/model_group/info?model_group=openai/tts-1'
    -H 'accept: application/json' \
    -H 'Authorization: Bearersk-1234'
    ```

    Learn how to use and set wildcard models [here](https://docs.hanzo.ai/docs/wildcard_routing)

    Example Response:
    ```json
        {
            "data": [
                {
                "model_group": "rerank-english-v3.0",
                "providers": [
                    "cohere"
                ],
                "max_input_tokens": null,
                "max_output_tokens": null,
                "input_cost_per_token": 0.0,
                "output_cost_per_token": 0.0,
                "mode": null,
                "tpm": null,
                "rpm": null,
                "supports_parallel_function_calling": false,
                "supports_vision": false,
                "supports_function_calling": false,
                "supported_openai_params": [
                    "stream",
                    "temperature",
                    "max_tokens",
                    "logit_bias",
                    "top_p",
                    "frequency_penalty",
                    "presence_penalty",
                    "stop",
                    "n",
                    "extra_headers"
                ]
                },
                {
                "model_group": "gpt-3.5-turbo",
                "providers": [
                    "openai"
                ],
                "max_input_tokens": 16385.0,
                "max_output_tokens": 4096.0,
                "input_cost_per_token": 1.5e-06,
                "output_cost_per_token": 2e-06,
                "mode": "chat",
                "tpm": null,
                "rpm": null,
                "supports_parallel_function_calling": false,
                "supports_vision": false,
                "supports_function_calling": true,
                "supported_openai_params": [
                    "frequency_penalty",
                    "logit_bias",
                    "logprobs",
                    "top_logprobs",
                    "max_tokens",
                    "max_completion_tokens",
                    "n",
                    "presence_penalty",
                    "seed",
                    "stop",
                    "stream",
                    "stream_options",
                    "temperature",
                    "top_p",
                    "tools",
                    "tool_choice",
                    "function_call",
                    "functions",
                    "max_retries",
                    "extra_headers",
                    "parallel_tool_calls",
                    "response_format"
                ]
                },
                {
                "model_group": "llava-hf",
                "providers": [
                    "openai"
                ],
                "max_input_tokens": null,
                "max_output_tokens": null,
                "input_cost_per_token": 0.0,
                "output_cost_per_token": 0.0,
                "mode": null,
                "tpm": null,
                "rpm": null,
                "supports_parallel_function_calling": false,
                "supports_vision": true,
                "supports_function_calling": false,
                "supported_openai_params": [
                    "frequency_penalty",
                    "logit_bias",
                    "logprobs",
                    "top_logprobs",
                    "max_tokens",
                    "max_completion_tokens",
                    "n",
                    "presence_penalty",
                    "seed",
                    "stop",
                    "stream",
                    "stream_options",
                    "temperature",
                    "top_p",
                    "tools",
                    "tool_choice",
                    "function_call",
                    "functions",
                    "max_retries",
                    "extra_headers",
                    "parallel_tool_calls",
                    "response_format"
                ]
                }
            ]
            }
    ```
    """
    global llm_model_list, general_settings, user_config_file_path, proxy_config, llm_router

    if llm_model_list is None:
        raise HTTPException(
            status_code=500, detail={"error": "LLM Model List not loaded in"}
        )
    if llm_router is None:
        raise HTTPException(
            status_code=500, detail={"error": "LLM Router is not loaded in"}
        )
    ## CHECK IF MODEL RESTRICTIONS ARE SET AT KEY/TEAM LEVEL ##
    model_access_groups: Dict[str, List[str]] = defaultdict(list)
    if llm_router is None:
        proxy_model_list = []
    else:
        proxy_model_list = llm_router.get_model_names()
        model_access_groups = llm_router.get_model_access_groups()

    key_models = get_key_models(
        user_api_key_dict=user_api_key_dict,
        proxy_model_list=proxy_model_list,
        model_access_groups=model_access_groups,
    )
    team_models = get_team_models(
        team_models=user_api_key_dict.team_models,
        proxy_model_list=proxy_model_list,
        model_access_groups=model_access_groups,
    )
    all_models_str = get_complete_model_list(
        key_models=key_models,
        team_models=team_models,
        proxy_model_list=proxy_model_list,
        user_model=user_model,
        infer_model_from_keys=general_settings.get("infer_model_from_keys", False),
    )

    model_groups: List[ModelGroupInfo] = _get_model_group_info(
        llm_router=llm_router, all_models_str=all_models_str, model_group=model_group
    )

    return {"data": model_groups}


@router.get(
    "/model/settings",
    description="Returns provider name, description, and required parameters for each provider",
    tags=["model management"],
    dependencies=[Depends(user_api_key_auth)],
    include_in_schema=False,
)
async def model_settings():
    """
    Used by UI to generate 'model add' page
    {
        field_name=field_name,
        field_type=allowed_args[field_name]["type"], # string/int
        field_description=field_info.description or "", # human-friendly description
        field_value=general_settings.get(field_name, None), # example value
    }
    """

    returned_list = []
    for provider in llm.provider_list:
        returned_list.append(
            ProviderInfo(
                name=provider,
                fields=llm.get_provider_fields(custom_llm_provider=provider),
            )
        )

    return returned_list


#### ALERTING MANAGEMENT ENDPOINTS ####


@router.get(
    "/alerting/settings",
    description="Return the configurable alerting param, description, and current value",
    tags=["alerting"],
    dependencies=[Depends(user_api_key_auth)],
    include_in_schema=False,
)
async def alerting_settings(
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    global proxy_logging_obj, prisma_client
    """
    Used by UI to generate 'alerting settings' page
    {
        field_name=field_name,
        field_type=allowed_args[field_name]["type"], # string/int
        field_description=field_info.description or "", # human-friendly description
        field_value=general_settings.get(field_name, None), # example value
    }
    """
    if prisma_client is None:
        raise HTTPException(
            status_code=400,
            detail={"error": CommonProxyErrors.db_not_connected_error.value},
        )

    if user_api_key_dict.user_role != LLMUserRoles.PROXY_ADMIN:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "{}, your role={}".format(
                    CommonProxyErrors.not_allowed_access.value,
                    user_api_key_dict.user_role,
                )
            },
        )

    ## get general settings from db
    db_general_settings = await prisma_client.db.llm_config.find_first(
        where={"param_name": "general_settings"}
    )

    if db_general_settings is not None and db_general_settings.param_value is not None:
        db_general_settings_dict = dict(db_general_settings.param_value)
        alerting_args_dict: dict = db_general_settings_dict.get("alerting_args", {})  # type: ignore
        alerting_values: Optional[list] = db_general_settings_dict.get("alerting")  # type: ignore
    else:
        alerting_args_dict = {}
        alerting_values = None

    allowed_args = {
        "slack_alerting": {"type": "Boolean"},
        "daily_report_frequency": {"type": "Integer"},
        "report_check_interval": {"type": "Integer"},
        "budget_alert_ttl": {"type": "Integer"},
        "outage_alert_ttl": {"type": "Integer"},
        "region_outage_alert_ttl": {"type": "Integer"},
        "minor_outage_alert_threshold": {"type": "Integer"},
        "major_outage_alert_threshold": {"type": "Integer"},
        "max_outage_alert_list_size": {"type": "Integer"},
    }

    _slack_alerting: SlackAlerting = proxy_logging_obj.slack_alerting_instance
    _slack_alerting_args_dict = _slack_alerting.alerting_args.model_dump()

    return_val = []

    is_slack_enabled = False

    if general_settings.get("alerting") and isinstance(
        general_settings["alerting"], list
    ):
        if "slack" in general_settings["alerting"]:
            is_slack_enabled = True

    _response_obj = ConfigList(
        field_name="slack_alerting",
        field_type=allowed_args["slack_alerting"]["type"],
        field_description="Enable slack alerting for monitoring proxy in production: llm outages, budgets, spend tracking failures.",
        field_value=is_slack_enabled,
        stored_in_db=True if alerting_values is not None else False,
        field_default_value=None,
        premium_field=False,
    )
    return_val.append(_response_obj)

    for field_name, field_info in SlackAlertingArgs.model_fields.items():
        if field_name in allowed_args:

            _stored_in_db: Optional[bool] = None
            if field_name in alerting_args_dict:
                _stored_in_db = True
            else:
                _stored_in_db = False

            _response_obj = ConfigList(
                field_name=field_name,
                field_type=allowed_args[field_name]["type"],
                field_description=field_info.description or "",
                field_value=_slack_alerting_args_dict.get(field_name, None),
                stored_in_db=_stored_in_db,
                field_default_value=field_info.default,
                premium_field=(
                    True if field_name == "region_outage_alert_ttl" else False
                ),
            )
            return_val.append(_response_obj)
    return return_val


#### EXPERIMENTAL QUEUING ####
@router.post(
    "/queue/chat/completions",
    tags=["experimental"],
    dependencies=[Depends(user_api_key_auth)],
    include_in_schema=False,
)
async def async_queue_request(
    request: Request,
    fastapi_response: Response,
    model: Optional[str] = None,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    global general_settings, user_debug, proxy_logging_obj
    """
    v2 attempt at a background worker to handle queuing.

    Just supports /chat/completion calls currently.

    Now using a FastAPI background task + /chat/completions compatible endpoint
    """
    data = {}
    try:
        data = await request.json()  # type: ignore

        # Include original request and headers in the data
        data["proxy_server_request"] = {
            "url": str(request.url),
            "method": request.method,
            "headers": dict(request.headers),
            "body": copy.copy(data),  # use copy instead of deepcopy
        }

        verbose_proxy_logger.debug("receiving data: %s", data)
        data["model"] = (
            general_settings.get("completion_model", None)  # server default
            or user_model  # model name passed via cli args
            or model  # for azure deployments
            or data.get("model", None)  # default passed in http request
        )

        # users can pass in 'user' param to /chat/completions. Don't override it
        if data.get("user", None) is None and user_api_key_dict.user_id is not None:
            # if users are using user_api_key_auth, set `user` in `data`
            data["user"] = user_api_key_dict.user_id

        if "metadata" not in data:
            data["metadata"] = {}
        data["metadata"]["user_api_key"] = user_api_key_dict.api_key
        data["metadata"]["user_api_key_metadata"] = user_api_key_dict.metadata
        _headers = dict(request.headers)
        _headers.pop(
            "authorization", None
        )  # do not store the original `sk-..` api key in the db
        data["metadata"]["headers"] = _headers
        data["metadata"]["user_api_key_alias"] = getattr(
            user_api_key_dict, "key_alias", None
        )
        data["metadata"]["user_api_key_user_id"] = user_api_key_dict.user_id
        data["metadata"]["user_api_key_team_id"] = getattr(
            user_api_key_dict, "team_id", None
        )
        data["metadata"]["endpoint"] = str(request.url)

        global user_temperature, user_request_timeout, user_max_tokens, user_api_base
        # override with user settings, these are params passed via cli
        if user_temperature:
            data["temperature"] = user_temperature
        if user_request_timeout:
            data["request_timeout"] = user_request_timeout
        if user_max_tokens:
            data["max_tokens"] = user_max_tokens
        if user_api_base:
            data["api_base"] = user_api_base

        if llm_router is None:
            raise HTTPException(
                status_code=500, detail={"error": CommonProxyErrors.no_llm_router.value}
            )

        response = await llm_router.schedule_acompletion(**data)

        if (
            "stream" in data and data["stream"] is True
        ):  # use generate_responses to stream responses
            return StreamingResponse(
                async_data_generator(
                    user_api_key_dict=user_api_key_dict,
                    response=response,
                    request_data=data,
                ),
                media_type="text/event-stream",
            )

        fastapi_response.headers.update({"x-llm-priority": str(data["priority"])})
        return response
    except Exception as e:
        await proxy_logging_obj.post_call_failure_hook(
            user_api_key_dict=user_api_key_dict, original_exception=e, request_data=data
        )
        if isinstance(e, HTTPException):
            raise ProxyException(
                message=getattr(e, "detail", f"Authentication Error({str(e)})"),
                type=ProxyErrorTypes.auth_error,
                param=getattr(e, "param", "None"),
                code=getattr(e, "status_code", status.HTTP_400_BAD_REQUEST),
            )
        elif isinstance(e, ProxyException):
            raise e
        raise ProxyException(
            message="Authentication Error, " + str(e),
            type=ProxyErrorTypes.auth_error,
            param=getattr(e, "param", "None"),
            code=status.HTTP_400_BAD_REQUEST,
        )


@app.get("/fallback/login", tags=["experimental"], include_in_schema=False)
async def fallback_login(request: Request):
    """
    Create Proxy API Keys using Google Workspace SSO. Requires setting PROXY_BASE_URL in .env
    PROXY_BASE_URL should be the your deployed proxy endpoint, e.g. PROXY_BASE_URL="https://llm-production-7002.up.railway.app/"
    Example:
    """
    # get url from request
    redirect_url = os.getenv("PROXY_BASE_URL", str(request.base_url))
    ui_username = os.getenv("UI_USERNAME")
    if redirect_url.endswith("/"):
        redirect_url += "sso/callback"
    else:
        redirect_url += "/sso/callback"

    if ui_username is not None:
        # No Google, Microsoft SSO
        # Use UI Credentials set in .env
        from fastapi.responses import HTMLResponse

        return HTMLResponse(content=html_form, status_code=200)
    else:
        from fastapi.responses import HTMLResponse

        return HTMLResponse(content=html_form, status_code=200)


@router.post(
    "/login", include_in_schema=False
)  # hidden since this is a helper for UI sso login
async def login(request: Request):  # noqa: PLR0915
    global premium_user, general_settings
    try:
        import multipart
    except ImportError:
        subprocess.run(["pip", "install", "python-multipart"])
    global master_key
    if master_key is None:
        raise ProxyException(
            message="Master Key not set for Proxy. Please set Master Key to use Admin UI. Set `LLM_MASTER_KEY` in .env or set general_settings:master_key in config.yaml.  https://docs.hanzo.ai/docs/proxy/virtual_keys. If set, use `--detailed_debug` to debug issue.",
            type=ProxyErrorTypes.auth_error,
            param="master_key",
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    form = await request.form()
    username = str(form.get("username"))
    password = str(form.get("password"))
    ui_username = os.getenv("UI_USERNAME", "admin")
    ui_password = os.getenv("UI_PASSWORD", None)
    if ui_password is None:
        ui_password = str(master_key) if master_key is not None else None
    if ui_password is None:
        raise ProxyException(
            message="set Proxy master key to use UI. https://docs.hanzo.ai/docs/proxy/virtual_keys. If set, use `--detailed_debug` to debug issue.",
            type=ProxyErrorTypes.auth_error,
            param="UI_PASSWORD",
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # check if we can find the `username` in the db. on the ui, users can enter username=their email
    _user_row = None
    user_role: Optional[
        Literal[
            LLMUserRoles.PROXY_ADMIN,
            LLMUserRoles.PROXY_ADMIN_VIEW_ONLY,
            LLMUserRoles.INTERNAL_USER,
            LLMUserRoles.INTERNAL_USER_VIEW_ONLY,
        ]
    ] = None
    if prisma_client is not None:
        _user_row = await prisma_client.db.llm_usertable.find_first(
            where={"user_email": {"equals": username}}
        )
    disabled_non_admin_personal_key_creation = (
        get_disabled_non_admin_personal_key_creation()
    )
    """
    To login to Admin UI, we support the following
    - Login with UI_USERNAME and UI_PASSWORD
    - Login with Invite Link `user_email` and `password` combination
    """
    if secrets.compare_digest(username, ui_username) and secrets.compare_digest(
        password, ui_password
    ):
        # Non SSO -> If user is using UI_USERNAME and UI_PASSWORD they are Proxy admin
        user_role = LLMUserRoles.PROXY_ADMIN
        user_id = llm_proxy_admin_name

        # we want the key created to have PROXY_ADMIN_PERMISSIONS
        key_user_id = llm_proxy_admin_name
        if (
            os.getenv("PROXY_ADMIN_ID", None) is not None
            and os.environ["PROXY_ADMIN_ID"] == user_id
        ) or user_id == llm_proxy_admin_name:
            # checks if user is admin
            key_user_id = os.getenv("PROXY_ADMIN_ID", llm_proxy_admin_name)

        # Admin is Authe'd in - generate key for the UI to access Proxy

        # ensure this user is set as the proxy admin, in this route there is no sso, we can assume this user is only the admin
        await user_update(
            data=UpdateUserRequest(
                user_id=key_user_id,
                user_role=user_role,
            )
        )
        if os.getenv("DATABASE_URL") is not None:
            response = await generate_key_helper_fn(
                request_type="key",
                **{
                    "user_role": LLMUserRoles.PROXY_ADMIN,
                    "duration": "24hr",
                    "key_max_budget": llm.max_ui_session_budget,
                    "models": [],
                    "aliases": {},
                    "config": {},
                    "spend": 0,
                    "user_id": key_user_id,
                    "team_id": "llm-dashboard",
                },  # type: ignore
            )
        else:
            raise ProxyException(
                message="No Database connected. Set DATABASE_URL in .env. If set, use `--detailed_debug` to debug issue.",
                type=ProxyErrorTypes.auth_error,
                param="DATABASE_URL",
                code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        key = response["token"]  # type: ignore
        llm_dashboard_ui = os.getenv("PROXY_BASE_URL", "")
        if llm_dashboard_ui.endswith("/"):
            llm_dashboard_ui += "ui/"
        else:
            llm_dashboard_ui += "/ui/"
        import jwt

        jwt_token = jwt.encode(  # type: ignore
            {
                "user_id": user_id,
                "key": key,
                "user_email": None,
                "user_role": user_role,  # this is the path without sso - we can assume only admins will use this
                "login_method": "username_password",
                "premium_user": premium_user,
                "auth_header_name": general_settings.get(
                    "llm_key_header_name", "Authorization"
                ),
                "disabled_non_admin_personal_key_creation": disabled_non_admin_personal_key_creation,
            },
            master_key,
            algorithm="HS256",
        )
        llm_dashboard_ui += "?userID=" + user_id
        redirect_response = RedirectResponse(url=llm_dashboard_ui, status_code=303)
        redirect_response.set_cookie(key="token", value=jwt_token)
        return redirect_response
    elif _user_row is not None:
        """
        When sharing invite links

        -> if the user has no role in the DB assume they are only a viewer
        """
        user_id = getattr(_user_row, "user_id", "unknown")
        user_role = getattr(
            _user_row, "user_role", LLMUserRoles.INTERNAL_USER_VIEW_ONLY
        )
        user_email = getattr(_user_row, "user_email", "unknown")
        _password = getattr(_user_row, "password", "unknown")

        # check if password == _user_row.password
        hash_password = hash_token(token=password)
        if secrets.compare_digest(password, _password) or secrets.compare_digest(
            hash_password, _password
        ):
            if os.getenv("DATABASE_URL") is not None:
                response = await generate_key_helper_fn(
                    request_type="key",
                    **{  # type: ignore
                        "user_role": user_role,
                        "duration": "24hr",
                        "key_max_budget": llm.max_ui_session_budget,
                        "models": [],
                        "aliases": {},
                        "config": {},
                        "spend": 0,
                        "user_id": user_id,
                        "team_id": "llm-dashboard",
                    },
                )
            else:
                raise ProxyException(
                    message="No Database connected. Set DATABASE_URL in .env. If set, use `--detailed_debug` to debug issue.",
                    type=ProxyErrorTypes.auth_error,
                    param="DATABASE_URL",
                    code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
            key = response["token"]  # type: ignore
            llm_dashboard_ui = os.getenv("PROXY_BASE_URL", "")
            if llm_dashboard_ui.endswith("/"):
                llm_dashboard_ui += "ui/"
            else:
                llm_dashboard_ui += "/ui/"
            import jwt

            jwt_token = jwt.encode(  # type: ignore
                {
                    "user_id": user_id,
                    "key": key,
                    "user_email": user_email,
                    "user_role": user_role,
                    "login_method": "username_password",
                    "premium_user": premium_user,
                    "auth_header_name": general_settings.get(
                        "llm_key_header_name", "Authorization"
                    ),
                    "disabled_non_admin_personal_key_creation": disabled_non_admin_personal_key_creation,
                },
                master_key,
                algorithm="HS256",
            )
            llm_dashboard_ui += "?userID=" + user_id
            redirect_response = RedirectResponse(
                url=llm_dashboard_ui, status_code=303
            )
            redirect_response.set_cookie(key="token", value=jwt_token)
            return redirect_response
        else:
            raise ProxyException(
                message=f"Invalid credentials used to access UI.\nNot valid credentials for {username}",
                type=ProxyErrorTypes.auth_error,
                param="invalid_credentials",
                code=status.HTTP_401_UNAUTHORIZED,
            )
    else:
        raise ProxyException(
            message="Invalid credentials used to access UI.\nCheck 'UI_USERNAME', 'UI_PASSWORD' in .env file",
            type=ProxyErrorTypes.auth_error,
            param="invalid_credentials",
            code=status.HTTP_401_UNAUTHORIZED,
        )


@app.get("/onboarding/get_token", include_in_schema=False)
async def onboarding(invite_link: str):
    """
    - Get the invite link
    - Validate it's still 'valid'
    - Invalidate the link (prevents abuse)
    - Get user from db
    - Pass in user_email if set
    """
    global prisma_client, master_key, general_settings
    if master_key is None:
        raise ProxyException(
            message="Master Key not set for Proxy. Please set Master Key to use Admin UI. Set `LLM_MASTER_KEY` in .env or set general_settings:master_key in config.yaml.  https://docs.hanzo.ai/docs/proxy/virtual_keys. If set, use `--detailed_debug` to debug issue.",
            type=ProxyErrorTypes.auth_error,
            param="master_key",
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    ### VALIDATE INVITE LINK ###
    if prisma_client is None:
        raise HTTPException(
            status_code=500,
            detail={"error": CommonProxyErrors.db_not_connected_error.value},
        )

    invite_obj = await prisma_client.db.llm_invitationlink.find_unique(
        where={"id": invite_link}
    )
    if invite_obj is None:
        raise HTTPException(
            status_code=401, detail={"error": "Invitation link does not exist in db."}
        )
    #### CHECK IF EXPIRED
    # Extract the date part from both datetime objects
    utc_now_date = llm.utils.get_utc_datetime().date()
    expires_at_date = invite_obj.expires_at.date()
    if expires_at_date < utc_now_date:
        raise HTTPException(
            status_code=401, detail={"error": "Invitation link has expired."}
        )

    #### INVALIDATE LINK
    current_time = llm.utils.get_utc_datetime()

    _ = await prisma_client.db.llm_invitationlink.update(
        where={"id": invite_link},
        data={
            "accepted_at": current_time,
            "updated_at": current_time,
            "is_accepted": True,
            "updated_by": invite_obj.user_id,  # type: ignore
        },
    )

    ### GET USER OBJECT ###
    user_obj = await prisma_client.db.llm_usertable.find_unique(
        where={"user_id": invite_obj.user_id}
    )

    if user_obj is None:
        raise HTTPException(
            status_code=401, detail={"error": "User does not exist in db."}
        )

    user_email = user_obj.user_email

    response = await generate_key_helper_fn(
        request_type="key",
        **{
            "user_role": user_obj.user_role,
            "duration": "24hr",
            "key_max_budget": llm.max_ui_session_budget,
            "models": [],
            "aliases": {},
            "config": {},
            "spend": 0,
            "user_id": user_obj.user_id,
            "team_id": "llm-dashboard",
        },  # type: ignore
    )
    key = response["token"]  # type: ignore

    llm_dashboard_ui = os.getenv("PROXY_BASE_URL", "")
    if llm_dashboard_ui.endswith("/"):
        llm_dashboard_ui += "ui/onboarding"
    else:
        llm_dashboard_ui += "/ui/onboarding"
    import jwt

    disabled_non_admin_personal_key_creation = (
        get_disabled_non_admin_personal_key_creation()
    )

    jwt_token = jwt.encode(  # type: ignore
        {
            "user_id": user_obj.user_id,
            "key": key,
            "user_email": user_obj.user_email,
            "user_role": user_obj.user_role,
            "login_method": "username_password",
            "premium_user": premium_user,
            "auth_header_name": general_settings.get(
                "llm_key_header_name", "Authorization"
            ),
            "disabled_non_admin_personal_key_creation": disabled_non_admin_personal_key_creation,
        },
        master_key,
        algorithm="HS256",
    )

    llm_dashboard_ui += "?token={}&user_email={}".format(jwt_token, user_email)
    return {
        "login_url": llm_dashboard_ui,
        "token": jwt_token,
        "user_email": user_email,
    }


@app.post("/onboarding/claim_token", include_in_schema=False)
async def claim_onboarding_link(data: InvitationClaim):
    """
    Special route. Allows UI link share user to update their password.

    - Get the invite link
    - Validate it's still 'valid'
    - Check if user within initial session (prevents abuse)
    - Get user from db
    - Update user password

    This route can only update user password.
    """
    global prisma_client
    ### VALIDATE INVITE LINK ###
    if prisma_client is None:
        raise HTTPException(
            status_code=500,
            detail={"error": CommonProxyErrors.db_not_connected_error.value},
        )

    invite_obj = await prisma_client.db.llm_invitationlink.find_unique(
        where={"id": data.invitation_link}
    )
    if invite_obj is None:
        raise HTTPException(
            status_code=401, detail={"error": "Invitation link does not exist in db."}
        )
    #### CHECK IF EXPIRED
    # Extract the date part from both datetime objects
    utc_now_date = llm.utils.get_utc_datetime().date()
    expires_at_date = invite_obj.expires_at.date()
    if expires_at_date < utc_now_date:
        raise HTTPException(
            status_code=401, detail={"error": "Invitation link has expired."}
        )

    #### CHECK IF CLAIMED
    ##### if claimed - accept
    ##### if unclaimed - reject

    if invite_obj.is_accepted is True:
        # this is a valid invite that was accepted
        pass
    else:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "The invitation link was never validated. Please file an issue, if this is not intended - https://github.com/hanzoai/llm/issues."
            },
        )

    #### CHECK IF VALID USER ID
    if invite_obj.user_id != data.user_id:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "Invalid invitation link. The user id submitted does not match the user id this link is attached to. Got={}, Expected={}".format(
                    data.user_id, invite_obj.user_id
                )
            },
        )
    ### UPDATE USER OBJECT ###
    hash_password = hash_token(token=data.password)
    user_obj = await prisma_client.db.llm_usertable.update(
        where={"user_id": invite_obj.user_id}, data={"password": hash_password}
    )

    if user_obj is None:
        raise HTTPException(
            status_code=401, detail={"error": "User does not exist in db."}
        )

    return user_obj


@app.get("/get_image", include_in_schema=False)
def get_image():
    """Get logo to show on admin UI"""

    # Use the Hanzo logo from the proxy directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    hanzo_logo = os.path.join(current_dir, "hanzo-logo.png")
    default_logo = os.path.join(current_dir, "logo.jpg")

    logo_path = os.getenv("UI_LOGO_PATH", hanzo_logo)
    verbose_proxy_logger.debug("Reading logo from path: %s", logo_path)

    # Check if the logo path is an HTTP/HTTPS URL
    if logo_path.startswith(("http://", "https://")):
        # Download the image and cache it
        client = HTTPHandler()
        response = client.get(logo_path)
        if response.status_code == 200:
            # Save the image to a local file
            cache_path = os.path.join(current_dir, "cached_logo.jpg")
            with open(cache_path, "wb") as f:
                f.write(response.content)

            # Return the cached image as a FileResponse
            return FileResponse(cache_path, media_type="image/jpeg")
        else:
            # Handle the case when the image cannot be downloaded
            return FileResponse(default_logo, media_type="image/jpeg")
    else:
        # Return the local image file if the logo path is not an HTTP/HTTPS URL
        if logo_path.endswith(".png"):
            return FileResponse(logo_path, media_type="image/png")
        else:
            return FileResponse(logo_path, media_type="image/jpeg")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Serve the favicon for the website"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    hanzo_logo = os.path.join(current_dir, "hanzo-logo.png")
    
    return FileResponse(hanzo_logo, media_type="image/png")


@app.get("/models", tags=["Public API"])
async def get_models_endpoint(request: Request, accept: Optional[str] = Header(None)):
    """
    Public endpoint for models that returns HTML or JSON based on the Accept header.
    """
    # Check if the client accepts JSON
    if accept and "application/json" in accept or request.headers.get("content-type") == "application/json":
        return await get_models_json()
    
    # Otherwise, return HTML
    return await get_models_html()


@app.get("/mcps", tags=["Public API"])
async def get_mcps_endpoint(request: Request, accept: Optional[str] = Header(None)):
    """
    Public endpoint for MCP servers that returns HTML or JSON based on the Accept header.
    """
    # Check if the client accepts JSON
    if accept and "application/json" in accept or request.headers.get("content-type") == "application/json":
        return await get_mcps_json()
    
    # Otherwise, return HTML
    return await get_mcps_html()


@app.get("/api/models", response_class=JSONResponse, tags=["Public API"])
async def get_models_json():
    """
    Public JSON API endpoint to get all available models with pricing and capabilities.
    This endpoint is accessible without authentication.
    """
    try:
        # Load model information from the pricing file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(os.path.dirname(current_dir))
        model_file_path = os.path.join(parent_dir, "model_prices_and_context_window.json")
        
        with open(model_file_path, 'r') as f:
            model_data = json.load(f)
        
        # Filter out the sample spec entry
        if "sample_spec" in model_data:
            del model_data["sample_spec"]
        
        return model_data
    except Exception as e:
        verbose_proxy_logger.error(f"Error loading model data: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error loading model data: {str(e)}"
        )


@app.get("/api/mcps", response_class=JSONResponse, tags=["Public API"])
async def get_mcps_json():
    """
    Public JSON API endpoint to get all available MCP servers.
    This endpoint is accessible without authentication.
    """
    try:
        # Load MCP server information
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(os.path.dirname(current_dir))
        mcp_file_path = os.path.join(parent_dir, "../mcp_servers.json")
        
        with open(mcp_file_path, 'r') as f:
            mcp_data = json.load(f)
        
        return mcp_data
    except Exception as e:
        verbose_proxy_logger.error(f"Error loading MCP server data: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error loading MCP server data: {str(e)}"
        )


@app.get("/models.html", response_class=HTMLResponse)
async def get_models_html():
    """Public endpoint to display all available models with pricing and capabilities in HTML format"""
    try:
        # Load model information from the pricing file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(os.path.dirname(current_dir))
        model_file_path = os.path.join(parent_dir, "model_prices_and_context_window.json")
        
        with open(model_file_path, 'r') as f:
            model_data = json.load(f)
        
        # Filter out the sample spec entry
        if "sample_spec" in model_data:
            del model_data["sample_spec"]
        
        # Create HTML table of models
        html_content = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Hanzo AI - Available Models</title>
            <link rel="icon" href="/favicon.ico" type="image/x-icon">
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                    line-height: 1.6;
                    color: #e4e4e4;
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #000;
                    color: #e4e4e4;
                }
                h1 {
                    color: #ffffff;
                    border-bottom: 1px solid #444;
                    padding-bottom: 10px;
                    margin-top: 0;
                }
                .logo {
                    max-width: 140px;
                    margin-right: 20px;
                    vertical-align: middle;
                }
                .header {
                    display: flex;
                    align-items: center;
                    margin-bottom: 30px;
                }
                .header-content {
                    flex-grow: 1;
                }
                table {
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 20px;
                    font-size: 14px;
                }
                th, td {
                    padding: 12px 15px;
                    text-align: left;
                    border-bottom: 1px solid #444;
                }
                th {
                    background-color: #1e1e1e;
                    color: #ffffff;
                    position: sticky;
                    top: 0;
                }
                tr:hover {
                    background-color: #2a2a2a;
                }
                .filter-container {
                    margin-bottom: 20px;
                    display: flex;
                    gap: 15px;
                    flex-wrap: wrap;
                }
                input, select {
                    padding: 8px 12px;
                    border: 1px solid #444;
                    border-radius: 4px;
                    font-size: 14px;
                    background-color: #2a2a2a;
                    color: #e4e4e4;
                }
                input:focus, select:focus {
                    outline: none;
                    border-color: #0070f3;
                }
                .badge {
                    display: inline-block;
                    padding: 2px 8px;
                    font-size: 12px;
                    border-radius: 12px;
                    margin-right: 5px;
                    background-color: #0070f3;
                    color: white;
                }
                .feature-yes {
                    color: #10b981;
                }
                .feature-no {
                    color: #888;
                }
                nav {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 20px;
                    background-color: #000;
                    padding: 10px 20px;
                    border-radius: 4px;
                    border-bottom: 1px solid #222;
                }
                nav a {
                    color: #e4e4e4;
                    text-decoration: none;
                    margin-left: 20px;
                    font-weight: 500;
                }
                nav a:hover {
                    color: #0070f3;
                }
                .search-input {
                    flex-grow: 1;
                    max-width: 300px;
                }
                .nav-logo {
                    height: 32px;
                }
            </style>
        </head>
        <body>
            <nav>
                <div>
                    <img src="/get_image" alt="Hanzo AI Logo" class="nav-logo">
                </div>
                <div>
                    <a href="/docs">API</a>
                    <a href="/models.html">Models</a>
                    <a href="/mcps.html">MCP Servers</a>
                    <a href="/ui/tool-hub">Tool Hub</a>
                    <a href="https://github.com/hanzoai/llm" target="_blank">GitHub</a>
                </div>
            </nav>
            
            <div class="header">
                <div class="header-content">
                    <h1>Available Models</h1>
                    <p>Browse all models available through Hanzo AI. API access via <a href="/models">/models</a> or <a href="/api/models">/api/models</a> (JSON).</p>
                </div>
            </div>
            
            <div class="filter-container">
                <input type="text" id="searchInput" placeholder="Search models..." class="search-input">
                <select id="providerFilter">
                    <option value="">All Providers</option>
                </select>
                <select id="modeFilter">
                    <option value="">All Types</option>
                </select>
            </div>
            
            <table id="modelsTable">
                <thead>
                    <tr>
                        <th>Model</th>
                        <th>Provider</th>
                        <th>Type</th>
                        <th>Context Window</th>
                        <th>Input Price</th>
                        <th>Output Price</th>
                        <th>Features</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        providers = set()
        modes = set()
        
        # Add rows for each model
        for model_name, model_info in sorted(model_data.items()):
            provider = model_info.get("llm_provider", "Unknown")
            mode = model_info.get("mode", "Unknown")
            
            providers.add(provider)
            modes.add(mode)
            
            max_tokens = model_info.get("max_tokens", "N/A")
            input_cost = model_info.get("input_cost_per_token", 0)
            output_cost = model_info.get("output_cost_per_token", 0)
            
            # Format costs properly
            input_price = f"${input_cost:.6f}" if input_cost > 0 else "Free"
            output_price = f"${output_cost:.6f}" if output_cost > 0 else "Free"
            
            # Collect features
            features = []
            
            if model_info.get("supports_function_calling", False):
                features.append("Function Calling")
            
            if model_info.get("supports_vision", False):
                features.append("Vision")
                
            if model_info.get("supports_audio_input", False):
                features.append("Audio Input")
                
            if model_info.get("supports_audio_output", False):
                features.append("Audio Output")
                
            if model_info.get("supports_system_messages", False):
                features.append("System Messages")
                
            if model_info.get("supports_web_search", False):
                features.append("Web Search")
            
            features_html = ""
            for feature in features:
                features_html += f'<span class="badge">{feature}</span>'
            
            html_content += f"""
                <tr data-provider="{provider}" data-mode="{mode}">
                    <td>{model_name}</td>
                    <td>{provider}</td>
                    <td>{mode}</td>
                    <td>{max_tokens}</td>
                    <td>{input_price}</td>
                    <td>{output_price}</td>
                    <td>{features_html}</td>
                </tr>
            """
        
        html_content += """
                </tbody>
            </table>
            
            <script>
                // Populate filter options
                const providerFilter = document.getElementById('providerFilter');
                const modeFilter = document.getElementById('modeFilter');
                const searchInput = document.getElementById('searchInput');
                
                // Populate provider options
        """
        
        # Add provider options
        html_content += "const providers = ["
        for provider in sorted(providers):
            html_content += f'"{provider}", '
        html_content = html_content.rstrip(", ")
        html_content += "];\n"
        
        # Add mode options
        html_content += "const modes = ["
        for mode in sorted(modes):
            html_content += f'"{mode}", '
        html_content = html_content.rstrip(", ")
        html_content += "];\n"
        
        html_content += """
                providers.forEach(provider => {
                    const option = document.createElement('option');
                    option.value = provider;
                    option.textContent = provider;
                    providerFilter.appendChild(option);
                });
                
                modes.forEach(mode => {
                    const option = document.createElement('option');
                    option.value = mode;
                    option.textContent = mode;
                    modeFilter.appendChild(option);
                });
                
                // Filter function
                function filterTable() {
                    const searchTerm = searchInput.value.toLowerCase();
                    const providerValue = providerFilter.value;
                    const modeValue = modeFilter.value;
                    
                    document.querySelectorAll('#modelsTable tbody tr').forEach(row => {
                        const modelName = row.children[0].textContent.toLowerCase();
                        const provider = row.dataset.provider;
                        const mode = row.dataset.mode;
                        
                        const matchesSearch = searchTerm === '' || modelName.includes(searchTerm);
                        const matchesProvider = providerValue === '' || provider === providerValue;
                        const matchesMode = modeValue === '' || mode === modeValue;
                        
                        row.style.display = (matchesSearch && matchesProvider && matchesMode) ? '' : 'none';
                    });
                }
                
                // Add event listeners
                searchInput.addEventListener('input', filterTable);
                providerFilter.addEventListener('change', filterTable);
                modeFilter.addEventListener('change', filterTable);
            </script>
        </body>
        </html>
        """
        
        return html_content
    except Exception as e:
        return f"""
        <html>
            <body style="font-family: sans-serif; background-color: #121212; color: #e4e4e4; padding: 20px;">
                <h1>Error loading model data</h1>
                <p>{str(e)}</p>
            </body>
        </html>
        """


@app.get("/mcps.html", response_class=HTMLResponse)
async def get_mcps_html():
    """Public endpoint to display all available MCP servers in HTML format"""
    try:
        # Load MCP server information
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(os.path.dirname(current_dir))
        mcp_file_path = os.path.join(parent_dir, "../mcp_servers.json")
        
        with open(mcp_file_path, 'r') as f:
            mcp_data = json.load(f)
        
        # Create HTML table of MCP servers
        html_content = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Hanzo AI - MCP Servers</title>
            <link rel="icon" href="/favicon.ico" type="image/x-icon">
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                    line-height: 1.6;
                    color: #e4e4e4;
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #000;
                    color: #e4e4e4;
                }
                h1 {
                    color: #ffffff;
                    border-bottom: 1px solid #444;
                    padding-bottom: 10px;
                    margin-top: 0;
                }
                .logo {
                    max-width: 140px;
                    margin-right: 20px;
                    vertical-align: middle;
                }
                .header {
                    display: flex;
                    align-items: center;
                    margin-bottom: 30px;
                }
                .header-content {
                    flex-grow: 1;
                }
                table {
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 20px;
                    font-size: 14px;
                }
                th, td {
                    padding: 12px 15px;
                    text-align: left;
                    border-bottom: 1px solid #444;
                }
                th {
                    background-color: #1e1e1e;
                    color: #ffffff;
                    position: sticky;
                    top: 0;
                }
                tr:hover {
                    background-color: #2a2a2a;
                }
                .filter-container {
                    margin-bottom: 20px;
                }
                input {
                    padding: 8px 12px;
                    border: 1px solid #444;
                    border-radius: 4px;
                    font-size: 14px;
                    width: 300px;
                    background-color: #2a2a2a;
                    color: #e4e4e4;
                }
                input:focus {
                    outline: none;
                    border-color: #0070f3;
                }
                pre {
                    background-color: #1e1e1e;
                    padding: 10px;
                    border-radius: 4px;
                    overflow: auto;
                    font-size: 13px;
                }
                code {
                    font-family: 'Menlo', 'Monaco', 'Courier New', monospace;
                }
                .commands {
                    background-color: #1e1e1e;
                    padding: 15px;
                    border-radius: 4px;
                    margin-top: 10px;
                }
                .command-title {
                    font-weight: bold;
                    margin-bottom: 5px;
                }
                .status-badge {
                    display: inline-block;
                    padding: 2px 8px;
                    font-size: 12px;
                    border-radius: 12px;
                    margin-left: 8px;
                }
                .status-badge.enabled {
                    background-color: #10b981;
                    color: white;
                }
                .status-badge.disabled {
                    background-color: #ef4444;
                    color: white;
                }
                tr.disabled {
                    opacity: 0.7;
                }
                nav {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 20px;
                    background-color: #000;
                    padding: 10px 20px;
                    border-radius: 4px;
                    border-bottom: 1px solid #222;
                }
                nav a {
                    color: #e4e4e4;
                    text-decoration: none;
                    margin-left: 20px;
                    font-weight: 500;
                }
                nav a:hover {
                    color: #0070f3;
                }
                .nav-logo {
                    height: 32px;
                }
            </style>
        </head>
        <body>
            <nav>
                <div>
                    <img src="/get_image" alt="Hanzo AI Logo" class="nav-logo">
                </div>
                <div>
                    <a href="/docs">API</a>
                    <a href="/models.html">Models</a>
                    <a href="/mcps.html">MCP Servers</a>
                    <a href="/ui/tool-hub">Tool Hub</a>
                    <a href="https://github.com/hanzoai/llm" target="_blank">GitHub</a>
                </div>
            </nav>
            
            <div class="header">
                <div class="header-content">
                    <h1>Model Calling Protocol (MCP) Servers</h1>
                    <p>Browse available MCP servers that can be used with Hanzo AI. API access via <a href="/mcps">/mcps</a> or <a href="/api/mcps">/api/mcps</a> (JSON).</p>
                </div>
            </div>
            
            <div class="filter-container">
                <input type="text" id="searchInput" placeholder="Search MCP servers...">
            </div>
            
            <table id="mcpTable">
                <thead>
                    <tr>
                        <th>Server Name</th>
                        <th>Launch Command</th>
                        <th>Required Environment Variables</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        # Add rows for each MCP server
        for server_name, server_info in sorted(mcp_data.items()):
            command = server_info.get("command", "")
            args = " ".join(server_info.get("args", []))
            launch_command = f"{command} {args}"
            
            # Format environment variables
            env_vars = server_info.get("env", {})
            env_vars_html = ""
            for var_name, var_value in env_vars.items():
                env_vars_html += f"{var_name}"
                if var_value != "YOUR_API_KEY_HERE":
                    env_vars_html += f" (default: {var_value})"
                env_vars_html += "<br>"
            
            # Check if server is enabled
            is_enabled = server_info.get("enabled", True)
            status_class = "enabled" if is_enabled else "disabled"
            status_text = "Enabled" if is_enabled else "Disabled"
            
            html_content += f"""
                <tr class="{status_class}">
                    <td>{server_name} <span class="status-badge {status_class}">{status_text}</span></td>
                    <td><code>{launch_command}</code></td>
                    <td>{env_vars_html}</td>
                </tr>
            """
        
        html_content += """
                </tbody>
            </table>
            
            <div style="margin-top: 30px;">
                <h2>How to Use MCP Servers</h2>
                
                <div class="commands">
                    <div class="command-title">1. Set up your environment:</div>
                    <pre><code>export HANZO_API_KEY=your_api_key_here
# Set any required environment variables for the MCP server
export BRAVE_API_KEY=your_brave_api_key</code></pre>
                </div>
                
                <div class="commands">
                    <div class="command-title">2. Run an MCP server:</div>
                    <pre><code>docker run -i --rm -e BRAVE_API_KEY mcp/brave-search</code></pre>
                </div>
                
                <div class="commands">
                    <div class="command-title">3. Use the MCP server in your app:</div>
                    <pre><code>import llm
from llm.experimental_mcp_client import MCPClient

client = MCPClient(
    api_key="your_hanzo_api_key",
    base_url="https://api.hanzo.ai"
)

result = client.run_tool(
    name="brave-search",
    params={"query": "latest AI developments"}
)
print(result)</code></pre>
                </div>
                
                <h2 style="margin-top: 30px;">Using with OpenAI Agents SDK</h2>
                <p>MCP servers can be used with the OpenAI Agents SDK:</p>
                
                <div class="commands">
                    <pre><code>from openai import OpenAI
from openai.types.beta.assistant import Tool
from openai.types.beta.assistant_create_params import ToolResources

# Initialize the OpenAI client
client = OpenAI(api_key="your_api_key")

# Create an agent with the MCP server tools
agent = client.beta.assistants.create(
    name="MCP Assistant",
    model="gpt-4-turbo",
    instructions="Use the tools to help the user.",
    tools=[
        {
            "type": "function",
            "function": {
                "name": "brave_search",
                "description": "Search the web using Brave Search",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query"
                        }
                    },
                    "required": ["query"]
                }
            }
        }
    ]
)

# Run the agent
thread = client.beta.threads.create()
message = client.beta.threads.messages.create(
    thread_id=thread.id,
    role="user",
    content="What are the latest AI developments?"
)

run = client.beta.threads.runs.create(
    thread_id=thread.id,
    assistant_id=agent.id
)

# Process the run with MCP server tools
# This would require integration with your MCP server tools
</code></pre>
                </div>
                
                <h2 style="margin-top: 30px;">Managing MCP Servers</h2>
                <p>Administrators can enable/disable MCP servers and track usage through the admin interface:</p>
                
                <div class="commands">
                    <div class="command-title">Admin API endpoints:</div>
                    <ul style="margin-top: 10px; line-height: 1.6;">
                        <li><code>GET /mcp/admin/servers</code> - List all MCP servers</li>
                        <li><code>GET /mcp/admin/servers/{server_name}</code> - Get server configuration</li>
                        <li><code>PATCH /mcp/admin/servers/{server_name}</code> - Update server configuration</li>
                        <li><code>GET /mcp/admin/usage</code> - Get usage statistics</li>
                        <li><code>GET /mcp/admin/usage/logs</code> - Get detailed usage logs</li>
                    </ul>
                </div>
                
                <div class="commands">
                    <div class="command-title">Managing servers with API:</div>
                    <pre><code>import requests

# Enable/disable an MCP server
response = requests.patch(
    "https://api.hanzo.ai/mcp/admin/servers/brave_search",
    headers={"Authorization": f"Bearer {HANZO_ADMIN_KEY}"},
    json={"enabled": True}
)

# View usage statistics
response = requests.get(
    "https://api.hanzo.ai/mcp/admin/usage",
    headers={"Authorization": f"Bearer {HANZO_ADMIN_KEY}"},
)
</code></pre>
                </div>
            </div>
            
            <script>
                // Search functionality
                const searchInput = document.getElementById('searchInput');
                
                searchInput.addEventListener('input', function() {
                    const searchTerm = this.value.toLowerCase();
                    
                    document.querySelectorAll('#mcpTable tbody tr').forEach(row => {
                        const serverName = row.children[0].textContent.toLowerCase();
                        
                        if (serverName.includes(searchTerm)) {
                            row.style.display = '';
                        } else {
                            row.style.display = 'none';
                        }
                    });
                });
            </script>
        </body>
        </html>
        """
        
        return html_content
    except Exception as e:
        return f"""
        <html>
            <body style="font-family: sans-serif; background-color: #121212; color: #e4e4e4; padding: 20px;">
                <h1>Error loading MCP server data</h1>
                <p>{str(e)}</p>
            </body>
        </html>
        """


#### INVITATION MANAGEMENT ####


@router.post(
    "/invitation/new",
    tags=["Invite Links"],
    dependencies=[Depends(user_api_key_auth)],
    response_model=InvitationModel,
    include_in_schema=False,
)
async def new_invitation(
    data: InvitationNew, user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth)
):
    """
    Allow admin to create invite links, to onboard new users to Admin UI.

    ```
    curl -X POST 'http://localhost:4000/invitation/new' \
        -H 'Content-Type: application/json' \
        -d '{
            "user_id": "1234" // 👈 id of user in 'LLM_UserTable'
        }'
    ```
    """
    global prisma_client

    if prisma_client is None:
        raise HTTPException(
            status_code=400,
            detail={"error": CommonProxyErrors.db_not_connected_error.value},
        )

    if user_api_key_dict.user_role != LLMUserRoles.PROXY_ADMIN:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "{}, your role={}".format(
                    CommonProxyErrors.not_allowed_access.value,
                    user_api_key_dict.user_role,
                )
            },
        )

    current_time = llm.utils.get_utc_datetime()
    expires_at = current_time + timedelta(days=7)

    try:
        response = await prisma_client.db.llm_invitationlink.create(
            data={
                "user_id": data.user_id,
                "created_at": current_time,
                "expires_at": expires_at,
                "created_by": user_api_key_dict.user_id or llm_proxy_admin_name,
                "updated_at": current_time,
                "updated_by": user_api_key_dict.user_id or llm_proxy_admin_name,
            }  # type: ignore
        )
        return response
    except Exception as e:
        if "Foreign key constraint failed on the field" in str(e):
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "User id does not exist in 'LLM_UserTable'. Fix this by creating user via `/user/new`."
                },
            )
        raise HTTPException(status_code=500, detail={"error": str(e)})


@router.get(
    "/invitation/info",
    tags=["Invite Links"],
    dependencies=[Depends(user_api_key_auth)],
    response_model=InvitationModel,
    include_in_schema=False,
)
async def invitation_info(
    invitation_id: str, user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth)
):
    """
    Allow admin to create invite links, to onboard new users to Admin UI.

    ```
    curl -X POST 'http://localhost:4000/invitation/new' \
        -H 'Content-Type: application/json' \
        -d '{
            "user_id": "1234" // 👈 id of user in 'LLM_UserTable'
        }'
    ```
    """
    global prisma_client

    if prisma_client is None:
        raise HTTPException(
            status_code=400,
            detail={"error": CommonProxyErrors.db_not_connected_error.value},
        )

    if user_api_key_dict.user_role != LLMUserRoles.PROXY_ADMIN:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "{}, your role={}".format(
                    CommonProxyErrors.not_allowed_access.value,
                    user_api_key_dict.user_role,
                )
            },
        )

    response = await prisma_client.db.llm_invitationlink.find_unique(
        where={"id": invitation_id}
    )

    if response is None:
        raise HTTPException(
            status_code=400,
            detail={"error": "Invitation id does not exist in the database."},
        )
    return response


@router.post(
    "/invitation/update",
    tags=["Invite Links"],
    dependencies=[Depends(user_api_key_auth)],
    response_model=InvitationModel,
    include_in_schema=False,
)
async def invitation_update(
    data: InvitationUpdate,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Update when invitation is accepted

    ```
    curl -X POST 'http://localhost:4000/invitation/update' \
        -H 'Content-Type: application/json' \
        -d '{
            "invitation_id": "1234" // 👈 id of invitation in 'LLM_InvitationTable'
            "is_accepted": True // when invitation is accepted
        }'
    ```
    """
    global prisma_client

    if prisma_client is None:
        raise HTTPException(
            status_code=400,
            detail={"error": CommonProxyErrors.db_not_connected_error.value},
        )

    if user_api_key_dict.user_id is None:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Unable to identify user id. Received={}".format(
                    user_api_key_dict.user_id
                )
            },
        )

    current_time = llm.utils.get_utc_datetime()
    response = await prisma_client.db.llm_invitationlink.update(
        where={"id": data.invitation_id},
        data={
            "id": data.invitation_id,
            "is_accepted": data.is_accepted,
            "accepted_at": current_time,
            "updated_at": current_time,
            "updated_by": user_api_key_dict.user_id,  # type: ignore
        },
    )

    if response is None:
        raise HTTPException(
            status_code=400,
            detail={"error": "Invitation id does not exist in the database."},
        )
    return response


@router.post(
    "/invitation/delete",
    tags=["Invite Links"],
    dependencies=[Depends(user_api_key_auth)],
    response_model=InvitationModel,
    include_in_schema=False,
)
async def invitation_delete(
    data: InvitationDelete,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Delete invitation link

    ```
    curl -X POST 'http://localhost:4000/invitation/delete' \
        -H 'Content-Type: application/json' \
        -d '{
            "invitation_id": "1234" // 👈 id of invitation in 'LLM_InvitationTable'
        }'
    ```
    """
    global prisma_client

    if prisma_client is None:
        raise HTTPException(
            status_code=400,
            detail={"error": CommonProxyErrors.db_not_connected_error.value},
        )

    if user_api_key_dict.user_role != LLMUserRoles.PROXY_ADMIN:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "{}, your role={}".format(
                    CommonProxyErrors.not_allowed_access.value,
                    user_api_key_dict.user_role,
                )
            },
        )

    response = await prisma_client.db.llm_invitationlink.delete(
        where={"id": data.invitation_id}
    )

    if response is None:
        raise HTTPException(
            status_code=400,
            detail={"error": "Invitation id does not exist in the database."},
        )
    return response


#### CONFIG MANAGEMENT ####
@router.post(
    "/config/update",
    tags=["config.yaml"],
    dependencies=[Depends(user_api_key_auth)],
    include_in_schema=False,
)
async def update_config(config_info: ConfigYAML):  # noqa: PLR0915
    """
    For Admin UI - allows admin to update config via UI

    Currently supports modifying General Settings + LLM settings
    """
    global llm_router, llm_model_list, general_settings, proxy_config, proxy_logging_obj, master_key, prisma_client
    try:
        import base64

        """
        - Update the ConfigTable DB
        - Run 'add_deployment'
        """
        if prisma_client is None:
            raise Exception("No DB Connected")

        if store_model_in_db is not True:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "Set `'STORE_MODEL_IN_DB='True'` in your env to enable this feature."
                },
            )

        updated_settings = config_info.json(exclude_none=True)
        updated_settings = prisma_client.jsonify_object(updated_settings)
        for k, v in updated_settings.items():
            if k == "router_settings":
                await prisma_client.db.llm_config.upsert(
                    where={"param_name": k},
                    data={
                        "create": {"param_name": k, "param_value": v},
                        "update": {"param_value": v},
                    },
                )

        ### OLD LOGIC [TODO] MOVE TO DB ###

        # Load existing config
        config = await proxy_config.get_config()
        verbose_proxy_logger.debug("Loaded config: %s", config)

        # update the general settings
        if config_info.general_settings is not None:
            config.setdefault("general_settings", {})
            updated_general_settings = config_info.general_settings.dict(
                exclude_none=True
            )

            _existing_settings = config["general_settings"]
            for k, v in updated_general_settings.items():
                # overwrite existing settings with updated values
                if k == "alert_to_webhook_url":
                    # check if slack is already enabled. if not, enable it
                    if "alerting" not in _existing_settings:
                        _existing_settings = {"alerting": ["slack"]}
                    elif isinstance(_existing_settings["alerting"], list):
                        if "slack" not in _existing_settings["alerting"]:
                            _existing_settings["alerting"].append("slack")
                _existing_settings[k] = v
            config["general_settings"] = _existing_settings

        if config_info.environment_variables is not None:
            config.setdefault("environment_variables", {})
            _updated_environment_variables = config_info.environment_variables

            # encrypt updated_environment_variables #
            for k, v in _updated_environment_variables.items():
                encrypted_value = encrypt_value_helper(value=v)
                _updated_environment_variables[k] = encrypted_value

            _existing_env_variables = config["environment_variables"]

            for k, v in _updated_environment_variables.items():
                # overwrite existing env variables with updated values
                _existing_env_variables[k] = _updated_environment_variables[k]

        # update the llm settings
        if config_info.llm_settings is not None:
            config.setdefault("llm_settings", {})
            updated_llm_settings = config_info.llm_settings
            config["llm_settings"] = {
                **updated_llm_settings,
                **config["llm_settings"],
            }

            # if llm.success_callback in updated_llm_settings and config["llm_settings"]
            if (
                "success_callback" in updated_llm_settings
                and "success_callback" in config["llm_settings"]
            ):

                # check both success callback are lists
                if isinstance(
                    config["llm_settings"]["success_callback"], list
                ) and isinstance(updated_llm_settings["success_callback"], list):
                    combined_success_callback = (
                        config["llm_settings"]["success_callback"]
                        + updated_llm_settings["success_callback"]
                    )
                    combined_success_callback = list(set(combined_success_callback))
                    config["llm_settings"][
                        "success_callback"
                    ] = combined_success_callback

        # Save the updated config
        await proxy_config.save_config(new_config=config)

        await proxy_config.add_deployment(
            prisma_client=prisma_client, proxy_logging_obj=proxy_logging_obj
        )

        return {"message": "Config updated successfully"}
    except Exception as e:
        verbose_proxy_logger.error(
            "llm.proxy.proxy_server.update_config(): Exception occured - {}".format(
                str(e)
            )
        )
        verbose_proxy_logger.debug(traceback.format_exc())
        if isinstance(e, HTTPException):
            raise ProxyException(
                message=getattr(e, "detail", f"Authentication Error({str(e)})"),
                type=ProxyErrorTypes.auth_error,
                param=getattr(e, "param", "None"),
                code=getattr(e, "status_code", status.HTTP_400_BAD_REQUEST),
            )
        elif isinstance(e, ProxyException):
            raise e
        raise ProxyException(
            message="Authentication Error, " + str(e),
            type=ProxyErrorTypes.auth_error,
            param=getattr(e, "param", "None"),
            code=status.HTTP_400_BAD_REQUEST,
        )


### CONFIG GENERAL SETTINGS
"""
- Update config settings
- Get config settings

Keep it more precise, to prevent overwrite other values unintentially
"""


@router.post(
    "/config/field/update",
    tags=["config.yaml"],
    dependencies=[Depends(user_api_key_auth)],
    include_in_schema=False,
)
async def update_config_general_settings(
    data: ConfigFieldUpdate,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Update a specific field in llm general settings
    """
    global prisma_client
    ## VALIDATION ##
    """
    - Check if prisma_client is None
    - Check if user allowed to call this endpoint (admin-only)
    - Check if param in general settings
    - Check if config value is valid type
    """

    if prisma_client is None:
        raise HTTPException(
            status_code=400,
            detail={"error": CommonProxyErrors.db_not_connected_error.value},
        )

    if user_api_key_dict.user_role != LLMUserRoles.PROXY_ADMIN:
        raise HTTPException(
            status_code=400,
            detail={"error": CommonProxyErrors.not_allowed_access.value},
        )

    if data.field_name not in ConfigGeneralSettings.model_fields:
        raise HTTPException(
            status_code=400,
            detail={"error": "Invalid field={} passed in.".format(data.field_name)},
        )

    try:
        ConfigGeneralSettings(**{data.field_name: data.field_value})
    except Exception:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Invalid type of field value={} passed in.".format(
                    type(data.field_value),
                )
            },
        )

    ## get general settings from db
    db_general_settings = await prisma_client.db.llm_config.find_first(
        where={"param_name": "general_settings"}
    )
    ### update value

    if db_general_settings is None or db_general_settings.param_value is None:
        general_settings = {}
    else:
        general_settings = dict(db_general_settings.param_value)

    ## update db

    general_settings[data.field_name] = data.field_value

    response = await prisma_client.db.llm_config.upsert(
        where={"param_name": "general_settings"},
        data={
            "create": {"param_name": "general_settings", "param_value": json.dumps(general_settings)},  # type: ignore
            "update": {"param_value": json.dumps(general_settings)},  # type: ignore
        },
    )

    return response


@router.get(
    "/config/field/info",
    tags=["config.yaml"],
    dependencies=[Depends(user_api_key_auth)],
    response_model=ConfigFieldInfo,
    include_in_schema=False,
)
async def get_config_general_settings(
    field_name: str,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    global prisma_client

    ## VALIDATION ##
    """
    - Check if prisma_client is None
    - Check if user allowed to call this endpoint (admin-only)
    - Check if param in general settings
    """
    if prisma_client is None:
        raise HTTPException(
            status_code=400,
            detail={"error": CommonProxyErrors.db_not_connected_error.value},
        )

    if user_api_key_dict.user_role != LLMUserRoles.PROXY_ADMIN:
        raise HTTPException(
            status_code=400,
            detail={"error": CommonProxyErrors.not_allowed_access.value},
        )

    if field_name not in ConfigGeneralSettings.model_fields:
        raise HTTPException(
            status_code=400,
            detail={"error": "Invalid field={} passed in.".format(field_name)},
        )

    ## get general settings from db
    db_general_settings = await prisma_client.db.llm_config.find_first(
        where={"param_name": "general_settings"}
    )
    ### pop the value

    if db_general_settings is None or db_general_settings.param_value is None:
        raise HTTPException(
            status_code=400,
            detail={"error": "Field name={} not in DB".format(field_name)},
        )
    else:
        general_settings = dict(db_general_settings.param_value)

        if field_name in general_settings:
            return ConfigFieldInfo(
                field_name=field_name, field_value=general_settings[field_name]
            )
        else:
            raise HTTPException(
                status_code=400,
                detail={"error": "Field name={} not in DB".format(field_name)},
            )


@router.get(
    "/config/list",
    tags=["config.yaml"],
    dependencies=[Depends(user_api_key_auth)],
    include_in_schema=False,
)
async def get_config_list(
    config_type: Literal["general_settings"],
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
) -> List[ConfigList]:
    """
    List the available fields + current values for a given type of setting (currently just 'general_settings'user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),)
    """
    global prisma_client, general_settings

    ## VALIDATION ##
    """
    - Check if prisma_client is None
    - Check if user allowed to call this endpoint (admin-only)
    - Check if param in general settings
    """
    if prisma_client is None:
        raise HTTPException(
            status_code=400,
            detail={"error": CommonProxyErrors.db_not_connected_error.value},
        )

    if user_api_key_dict.user_role != LLMUserRoles.PROXY_ADMIN:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "{}, your role={}".format(
                    CommonProxyErrors.not_allowed_access.value,
                    user_api_key_dict.user_role,
                )
            },
        )

    ## get general settings from db
    db_general_settings = await prisma_client.db.llm_config.find_first(
        where={"param_name": "general_settings"}
    )

    if db_general_settings is not None and db_general_settings.param_value is not None:
        db_general_settings_dict = dict(db_general_settings.param_value)
    else:
        db_general_settings_dict = {}

    allowed_args = {
        "max_parallel_requests": {"type": "Integer"},
        "global_max_parallel_requests": {"type": "Integer"},
        "max_request_size_mb": {"type": "Integer"},
        "max_response_size_mb": {"type": "Integer"},
        "pass_through_endpoints": {"type": "PydanticModel"},
    }

    return_val = []

    for field_name, field_info in ConfigGeneralSettings.model_fields.items():
        if field_name in allowed_args:

            ## HANDLE TYPED DICT

            typed_dict_type = allowed_args[field_name]["type"]

            if typed_dict_type == "PydanticModel":
                if field_name == "pass_through_endpoints":
                    pydantic_class_list = [PassThroughGenericEndpoint]
                else:
                    pydantic_class_list = []

                for pydantic_class in pydantic_class_list:
                    # Get type hints from the TypedDict to create FieldDetail objects
                    nested_fields = [
                        FieldDetail(
                            field_name=sub_field,
                            field_type=sub_field_type.__name__,
                            field_description="",  # Add custom logic if descriptions are available
                            field_default_value=general_settings.get(sub_field, None),
                            stored_in_db=None,
                        )
                        for sub_field, sub_field_type in pydantic_class.__annotations__.items()
                    ]

                    idx = 0
                    for (
                        sub_field,
                        sub_field_info,
                    ) in pydantic_class.model_fields.items():
                        if (
                            hasattr(sub_field_info, "description")
                            and sub_field_info.description is not None
                        ):
                            nested_fields[idx].field_description = (
                                sub_field_info.description
                            )
                        idx += 1

                    _stored_in_db = None
                    if field_name in db_general_settings_dict:
                        _stored_in_db = True
                    elif field_name in general_settings:
                        _stored_in_db = False

                    _response_obj = ConfigList(
                        field_name=field_name,
                        field_type=allowed_args[field_name]["type"],
                        field_description=field_info.description or "",
                        field_value=general_settings.get(field_name, None),
                        stored_in_db=_stored_in_db,
                        field_default_value=field_info.default,
                        nested_fields=nested_fields,
                    )
                    return_val.append(_response_obj)

            else:
                nested_fields = None

                _stored_in_db = None
                if field_name in db_general_settings_dict:
                    _stored_in_db = True
                elif field_name in general_settings:
                    _stored_in_db = False

                _response_obj = ConfigList(
                    field_name=field_name,
                    field_type=allowed_args[field_name]["type"],
                    field_description=field_info.description or "",
                    field_value=general_settings.get(field_name, None),
                    stored_in_db=_stored_in_db,
                    field_default_value=field_info.default,
                    nested_fields=nested_fields,
                )
                return_val.append(_response_obj)

    return return_val


@router.post(
    "/config/field/delete",
    tags=["config.yaml"],
    dependencies=[Depends(user_api_key_auth)],
    include_in_schema=False,
)
async def delete_config_general_settings(
    data: ConfigFieldDelete,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Delete the db value of this field in llm general settings. Resets it to it's initial default value on llm.
    """
    global prisma_client
    ## VALIDATION ##
    """
    - Check if prisma_client is None
    - Check if user allowed to call this endpoint (admin-only)
    - Check if param in general settings
    """
    if prisma_client is None:
        raise HTTPException(
            status_code=400,
            detail={"error": CommonProxyErrors.db_not_connected_error.value},
        )

    if user_api_key_dict.user_role != LLMUserRoles.PROXY_ADMIN:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "{}, your role={}".format(
                    CommonProxyErrors.not_allowed_access.value,
                    user_api_key_dict.user_role,
                )
            },
        )

    if data.field_name not in ConfigGeneralSettings.model_fields:
        raise HTTPException(
            status_code=400,
            detail={"error": "Invalid field={} passed in.".format(data.field_name)},
        )

    ## get general settings from db
    db_general_settings = await prisma_client.db.llm_config.find_first(
        where={"param_name": "general_settings"}
    )
    ### pop the value

    if db_general_settings is None or db_general_settings.param_value is None:
        raise HTTPException(
            status_code=400,
            detail={"error": "Field name={} not in config".format(data.field_name)},
        )
    else:
        general_settings = dict(db_general_settings.param_value)

    ## update db

    general_settings.pop(data.field_name, None)

    response = await prisma_client.db.llm_config.upsert(
        where={"param_name": "general_settings"},
        data={
            "create": {"param_name": "general_settings", "param_value": json.dumps(general_settings)},  # type: ignore
            "update": {"param_value": json.dumps(general_settings)},  # type: ignore
        },
    )

    return response


@router.get(
    "/get/config/callbacks",
    tags=["config.yaml"],
    include_in_schema=False,
    dependencies=[Depends(user_api_key_auth)],
)
async def get_config():  # noqa: PLR0915
    """
    For Admin UI - allows admin to view config via UI
    # return the callbacks and the env variables for the callback

    """
    global llm_router, llm_model_list, general_settings, proxy_config, proxy_logging_obj, master_key
    try:
        import base64

        all_available_callbacks = AllCallbacks()

        config_data = await proxy_config.get_config()
        _llm_settings = config_data.get("llm_settings", {})
        _general_settings = config_data.get("general_settings", {})
        environment_variables = config_data.get("environment_variables", {})

        # check if "langfuse" in llm_settings
        _success_callbacks = _llm_settings.get("success_callback", [])
        _data_to_return = []
        """
        [
            {
                "name": "langfuse",
                "variables": {
                    "LANGFUSE_PUB_KEY": "value",
                    "LANGFUSE_SECRET_KEY": "value",
                    "LANGFUSE_HOST": "value"
                },
            }
        ]

        """
        for _callback in _success_callbacks:
            if _callback != "langfuse":
                if _callback == "openmeter":
                    env_vars = [
                        "OPENMETER_API_KEY",
                    ]
                elif _callback == "braintrust":
                    env_vars = [
                        "BRAINTRUST_API_KEY",
                    ]
                elif _callback == "traceloop":
                    env_vars = ["TRACELOOP_API_KEY"]
                elif _callback == "custom_callback_api":
                    env_vars = ["GENERIC_LOGGER_ENDPOINT"]
                elif _callback == "otel":
                    env_vars = ["OTEL_EXPORTER", "OTEL_ENDPOINT", "OTEL_HEADERS"]
                elif _callback == "langsmith":
                    env_vars = [
                        "LANGSMITH_API_KEY",
                        "LANGSMITH_PROJECT",
                        "LANGSMITH_DEFAULT_RUN_NAME",
                    ]
                else:
                    env_vars = []

                env_vars_dict = {}
                for _var in env_vars:
                    env_variable = environment_variables.get(_var, None)
                    if env_variable is None:
                        env_vars_dict[_var] = None
                    else:
                        # decode + decrypt the value
                        decrypted_value = decrypt_value_helper(value=env_variable)
                        env_vars_dict[_var] = decrypted_value

                _data_to_return.append({"name": _callback, "variables": env_vars_dict})
            elif _callback == "langfuse":
                _langfuse_vars = [
                    "LANGFUSE_PUBLIC_KEY",
                    "LANGFUSE_SECRET_KEY",
                    "LANGFUSE_HOST",
                ]
                _langfuse_env_vars = {}
                for _var in _langfuse_vars:
                    env_variable = environment_variables.get(_var, None)
                    if env_variable is None:
                        _langfuse_env_vars[_var] = None
                    else:
                        # decode + decrypt the value
                        decrypted_value = decrypt_value_helper(value=env_variable)
                        _langfuse_env_vars[_var] = decrypted_value

                _data_to_return.append(
                    {"name": _callback, "variables": _langfuse_env_vars}
                )

        # Check if slack alerting is on
        _alerting = _general_settings.get("alerting", [])
        alerting_data = []
        if "slack" in _alerting:
            _slack_vars = [
                "SLACK_WEBHOOK_URL",
            ]
            _slack_env_vars = {}
            for _var in _slack_vars:
                env_variable = environment_variables.get(_var, None)
                if env_variable is None:
                    _value = os.getenv("SLACK_WEBHOOK_URL", None)
                    _slack_env_vars[_var] = _value
                else:
                    # decode + decrypt the value
                    _decrypted_value = decrypt_value_helper(value=env_variable)
                    _slack_env_vars[_var] = _decrypted_value

            _alerting_types = proxy_logging_obj.slack_alerting_instance.alert_types
            _all_alert_types = (
                proxy_logging_obj.slack_alerting_instance._all_possible_alert_types()
            )
            _alerts_to_webhook = (
                proxy_logging_obj.slack_alerting_instance.alert_to_webhook_url
            )
            alerting_data.append(
                {
                    "name": "slack",
                    "variables": _slack_env_vars,
                    "active_alerts": _alerting_types,
                    "alerts_to_webhook": _alerts_to_webhook,
                }
            )
        # pass email alerting vars
        _email_vars = [
            "SMTP_HOST",
            "SMTP_PORT",
            "SMTP_USERNAME",
            "SMTP_PASSWORD",
            "SMTP_SENDER_EMAIL",
            "TEST_EMAIL_ADDRESS",
            "EMAIL_LOGO_URL",
            "EMAIL_SUPPORT_CONTACT",
        ]
        _email_env_vars = {}
        for _var in _email_vars:
            env_variable = environment_variables.get(_var, None)
            if env_variable is None:
                _email_env_vars[_var] = None
            else:
                # decode + decrypt the value
                _decrypted_value = decrypt_value_helper(value=env_variable)
                _email_env_vars[_var] = _decrypted_value

        alerting_data.append(
            {
                "name": "email",
                "variables": _email_env_vars,
            }
        )

        if llm_router is None:
            _router_settings = {}
        else:
            _router_settings = llm_router.get_settings()

        return {
            "status": "success",
            "callbacks": _data_to_return,
            "alerts": alerting_data,
            "router_settings": _router_settings,
            "available_callbacks": all_available_callbacks,
        }
    except Exception as e:
        verbose_proxy_logger.exception(
            "llm.proxy.proxy_server.get_config(): Exception occured - {}".format(
                str(e)
            )
        )
        if isinstance(e, HTTPException):
            raise ProxyException(
                message=getattr(e, "detail", f"Authentication Error({str(e)})"),
                type=ProxyErrorTypes.auth_error,
                param=getattr(e, "param", "None"),
                code=getattr(e, "status_code", status.HTTP_400_BAD_REQUEST),
            )
        elif isinstance(e, ProxyException):
            raise e
        raise ProxyException(
            message="Authentication Error, " + str(e),
            type=ProxyErrorTypes.auth_error,
            param=getattr(e, "param", "None"),
            code=status.HTTP_400_BAD_REQUEST,
        )


@router.get(
    "/config/yaml",
    tags=["config.yaml"],
    dependencies=[Depends(user_api_key_auth)],
    include_in_schema=False,
)
async def config_yaml_endpoint(config_info: ConfigYAML):
    """
    This is a mock endpoint, to show what you can set in config.yaml details in the Swagger UI.

    Parameters:

    The config.yaml object has the following attributes:
    - **model_list**: *Optional[List[ModelParams]]* - A list of supported models on the server, along with model-specific configurations. ModelParams includes "model_name" (name of the model), "llm_params" (llm-specific parameters for the model), and "model_info" (additional info about the model such as id, mode, cost per token, etc).

    - **llm_settings**: *Optional[dict]*: Settings for the llm module. You can specify multiple properties like "drop_params", "set_verbose", "api_base", "cache".

    - **general_settings**: *Optional[ConfigGeneralSettings]*: General settings for the server like "completion_model" (default model for chat completion calls), "use_azure_key_vault" (option to load keys from azure key vault), "master_key" (key required for all calls to proxy), and others.

    Please, refer to each class's description for a better understanding of the specific attributes within them.

    Note: This is a mock endpoint primarily meant for demonstration purposes, and does not actually provide or change any configurations.
    """
    return {"hello": "world"}


@router.get(
    "/get/llm_model_cost_map",
    include_in_schema=False,
    dependencies=[Depends(user_api_key_auth)],
)
async def get_llm_model_cost_map():
    try:
        _model_cost_map = llm.model_cost
        return _model_cost_map
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal Server Error ({str(e)})",
        )


@router.get("/", dependencies=[Depends(user_api_key_auth)])
async def home(request: Request):
    return "LLM: RUNNING"


@router.get("/routes", dependencies=[Depends(user_api_key_auth)])
async def get_routes():
    """
    Get a list of available routes in the FastAPI application.
    """
    routes = []
    for route in app.routes:
        endpoint_route = getattr(route, "endpoint", None)
        if endpoint_route is not None:
            route_info = {
                "path": getattr(route, "path", None),
                "methods": getattr(route, "methods", None),
                "name": getattr(route, "name", None),
                "endpoint": (
                    endpoint_route.__name__
                    if getattr(route, "endpoint", None)
                    else None
                ),
            }
            routes.append(route_info)

    return {"routes": routes}


#### TEST ENDPOINTS ####
# @router.get(
#     "/token/generate",
#     dependencies=[Depends(user_api_key_auth)],
#     include_in_schema=False,
# )
# async def token_generate():
#     """
#     Test endpoint. Admin-only access. Meant for generating admin tokens with specific claims and testing if they work for creating keys, etc.
#     """
#     # Initialize AuthJWTSSO with your OpenID Provider configuration
#     from fastapi_sso import AuthJWTSSO

#     auth_jwt_sso = AuthJWTSSO(
#         issuer=os.getenv("OPENID_BASE_URL"),
#         client_id=os.getenv("OPENID_CLIENT_ID"),
#         client_secret=os.getenv("OPENID_CLIENT_SECRET"),
#         scopes=["llm_proxy_admin"],
#     )

#     token = auth_jwt_sso.create_access_token()

#     return {"token": token}


app.include_router(router)
app.include_router(response_router)
app.include_router(batches_router)
app.include_router(rerank_router)
app.include_router(fine_tuning_router)
app.include_router(credential_router)
app.include_router(llm_passthrough_router)
app.include_router(mcp_router)
app.include_router(mcp_admin_router)
app.include_router(mcp_public_router)  # Public access to MCP servers
# Removed admin_ui_router to use Next.js UI instead
app.include_router(mcp_openai_agents_router)
app.include_router(anthropic_router)
app.include_router(langfuse_router)
app.include_router(pass_through_router)
app.include_router(health_router)
app.include_router(key_management_router)
app.include_router(internal_user_router)
app.include_router(team_router)
app.include_router(ui_sso_router)
app.include_router(organization_router)
app.include_router(customer_router)
app.include_router(spend_management_router)
app.include_router(caching_router)
app.include_router(analytics_router)
app.include_router(guardrails_router)
app.include_router(debugging_endpoints_router)
app.include_router(ui_crud_endpoints_router)
app.include_router(openai_files_router)
app.include_router(team_callback_router)
app.include_router(budget_management_router)
app.include_router(model_management_router)
