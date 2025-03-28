from typing import Any, Union

from llm.proxy._types import (
    GenerateKeyRequest,
    LLM_ManagementEndpoint_MetadataFields_Premium,
    LLM_TeamTable,
    UserAPIKeyAuth,
)
from llm.proxy.utils import _premium_user_check


def _is_user_team_admin(
    user_api_key_dict: UserAPIKeyAuth, team_obj: LLM_TeamTable
) -> bool:
    for member in team_obj.members_with_roles:
        if (
            member.user_id is not None and member.user_id == user_api_key_dict.user_id
        ) and member.role == "admin":

            return True

    return False


def _set_object_metadata_field(
    object_data: Union[LLM_TeamTable, GenerateKeyRequest],
    field_name: str,
    value: Any,
) -> None:
    """
    Helper function to set metadata fields that require premium user checks

    Args:
        object_data: The team data object to modify
        field_name: Name of the metadata field to set
        value: Value to set for the field
    """
    if field_name in LLM_ManagementEndpoint_MetadataFields_Premium:
        _premium_user_check()
    object_data.metadata = object_data.metadata or {}
    object_data.metadata[field_name] = value
