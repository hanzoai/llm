import enum
import json
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Literal, Optional, Union

import httpx
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    Json,
    field_validator,
    model_validator,
)
from typing_extensions import Required, TypedDict

from llm.types.integrations.slack_alerting import AlertType
from llm.types.llms.openai import AllMessageValues
from llm.types.router import RouterErrors, UpdateRouterConfig
from llm.types.utils import (
    CallTypes,
    EmbeddingResponse,
    GenericBudgetConfigType,
    ImageResponse,
    LLMPydanticObjectBase,
    ModelResponse,
    ProviderField,
    StandardCallbackDynamicParams,
    StandardLoggingPayloadErrorInformation,
    StandardLoggingPayloadStatus,
    StandardPassThroughResponseObject,
    TextCompletionResponse,
)

from .types_utils.utils import get_instance_fn, validate_custom_validate_return_type

if TYPE_CHECKING:
    from opentelemetry.trace import Span as _Span

    Span = _Span
else:
    Span = Any


class LLMTeamRoles(enum.Enum):
    # team admin
    TEAM_ADMIN = "admin"
    # team member
    TEAM_MEMBER = "user"


class LLMUserRoles(str, enum.Enum):
    """
    Admin Roles:
    PROXY_ADMIN: admin over the platform
    PROXY_ADMIN_VIEW_ONLY: can login, view all own keys, view all spend
    ORG_ADMIN: admin over a specific organization, can create teams, users only within their organization

    Internal User Roles:
    INTERNAL_USER: can login, view/create/delete their own keys, view their spend
    INTERNAL_USER_VIEW_ONLY: can login, view their own keys, view their own spend


    Team Roles:
    TEAM: used for JWT auth


    Customer Roles:
    CUSTOMER: External users -> these are customers

    """

    # Admin Roles
    PROXY_ADMIN = "proxy_admin"
    PROXY_ADMIN_VIEW_ONLY = "proxy_admin_viewer"

    # Organization admins
    ORG_ADMIN = "org_admin"

    # Internal User Roles
    INTERNAL_USER = "internal_user"
    INTERNAL_USER_VIEW_ONLY = "internal_user_viewer"

    # Team Roles
    TEAM = "team"

    # Customer Roles - External users of proxy
    CUSTOMER = "customer"

    def __str__(self):
        return str(self.value)

    def values(self) -> List[str]:
        return list(self.__annotations__.keys())

    @property
    def description(self):
        """
        Descriptions for the enum values
        """
        descriptions = {
            "proxy_admin": "admin over llm proxy, has all permissions",
            "proxy_admin_viewer": "view all keys, view all spend",
            "internal_user": "view/create/delete their own keys, view their own spend",
            "internal_user_viewer": "view their own keys, view their own spend",
            "team": "team scope used for JWT auth",
            "customer": "customer",
        }
        return descriptions.get(self.value, "")

    @property
    def ui_label(self):
        """
        UI labels for the enum values
        """
        ui_labels = {
            "proxy_admin": "Admin (All Permissions)",
            "proxy_admin_viewer": "Admin (View Only)",
            "internal_user": "Internal User (Create/Delete/View)",
            "internal_user_viewer": "Internal User (View Only)",
            "team": "Team",
            "customer": "Customer",
        }
        return ui_labels.get(self.value, "")

    @property
    def is_internal_user_role(self) -> bool:
        """returns true if this role is an `internal_user` or `internal_user_viewer` role"""
        return self.value in [
            self.INTERNAL_USER,
            self.INTERNAL_USER_VIEW_ONLY,
        ]


class LLMTableNames(str, enum.Enum):
    """
    Enum for Table Names used by LLM
    """

    TEAM_TABLE_NAME = "LLM_TeamTable"
    USER_TABLE_NAME = "LLM_UserTable"
    KEY_TABLE_NAME = "LLM_VerificationToken"
    PROXY_MODEL_TABLE_NAME = "LLM_ProxyModelTable"


def hash_token(token: str):
    import hashlib

    # Hash the string using SHA-256
    hashed_token = hashlib.sha256(token.encode()).hexdigest()

    return hashed_token


class LLM_UpperboundKeyGenerateParams(LLMPydanticObjectBase):
    """
    Set default upperbound to max budget a key called via `/key/generate` can be.

    Args:
        max_budget (Optional[float], optional): Max budget a key can be. Defaults to None.
        budget_duration (Optional[str], optional): Duration of the budget. Defaults to None.
        duration (Optional[str], optional): Duration of the key. Defaults to None.
        max_parallel_requests (Optional[int], optional): Max number of requests that can be made in parallel. Defaults to None.
        tpm_limit (Optional[int], optional): Tpm limit. Defaults to None.
        rpm_limit (Optional[int], optional): Rpm limit. Defaults to None.
    """

    max_budget: Optional[float] = None
    budget_duration: Optional[str] = None
    duration: Optional[str] = None
    max_parallel_requests: Optional[int] = None
    tpm_limit: Optional[int] = None
    rpm_limit: Optional[int] = None


class LLMRoutes(enum.Enum):
    openai_route_names = [
        "chat_completion",
        "completion",
        "embeddings",
        "image_generation",
        "audio_transcriptions",
        "moderations",
        "model_list",  # OpenAI /v1/models route
    ]
    openai_routes = [
        # chat completions
        "/engines/{model}/chat/completions",
        "/openai/deployments/{model}/chat/completions",
        "/chat/completions",
        "/v1/chat/completions",
        # completions
        "/engines/{model}/completions",
        "/openai/deployments/{model}/completions",
        "/completions",
        "/v1/completions",
        # embeddings
        "/engines/{model}/embeddings",
        "/openai/deployments/{model}/embeddings",
        "/embeddings",
        "/v1/embeddings",
        # image generation
        "/images/generations",
        "/v1/images/generations",
        # audio transcription
        "/audio/transcriptions",
        "/v1/audio/transcriptions",
        # audio Speech
        "/audio/speech",
        "/v1/audio/speech",
        # moderations
        "/moderations",
        "/v1/moderations",
        # batches
        "/v1/batches",
        "/batches",
        "/v1/batches/{batch_id}",
        "/batches/{batch_id}",
        # files
        "/v1/files",
        "/files",
        "/v1/files/{file_id}",
        "/files/{file_id}",
        "/v1/files/{file_id}/content",
        "/files/{file_id}/content",
        # fine_tuning
        "/fine_tuning/jobs",
        "/v1/fine_tuning/jobs",
        "/fine_tuning/jobs/{fine_tuning_job_id}/cancel",
        "/v1/fine_tuning/jobs/{fine_tuning_job_id}/cancel",
        # assistants-related routes
        "/assistants",
        "/v1/assistants",
        "/v1/assistants/{assistant_id}",
        "/assistants/{assistant_id}",
        "/threads",
        "/v1/threads",
        "/threads/{thread_id}",
        "/v1/threads/{thread_id}",
        "/threads/{thread_id}/messages",
        "/v1/threads/{thread_id}/messages",
        "/threads/{thread_id}/runs",
        "/v1/threads/{thread_id}/runs",
        # models
        "/models",
        "/v1/models",
        # token counter
        "/utils/token_counter",
        # rerank
        "/rerank",
        "/v1/rerank",
        "/v2/rerank"
        # realtime
        "/realtime",
        "/v1/realtime",
        "/realtime?{model}",
        "/v1/realtime?{model}",
        # responses API
        "/responses",
        "/v1/responses",
        "/responses/{response_id}",
        "/v1/responses/{response_id}",
        "/responses/{response_id}/input_items",
        "/v1/responses/{response_id}/input_items",
    ]

    mapped_pass_through_routes = [
        "/bedrock",
        "/vertex-ai",
        "/vertex_ai",
        "/cohere",
        "/gemini",
        "/anthropic",
        "/langfuse",
        "/azure",
        "/openai",
        "/assemblyai",
        "/eu.assemblyai",
    ]

    anthropic_routes = [
        "/v1/messages",
    ]

    info_routes = [
        "/key/info",
        "/key/health",
        "/team/info",
        "/team/list",
        "/organization/list",
        "/team/available",
        "/user/info",
        "/model/info",
        "/v2/model/info",
        "/v2/key/info",
        "/model_group/info",
        "/health",
        "/key/list",
        "/user/filter/ui",
    ]

    # NOTE: ROUTES ONLY FOR MASTER KEY - only the Master Key should be able to Reset Spend
    master_key_only_routes = ["/global/spend/reset"]

    management_routes = [  # key
        "/key/generate",
        "/key/{token_id}/regenerate",
        "/key/update",
        "/key/delete",
        "/key/info",
        "/key/health",
        "/key/list",
        # user
        "/user/new",
        "/user/update",
        "/user/delete",
        "/user/info",
        # team
        "/team/new",
        "/team/update",
        "/team/delete",
        "/team/list",
        "/team/info",
        "/team/block",
        "/team/unblock",
        "/team/available",
        # model
        "/model/new",
        "/model/update",
        "/model/delete",
        "/model/info",
    ]

    spend_tracking_routes = [
        # spend
        "/spend/keys",
        "/spend/users",
        "/spend/tags",
        "/spend/calculate",
        "/spend/logs",
    ]

    global_spend_tracking_routes = [
        # global spend
        "/global/spend/logs",
        "/global/spend",
        "/global/spend/keys",
        "/global/spend/teams",
        "/global/spend/end_users",
        "/global/spend/models",
        "/global/predict/spend/logs",
        "/global/spend/report",
        "/global/spend/provider",
    ]

    public_routes = set(
        [
            "/routes",
            "/",
            "/health/liveliness",
            "/health/liveness",
            "/health/readiness",
            "/test",
            "/config/yaml",
            "/metrics",
        ]
    )

    ui_routes = [
        "/sso",
        "/sso/get/ui_settings",
        "/login",
        "/key/info",
        "/config",
        "/spend",
        "/model/info",
        "/v2/model/info",
        "/v2/key/info",
        "/models",
        "/v1/models",
        "/global/spend",
        "/global/spend/logs",
        "/global/spend/keys",
        "/global/spend/models",
        "/global/predict/spend/logs",
        "/global/activity",
        "/health/services",
    ] + info_routes

    internal_user_routes = [
        "/key/generate",
        "/key/{token_id}/regenerate",
        "/key/update",
        "/key/delete",
        "/key/health",
        "/key/info",
        "/global/spend/tags",
        "/global/spend/keys",
        "/global/spend/models",
        "/global/spend/provider",
        "/global/spend/end_users",
        "/global/activity",
        "/global/activity/model",
    ] + spend_tracking_routes

    internal_user_view_only_routes = (
        spend_tracking_routes + global_spend_tracking_routes
    )

    self_managed_routes = [
        "/team/member_add",
        "/team/member_delete",
        "/model/new",
    ]  # routes that manage their own allowed/disallowed logic

    ## Org Admin Routes ##

    # Routes only an Org Admin Can Access
    org_admin_only_routes = [
        "/organization/info",
        "/organization/delete",
        "/organization/member_add",
        "/organization/member_update",
    ]

    # All routes accesible by an Org Admin
    org_admin_allowed_routes = (
        org_admin_only_routes + management_routes + self_managed_routes
    )


