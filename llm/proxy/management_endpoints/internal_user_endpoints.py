"""
Internal User Management Endpoints


These are members of a Team on LLM

/user/new
/user/update
/user/delete
/user/info
/user/list
"""

import asyncio
import traceback
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional, Union, cast

import fastapi
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

import llm
from llm._logging import verbose_proxy_logger
from llm.llm_core_utils.duration_parser import duration_in_seconds
from llm.proxy._types import *
from llm.proxy.auth.user_api_key_auth import user_api_key_auth
from llm.proxy.management_endpoints.key_management_endpoints import (
    generate_key_helper_fn,
    prepare_metadata_fields,
)
from llm.proxy.management_helpers.audit_logs import create_audit_log_for_update
from llm.proxy.management_helpers.utils import management_endpoint_wrapper
from llm.proxy.utils import handle_exception_on_proxy

router = APIRouter()


async def create_internal_user_audit_log(
    user_id: str,
    action: AUDIT_ACTIONS,
    llm_changed_by: Optional[str],
    user_api_key_dict: UserAPIKeyAuth,
    llm_proxy_admin_name: Optional[str],
    before_value: Optional[str] = None,
    after_value: Optional[str] = None,
):
    """
    Create an audit log for an internal user.

    Parameters:
    - user_id: str - The id of the user to create the audit log for.
    - action: AUDIT_ACTIONS - The action to create the audit log for.
    - user_row: LLM_UserTable - The user row to create the audit log for.
    - llm_changed_by: Optional[str] - The user id of the user who is changing the user.
    - user_api_key_dict: UserAPIKeyAuth - The user api key dictionary.
    - llm_proxy_admin_name: Optional[str] - The name of the proxy admin.
    """
    if not llm.store_audit_logs:
        return

    await create_audit_log_for_update(
        request_data=LLM_AuditLogs(
            id=str(uuid.uuid4()),
            updated_at=datetime.now(timezone.utc),
            changed_by=llm_changed_by
            or user_api_key_dict.user_id
            or llm_proxy_admin_name,
            changed_by_api_key=user_api_key_dict.api_key,
            table_name=LlmTableNames.USER_TABLE_NAME,
            object_id=user_id,
            action=action,
            updated_values=after_value,
            before_value=before_value,
        )
    )


def _update_internal_new_user_params(data_json: dict, data: NewUserRequest) -> dict:
    if "user_id" in data_json and data_json["user_id"] is None:
        data_json["user_id"] = str(uuid.uuid4())
    auto_create_key = data_json.pop("auto_create_key", True)
    if auto_create_key is False:
        data_json["table_name"] = (
            "user"  # only create a user, don't create key if 'auto_create_key' set to False
        )

    is_internal_user = False
    if data.user_role and data.user_role.is_internal_user_role:
        is_internal_user = True
        if llm.default_internal_user_params:
            for key, value in llm.default_internal_user_params.items():
                if key == "available_teams":
                    continue
                elif key not in data_json or data_json[key] is None:
                    data_json[key] = value
                elif (
                    key == "models"
                    and isinstance(data_json[key], list)
                    and len(data_json[key]) == 0
                ):
                    data_json[key] = value

    if "max_budget" in data_json and data_json["max_budget"] is None:
        if is_internal_user and llm.max_internal_user_budget is not None:
            data_json["max_budget"] = llm.max_internal_user_budget

    if "budget_duration" in data_json and data_json["budget_duration"] is None:
        if is_internal_user and llm.internal_user_budget_duration is not None:
            data_json["budget_duration"] = llm.internal_user_budget_duration

    return data_json


async def _check_duplicate_user_email(
    user_email: Optional[str], prisma_client: Any
) -> None:
    """
    Helper function to check if a user email already exists in the database.

    Args:
        user_email (Optional[str]): Email to check
        prisma_client (Any): Database client instance

    Raises:
        Exception: If database is not connected
        HTTPException: If user with email already exists
    """
    if user_email:
        if prisma_client is None:
            raise Exception("Database not connected")

        existing_user = await prisma_client.db.llm_usertable.find_first(
            where={"user_email": user_email}
        )

        if existing_user is not None:
            raise HTTPException(
                status_code=400,
                detail={"error": f"User with email {user_email} already exists"},
            )


