from typing import TYPE_CHECKING, Any, Dict, Optional, TypedDict

from llm.types.utils import StandardLoggingPayload

if TYPE_CHECKING:
    from llm.llms.vertex_ai.vertex_llm_base import VertexBase
else:
    VertexBase = Any


class GCSLoggingConfig(TypedDict):
    """
    Internal Hanzo Config for GCS Bucket logging
    """

    bucket_name: str
    vertex_instance: VertexBase
    path_service_account: Optional[str]


class GCSLogQueueItem(TypedDict):
    """
    Internal Type, used for queueing logs to be sent to GCS Bucket
    """

    payload: StandardLoggingPayload
    kwargs: Dict[str, Any]
    response_obj: Optional[Any]