class LLMPromptInjectionParams(LLMPydanticObjectBase):
    heuristics_check: bool = False
    vector_db_check: bool = False
    llm_api_check: bool = False
    llm_api_name: Optional[str] = None
    llm_api_system_prompt: Optional[str] = None
    llm_api_fail_call_string: Optional[str] = None
    reject_as_response: Optional[bool] = Field(
        default=False,
        description="Return rejected request error message as a string to the user. Default behaviour is to raise an exception.",
    )

    @model_validator(mode="before")
    @classmethod
    def check_llm_api_params(cls, values):
        llm_api_check = values.get("llm_api_check")
        if llm_api_check is True:
            if "llm_api_name" not in values or not values["llm_api_name"]:
                raise ValueError(
                    "If llm_api_check is set to True, llm_api_name must be provided"
                )
            if (
                "llm_api_system_prompt" not in values
                or not values["llm_api_system_prompt"]
            ):
                raise ValueError(
                    "If llm_api_check is set to True, llm_api_system_prompt must be provided"
                )
            if (
                "llm_api_fail_call_string" not in values
                or not values["llm_api_fail_call_string"]
            ):
                raise ValueError(
                    "If llm_api_check is set to True, llm_api_fail_call_string must be provided"
                )
        return values


######### Request Class Definition ######
class ProxyChatCompletionRequest(LLMPydanticObjectBase):
    model: str
    messages: List[Dict[str, str]]
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    n: Optional[int] = None
    stream: Optional[bool] = None
    stop: Optional[List[str]] = None
    max_tokens: Optional[int] = None
    presence_penalty: Optional[float] = None
    frequency_penalty: Optional[float] = None
    logit_bias: Optional[Dict[str, float]] = None
    user: Optional[str] = None
    response_format: Optional[Dict[str, str]] = None
    seed: Optional[int] = None
    tools: Optional[List[str]] = None
    tool_choice: Optional[str] = None
    functions: Optional[List[str]] = None  # soon to be deprecated
    function_call: Optional[str] = None  # soon to be deprecated

    # Optional LLM params
    caching: Optional[bool] = None
    api_base: Optional[str] = None
    api_version: Optional[str] = None
    api_key: Optional[str] = None
    num_retries: Optional[int] = None
    context_window_fallback_dict: Optional[Dict[str, str]] = None
    fallbacks: Optional[List[str]] = None
    metadata: Optional[Dict[str, str]] = {}
    deployment_id: Optional[str] = None
    request_timeout: Optional[int] = None

    model_config = ConfigDict(
        extra="allow"
    )  # allow params not defined here, these fall in llm.completion(**kwargs)


class ModelInfoDelete(LLMPydanticObjectBase):
    id: str


class ModelInfo(LLMPydanticObjectBase):
    id: Optional[str]
    mode: Optional[Literal["embedding", "chat", "completion"]]
    input_cost_per_token: Optional[float] = 0.0
    output_cost_per_token: Optional[float] = 0.0
    max_tokens: Optional[int] = 2048  # assume 2048 if not set

    # for azure models we need users to specify the base model, one azure you can call deployments - azure/my-random-model
    # we look up the base model in model_prices_and_context_window.json
    base_model: Optional[
        Literal[
            "gpt-4-1106-preview",
            "gpt-4-32k",
            "gpt-4",
            "gpt-3.5-turbo-16k",
            "gpt-3.5-turbo",
            "text-embedding-ada-002",
        ]
    ]

    model_config = ConfigDict(protected_namespaces=(), extra="allow")

    @model_validator(mode="before")
    @classmethod
    def set_model_info(cls, values):
        if values.get("id") is None:
            values.update({"id": str(uuid.uuid4())})
        if values.get("mode") is None:
            values.update({"mode": None})
        if values.get("input_cost_per_token") is None:
            values.update({"input_cost_per_token": None})
        if values.get("output_cost_per_token") is None:
            values.update({"output_cost_per_token": None})
        if values.get("max_tokens") is None:
            values.update({"max_tokens": None})
        if values.get("base_model") is None:
            values.update({"base_model": None})
        return values


class ProviderInfo(LLMPydanticObjectBase):
    name: str
    fields: List[ProviderField]


class BlockUsers(LLMPydanticObjectBase):
    user_ids: List[str]  # required


class ModelParams(LLMPydanticObjectBase):
    model_name: str
    llm_params: dict
    model_info: ModelInfo

    model_config = ConfigDict(protected_namespaces=())

    @model_validator(mode="before")
    @classmethod
    def set_model_info(cls, values):
        if values.get("model_info") is None:
            values.update(
                {"model_info": ModelInfo(id=None, mode="chat", base_model=None)}
            )
        return values


class GenerateRequestBase(LLMPydanticObjectBase):
    """
    Overlapping schema between key and user generate/update requests
    """

    key_alias: Optional[str] = None
    duration: Optional[str] = None
    models: Optional[list] = []
    spend: Optional[float] = 0
    max_budget: Optional[float] = None
    user_id: Optional[str] = None
    team_id: Optional[str] = None
    max_parallel_requests: Optional[int] = None
    metadata: Optional[dict] = {}
    tpm_limit: Optional[int] = None
    rpm_limit: Optional[int] = None
    budget_duration: Optional[str] = None
    allowed_cache_controls: Optional[list] = []
    config: Optional[dict] = {}
    permissions: Optional[dict] = {}
    model_max_budget: Optional[dict] = (
        {}
    )  # {"gpt-4": 5.0, "gpt-3.5-turbo": 5.0}, defaults to {}

    model_config = ConfigDict(protected_namespaces=())
    model_rpm_limit: Optional[dict] = None
    model_tpm_limit: Optional[dict] = None
    guardrails: Optional[List[str]] = None
    blocked: Optional[bool] = None
    aliases: Optional[dict] = {}


class KeyRequestBase(GenerateRequestBase):
    key: Optional[str] = None
    budget_id: Optional[str] = None
    tags: Optional[List[str]] = None
    enforced_params: Optional[List[str]] = None


class GenerateKeyRequest(KeyRequestBase):
    soft_budget: Optional[float] = None
    send_invite_email: Optional[bool] = None


class GenerateKeyResponse(KeyRequestBase):
    key: str  # type: ignore
    key_name: Optional[str] = None
    expires: Optional[datetime]
    user_id: Optional[str] = None
    token_id: Optional[str] = None
    llm_budget_table: Optional[Any] = None
    token: Optional[str] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def set_model_info(cls, values):
        if values.get("token") is not None:
            values.update({"key": values.get("token")})
        dict_fields = [
            "metadata",
            "aliases",
            "config",
            "permissions",
            "model_max_budget",
        ]
        for field in dict_fields:
            value = values.get(field)
            if value is not None and isinstance(value, str):
                try:
                    values[field] = json.loads(value)
                except json.JSONDecodeError:
                    raise ValueError(f"Field {field} should be a valid dictionary")

        return values


class UpdateKeyRequest(KeyRequestBase):
    # Note: the defaults of all Params here MUST BE NONE
    # else they will get overwritten
    key: str  # type: ignore
    duration: Optional[str] = None
    spend: Optional[float] = None
    metadata: Optional[dict] = None
    temp_budget_increase: Optional[float] = None
    temp_budget_expiry: Optional[datetime] = None

    @model_validator(mode="after")
    def validate_temp_budget(self) -> "UpdateKeyRequest":
        if self.temp_budget_increase is not None or self.temp_budget_expiry is not None:
            if self.temp_budget_increase is None or self.temp_budget_expiry is None:
                raise ValueError(
                    "temp_budget_increase and temp_budget_expiry must be set together"
                )
        return self


class RegenerateKeyRequest(GenerateKeyRequest):
    # This needs to be different from UpdateKeyRequest, because "key" is optional for this
    key: Optional[str] = None
    duration: Optional[str] = None
    spend: Optional[float] = None
    metadata: Optional[dict] = None
    new_master_key: Optional[str] = None


class KeyRequest(LLMPydanticObjectBase):
    keys: Optional[List[str]] = None
    key_aliases: Optional[List[str]] = None

    @model_validator(mode="before")
    @classmethod
    def validate_at_least_one(cls, values):
        if not values.get("keys") and not values.get("key_aliases"):
            raise ValueError(
                "At least one of 'keys' or 'key_aliases' must be provided."
            )
        return values


class LLM_ModelTable(LLMPydanticObjectBase):
    model_aliases: Optional[Union[str, dict]] = None  # json dump the dict
    created_by: str
    updated_by: str

    model_config = ConfigDict(protected_namespaces=())


class LLM_ProxyModelTable(LLMPydanticObjectBase):
    model_id: str
    model_name: str
    llm_params: dict
    model_info: dict
    created_by: str
    updated_by: str

    @model_validator(mode="before")
    @classmethod
    def check_potential_json_str(cls, values):
        if isinstance(values.get("llm_params"), str):
            try:
                values["llm_params"] = json.loads(values["llm_params"])
            except json.JSONDecodeError:
                pass
        if isinstance(values.get("model_info"), str):
            try:
                values["model_info"] = json.loads(values["model_info"])
            except json.JSONDecodeError:
                pass
        return values


class NewUserRequest(GenerateRequestBase):
    max_budget: Optional[float] = None
    user_email: Optional[str] = None
    user_alias: Optional[str] = None
    user_role: Optional[
        Literal[
            LLMUserRoles.PROXY_ADMIN,
            LLMUserRoles.PROXY_ADMIN_VIEW_ONLY,
            LLMUserRoles.INTERNAL_USER,
            LLMUserRoles.INTERNAL_USER_VIEW_ONLY,
        ]
    ] = None
    teams: Optional[list] = None
    auto_create_key: bool = (
        True  # flag used for returning a key as part of the /user/new response
    )
    send_invite_email: Optional[bool] = None