@router.post(
    "/user/new",
    tags=["Internal User management"],
    dependencies=[Depends(user_api_key_auth)],
    response_model=NewUserResponse,
)
@management_endpoint_wrapper
async def new_user(
    data: NewUserRequest,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Use this to create a new INTERNAL user with a budget.
    Internal Users can access LLM Admin UI to make keys, request access to models.
    This creates a new user and generates a new api key for the new user. The new api key is returned.

    Returns user id, budget + new key.

    Parameters:
    - user_id: Optional[str] - Specify a user id. If not set, a unique id will be generated.
    - user_alias: Optional[str] - A descriptive name for you to know who this user id refers to.
    - teams: Optional[list] - specify a list of team id's a user belongs to.
    - user_email: Optional[str] - Specify a user email.
    - send_invite_email: Optional[bool] - Specify if an invite email should be sent.
    - user_role: Optional[str] - Specify a user role - "proxy_admin", "proxy_admin_viewer", "internal_user", "internal_user_viewer", "team", "customer". Info about each role here: `https://github.com/BerriAI/llm/llm/proxy/_types.py#L20`
    - max_budget: Optional[float] - Specify max budget for a given user.
    - budget_duration: Optional[str] - Budget is reset at the end of specified duration. If not set, budget is never reset. You can set duration as seconds ("30s"), minutes ("30m"), hours ("30h"), days ("30d"), months ("1mo").
    - models: Optional[list] - Model_name's a user is allowed to call. (if empty, key is allowed to call all models). Set to ['no-default-models'] to block all model access. Restricting user to only team-based model access.
    - tpm_limit: Optional[int] - Specify tpm limit for a given user (Tokens per minute)
    - rpm_limit: Optional[int] - Specify rpm limit for a given user (Requests per minute)
    - auto_create_key: bool - Default=True. Flag used for returning a key as part of the /user/new response
    - aliases: Optional[dict] - Model aliases for the user - [Docs](https://llm.vercel.app/docs/proxy/virtual_keys#model-aliases)
    - config: Optional[dict] - [DEPRECATED PARAM] User-specific config.
    - allowed_cache_controls: Optional[list] - List of allowed cache control values. Example - ["no-cache", "no-store"]. See all values - https://docs.llm.ai/docs/proxy/caching#turn-on--off-caching-per-request-
    - blocked: Optional[bool] - [Not Implemented Yet] Whether the user is blocked.
    - guardrails: Optional[List[str]] - [Not Implemented Yet] List of active guardrails for the user
    - permissions: Optional[dict] - [Not Implemented Yet] User-specific permissions, eg. turning off pii masking.
    - metadata: Optional[dict] - Metadata for user, store information for user. Example metadata = {"team": "core-infra", "app": "app2", "email": "ishaan@berri.ai" }
    - max_parallel_requests: Optional[int] - Rate limit a user based on the number of parallel requests. Raises 429 error, if user's parallel requests > x.
    - soft_budget: Optional[float] - Get alerts when user crosses given budget, doesn't block requests.
    - model_max_budget: Optional[dict] - Model-specific max budget for user. [Docs](https://docs.llm.ai/docs/proxy/users#add-model-specific-budgets-to-keys)
    - model_rpm_limit: Optional[float] - Model-specific rpm limit for user. [Docs](https://docs.llm.ai/docs/proxy/users#add-model-specific-limits-to-keys)
    - model_tpm_limit: Optional[float] - Model-specific tpm limit for user. [Docs](https://docs.llm.ai/docs/proxy/users#add-model-specific-limits-to-keys)
    - spend: Optional[float] - Amount spent by user. Default is 0. Will be updated by proxy whenever user is used. You can set duration as seconds ("30s"), minutes ("30m"), hours ("30h"), days ("30d"), months ("1mo").
    - team_id: Optional[str] - [DEPRECATED PARAM] The team id of the user. Default is None. 
    - duration: Optional[str] - Duration for the key auto-created on `/user/new`. Default is None.
    - key_alias: Optional[str] - Alias for the key auto-created on `/user/new`. Default is None.

    Returns:
    - key: (str) The generated api key for the user
    - expires: (datetime) Datetime object for when key expires.
    - user_id: (str) Unique user id - used for tracking spend across multiple keys for same user id.
    - max_budget: (float|None) Max budget for given user.

    Usage Example 

    ```shell
     curl -X POST "http://localhost:4000/user/new" \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer sk-1234" \
     -d '{
         "username": "new_user",
         "email": "new_user@example.com"
     }'
    ```
    """
    try:
        from llm.proxy.proxy_server import (
            general_settings,
            llm_proxy_admin_name,
            prisma_client,
            proxy_logging_obj,
        )

        # Check for duplicate email
        await _check_duplicate_user_email(data.user_email, prisma_client)

        data_json = data.json()  # type: ignore
        data_json = _update_internal_new_user_params(data_json, data)
        response = await generate_key_helper_fn(request_type="user", **data_json)
        # Admin UI Logic
        # Add User to Team and Organization
        # if team_id passed add this user to the team
        if data_json.get("team_id", None) is not None:
            from llm.proxy.management_endpoints.team_endpoints import (
                team_member_add,
            )

            try:
                await team_member_add(
                    data=TeamMemberAddRequest(
                        team_id=data_json.get("team_id", None),
                        member=Member(
                            user_id=data_json.get("user_id", None),
                            role="user",
                            user_email=data_json.get("user_email", None),
                        ),
                    ),
                    http_request=Request(
                        scope={"type": "http", "path": "/user/new"},
                    ),
                    user_api_key_dict=user_api_key_dict,
                )
            except HTTPException as e:
                if e.status_code == 400 and (
                    "already exists" in str(e) or "doesn't exist" in str(e)
                ):
                    verbose_proxy_logger.debug(
                        "llm.proxy.management_endpoints.internal_user_endpoints.new_user(): User already exists in team - {}".format(
                            str(e)
                        )
                    )
                else:
                    verbose_proxy_logger.debug(
                        "llm.proxy.management_endpoints.internal_user_endpoints.new_user(): Exception occured - {}".format(
                            str(e)
                        )
                    )
            except Exception as e:
                if "already exists" in str(e) or "doesn't exist" in str(e):
                    verbose_proxy_logger.debug(
                        "llm.proxy.management_endpoints.internal_user_endpoints.new_user(): User already exists in team - {}".format(
                            str(e)
                        )
                    )
                else:
                    raise e

        if data.send_invite_email is True:
            # check if user has setup email alerting
            if "email" not in general_settings.get("alerting", []):
                raise ValueError(
                    "Email alerting not setup on config.yaml. Please set `alerting=['email']. \nDocs: https://docs.llm.ai/docs/proxy/email`"
                )

            event = WebhookEvent(
                event="internal_user_created",
                event_group="internal_user",
                event_message="Welcome to LLM Proxy",
                token=response.get("token", ""),
                spend=response.get("spend", 0.0),
                max_budget=response.get("max_budget", 0.0),
                user_id=response.get("user_id", None),
                user_email=response.get("user_email", None),
                team_id=response.get("team_id", "Default Team"),
                key_alias=response.get("key_alias", None),
            )

            # If user configured email alerting - send an Email letting their end-user know the key was created
            asyncio.create_task(
                proxy_logging_obj.slack_alerting_instance.send_key_created_or_user_invited_email(
                    webhook_event=event,
                )
            )

        try:
            if prisma_client is None:
                raise Exception(CommonProxyErrors.db_not_connected_error.value)
            user_row: BaseModel = await prisma_client.db.llm_usertable.find_first(
                where={"user_id": response["user_id"]}
            )

            user_row_llm_typed = LLM_UserTable(
                **user_row.model_dump(exclude_none=True)
            )
            asyncio.create_task(
                create_internal_user_audit_log(
                    user_id=user_row_llm_typed.user_id,
                    action="created",
                    llm_changed_by=user_api_key_dict.user_id,
                    user_api_key_dict=user_api_key_dict,
                    llm_proxy_admin_name=llm_proxy_admin_name,
                    before_value=None,
                    after_value=user_row_llm_typed.model_dump_json(
                        exclude_none=True
                    ),
                )
            )
        except Exception as e:
            verbose_proxy_logger.warning(
                "Unable to create audit log for user on `/user/new` - {}".format(str(e))
            )

        return NewUserResponse(
            key=response.get("token", ""),
            expires=response.get("expires", None),
            max_budget=response["max_budget"],
            user_id=response["user_id"],
            user_role=response.get("user_role", None),
            user_email=response.get("user_email", None),
            user_alias=response.get("user_alias", None),
            teams=response.get("teams", None),
            team_id=response.get("team_id", None),
            metadata=response.get("metadata", None),
            models=response.get("models", None),
            tpm_limit=response.get("tpm_limit", None),
            rpm_limit=response.get("rpm_limit", None),
            budget_duration=response.get("budget_duration", None),
            model_max_budget=response.get("model_max_budget", None),
        )
    except Exception as e:
        verbose_proxy_logger.exception(
            "/user/new: Exception occured - {}".format(str(e))
        )
        raise handle_exception_on_proxy(e)


@router.get(
    "/user/available_roles",
    tags=["Internal User management"],
    include_in_schema=False,
    dependencies=[Depends(user_api_key_auth)],
)
async def ui_get_available_role(
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Endpoint used by Admin UI to show all available roles to assign a user
    return {
        "proxy_admin": {
            "description": "Proxy Admin role",
            "ui_label": "Admin"
        }
    }
    """

    _data_to_return = {}
    for role in LlmUserRoles:

        # We only show a subset of roles on UI
        if role in [
            LLMUserRoles.PROXY_ADMIN,
            LLMUserRoles.PROXY_ADMIN_VIEW_ONLY,
            LLMUserRoles.INTERNAL_USER,
            LLMUserRoles.INTERNAL_USER_VIEW_ONLY,
        ]:
            _data_to_return[role.value] = {
                "description": role.description,
                "ui_label": role.ui_label,
            }
    return _data_to_return


def get_team_from_list(
    team_list: Optional[Union[List[LLM_TeamTable], List[TeamListResponseObject]]],
    team_id: str,
) -> Optional[Union[LLM_TeamTable, LLM_TeamMembership]]:
    if team_list is None:
        return None

    for team in team_list:
        if team.team_id == team_id:
            return team
    return None


@router.get(
    "/user/info",
    tags=["Internal User management"],
    dependencies=[Depends(user_api_key_auth)],
    # response_model=UserInfoResponse,
)
@management_endpoint_wrapper
async def user_info(
    user_id: Optional[str] = fastapi.Query(
        default=None, description="User ID in the request parameters"
    ),
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    [10/07/2024]
    Note: To get all users (+pagination), use `/user/list` endpoint.


    Use this to get user information. (user row + all user key info)

    Example request
    ```
    curl -X GET 'http://localhost:4000/user/info?user_id=krrish7%40berri.ai' \
    --header 'Authorization: Bearer sk-1234'
    ```
    """
    from llm.proxy.proxy_server import prisma_client

    try:
        if prisma_client is None:
            raise Exception(
                "Database not connected. Connect a database to your proxy - https://docs.llm.ai/docs/simple_proxy#managing-auth---virtual-keys"
            )
        if (
            user_id is None
            and user_api_key_dict.user_role == LLMUserRoles.PROXY_ADMIN
        ):
            return await _get_user_info_for_proxy_admin()
        elif user_id is None:
            user_id = user_api_key_dict.user_id
        ## GET USER ROW ##
        if user_id is not None:
            user_info = await prisma_client.get_data(user_id=user_id)
        else:
            user_info = None
        ## GET ALL TEAMS ##
        team_list = []
        team_id_list = []
        from llm.proxy.management_endpoints.team_endpoints import list_team

        teams_1 = await list_team(
            http_request=Request(
                scope={"type": "http", "path": "/user/info"},
            ),
            user_id=user_id,
            user_api_key_dict=user_api_key_dict,
        )

        if teams_1 is not None and isinstance(teams_1, list):
            team_list = teams_1
            for team in teams_1:
                team_id_list.append(team.team_id)

        teams_2: Optional[Any] = None
        if user_info is not None:
            # *NEW* get all teams in user 'teams' field
            teams_2 = await prisma_client.get_data(
                team_id_list=user_info.teams, table_name="team", query_type="find_all"
            )

            if teams_2 is not None and isinstance(teams_2, list):
                for team in teams_2:
                    if team.team_id not in team_id_list:
                        team_list.append(team)
                        team_id_list.append(team.team_id)

        elif (
            user_api_key_dict.user_id is not None and user_id is None
        ):  # the key querying the endpoint is the one asking for it's teams
            caller_user_info = await prisma_client.get_data(
                user_id=user_api_key_dict.user_id
            )
            # *NEW* get all teams in user 'teams' field
            if caller_user_info is not None:
                teams_2 = await prisma_client.get_data(
                    team_id_list=caller_user_info.teams,
                    table_name="team",
                    query_type="find_all",
                )

            if teams_2 is not None and isinstance(teams_2, list):
                for team in teams_2:
                    if team.team_id not in team_id_list:
                        team_list.append(team)
                        team_id_list.append(team.team_id)

        ## GET ALL KEYS ##
        keys = await prisma_client.get_data(
            user_id=user_id,
            table_name="key",
            query_type="find_all",
        )

        if user_info is None and keys is not None:
            ## make sure we still return a total spend ##
            spend = 0
            for k in keys:
                spend += getattr(k, "spend", 0)
            user_info = {"spend": spend}

        ## REMOVE HASHED TOKEN INFO before returning ##
        returned_keys = _process_keys_for_user_info(keys=keys, all_teams=teams_1)
        team_list.sort(key=lambda x: (getattr(x, "team_alias", "") or ""))
        _user_info = (
            user_info.model_dump() if isinstance(user_info, BaseModel) else user_info
        )
        response_data = UserInfoResponse(
            user_id=user_id, user_info=_user_info, keys=returned_keys, teams=team_list
        )

        return response_data
    except Exception as e:
        verbose_proxy_logger.exception(
            "llm.proxy.proxy_server.user_info(): Exception occured - {}".format(
                str(e)
            )
        )
        raise handle_exception_on_proxy(e)


async def _get_user_info_for_proxy_admin():
    """
    Admin UI Endpoint - Returns All Teams and Keys when Proxy Admin is querying

    - get all teams in LLM_TeamTable
    - get all keys in LLM_VerificationToken table

    Why separate helper for proxy admin ?
        - To get Faster UI load times, get all teams and virtual keys in 1 query
    """

    from llm.proxy.proxy_server import prisma_client

    sql_query = """
        SELECT 
            (SELECT json_agg(t.*) FROM "LLM_TeamTable" t) as teams,
            (SELECT json_agg(k.*) FROM "LLM_VerificationToken" k WHERE k.team_id != 'llm-dashboard' OR k.team_id IS NULL) as keys
    """
    if prisma_client is None:
        raise Exception(
            "Database not connected. Connect a database to your proxy - https://docs.llm.ai/docs/simple_proxy#managing-auth---virtual-keys"
        )

    results = await prisma_client.db.query_raw(sql_query)

    verbose_proxy_logger.debug("results_keys: %s", results)

    _keys_in_db: List = results[0]["keys"] or []
    # cast all keys to LLM_VerificationToken
    keys_in_db = []
    for key in _keys_in_db:
        if key.get("models") is None:
            key["models"] = []
        keys_in_db.append(LLM_VerificationToken(**key))

    # cast all teams to LLM_TeamTable
    _teams_in_db: List = results[0]["teams"] or []
    _teams_in_db = [LLM_TeamTable(**team) for team in _teams_in_db]
    _teams_in_db.sort(key=lambda x: (getattr(x, "team_alias", "") or ""))
    returned_keys = _process_keys_for_user_info(keys=keys_in_db, all_teams=_teams_in_db)
    return UserInfoResponse(
        user_id=None,
        user_info=None,
        keys=returned_keys,
        teams=_teams_in_db,
    )


def _process_keys_for_user_info(
    keys: Optional[List[LLM_VerificationToken]],
    all_teams: Optional[Union[List[LLM_TeamTable], List[TeamListResponseObject]]],
):
    from llm.proxy.proxy_server import general_settings, llm_master_key_hash

    returned_keys = []
    if keys is None:
        pass
    else:
        for key in keys:
            if (
                key.token == llm_master_key_hash
                and general_settings.get("disable_master_key_return", False)
                is True  ## [IMPORTANT] used by hosted proxy-ui to prevent sharing master key on ui
            ):
                continue

            try:
                _key: dict = key.model_dump()  # noqa
            except Exception:
                # if using pydantic v1
                _key = key.dict()
            if (
                "team_id" in _key
                and _key["team_id"] is not None
                and _key["team_id"] != "llm-dashboard"
            ):
                team_info = get_team_from_list(
                    team_list=all_teams, team_id=_key["team_id"]
                )
                if team_info is not None:
                    team_alias = getattr(team_info, "team_alias", None)
                    _key["team_alias"] = team_alias
                else:
                    _key["team_alias"] = None
            else:
                _key["team_alias"] = "None"
            returned_keys.append(_key)
    return returned_keys


def _update_internal_user_params(data_json: dict, data: UpdateUserRequest) -> dict:
    non_default_values = {}
    for k, v in data_json.items():
        if (
            v is not None
            and v
            not in (
                [],
                {},
                0,
            )
            and k not in LLM_ManagementEndpoint_MetadataFields
        ):  # models default to [], spend defaults to 0, we should not reset these values
            non_default_values[k] = v

    is_internal_user = False
    if data.user_role == LLMUserRoles.INTERNAL_USER:
        is_internal_user = True

    if "budget_duration" in non_default_values:
        duration_s = duration_in_seconds(duration=non_default_values["budget_duration"])
        user_reset_at = datetime.now(timezone.utc) + timedelta(seconds=duration_s)
        non_default_values["budget_reset_at"] = user_reset_at

    if "max_budget" not in non_default_values:
        if (
            is_internal_user and llm.max_internal_user_budget is not None
        ):  # applies internal user limits, if user role updated
            non_default_values["max_budget"] = llm.max_internal_user_budget

    if (
        "budget_duration" not in non_default_values
    ):  # applies internal user limits, if user role updated
        if is_internal_user and llm.internal_user_budget_duration is not None:
            non_default_values["budget_duration"] = (
                llm.internal_user_budget_duration
            )
            duration_s = duration_in_seconds(
                duration=non_default_values["budget_duration"]
            )
            user_reset_at = datetime.now(timezone.utc) + timedelta(seconds=duration_s)
            non_default_values["budget_reset_at"] = user_reset_at

    return non_default_values


@router.post(
    "/user/update",
    tags=["Internal User management"],
    dependencies=[Depends(user_api_key_auth)],
)
@management_endpoint_wrapper
async def user_update(
    data: UpdateUserRequest,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Example curl 

    ```
    curl --location 'http://0.0.0.0:4000/user/update' \
    --header 'Authorization: Bearer sk-1234' \
    --header 'Content-Type: application/json' \
    --data '{
        "user_id": "test-llm-user-4",
        "user_role": "proxy_admin_viewer"
    }'
    ```
    
    Parameters:
        - user_id: Optional[str] - Specify a user id. If not set, a unique id will be generated.
        - user_email: Optional[str] - Specify a user email.
        - password: Optional[str] - Specify a user password.
        - user_alias: Optional[str] - A descriptive name for you to know who this user id refers to.
        - teams: Optional[list] - specify a list of team id's a user belongs to.
        - send_invite_email: Optional[bool] - Specify if an invite email should be sent.
        - user_role: Optional[str] - Specify a user role - "proxy_admin", "proxy_admin_viewer", "internal_user", "internal_user_viewer", "team", "customer". Info about each role here: `https://github.com/BerriAI/llm/llm/proxy/_types.py#L20`
        - max_budget: Optional[float] - Specify max budget for a given user.
        - budget_duration: Optional[str] - Budget is reset at the end of specified duration. If not set, budget is never reset. You can set duration as seconds ("30s"), minutes ("30m"), hours ("30h"), days ("30d"), months ("1mo").
        - models: Optional[list] - Model_name's a user is allowed to call. (if empty, key is allowed to call all models)
        - tpm_limit: Optional[int] - Specify tpm limit for a given user (Tokens per minute)
        - rpm_limit: Optional[int] - Specify rpm limit for a given user (Requests per minute)
        - auto_create_key: bool - Default=True. Flag used for returning a key as part of the /user/new response
        - aliases: Optional[dict] - Model aliases for the user - [Docs](https://llm.vercel.app/docs/proxy/virtual_keys#model-aliases)
        - config: Optional[dict] - [DEPRECATED PARAM] User-specific config.
        - allowed_cache_controls: Optional[list] - List of allowed cache control values. Example - ["no-cache", "no-store"]. See all values - https://docs.llm.ai/docs/proxy/caching#turn-on--off-caching-per-request-
        - blocked: Optional[bool] - [Not Implemented Yet] Whether the user is blocked.
        - guardrails: Optional[List[str]] - [Not Implemented Yet] List of active guardrails for the user
        - permissions: Optional[dict] - [Not Implemented Yet] User-specific permissions, eg. turning off pii masking.
        - metadata: Optional[dict] - Metadata for user, store information for user. Example metadata = {"team": "core-infra", "app": "app2", "email": "ishaan@berri.ai" }
        - max_parallel_requests: Optional[int] - Rate limit a user based on the number of parallel requests. Raises 429 error, if user's parallel requests > x.
        - soft_budget: Optional[float] - Get alerts when user crosses given budget, doesn't block requests.
        - model_max_budget: Optional[dict] - Model-specific max budget for user. [Docs](https://docs.llm.ai/docs/proxy/users#add-model-specific-budgets-to-keys)
        - model_rpm_limit: Optional[float] - Model-specific rpm limit for user. [Docs](https://docs.llm.ai/docs/proxy/users#add-model-specific-limits-to-keys)
        - model_tpm_limit: Optional[float] - Model-specific tpm limit for user. [Docs](https://docs.llm.ai/docs/proxy/users#add-model-specific-limits-to-keys)
        - spend: Optional[float] - Amount spent by user. Default is 0. Will be updated by proxy whenever user is used. You can set duration as seconds ("30s"), minutes ("30m"), hours ("30h"), days ("30d"), months ("1mo").
        - team_id: Optional[str] - [DEPRECATED PARAM] The team id of the user. Default is None. 
        - duration: Optional[str] - [NOT IMPLEMENTED].
        - key_alias: Optional[str] - [NOT IMPLEMENTED].
            
    
    """
    from llm.proxy.proxy_server import llm_proxy_admin_name, prisma_client

    try:
        data_json: dict = data.json()
        # get the row from db
        if prisma_client is None:
            raise Exception("Not connected to DB!")

        # get non default values for key
        non_default_values = _update_internal_user_params(
            data_json=data_json, data=data
        )

        existing_user_row: Optional[BaseModel] = None
        if data.user_id is not None:
            existing_user_row = await prisma_client.db.llm_usertable.find_first(
                where={"user_id": data.user_id}
            )
            if existing_user_row is not None:
                existing_user_row = LLM_UserTable(
                    **existing_user_row.model_dump(exclude_none=True)
                )

        existing_metadata = (
            cast(Dict, getattr(existing_user_row, "metadata", {}) or {})
            if existing_user_row is not None
            else {}
        )

        non_default_values = prepare_metadata_fields(
            data=data,
            non_default_values=non_default_values,
            existing_metadata=existing_metadata or {},
        )

        ## ADD USER, IF NEW ##
        verbose_proxy_logger.debug("/user/update: Received data = %s", data)
        response: Optional[Any] = None
        if data.user_id is not None and len(data.user_id) > 0:
            non_default_values["user_id"] = data.user_id  # type: ignore
            verbose_proxy_logger.debug("In update user, user_id condition block.")
            response = await prisma_client.update_data(
                user_id=data.user_id,
                data=non_default_values,
                table_name="user",
            )
            verbose_proxy_logger.debug(
                f"received response from updating prisma client. response={response}"
            )
        elif data.user_email is not None:
            non_default_values["user_id"] = str(uuid.uuid4())
            non_default_values["user_email"] = data.user_email
            ## user email is not unique acc. to prisma schema -> future improvement
            ### for now: check if it exists in db, if not - insert it
            existing_user_rows = await prisma_client.get_data(
                key_val={"user_email": data.user_email},
                table_name="user",
                query_type="find_all",
            )
            if existing_user_rows is None or (
                isinstance(existing_user_rows, list) and len(existing_user_rows) == 0
            ):
                response = await prisma_client.insert_data(
                    data=non_default_values, table_name="user"
                )
            elif isinstance(existing_user_rows, list) and len(existing_user_rows) > 0:
                for existing_user in existing_user_rows:
                    response = await prisma_client.update_data(
                        user_id=existing_user.user_id,
                        data=non_default_values,
                        table_name="user",
                    )

        if response is not None:  # emit audit log
            try:
                user_row: BaseModel = (
                    await prisma_client.db.llm_usertable.find_first(
                        where={"user_id": response["user_id"]}
                    )
                )

                user_row_llm_typed = LLM_UserTable(
                    **user_row.model_dump(exclude_none=True)
                )
                asyncio.create_task(
                    create_internal_user_audit_log(
                        user_id=user_row_llm_typed.user_id,
                        action="updated",
                        llm_changed_by=user_api_key_dict.user_id,
                        user_api_key_dict=user_api_key_dict,
                        llm_proxy_admin_name=llm_proxy_admin_name,
                        before_value=(
                            existing_user_row.model_dump_json(exclude_none=True)
                            if existing_user_row
                            else None
                        ),
                        after_value=user_row_llm_typed.model_dump_json(
                            exclude_none=True
                        ),
                    )
                )
            except Exception as e:
                verbose_proxy_logger.warning(
                    "Unable to create audit log for user on `/user/update` - {}".format(
                        str(e)
                    )
                )
        return response  # type: ignore
        # update based on remaining passed in values
    except Exception as e:
        verbose_proxy_logger.exception(
            "llm.proxy.proxy_server.user_update(): Exception occured - {}".format(
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


async def get_user_key_counts(
    prisma_client,
    user_ids: Optional[List[str]] = None,
):
    """
    Helper function to get the count of keys for each user using Prisma's count method.

    Args:
        prisma_client: The Prisma client instance
        user_ids: List of user IDs to get key counts for

    Returns:
        Dictionary mapping user_id to key count
    """
    from llm.constants import UI_SESSION_TOKEN_TEAM_ID

    if not user_ids or len(user_ids) == 0:
        return {}

    result = {}

    # Get count for each user_id individually
    for user_id in user_ids:
        count = await prisma_client.db.llm_verificationtoken.count(
            where={
                "user_id": user_id,
                "OR": [
                    {"team_id": None},
                    {"team_id": {"not": UI_SESSION_TOKEN_TEAM_ID}},
                ],
            }
        )
        result[user_id] = count

    return result


@router.get(
    "/user/get_users",
    tags=["Internal User management"],
    dependencies=[Depends(user_api_key_auth)],
)
@router.get(
    "/user/list",
    tags=["Internal User management"],
    dependencies=[Depends(user_api_key_auth)],
)
async def get_users(
    role: Optional[str] = fastapi.Query(
        default=None, description="Filter users by role"
    ),
    user_ids: Optional[str] = fastapi.Query(
        default=None, description="Get list of users by user_ids"
    ),
    page: int = fastapi.Query(default=1, ge=1, description="Page number"),
    page_size: int = fastapi.Query(
        default=25, ge=1, le=100, description="Number of items per page"
    ),
):
    """
    Get a paginated list of users, optionally filtered by role.

    Used by the UI to populate the user lists.

    Parameters:
        role: Optional[str]
            Filter users by role. Can be one of:
            - proxy_admin
            - proxy_admin_viewer
            - internal_user
            - internal_user_viewer
        user_ids: Optional[str]
            Get list of users by user_ids. Comma separated list of user_ids.
        page: int
            The page number to return
        page_size: int
            The number of items per page

    Currently - admin-only endpoint.

    Example curl:
    ```
    http://0.0.0.0:4000/user/list?user_ids=default_user_id,693c1a4a-1cc0-4c7c-afe8-b5d2c8d52e17
    ```
    """
    from llm.proxy.proxy_server import prisma_client

    if prisma_client is None:
        raise HTTPException(
            status_code=500,
            detail={"error": f"No db connected. prisma client={prisma_client}"},
        )

    # Calculate skip and take for pagination
    skip = (page - 1) * page_size

    # Prepare the query conditions
    # Build where conditions based on provided parameters
    where_conditions: Dict[str, Any] = {}

    if role:
        where_conditions["user_role"] = {
            "contains": role,
            "mode": "insensitive",  # Case-insensitive search
        }

    if user_ids and isinstance(user_ids, str):
        user_id_list = [uid.strip() for uid in user_ids.split(",") if uid.strip()]
        where_conditions["user_id"] = {
            "in": user_id_list,  # Now passing a list of strings as required by Prisma
        }

    users: Optional[List[LLM_UserTable]] = (
        await prisma_client.db.llm_usertable.find_many(
            where=where_conditions,
            skip=skip,
            take=page_size,
            order={"created_at": "desc"},
        )
    )

    # Get total count of user rows
    total_count = await prisma_client.db.llm_usertable.count(
        where=where_conditions  # type: ignore
    )

    # Get key count for each user
    if users is not None:
        user_key_counts = await get_user_key_counts(
            prisma_client, [user.user_id for user in users]
        )
    else:
        user_key_counts = {}

    verbose_proxy_logger.debug(f"Total count of users: {total_count}")

    # Calculate total pages
    total_pages = -(-total_count // page_size)  # Ceiling division

    # Prepare response
    user_list: List[LLM_UserTableWithKeyCount] = []
    if users is not None:
        for user in users:
            user_list.append(
                LLM_UserTableWithKeyCount(
                    **user.model_dump(), key_count=user_key_counts.get(user.user_id, 0)
                )
            )  # Return full key object
    else:
        user_list = []

    return {
        "users": user_list,
        "total": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@router.post(
    "/user/delete",
    tags=["Internal User management"],
    dependencies=[Depends(user_api_key_auth)],
)
@management_endpoint_wrapper
async def delete_user(
    data: DeleteUserRequest,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
    llm_changed_by: Optional[str] = Header(
        None,
        description="The llm-changed-by header enables tracking of actions performed by authorized users on behalf of other users, providing an audit trail for accountability",
    ),
):
    """
    delete user and associated user keys

    ```
    curl --location 'http://0.0.0.0:4000/user/delete' \

    --header 'Authorization: Bearer sk-1234' \

    --header 'Content-Type: application/json' \

    --data-raw '{
        "user_ids": ["45e3e396-ee08-4a61-a88e-16b3ce7e0849"]
    }'
    ```

    Parameters:
    - user_ids: List[str] - The list of user id's to be deleted.
    """
    from llm.proxy.proxy_server import (
        create_audit_log_for_update,
        llm_proxy_admin_name,
        prisma_client,
    )

    if prisma_client is None:
        raise HTTPException(status_code=500, detail={"error": "No db connected"})

    if data.user_ids is None:
        raise HTTPException(status_code=400, detail={"error": "No user id passed in"})

    # check that all teams passed exist
    for user_id in data.user_ids:
        user_row = await prisma_client.db.llm_usertable.find_unique(
            where={"user_id": user_id}
        )

        if user_row is None:
            raise HTTPException(
                status_code=404,
                detail={"error": f"User not found, passed user_id={user_id}"},
            )
        else:
            # Enterprise Feature - Audit Logging. Enable with llm.store_audit_logs = True
            # we do this after the first for loop, since first for loop is for validation. we only want this inserted after validation passes
            if llm.store_audit_logs is True:
                # make an audit log for each team deleted
                _user_row = user_row.json(exclude_none=True)

                asyncio.create_task(
                    create_audit_log_for_update(
                        request_data=LLM_AuditLogs(
                            id=str(uuid.uuid4()),
                            updated_at=datetime.now(timezone.utc),
                            changed_by=llm_changed_by
                            or user_api_key_dict.user_id
                            or llm_proxy_admin_name,
                            changed_by_api_key=user_api_key_dict.api_key,
                            table_name=LlmTableNames.USER_TABLE_NAME,
                            object_id=user_id,
                            action="deleted",
                            updated_values="{}",
                            before_value=_user_row,
                        )
                    )
                )

    # End of Audit logging

    ## DELETE ASSOCIATED KEYS
    await prisma_client.db.llm_verificationtoken.delete_many(
        where={"user_id": {"in": data.user_ids}}
    )

    ## DELETE ASSOCIATED INVITATION LINKS
    await prisma_client.db.llm_invitationlink.delete_many(
        where={"user_id": {"in": data.user_ids}}
    )

    ## DELETE ASSOCIATED ORGANIZATION MEMBERSHIPS
    await prisma_client.db.llm_organizationmembership.delete_many(
        where={"user_id": {"in": data.user_ids}}
    )

    ## DELETE USERS
    deleted_users = await prisma_client.db.llm_usertable.delete_many(
        where={"user_id": {"in": data.user_ids}}
    )

    return deleted_users


async def add_internal_user_to_organization(
    user_id: str,
    organization_id: str,
    user_role: LlmUserRoles,
):
    """
    Helper function to add an internal user to an organization

    Adds the user to LLM_OrganizationMembership table

    - Checks if organization_id exists

    Raises:
    - Exception if database not connected
    - Exception if user_id or organization_id not found
    """
    from llm.proxy.proxy_server import prisma_client

    if prisma_client is None:
        raise Exception("Database not connected")

    try:
        # Check if organization_id exists
        organization_row = await prisma_client.db.llm_organizationtable.find_unique(
            where={"organization_id": organization_id}
        )
        if organization_row is None:
            raise Exception(
                f"Organization not found, passed organization_id={organization_id}"
            )

        # Create a new organization membership entry
        new_membership = await prisma_client.db.llm_organizationmembership.create(
            data={
                "user_id": user_id,
                "organization_id": organization_id,
                "user_role": user_role,
                # Note: You can also set budget within an organization if needed
            }
        )

        return new_membership
    except Exception as e:
        raise Exception(f"Failed to add user to organization: {str(e)}")


@router.get(
    "/user/filter/ui",
    tags=["Internal User management"],
    dependencies=[Depends(user_api_key_auth)],
    include_in_schema=False,
    responses={
        200: {"model": List[LLM_UserTableFiltered]},
    },
)
async def ui_view_users(
    user_id: Optional[str] = fastapi.Query(
        default=None, description="User ID in the request parameters"
    ),
    user_email: Optional[str] = fastapi.Query(
        default=None, description="User email in the request parameters"
    ),
    page: int = fastapi.Query(
        default=1, description="Page number for pagination", ge=1
    ),
    page_size: int = fastapi.Query(
        default=50, description="Number of items per page", ge=1, le=100
    ),
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    [PROXY-ADMIN ONLY]Filter users based on partial match of user_id or email with pagination.

    Args:
        user_id (Optional[str]): Partial user ID to search for
        user_email (Optional[str]): Partial email to search for
        page (int): Page number for pagination (starts at 1)
        page_size (int): Number of items per page (max 100)
        user_api_key_dict (UserAPIKeyAuth): User authentication information

    Returns:
        List[LLM_SpendLogs]: Paginated list of matching user records
    """
    from llm.proxy.proxy_server import prisma_client

    if prisma_client is None:
        raise HTTPException(status_code=500, detail={"error": "No db connected"})

    try:
        # Calculate offset for pagination
        skip = (page - 1) * page_size

        # Build where conditions based on provided parameters
        where_conditions = {}

        if user_id:
            where_conditions["user_id"] = {
                "contains": user_id,
                "mode": "insensitive",  # Case-insensitive search
            }

        if user_email:
            where_conditions["user_email"] = {
                "contains": user_email,
                "mode": "insensitive",  # Case-insensitive search
            }

        # Query users with pagination and filters
        users: Optional[List[BaseModel]] = (
            await prisma_client.db.llm_usertable.find_many(
                where=where_conditions,
                skip=skip,
                take=page_size,
                order={"created_at": "desc"},
            )
        )

        if not users:
            return []

        return [LLM_UserTableFiltered(**user.model_dump()) for user in users]

    except Exception as e:
        verbose_proxy_logger.exception(f"Error searching users: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error searching users: {str(e)}")
