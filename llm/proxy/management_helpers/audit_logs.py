"""
Functions to create audit logs for LLM Proxy
"""

import json
import uuid
from datetime import datetime, timezone

import llm
from llm._logging import verbose_proxy_logger
from llm.proxy._types import (
    AUDIT_ACTIONS,
    LLM_AuditLogs,
    LLMTableNames,
    Optional,
    UserAPIKeyAuth,
)


async def create_object_audit_log(
    object_id: str,
    action: AUDIT_ACTIONS,
    llm_changed_by: Optional[str],
    user_api_key_dict: UserAPIKeyAuth,
    llm_proxy_admin_name: Optional[str],
    table_name: LLMTableNames,
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
            table_name=table_name,
            object_id=object_id,
            action=action,
            updated_values=after_value,
            before_value=before_value,
        )
    )


async def create_audit_log_for_update(request_data: LLM_AuditLogs):
    """
    Create an audit log for an object.
    """
    if not llm.store_audit_logs:
        return

    from llm.proxy.proxy_server import premium_user, prisma_client

    if premium_user is not True:
        return

    if llm.store_audit_logs is not True:
        return
    if prisma_client is None:
        raise Exception("prisma_client is None, no DB connected")

    verbose_proxy_logger.debug("creating audit log for %s", request_data)

    if isinstance(request_data.updated_values, dict):
        request_data.updated_values = json.dumps(request_data.updated_values)

    if isinstance(request_data.before_value, dict):
        request_data.before_value = json.dumps(request_data.before_value)

    _request_data = request_data.model_dump(exclude_none=True)

    try:
        await prisma_client.db.llm_auditlog.create(
            data={
                **_request_data,  # type: ignore
            }
        )
    except Exception as e:
        # [Non-Blocking Exception. Do not allow blocking LLM API call]
        verbose_proxy_logger.error(f"Failed Creating audit log {e}")

    return