class NewUserResponse(GenerateKeyResponse):
    max_budget: Optional[float] = None
    user_email: Optional[str] = None
    user_role: Optional[
        Literal[
            LLMUserRoles.PROXY_ADMIN,
            LLMUserRoles.PROXY_ADMIN_VIEW_ONLY,
            LLMUserRoles.INTERNAL_USER,
            LLMUserRoles.INTERNAL_USER_VIEW_ONLY,
        ]
    ] = None
    teams: Optional[list] = None
    user_alias: Optional[str] = None
    model_max_budget: Optional[dict] = None


class UpdateUserRequest(GenerateRequestBase):
    # Note: the defaults of all Params here MUST BE NONE
    # else they will get overwritten
    user_id: Optional[str] = None
    password: Optional[str] = None
    user_email: Optional[str] = None
    spend: Optional[float] = None
    metadata: Optional[dict] = None
    user_role: Optional[
        Literal[
            LLMUserRoles.PROXY_ADMIN,
            LLMUserRoles.PROXY_ADMIN_VIEW_ONLY,
            LLMUserRoles.INTERNAL_USER,
            LLMUserRoles.INTERNAL_USER_VIEW_ONLY,
        ]
    ] = None
    max_budget: Optional[float] = None

    @model_validator(mode="before")
    @classmethod
    def check_user_info(cls, values):
        if values.get("user_id") is None and values.get("user_email") is None:
            raise ValueError("Either user id or user email must be provided")
        return values


class DeleteUserRequest(LLMPydanticObjectBase):
    user_ids: List[str]  # required


AllowedModelRegion = Literal["eu", "us"]


class BudgetNewRequest(LLMPydanticObjectBase):
    budget_id: Optional[str] = Field(default=None, description="The unique budget id.")
    max_budget: Optional[float] = Field(
        default=None,
        description="Requests will fail if this budget (in USD) is exceeded.",
    )
    soft_budget: Optional[float] = Field(
        default=None,
        description="Requests will NOT fail if this is exceeded. Will fire alerting though.",
    )
    max_parallel_requests: Optional[int] = Field(
        default=None, description="Max concurrent requests allowed for this budget id."
    )
    tpm_limit: Optional[int] = Field(
        default=None, description="Max tokens per minute, allowed for this budget id."
    )
    rpm_limit: Optional[int] = Field(
        default=None, description="Max requests per minute, allowed for this budget id."
    )
    budget_duration: Optional[str] = Field(
        default=None,
        description="Max duration budget should be set for (e.g. '1hr', '1d', '28d')",
    )
    model_max_budget: Optional[GenericBudgetConfigType] = Field(
        default=None,
        description="Max budget for each model (e.g. {'gpt-4o': {'max_budget': '0.0000001', 'budget_duration': '1d', 'tpm_limit': 1000, 'rpm_limit': 1000}})",
    )


class BudgetRequest(LLMPydanticObjectBase):
    budgets: List[str]


class BudgetDeleteRequest(LLMPydanticObjectBase):
    id: str


class CustomerBase(LLMPydanticObjectBase):
    user_id: str
    alias: Optional[str] = None
    spend: float = 0.0
    allowed_model_region: Optional[AllowedModelRegion] = None
    default_model: Optional[str] = None
    budget_id: Optional[str] = None
    llm_budget_table: Optional[BudgetNewRequest] = None
    blocked: bool = False


class NewCustomerRequest(BudgetNewRequest):
    """
    Create a new customer, allocate a budget to them
    """

    user_id: str
    alias: Optional[str] = None  # human-friendly alias
    blocked: bool = False  # allow/disallow requests for this end-user
    budget_id: Optional[str] = None  # give either a budget_id or max_budget
    allowed_model_region: Optional[AllowedModelRegion] = (
        None  # require all user requests to use models in this specific region
    )
    default_model: Optional[str] = (
        None  # if no equivalent model in allowed region - default all requests to this model
    )

    @model_validator(mode="before")
    @classmethod
    def check_user_info(cls, values):
        if values.get("max_budget") is not None and values.get("budget_id") is not None:
            raise ValueError("Set either 'max_budget' or 'budget_id', not both.")

        return values


class UpdateCustomerRequest(LLMPydanticObjectBase):
    """
    Update a Customer, use this to update customer budgets etc

    """

    user_id: str
    alias: Optional[str] = None  # human-friendly alias
    blocked: bool = False  # allow/disallow requests for this end-user
    max_budget: Optional[float] = None
    budget_id: Optional[str] = None  # give either a budget_id or max_budget
    allowed_model_region: Optional[AllowedModelRegion] = (
        None  # require all user requests to use models in this specific region
    )
    default_model: Optional[str] = (
        None  # if no equivalent model in allowed region - default all requests to this model
    )


class DeleteCustomerRequest(LLMPydanticObjectBase):
    """
    Delete multiple Customers
    """

    user_ids: List[str]


class MemberBase(LLMPydanticObjectBase):
    user_id: Optional[str] = None
    user_email: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def check_user_info(cls, values):
        if not isinstance(values, dict):
            raise ValueError("input needs to be a dictionary")
        if values.get("user_id") is None and values.get("user_email") is None:
            raise ValueError("Either user id or user email must be provided")
        return values


class Member(MemberBase):
    role: Literal[
        "admin",
        "user",
    ]


class OrgMember(MemberBase):
    role: Literal[
        LLMUserRoles.ORG_ADMIN,
        LLMUserRoles.INTERNAL_USER,
        LLMUserRoles.INTERNAL_USER_VIEW_ONLY,
    ]


class TeamBase(LLMPydanticObjectBase):
    team_alias: Optional[str] = None
    team_id: Optional[str] = None
    organization_id: Optional[str] = None
    admins: list = []
    members: list = []
    members_with_roles: List[Member] = []
    metadata: Optional[dict] = None
    tpm_limit: Optional[int] = None
    rpm_limit: Optional[int] = None

    # Budget fields
    max_budget: Optional[float] = None
    budget_duration: Optional[str] = None

    models: list = []
    blocked: bool = False


class NewTeamRequest(TeamBase):
    model_aliases: Optional[dict] = None
    tags: Optional[list] = None
    guardrails: Optional[List[str]] = None

    model_config = ConfigDict(protected_namespaces=())


class GlobalEndUsersSpend(LLMPydanticObjectBase):
    api_key: Optional[str] = None
    startTime: Optional[datetime] = None
    endTime: Optional[datetime] = None


class UpdateTeamRequest(LLMPydanticObjectBase):
    """
    UpdateTeamRequest, used by /team/update when you need to update a team

    team_id: str
    team_alias: Optional[str] = None
    organization_id: Optional[str] = None
    metadata: Optional[dict] = None
    tpm_limit: Optional[int] = None
    rpm_limit: Optional[int] = None
    max_budget: Optional[float] = None
    models: Optional[list] = None
    blocked: Optional[bool] = None
    budget_duration: Optional[str] = None
    guardrails: Optional[List[str]] = None
    """

    team_id: str  # required
    team_alias: Optional[str] = None
    organization_id: Optional[str] = None
    metadata: Optional[dict] = None
    tpm_limit: Optional[int] = None
    rpm_limit: Optional[int] = None
    max_budget: Optional[float] = None
    models: Optional[list] = None
    blocked: Optional[bool] = None
    budget_duration: Optional[str] = None
    tags: Optional[list] = None
    model_aliases: Optional[dict] = None
    guardrails: Optional[List[str]] = None


class ResetTeamBudgetRequest(LLMPydanticObjectBase):
    """
    internal type used to reset the budget on a team
    used by reset_budget()

    team_id: str
    spend: float
    budget_reset_at: datetime
    """

    team_id: str
    spend: float
    budget_reset_at: datetime
    updated_at: datetime


class DeleteTeamRequest(LLMPydanticObjectBase):
    team_ids: List[str]  # required


class BlockTeamRequest(LLMPydanticObjectBase):
    team_id: str  # required


class BlockKeyRequest(LLMPydanticObjectBase):
    key: str  # required


class AddTeamCallback(LLMPydanticObjectBase):
    callback_name: str
    callback_type: Optional[Literal["success", "failure", "success_and_failure"]] = (
        "success_and_failure"
    )
    callback_vars: Dict[str, str]

    @model_validator(mode="before")
    @classmethod
    def validate_callback_vars(cls, values):
        callback_vars = values.get("callback_vars", {})
        valid_keys = set(StandardCallbackDynamicParams.__annotations__.keys())
        for key, value in callback_vars.items():
            if key not in valid_keys:
                raise ValueError(
                    f"Invalid callback variable: {key}. Must be one of {valid_keys}"
                )
            if not isinstance(value, str):
                callback_vars[key] = str(value)
        return values


class TeamCallbackMetadata(LLMPydanticObjectBase):
    success_callback: Optional[List[str]] = []
    failure_callback: Optional[List[str]] = []
    callbacks: Optional[List[str]] = []
    # for now - only supported for langfuse
    callback_vars: Optional[Dict[str, str]] = {}

    @model_validator(mode="before")
    @classmethod
    def validate_callback_vars(cls, values):
        success_callback = values.get("success_callback", [])
        if success_callback is None:
            values.pop("success_callback", None)
        failure_callback = values.get("failure_callback", [])
        if failure_callback is None:
            values.pop("failure_callback", None)
        callbacks = values.get("callbacks", [])
        if callbacks is None:
            values.pop("callbacks", None)

        callback_vars = values.get("callback_vars", {})
        if callback_vars is None:
            values.pop("callback_vars", None)
        if all(val is None for val in values.values()):
            return {
                "success_callback": [],
                "failure_callback": [],
                "callbacks": [],
                "callback_vars": {},
            }
        valid_keys = set(StandardCallbackDynamicParams.__annotations__.keys())
        if callback_vars is not None:
            for key in callback_vars:
                if key not in valid_keys:
                    raise ValueError(
                        f"Invalid callback variable: {key}. Must be one of {valid_keys}"
                    )
        return values


class LLM_TeamTable(TeamBase):
    team_id: str  # type: ignore
    spend: Optional[float] = None
    max_parallel_requests: Optional[int] = None
    budget_duration: Optional[str] = None
    budget_reset_at: Optional[datetime] = None
    model_id: Optional[int] = None
    llm_model_table: Optional[LLM_ModelTable] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(protected_namespaces=())

    @model_validator(mode="before")
    @classmethod
    def set_model_info(cls, values):
        dict_fields = [
            "metadata",
            "aliases",
            "config",
            "permissions",
            "model_max_budget",
            "model_aliases",
        ]

        if isinstance(values, BaseModel):
            values = values.model_dump()

        if (
            isinstance(values.get("members_with_roles"), dict)
            and not values["members_with_roles"]
        ):
            values["members_with_roles"] = []

        for field in dict_fields:
            value = values.get(field)
            if value is not None and isinstance(value, str):
                try:
                    values[field] = json.loads(value)
                except json.JSONDecodeError:
                    raise ValueError(f"Field {field} should be a valid dictionary")

        return values


class LLM_TeamTableCachedObj(LLM_TeamTable):
    last_refreshed_at: Optional[float] = None


class TeamRequest(LLMPydanticObjectBase):
    teams: List[str]


class LLM_BudgetTable(LLMPydanticObjectBase):
    """Represents user-controllable params for a LLM_BudgetTable record"""

    soft_budget: Optional[float] = None
    max_budget: Optional[float] = None
    max_parallel_requests: Optional[int] = None
    tpm_limit: Optional[int] = None
    rpm_limit: Optional[int] = None
    model_max_budget: Optional[dict] = None
    budget_duration: Optional[str] = None

    model_config = ConfigDict(protected_namespaces=())


class LLM_TeamMemberTable(LLM_BudgetTable):
    """
    Used to track spend of a user_id within a team_id
    """

    spend: Optional[float] = None
    user_id: Optional[str] = None
    team_id: Optional[str] = None
    budget_id: Optional[str] = None

    model_config = ConfigDict(protected_namespaces=())


class NewOrganizationRequest(LLM_BudgetTable):
    organization_id: Optional[str] = None
    organization_alias: str
    models: List = []
    budget_id: Optional[str] = None
    metadata: Optional[dict] = None


class OrganizationRequest(LLMPydanticObjectBase):
    organizations: List[str]


class DeleteOrganizationRequest(LLMPydanticObjectBase):
    organization_ids: List[str]  # required


class KeyManagementSystem(enum.Enum):
    GOOGLE_KMS = "google_kms"
    AZURE_KEY_VAULT = "azure_key_vault"
    AWS_SECRET_MANAGER = "aws_secret_manager"
    GOOGLE_SECRET_MANAGER = "google_secret_manager"
    HASHICORP_VAULT = "hashicorp_vault"
    LOCAL = "local"
    AWS_KMS = "aws_kms"


class KeyManagementSettings(LLMPydanticObjectBase):
    hosted_keys: Optional[List] = None
    store_virtual_keys: Optional[bool] = False
    """
    If True, virtual keys created by llm will be stored in the secret manager
    """
    prefix_for_stored_virtual_keys: str = "llm/"
    """
    If set, this prefix will be used for stored virtual keys in the secret manager
    """

    access_mode: Literal["read_only", "write_only", "read_and_write"] = "read_only"
    """
    Access mode for the secret manager, when write_only will only use for writing secrets
    """

    primary_secret_name: Optional[str] = None
    """
    If set, will read secrets from this primary secret in the secret manager

    eg. on AWS you can store multiple secret values as K/V pairs in a single secret
    """


class TeamDefaultSettings(LLMPydanticObjectBase):
    team_id: str

    model_config = ConfigDict(
        extra="allow"
    )  # allow params not defined here, these fall in llm.completion(**kwargs)


class DynamoDBArgs(LLMPydanticObjectBase):
    billing_mode: Literal["PROVISIONED_THROUGHPUT", "PAY_PER_REQUEST"]
    read_capacity_units: Optional[int] = None
    write_capacity_units: Optional[int] = None
    ssl_verify: Optional[bool] = None
    region_name: str
    user_table_name: str = "LLM_UserTable"
    key_table_name: str = "LLM_VerificationToken"
    config_table_name: str = "LLM_Config"
    spend_table_name: str = "LLM_SpendLogs"
    aws_role_name: Optional[str] = None
    aws_session_name: Optional[str] = None
    aws_web_identity_token: Optional[str] = None
    aws_provider_id: Optional[str] = None
    aws_policy_arns: Optional[List[str]] = None
    aws_policy: Optional[str] = None
    aws_duration_seconds: Optional[int] = None
    assume_role_aws_role_name: Optional[str] = None
    assume_role_aws_session_name: Optional[str] = None


class PassThroughGenericEndpoint(LLMPydanticObjectBase):
    path: str = Field(description="The route to be added to the LLM Proxy Server.")
    target: str = Field(
        description="The URL to which requests for this path should be forwarded."
    )
    headers: dict = Field(
        description="Key-value pairs of headers to be forwarded with the request. You can set any key value pair here and it will be forwarded to your target endpoint"
    )


class PassThroughEndpointResponse(LLMPydanticObjectBase):
    endpoints: List[PassThroughGenericEndpoint]


class ConfigFieldUpdate(LLMPydanticObjectBase):
    field_name: str
    field_value: Any
    config_type: Literal["general_settings"]


class ConfigFieldDelete(LLMPydanticObjectBase):
    config_type: Literal["general_settings"]
    field_name: str


class FieldDetail(BaseModel):
    field_name: str
    field_type: str
    field_description: str
    field_default_value: Any = None
    stored_in_db: Optional[bool]


class ConfigList(LLMPydanticObjectBase):
    field_name: str
    field_type: str
    field_description: str
    field_value: Any
    stored_in_db: Optional[bool]
    field_default_value: Any
    premium_field: bool = False
    nested_fields: Optional[List[FieldDetail]] = (
        None  # For nested dictionary or Pydantic fields
    )


class ConfigGeneralSettings(LLMPydanticObjectBase):
    """
    Documents all the fields supported by `general_settings` in config.yaml
    """

    completion_model: Optional[str] = Field(
        None, description="proxy level default model for all chat completion calls"
    )
    key_management_system: Optional[KeyManagementSystem] = Field(
        None, description="key manager to load keys from / decrypt keys with"
    )
    use_google_kms: Optional[bool] = Field(
        None, description="decrypt keys with google kms"
    )
    use_azure_key_vault: Optional[bool] = Field(
        None, description="load keys from azure key vault"
    )
    master_key: Optional[str] = Field(
        None, description="require a key for all calls to proxy"
    )
    database_url: Optional[str] = Field(
        None,
        description="connect to a postgres db - needed for generating temporary keys + tracking spend / key",
    )
    database_connection_pool_limit: Optional[int] = Field(
        100,
        description="default connection pool for prisma client connecting to postgres db",
    )
    database_connection_timeout: Optional[float] = Field(
        60, description="default timeout for a connection to the database"
    )
    database_type: Optional[Literal["dynamo_db"]] = Field(
        None, description="to use dynamodb instead of postgres db"
    )
    database_args: Optional[DynamoDBArgs] = Field(
        None,
        description="custom args for instantiating dynamodb client - e.g. billing provision",
    )
    otel: Optional[bool] = Field(
        None,
        description="[BETA] OpenTelemetry support - this might change, use with caution.",
    )
    custom_auth: Optional[str] = Field(
        None,
        description="override user_api_key_auth with your own auth script - https://docs.llm.ai/docs/proxy/virtual_keys#custom-auth",
    )
    max_parallel_requests: Optional[int] = Field(
        None,
        description="maximum parallel requests for each api key",
    )
    global_max_parallel_requests: Optional[int] = Field(
        None, description="global max parallel requests to allow for a proxy instance."
    )
    max_request_size_mb: Optional[int] = Field(
        None,
        description="max request size in MB, if a request is larger than this size it will be rejected",
    )
    max_response_size_mb: Optional[int] = Field(
        None,
        description="max response size in MB, if a response is larger than this size it will be rejected",
    )
    infer_model_from_keys: Optional[bool] = Field(
        None,
        description="for `/models` endpoint, infers available model based on environment keys (e.g. OPENAI_API_KEY)",
    )
    background_health_checks: Optional[bool] = Field(
        None, description="run health checks in background"
    )
    health_check_interval: int = Field(
        300, description="background health check interval in seconds"
    )
    alerting: Optional[List] = Field(
        None,
        description="List of alerting integrations. Today, just slack - `alerting: ['slack']`",
    )
    alert_types: Optional[List[AlertType]] = Field(
        None,
        description="List of alerting types. By default it is all alerts",
    )
    alert_to_webhook_url: Optional[Dict] = Field(
        None,
        description="Mapping of alert type to webhook url. e.g. `alert_to_webhook_url: {'budget_alerts': 'https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX'}`",
    )
    alerting_args: Optional[Dict] = Field(
        None, description="Controllable params for slack alerting - e.g. ttl in cache."
    )
    alerting_threshold: Optional[int] = Field(
        None,
        description="sends alerts if requests hang for 5min+",
    )
    ui_access_mode: Optional[Literal["admin_only", "all"]] = Field(
        "all", description="Control access to the Proxy UI"
    )
    allowed_routes: Optional[List] = Field(
        None, description="Proxy API Endpoints you want users to be able to access"
    )
    enable_public_model_hub: bool = Field(
        default=False,
        description="Public model hub for users to see what models they have access to, supported openai params, etc.",
    )
    pass_through_endpoints: Optional[List[PassThroughGenericEndpoint]] = Field(
        default=None,
        description="Set-up pass-through endpoints for provider-specific endpoints. Docs - https://docs.llm.ai/docs/proxy/pass_through",
    )


class ConfigYAML(LLMPydanticObjectBase):
    """
    Documents all the fields supported by the config.yaml
    """

    environment_variables: Optional[dict] = Field(
        None,
        description="Object to pass in additional environment variables via POST request",
    )
    model_list: Optional[List[ModelParams]] = Field(
        None,
        description="List of supported models on the server, with model-specific configs",
    )
    llm_settings: Optional[dict] = Field(
        None,
        description="llm Module settings. See __init__.py for all, example llm.drop_params=True, llm.set_verbose=True, llm.api_base, llm.cache",
    )
    general_settings: Optional[ConfigGeneralSettings] = None
    router_settings: Optional[UpdateRouterConfig] = Field(
        None,
        description="llm router object settings. See router.py __init__ for all, example router.num_retries=5, router.timeout=5, router.max_retries=5, router.retry_after=5",
    )

    model_config = ConfigDict(protected_namespaces=())


class LLM_VerificationToken(LLMPydanticObjectBase):
    token: Optional[str] = None
    key_name: Optional[str] = None
    key_alias: Optional[str] = None
    spend: float = 0.0
    max_budget: Optional[float] = None
    expires: Optional[Union[str, datetime]] = None
    models: List = []
    aliases: Dict = {}
    config: Dict = {}
    user_id: Optional[str] = None
    team_id: Optional[str] = None
    max_parallel_requests: Optional[int] = None
    metadata: Dict = {}
    tpm_limit: Optional[int] = None
    rpm_limit: Optional[int] = None
    budget_duration: Optional[str] = None
    budget_reset_at: Optional[datetime] = None
    allowed_cache_controls: Optional[list] = []
    permissions: Dict = {}
    model_spend: Dict = {}
    model_max_budget: Dict = {}
    soft_budget_cooldown: bool = False
    blocked: Optional[bool] = None
    llm_budget_table: Optional[dict] = None
    org_id: Optional[str] = None  # org id for a given key
    created_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None

    model_config = ConfigDict(protected_namespaces=())


class LLM_VerificationTokenView(LLM_VerificationToken):
    """
    Combined view of llm verification token + llm team table (select values)
    """

    team_spend: Optional[float] = None
    team_alias: Optional[str] = None
    team_tpm_limit: Optional[int] = None
    team_rpm_limit: Optional[int] = None
    team_max_budget: Optional[float] = None
    team_models: List = []
    team_blocked: bool = False
    soft_budget: Optional[float] = None
    team_model_aliases: Optional[Dict] = None
    team_member_spend: Optional[float] = None
    team_member: Optional[Member] = None
    team_metadata: Optional[Dict] = None

    # End User Params
    end_user_id: Optional[str] = None
    end_user_tpm_limit: Optional[int] = None
    end_user_rpm_limit: Optional[int] = None
    end_user_max_budget: Optional[float] = None

    # Time stamps
    last_refreshed_at: Optional[float] = None  # last time joint view was pulled from db

    def __init__(self, **kwargs):
        # Handle llm_budget_table_* keys
        for key, value in list(kwargs.items()):
            if key.startswith("llm_budget_table_") and value is not None:
                # Extract the corresponding attribute name
                attr_name = key.replace("llm_budget_table_", "")
                # Check if the value is None and set the corresponding attribute
                if getattr(self, attr_name, None) is None:
                    kwargs[attr_name] = value
            if key == "end_user_id" and value is not None and isinstance(value, int):
                kwargs[key] = str(value)
        # Initialize the superclass
        super().__init__(**kwargs)


class UserAPIKeyAuth(
    LLM_VerificationTokenView
):  # the expected response object for user api key auth
    """
    Return the row in the db
    """

    api_key: Optional[str] = None
    user_role: Optional[LLMUserRoles] = None
    allowed_model_region: Optional[AllowedModelRegion] = None
    parent_otel_span: Optional[Span] = None
    rpm_limit_per_model: Optional[Dict[str, int]] = None
    tpm_limit_per_model: Optional[Dict[str, int]] = None
    user_tpm_limit: Optional[int] = None
    user_rpm_limit: Optional[int] = None
    user_email: Optional[str] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @model_validator(mode="before")
    @classmethod
    def check_api_key(cls, values):
        if values.get("api_key") is not None:
            values.update({"token": hash_token(values.get("api_key"))})
            if isinstance(values.get("api_key"), str) and values.get(
                "api_key"
            ).startswith("sk-"):
                values.update({"api_key": hash_token(values.get("api_key"))})
        return values


class UserInfoResponse(LLMPydanticObjectBase):
    user_id: Optional[str]
    user_info: Optional[Union[dict, BaseModel]]
    keys: List
    teams: List


class LLM_Config(LLMPydanticObjectBase):
    param_name: str
    param_value: Dict


class LLM_OrganizationMembershipTable(LLMPydanticObjectBase):
    """
    This is the table that track what organizations a user belongs to and users spend within the organization
    """

    user_id: str
    organization_id: str
    user_role: Optional[str] = None
    spend: float = 0.0
    budget_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    user: Optional[Any] = (
        None  # You might want to replace 'Any' with a more specific type if available
    )
    llm_budget_table: Optional[LLM_BudgetTable] = None

    model_config = ConfigDict(protected_namespaces=())


class LLM_OrganizationTable(LLMPydanticObjectBase):
    """Represents user-controllable params for a LLM_OrganizationTable record"""

    organization_id: Optional[str] = None
    organization_alias: Optional[str] = None
    budget_id: str
    spend: float = 0.0
    metadata: Optional[dict] = None
    models: List[str]
    created_by: str
    updated_by: str


class LLM_OrganizationTableUpdate(LLMPydanticObjectBase):
    """Represents user-controllable params for a LLM_OrganizationTable record"""

    organization_id: Optional[str] = None
    organization_alias: Optional[str] = None
    budget_id: Optional[str] = None
    spend: Optional[float] = None
    metadata: Optional[dict] = None
    models: Optional[List[str]] = None
    updated_by: Optional[str] = None


class LLM_OrganizationTableWithMembers(LLM_OrganizationTable):
    """Returned by the /organization/info endpoint and /organization/list endpoint"""

    members: List[LLM_OrganizationMembershipTable] = []
    teams: List[LLM_TeamTable] = []
    llm_budget_table: Optional[LLM_BudgetTable] = None
    created_at: datetime
    updated_at: datetime


class NewOrganizationResponse(LLM_OrganizationTable):
    organization_id: str  # type: ignore
    created_at: datetime
    updated_at: datetime


class LLM_UserTable(LLMPydanticObjectBase):
    user_id: str
    max_budget: Optional[float] = None
    spend: float = 0.0
    model_max_budget: Optional[Dict] = {}
    model_spend: Optional[Dict] = {}
    user_email: Optional[str] = None
    models: list = []
    tpm_limit: Optional[int] = None
    rpm_limit: Optional[int] = None
    user_role: Optional[str] = None
    organization_memberships: Optional[List[LLM_OrganizationMembershipTable]] = None
    teams: List[str] = []
    sso_user_id: Optional[str] = None
    budget_duration: Optional[str] = None
    budget_reset_at: Optional[datetime] = None
    metadata: Optional[dict] = None

    @model_validator(mode="before")
    @classmethod
    def set_model_info(cls, values):
        if values.get("spend") is None:
            values.update({"spend": 0.0})
        if values.get("models") is None:
            values.update({"models": []})
        if values.get("teams") is None:
            values.update({"teams": []})
        return values

    model_config = ConfigDict(protected_namespaces=())


class LLM_UserTableFiltered(BaseModel):  # done to avoid exposing sensitive data
    user_id: str
    user_email: Optional[str] = None


class LLM_UserTableWithKeyCount(LLM_UserTable):
    key_count: int = 0


class LLM_EndUserTable(LLMPydanticObjectBase):
    user_id: str
    blocked: bool
    alias: Optional[str] = None
    spend: float = 0.0
    allowed_model_region: Optional[AllowedModelRegion] = None
    default_model: Optional[str] = None
    llm_budget_table: Optional[LLM_BudgetTable] = None

    @model_validator(mode="before")
    @classmethod
    def set_model_info(cls, values):
        if values.get("spend") is None:
            values.update({"spend": 0.0})
        return values

    model_config = ConfigDict(protected_namespaces=())


class LLM_SpendLogs(LLMPydanticObjectBase):
    request_id: str
    api_key: str
    model: Optional[str] = ""
    api_base: Optional[str] = ""
    call_type: str
    spend: Optional[float] = 0.0
    total_tokens: Optional[int] = 0
    prompt_tokens: Optional[int] = 0
    completion_tokens: Optional[int] = 0
    startTime: Union[str, datetime, None]
    endTime: Union[str, datetime, None]
    user: Optional[str] = ""
    metadata: Optional[Json] = {}
    cache_hit: Optional[str] = "False"
    cache_key: Optional[str] = None
    request_tags: Optional[Json] = None
    requester_ip_address: Optional[str] = None
    messages: Optional[Union[str, list, dict]]
    response: Optional[Union[str, list, dict]]


class LLM_ErrorLogs(LLMPydanticObjectBase):
    request_id: Optional[str] = str(uuid.uuid4())
    api_base: Optional[str] = ""
    model_group: Optional[str] = ""
    llm_model_name: Optional[str] = ""
    model_id: Optional[str] = ""
    request_kwargs: Optional[dict] = {}
    exception_type: Optional[str] = ""
    status_code: Optional[str] = ""
    exception_string: Optional[str] = ""
    startTime: Union[str, datetime, None]
    endTime: Union[str, datetime, None]


AUDIT_ACTIONS = Literal["created", "updated", "deleted", "blocked"]


class LLM_AuditLogs(LLMPydanticObjectBase):
    id: str
    updated_at: datetime
    changed_by: Optional[Any] = None
    changed_by_api_key: Optional[str] = None
    action: AUDIT_ACTIONS
    table_name: LLMTableNames
    object_id: str
    before_value: Optional[Json] = None
    updated_values: Optional[Json] = None

    @model_validator(mode="before")
    @classmethod
    def cast_changed_by_to_str(cls, values):
        if values.get("changed_by") is not None:
            values["changed_by"] = str(values["changed_by"])
        return values


class LLM_SpendLogs_ResponseObject(LLMPydanticObjectBase):
    response: Optional[List[Union[LLM_SpendLogs, Any]]] = None


class TokenCountRequest(LLMPydanticObjectBase):
    model: str
    prompt: Optional[str] = None
    messages: Optional[List[dict]] = None


class TokenCountResponse(LLMPydanticObjectBase):
    total_tokens: int
    request_model: str
    model_used: str
    tokenizer_type: str


class CallInfo(LLMPydanticObjectBase):
    """Used for slack budget alerting"""

    spend: float
    max_budget: Optional[float] = None
    soft_budget: Optional[float] = None
    token: Optional[str] = Field(default=None, description="Hashed value of that key")
    customer_id: Optional[str] = None
    user_id: Optional[str] = None
    team_id: Optional[str] = None
    team_alias: Optional[str] = None
    user_email: Optional[str] = None
    key_alias: Optional[str] = None
    projected_exceeded_date: Optional[str] = None
    projected_spend: Optional[float] = None


class WebhookEvent(CallInfo):
    event: Literal[
        "budget_crossed",
        "soft_budget_crossed",
        "threshold_crossed",
        "projected_limit_exceeded",
        "key_created",
        "internal_user_created",
        "spend_tracked",
    ]
    event_group: Literal["internal_user", "key", "team", "proxy", "customer"]
    event_message: str  # human-readable description of event


class SpecialModelNames(enum.Enum):
    all_team_models = "all-team-models"
    all_proxy_models = "all-proxy-models"
    no_default_models = "no-default-models"


class InvitationNew(LLMPydanticObjectBase):
    user_id: str


class InvitationUpdate(LLMPydanticObjectBase):
    invitation_id: str
    is_accepted: bool


class InvitationDelete(LLMPydanticObjectBase):
    invitation_id: str


class InvitationModel(LLMPydanticObjectBase):
    id: str
    user_id: str
    is_accepted: bool
    accepted_at: Optional[datetime]
    expires_at: datetime
    created_at: datetime
    created_by: str
    updated_at: datetime
    updated_by: str


class InvitationClaim(LLMPydanticObjectBase):
    invitation_link: str
    user_id: str
    password: str


class ConfigFieldInfo(LLMPydanticObjectBase):
    field_name: str
    field_value: Any


class CallbackOnUI(LLMPydanticObjectBase):
    llm_callback_name: str
    llm_callback_params: Optional[list]
    ui_callback_name: str


class AllCallbacks(LLMPydanticObjectBase):
    langfuse: CallbackOnUI = CallbackOnUI(
        llm_callback_name="langfuse",
        ui_callback_name="Langfuse",
        llm_callback_params=[
            "LANGFUSE_PUBLIC_KEY",
            "LANGFUSE_SECRET_KEY",
        ],
    )

    otel: CallbackOnUI = CallbackOnUI(
        llm_callback_name="otel",
        ui_callback_name="OpenTelemetry",
        llm_callback_params=[
            "OTEL_EXPORTER",
            "OTEL_ENDPOINT",
            "OTEL_HEADERS",
        ],
    )

    s3: CallbackOnUI = CallbackOnUI(
        llm_callback_name="s3",
        ui_callback_name="s3 Bucket (AWS)",
        llm_callback_params=[
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY",
            "AWS_REGION_NAME",
        ],
    )

    openmeter: CallbackOnUI = CallbackOnUI(
        llm_callback_name="openmeter",
        ui_callback_name="OpenMeter",
        llm_callback_params=[
            "OPENMETER_API_ENDPOINT",
            "OPENMETER_API_KEY",
        ],
    )

    custom_callback_api: CallbackOnUI = CallbackOnUI(
        llm_callback_name="custom_callback_api",
        llm_callback_params=["GENERIC_LOGGER_ENDPOINT"],
        ui_callback_name="Custom Callback API",
    )

    datadog: CallbackOnUI = CallbackOnUI(
        llm_callback_name="datadog",
        llm_callback_params=["DD_API_KEY", "DD_SITE"],
        ui_callback_name="Datadog",
    )

    braintrust: CallbackOnUI = CallbackOnUI(
        llm_callback_name="braintrust",
        llm_callback_params=["BRAINTRUST_API_KEY"],
        ui_callback_name="Braintrust",
    )

    langsmith: CallbackOnUI = CallbackOnUI(
        llm_callback_name="langsmith",
        llm_callback_params=[
            "LANGSMITH_API_KEY",
            "LANGSMITH_PROJECT",
            "LANGSMITH_DEFAULT_RUN_NAME",
        ],
        ui_callback_name="Langsmith",
    )

    lago: CallbackOnUI = CallbackOnUI(
        llm_callback_name="lago",
        llm_callback_params=[
            "LAGO_API_BASE",
            "LAGO_API_KEY",
            "LAGO_API_EVENT_CODE",
            "LAGO_API_CHARGE_BY",
        ],
        ui_callback_name="Lago Billing",
    )


class SpendLogsMetadata(TypedDict):
    """
    Specific metadata k,v pairs logged to spendlogs for easier cost tracking
    """

    additional_usage_values: Optional[
        dict
    ]  # covers provider-specific usage information - e.g. prompt caching
    user_api_key: Optional[str]
    user_api_key_alias: Optional[str]
    user_api_key_team_id: Optional[str]
    user_api_key_org_id: Optional[str]
    user_api_key_user_id: Optional[str]
    user_api_key_team_alias: Optional[str]
    spend_logs_metadata: Optional[
        dict
    ]  # special param to log k,v pairs to spendlogs for a call
    requester_ip_address: Optional[str]
    applied_guardrails: Optional[List[str]]
    status: StandardLoggingPayloadStatus
    proxy_server_request: Optional[str]
    batch_models: Optional[List[str]]
    error_information: Optional[StandardLoggingPayloadErrorInformation]


class SpendLogsPayload(TypedDict):
    request_id: str
    call_type: str
    api_key: str
    spend: float
    total_tokens: int
    prompt_tokens: int
    completion_tokens: int
    startTime: Union[datetime, str]
    endTime: Union[datetime, str]
    completionStartTime: Optional[Union[datetime, str]]
    model: str
    model_id: Optional[str]
    model_group: Optional[str]
    api_base: str
    user: str
    metadata: str  # json str
    cache_hit: str
    cache_key: str
    request_tags: str  # json str
    team_id: Optional[str]
    end_user: Optional[str]
    requester_ip_address: Optional[str]
    custom_llm_provider: Optional[str]
    messages: Optional[Union[str, list, dict]]
    response: Optional[Union[str, list, dict]]


class SpanAttributes(str, enum.Enum):
    # Note: We've taken this from opentelemetry-semantic-conventions-ai
    # I chose to not add a new dependency to llm for this

    # Semantic Conventions for LLM requests, this needs to be removed after
    # OpenTelemetry Semantic Conventions support Gen AI.
    # Issue at https://github.com/open-telemetry/opentelemetry-python/issues/3868
    # Refer to https://github.com/open-telemetry/semantic-conventions/blob/main/docs/gen-ai/llm-spans.md

    LLM_SYSTEM = "gen_ai.system"
    LLM_REQUEST_MODEL = "gen_ai.request.model"
    LLM_REQUEST_MAX_TOKENS = "gen_ai.request.max_tokens"
    LLM_REQUEST_TEMPERATURE = "gen_ai.request.temperature"
    LLM_REQUEST_TOP_P = "gen_ai.request.top_p"
    LLM_PROMPTS = "gen_ai.prompt"
    LLM_COMPLETIONS = "gen_ai.completion"
    LLM_RESPONSE_MODEL = "gen_ai.response.model"
    LLM_USAGE_COMPLETION_TOKENS = "gen_ai.usage.completion_tokens"
    LLM_USAGE_PROMPT_TOKENS = "gen_ai.usage.prompt_tokens"
    LLM_TOKEN_TYPE = "gen_ai.token.type"
    # To be added
    # LLM_RESPONSE_FINISH_REASON = "gen_ai.response.finish_reasons"
    # LLM_RESPONSE_ID = "gen_ai.response.id"

    # LLM
    LLM_REQUEST_TYPE = "llm.request.type"
    LLM_USAGE_TOTAL_TOKENS = "llm.usage.total_tokens"
    LLM_USAGE_TOKEN_TYPE = "llm.usage.token_type"
    LLM_USER = "llm.user"
    LLM_HEADERS = "llm.headers"
    LLM_TOP_K = "llm.top_k"
    LLM_IS_STREAMING = "llm.is_streaming"
    LLM_FREQUENCY_PENALTY = "llm.frequency_penalty"
    LLM_PRESENCE_PENALTY = "llm.presence_penalty"
    LLM_CHAT_STOP_SEQUENCES = "llm.chat.stop_sequences"
    LLM_REQUEST_FUNCTIONS = "llm.request.functions"
    LLM_REQUEST_REPETITION_PENALTY = "llm.request.repetition_penalty"
    LLM_RESPONSE_FINISH_REASON = "llm.response.finish_reason"
    LLM_RESPONSE_STOP_REASON = "llm.response.stop_reason"
    LLM_CONTENT_COMPLETION_CHUNK = "llm.content.completion.chunk"

    # OpenAI
    LLM_OPENAI_RESPONSE_SYSTEM_FINGERPRINT = "gen_ai.openai.system_fingerprint"
    LLM_OPENAI_API_BASE = "gen_ai.openai.api_base"
    LLM_OPENAI_API_VERSION = "gen_ai.openai.api_version"
    LLM_OPENAI_API_TYPE = "gen_ai.openai.api_type"


class ManagementEndpointLoggingPayload(LLMPydanticObjectBase):
    route: str
    request_data: dict
    response: Optional[dict] = None
    exception: Optional[Any] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class ProxyException(Exception):
    # NOTE: DO NOT MODIFY THIS
    # This is used to map exactly to OPENAI Exceptions
    def __init__(
        self,
        message: str,
        type: str,
        param: Optional[str],
        code: Optional[Union[int, str]] = None,  # maps to status code
        headers: Optional[Dict[str, str]] = None,
        openai_code: Optional[str] = None,  # maps to 'code'  in openai
    ):
        self.message = str(message)
        self.type = type
        self.param = param
        self.openai_code = openai_code or code
        # If we look on official python OpenAI lib, the code should be a string:
        # https://github.com/openai/openai-python/blob/195c05a64d39c87b2dfdf1eca2d339597f1fce03/src/openai/types/shared/error_object.py#L11
        # Related LLM issue: https://github.com/BerriAI/llm/discussions/4834
        self.code = str(code)
        if headers is not None:
            for k, v in headers.items():
                if not isinstance(v, str):
                    headers[k] = str(v)
        self.headers = headers or {}

        # rules for proxyExceptions
        # Llm router.py returns "No healthy deployment available" when there are no deployments available
        # Should map to 429 errors https://github.com/BerriAI/llm/issues/2487
        if (
            "No healthy deployment available" in self.message
            or "No deployments available" in self.message
        ):
            self.code = "429"
        elif RouterErrors.no_deployments_with_tag_routing.value in self.message:
            self.code = "401"

    def to_dict(self) -> dict:
        """Converts the ProxyException instance to a dictionary."""
        return {
            "message": self.message,
            "type": self.type,
            "param": self.param,
            "code": self.code,
        }


class CommonProxyErrors(str, enum.Enum):
    db_not_connected_error = (
        "DB not connected. See https://docs.llm.ai/docs/proxy/virtual_keys"
    )
    no_llm_router = "No models configured on proxy"
    not_allowed_access = "Admin-only endpoint. Not allowed to access this."
    not_premium_user = "You must be a LLM Enterprise user to use this feature. If you have a license please set `LLM_LICENSE` in your env. Get a 7 day trial key here: https://www.llm.ai/#trial. \nPricing: https://www.llm.ai/#pricing"
    max_parallel_request_limit_reached = (
        "Crossed TPM / RPM / Max Parallel Request Limit"
    )


class SpendCalculateRequest(LLMPydanticObjectBase):
    model: Optional[str] = None
    messages: Optional[List] = None
    completion_response: Optional[dict] = None


class ProxyErrorTypes(str, enum.Enum):
    budget_exceeded = "budget_exceeded"
    key_model_access_denied = "key_model_access_denied"
    team_model_access_denied = "team_model_access_denied"
    user_model_access_denied = "user_model_access_denied"
    expired_key = "expired_key"
    auth_error = "auth_error"
    internal_server_error = "internal_server_error"
    bad_request_error = "bad_request_error"
    not_found_error = "not_found_error"
    validation_error = "bad_request_error"
    cache_ping_error = "cache_ping_error"

    @classmethod
    def get_model_access_error_type_for_object(
        cls, object_type: Literal["key", "user", "team"]
    ) -> "ProxyErrorTypes":
        """
        Get the model access error type for object_type
        """
        if object_type == "key":
            return cls.key_model_access_denied
        elif object_type == "team":
            return cls.team_model_access_denied
        elif object_type == "user":
            return cls.user_model_access_denied


DB_CONNECTION_ERROR_TYPES = (httpx.ConnectError, httpx.ReadError, httpx.ReadTimeout)


class SSOUserDefinedValues(TypedDict):
    models: List[str]
    user_id: str
    user_email: Optional[str]
    user_role: Optional[str]
    max_budget: Optional[float]
    budget_duration: Optional[str]


class VirtualKeyEvent(LLMPydanticObjectBase):
    created_by_user_id: str
    created_by_user_role: str
    created_by_key_alias: Optional[str]
    request_kwargs: dict


class CreatePassThroughEndpoint(LLMPydanticObjectBase):
    path: str
    target: str
    headers: dict


class LLM_TeamMembership(LLMPydanticObjectBase):
    user_id: str
    team_id: str
    budget_id: str
    llm_budget_table: Optional[LLM_BudgetTable]


#### Organization / Team Member Requests ####


class MemberAddRequest(LLMPydanticObjectBase):
    member: Union[List[Member], Member]

    def __init__(self, **data):
        member_data = data.get("member")
        if isinstance(member_data, list):
            # If member is a list of dictionaries, convert each dictionary to a Member object
            members = [Member(**item) for item in member_data]
            # Replace member_data with the list of Member objects
            data["member"] = members
        elif isinstance(member_data, dict):
            # If member is a dictionary, convert it to a single Member object
            member = Member(**member_data)
            # Replace member_data with the single Member object
            data["member"] = member
        # Call the superclass __init__ method to initialize the object
        super().__init__(**data)


class OrgMemberAddRequest(LLMPydanticObjectBase):
    member: Union[List[OrgMember], OrgMember]

    def __init__(self, **data):
        member_data = data.get("member")
        if isinstance(member_data, list):
            # If member is a list of dictionaries, convert each dictionary to a Member object
            members = [OrgMember(**item) for item in member_data]
            # Replace member_data with the list of Member objects
            data["member"] = members
        elif isinstance(member_data, dict):
            # If member is a dictionary, convert it to a single Member object
            member = OrgMember(**member_data)
            # Replace member_data with the single Member object
            data["member"] = member
        # Call the superclass __init__ method to initialize the object
        super().__init__(**data)


class TeamAddMemberResponse(LLM_TeamTable):
    updated_users: List[LLM_UserTable]
    updated_team_memberships: List[LLM_TeamMembership]


class OrganizationAddMemberResponse(LLMPydanticObjectBase):
    organization_id: str
    updated_users: List[LLM_UserTable]
    updated_organization_memberships: List[LLM_OrganizationMembershipTable]


class MemberDeleteRequest(LLMPydanticObjectBase):
    user_id: Optional[str] = None
    user_email: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def check_user_info(cls, values):
        if values.get("user_id") is None and values.get("user_email") is None:
            raise ValueError("Either user id or user email must be provided")
        return values


class MemberUpdateResponse(LLMPydanticObjectBase):
    user_id: str
    user_email: Optional[str] = None


# Team Member Requests
class TeamMemberAddRequest(MemberAddRequest):
    team_id: str
    max_budget_in_team: Optional[float] = None  # Users max budget within the team


class TeamMemberDeleteRequest(MemberDeleteRequest):
    team_id: str


class TeamMemberUpdateRequest(TeamMemberDeleteRequest):
    max_budget_in_team: Optional[float] = None
    role: Optional[Literal["admin", "user"]] = None


class TeamMemberUpdateResponse(MemberUpdateResponse):
    team_id: str
    max_budget_in_team: Optional[float] = None


class TeamModelAddRequest(BaseModel):
    """Request to add models to a team"""

    team_id: str
    models: List[str]


class TeamModelDeleteRequest(BaseModel):
    """Request to delete models from a team"""

    team_id: str
    models: List[str]


# Organization Member Requests
class OrganizationMemberAddRequest(OrgMemberAddRequest):
    organization_id: str
    max_budget_in_organization: Optional[float] = (
        None  # Users max budget within the organization
    )


class OrganizationMemberDeleteRequest(MemberDeleteRequest):
    organization_id: str


ROLES_WITHIN_ORG = [
    LLMUserRoles.ORG_ADMIN,
    LLMUserRoles.INTERNAL_USER,
    LLMUserRoles.INTERNAL_USER_VIEW_ONLY,
]


class OrganizationMemberUpdateRequest(OrganizationMemberDeleteRequest):
    max_budget_in_organization: Optional[float] = None
    role: Optional[LLMUserRoles] = None

    @field_validator("role")
    def validate_role(
        cls, value: Optional[LLMUserRoles]
    ) -> Optional[LLMUserRoles]:
        if value is not None and value not in ROLES_WITHIN_ORG:
            raise ValueError(
                f"Invalid role. Must be one of: {[role.value for role in ROLES_WITHIN_ORG]}"
            )
        return value


class OrganizationMemberUpdateResponse(MemberUpdateResponse):
    organization_id: str
    max_budget_in_organization: float


##########################################


class TeamInfoResponseObject(TypedDict):
    team_id: str
    team_info: LLM_TeamTable
    keys: List
    team_memberships: List[LLM_TeamMembership]


class TeamListResponseObject(LLM_TeamTable):
    team_memberships: List[LLM_TeamMembership]
    keys: List  # list of keys that belong to the team


class KeyListResponseObject(TypedDict, total=False):
    keys: List[Union[str, UserAPIKeyAuth]]
    total_count: Optional[int]
    current_page: Optional[int]
    total_pages: Optional[int]


class CurrentItemRateLimit(TypedDict):
    current_requests: int
    current_tpm: int
    current_rpm: int


class LoggingCallbackStatus(TypedDict, total=False):
    callbacks: List[str]
    status: Literal["healthy", "unhealthy"]
    details: Optional[str]


class KeyHealthResponse(TypedDict, total=False):
    key: Literal["healthy", "unhealthy"]
    logging_callbacks: Optional[LoggingCallbackStatus]


class SpecialHeaders(enum.Enum):
    """Used by user_api_key_auth.py to get llm key"""

    openai_authorization = "Authorization"
    azure_authorization = "API-Key"
    anthropic_authorization = "x-api-key"
    google_ai_studio_authorization = "x-goog-api-key"
    azure_apim_authorization = "Ocp-Apim-Subscription-Key"


class LlmDataForBackendLLMCall(TypedDict, total=False):
    headers: dict
    organization: str
    timeout: Optional[float]


class JWTKeyItem(TypedDict, total=False):
    kid: str


JWKKeyValue = Union[List[JWTKeyItem], JWTKeyItem]


class JWKUrlResponse(TypedDict, total=False):
    keys: JWKKeyValue


class UserManagementEndpointParamDocStringEnums(str, enum.Enum):
    user_id_doc_str = (
        "Optional[str] - Specify a user id. If not set, a unique id will be generated."
    )
    user_alias_doc_str = (
        "Optional[str] - A descriptive name for you to know who this user id refers to."
    )
    teams_doc_str = "Optional[list] - specify a list of team id's a user belongs to."
    user_email_doc_str = "Optional[str] - Specify a user email."
    send_invite_email_doc_str = (
        "Optional[bool] - Specify if an invite email should be sent."
    )
    user_role_doc_str = """Optional[str] - Specify a user role - "proxy_admin", "proxy_admin_viewer", "internal_user", "internal_user_viewer", "team", "customer". Info about each role here: `https://github.com/BerriAI/llm/llm/proxy/_types.py#L20`"""
    max_budget_doc_str = """Optional[float] - Specify max budget for a given user."""
    budget_duration_doc_str = """Optional[str] - Budget is reset at the end of specified duration. If not set, budget is never reset. You can set duration as seconds ("30s"), minutes ("30m"), hours ("30h"), days ("30d"), months ("1mo")."""
    models_doc_str = """Optional[list] - Model_name's a user is allowed to call. (if empty, key is allowed to call all models)"""
    tpm_limit_doc_str = (
        """Optional[int] - Specify tpm limit for a given user (Tokens per minute)"""
    )
    rpm_limit_doc_str = (
        """Optional[int] - Specify rpm limit for a given user (Requests per minute)"""
    )
    auto_create_key_doc_str = """bool - Default=True. Flag used for returning a key as part of the /user/new response"""
    aliases_doc_str = """Optional[dict] - Model aliases for the user - [Docs](https://llm.vercel.app/docs/proxy/virtual_keys#model-aliases)"""
    config_doc_str = """Optional[dict] - [DEPRECATED PARAM] User-specific config."""
    allowed_cache_controls_doc_str = """Optional[list] - List of allowed cache control values. Example - ["no-cache", "no-store"]. See all values - https://docs.llm.ai/docs/proxy/caching#turn-on--off-caching-per-request-"""
    blocked_doc_str = (
        """Optional[bool] - [Not Implemented Yet] Whether the user is blocked."""
    )
    guardrails_doc_str = """Optional[List[str]] - [Not Implemented Yet] List of active guardrails for the user"""
    permissions_doc_str = """Optional[dict] - [Not Implemented Yet] User-specific permissions, eg. turning off pii masking."""
    metadata_doc_str = """Optional[dict] - Metadata for user, store information for user. Example metadata = {"team": "core-infra", "app": "app2", "email": "ishaan@berri.ai" }"""
    max_parallel_requests_doc_str = """Optional[int] - Rate limit a user based on the number of parallel requests. Raises 429 error, if user's parallel requests > x."""
    soft_budget_doc_str = """Optional[float] - Get alerts when user crosses given budget, doesn't block requests."""
    model_max_budget_doc_str = """Optional[dict] - Model-specific max budget for user. [Docs](https://docs.llm.ai/docs/proxy/users#add-model-specific-budgets-to-keys)"""
    model_rpm_limit_doc_str = """Optional[float] - Model-specific rpm limit for user. [Docs](https://docs.llm.ai/docs/proxy/users#add-model-specific-limits-to-keys)"""
    model_tpm_limit_doc_str = """Optional[float] - Model-specific tpm limit for user. [Docs](https://docs.llm.ai/docs/proxy/users#add-model-specific-limits-to-keys)"""
    spend_doc_str = """Optional[float] - Amount spent by user. Default is 0. Will be updated by proxy whenever user is used."""
    team_id_doc_str = """Optional[str] - [DEPRECATED PARAM] The team id of the user. Default is None."""
    duration_doc_str = """Optional[str] - Duration for the key auto-created on `/user/new`. Default is None."""


PassThroughEndpointLoggingResultValues = Union[
    ModelResponse,
    TextCompletionResponse,
    ImageResponse,
    EmbeddingResponse,
    StandardPassThroughResponseObject,
]


class PassThroughEndpointLoggingTypedDict(TypedDict):
    result: Optional[PassThroughEndpointLoggingResultValues]
    kwargs: dict


LLM_ManagementEndpoint_MetadataFields = [
    "model_rpm_limit",
    "model_tpm_limit",
    "guardrails",
    "tags",
    "enforced_params",
    "temp_budget_increase",
    "temp_budget_expiry",
]

LLM_ManagementEndpoint_MetadataFields_Premium = [
    "guardrails",
    "tags",
]


class ProviderBudgetResponseObject(LLMPydanticObjectBase):
    """
    Configuration for a single provider's budget settings
    """

    budget_limit: Optional[float]  # Budget limit in USD for the time period
    time_period: Optional[str]  # Time period for budget (e.g., '1d', '30d', '1mo')
    spend: Optional[float] = 0.0  # Current spend for this provider
    budget_reset_at: Optional[str] = None  # When the current budget period resets


class ProviderBudgetResponse(LLMPydanticObjectBase):
    """
    Complete provider budget configuration and status.
    Maps provider names to their budget configs.
    """

    providers: Dict[str, ProviderBudgetResponseObject] = (
        {}
    )  # Dictionary mapping provider names to their budget configurations


class ProxyStateVariables(TypedDict):
    """
    TypedDict for Proxy state variables.
    """

    spend_logs_row_count: int


UI_TEAM_ID = "llm-dashboard"


class JWTAuthBuilderResult(TypedDict):
    is_proxy_admin: bool
    team_object: Optional[LLM_TeamTable]
    user_object: Optional[LLM_UserTable]
    end_user_object: Optional[LLM_EndUserTable]
    org_object: Optional[LLM_OrganizationTable]
    token: str
    team_id: Optional[str]
    user_id: Optional[str]
    end_user_id: Optional[str]
    org_id: Optional[str]


class ClientSideFallbackModel(TypedDict, total=False):
    """
    Dictionary passed when client configuring input
    """

    model: Required[str]
    messages: List[AllMessageValues]


ALL_FALLBACK_MODEL_VALUES = Union[str, ClientSideFallbackModel]


RBAC_ROLES = Literal[
    LLMUserRoles.PROXY_ADMIN,
    LLMUserRoles.TEAM,
    LLMUserRoles.INTERNAL_USER,
]


class OIDCPermissions(LLMPydanticObjectBase):
    models: Optional[List[str]] = None
    routes: Optional[List[str]] = None


class RoleBasedPermissions(OIDCPermissions):
    role: RBAC_ROLES

    model_config = {
        "extra": "forbid",
    }


class RoleMapping(BaseModel):
    role: str
    internal_role: RBAC_ROLES


class ScopeMapping(OIDCPermissions):
    scope: str

    model_config = {
        "extra": "forbid",
    }


class LLM_JWTAuth(LLMPydanticObjectBase):
    """
    A class to define the roles and permissions for a LLM Proxy w/ JWT Auth.

    Attributes:
    - admin_jwt_scope: The JWT scope required for proxy admin roles.
    - admin_allowed_routes: list of allowed routes for proxy admin roles.
    - team_jwt_scope: The JWT scope required for proxy team roles.
    - team_id_jwt_field: The field in the JWT token that stores the team ID. Default - `client_id`.
    - team_allowed_routes: list of allowed routes for proxy team roles.
    - user_id_jwt_field: The field in the JWT token that stores the user id (maps to `LLMUserTable`). Use this for internal employees.
    - user_email_jwt_field: The field in the JWT token that stores the user email (maps to `LLMUserTable`). Use this for internal employees.
    - user_allowed_email_subdomain: If specified, only emails from specified subdomain will be allowed to access proxy.
    - end_user_id_jwt_field: The field in the JWT token that stores the end-user ID (maps to `LLMEndUserTable`). Turn this off by setting to `None`. Enables end-user cost tracking. Use this for external customers.
    - public_key_ttl: Default - 600s. TTL for caching public JWT keys.
    - public_allowed_routes: list of allowed routes for authenticated but unknown llm role jwt tokens.
    - enforce_rbac: If true, enforce RBAC for all routes.
    - custom_validate: A custom function to validates the JWT token.

    See `auth_checks.py` for the specific routes
    """

    admin_jwt_scope: str = "llm_proxy_admin"
    admin_allowed_routes: List[str] = [
        "management_routes",
        "spend_tracking_routes",
        "global_spend_tracking_routes",
        "info_routes",
    ]
    team_id_jwt_field: Optional[str] = None
    team_id_upsert: bool = False
    team_ids_jwt_field: Optional[str] = None
    upsert_sso_user_to_team: bool = False
    team_allowed_routes: List[
        Literal["openai_routes", "info_routes", "management_routes"]
    ] = ["openai_routes", "info_routes"]
    team_id_default: Optional[str] = Field(
        default=None,
        description="If no team_id given, default permissions/spend-tracking to this team.s",
    )

    org_id_jwt_field: Optional[str] = None
    user_id_jwt_field: Optional[str] = None
    user_email_jwt_field: Optional[str] = None
    user_allowed_email_domain: Optional[str] = None
    user_roles_jwt_field: Optional[str] = None
    user_allowed_roles: Optional[List[str]] = None
    user_id_upsert: bool = Field(
        default=False, description="If user doesn't exist, upsert them into the db."
    )
    end_user_id_jwt_field: Optional[str] = None
    public_key_ttl: float = 600
    public_allowed_routes: List[str] = ["public_routes"]
    enforce_rbac: bool = False
    roles_jwt_field: Optional[str] = None  # v2 on role mappings
    role_mappings: Optional[List[RoleMapping]] = None
    object_id_jwt_field: Optional[str] = (
        None  # can be either user / team, inferred from the role mapping
    )
    scope_mappings: Optional[List[ScopeMapping]] = None
    enforce_scope_based_access: bool = False
    enforce_team_based_model_access: bool = False
    custom_validate: Optional[Callable[..., Literal[True]]] = None

    def __init__(self, **kwargs: Any) -> None:
        # get the attribute names for this Pydantic model
        allowed_keys = self.__annotations__.keys()

        invalid_keys = set(kwargs.keys()) - allowed_keys
        user_roles_jwt_field = kwargs.get("user_roles_jwt_field")
        user_allowed_roles = kwargs.get("user_allowed_roles")
        object_id_jwt_field = kwargs.get("object_id_jwt_field")
        role_mappings = kwargs.get("role_mappings")
        scope_mappings = kwargs.get("scope_mappings")
        enforce_scope_based_access = kwargs.get("enforce_scope_based_access")
        custom_validate = kwargs.get("custom_validate")

        if custom_validate is not None:
            fn = get_instance_fn(custom_validate)
            validate_custom_validate_return_type(fn)
            kwargs["custom_validate"] = fn

        if invalid_keys:
            raise ValueError(
                f"Invalid arguments provided: {', '.join(invalid_keys)}. Allowed arguments are: {', '.join(allowed_keys)}."
            )
        if (user_roles_jwt_field is not None and user_allowed_roles is None) or (
            user_roles_jwt_field is None and user_allowed_roles is not None
        ):
            raise ValueError(
                "user_allowed_roles must be provided if user_roles_jwt_field is set."
            )

        if object_id_jwt_field is not None and role_mappings is None:
            raise ValueError(
                "if object_id_jwt_field is set, role_mappings must also be set. Needed to infer if the caller is a user or team."
            )

        if scope_mappings is not None and not enforce_scope_based_access:
            raise ValueError(
                "scope_mappings must be set if enforce_scope_based_access is true."
            )

        super().__init__(**kwargs)


class PrismaCompatibleUpdateDBModel(TypedDict, total=False):
    model_name: str
    llm_params: str
    model_info: str
    updated_at: str
    updated_by: str


class SpecialManagementEndpointEnums(enum.Enum):
    DEFAULT_ORGANIZATION = "default_organization"


class TransformRequestBody(BaseModel):
    call_type: CallTypes
    request_body: dict


class DefaultInternalUserParams(LLMPydanticObjectBase):
    """
    Default parameters to apply when a new user signs in via SSO or is created on the /user/new API endpoint
    """

    user_role: Optional[
        Literal[
            LLMUserRoles.INTERNAL_USER,
            LLMUserRoles.INTERNAL_USER_VIEW_ONLY,
            LLMUserRoles.PROXY_ADMIN,
            LLMUserRoles.PROXY_ADMIN_VIEW_ONLY,
        ]
    ] = Field(
        default=LLMUserRoles.INTERNAL_USER,
        description="Default role assigned to new users created",
    )
    max_budget: Optional[float] = Field(
        default=None,
        description="Default maximum budget (in USD) for new users created",
    )
    budget_duration: Optional[str] = Field(
        default=None,
        description="Default budget duration for new users (e.g. 'daily', 'weekly', 'monthly')",
    )
    models: Optional[List[str]] = Field(
        default=None, description="Default list of models that new users can access"
    )
