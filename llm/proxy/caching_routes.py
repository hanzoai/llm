from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Request

import llm
from llm._logging import verbose_proxy_logger
from llm.caching.caching import RedisCache
from llm.llm_core_utils.safe_json_dumps import safe_dumps
from llm.llm_core_utils.sensitive_data_masker import SensitiveDataMasker
from llm.proxy._types import ProxyErrorTypes, ProxyException
from llm.proxy.auth.user_api_key_auth import user_api_key_auth
from llm.types.caching import CachePingResponse, HealthCheckCacheParams

masker = SensitiveDataMasker()

router = APIRouter(
    prefix="/cache",
    tags=["caching"],
)


def _extract_cache_params() -> Dict[str, Any]:
    """
    Safely extracts and cleans cache parameters.

    The health check UI needs to display specific cache parameters, to show users how they set up their cache.

    eg.
        {
            "host": "localhost",
            "port": 6379,
            "redis_kwargs": {"db": 0},
            "namespace": "test",
        }

    Returns:
        Dict containing cleaned and masked cache parameters
    """
    if llm.cache is None:
        return {}
    try:
        cache_params = vars(llm.cache.cache)
        cleaned_params = (
            HealthCheckCacheParams(**cache_params).model_dump() if cache_params else {}
        )
        return masker.mask_dict(cleaned_params)
    except (AttributeError, TypeError) as e:
        verbose_proxy_logger.debug(f"Error extracting cache params: {str(e)}")
        return {}


@router.get(
    "/ping",
    response_model=CachePingResponse,
    dependencies=[Depends(user_api_key_auth)],
)
async def cache_ping():
    """
    Endpoint for checking if cache can be pinged
    """
    llm_cache_params: Dict[str, Any] = {}
    cleaned_cache_params: Dict[str, Any] = {}
    try:
        if llm.cache is None:
            raise HTTPException(
                status_code=503, detail="Cache not initialized. llm.cache is None"
            )
        llm_cache_params = masker.mask_dict(vars(llm.cache))
        # remove field that might reference itself
        llm_cache_params.pop("cache", None)
        cleaned_cache_params = _extract_cache_params()

        if llm.cache.type == "redis":
            ping_response = await llm.cache.ping()
            verbose_proxy_logger.debug(
                "/cache/ping: ping_response: " + str(ping_response)
            )
            # add cache does not return anything
            await llm.cache.async_add_cache(
                result="test_key",
                model="test-model",
                messages=[{"role": "user", "content": "test from llm"}],
            )
            verbose_proxy_logger.debug("/cache/ping: done with set_cache()")

            return CachePingResponse(
                status="healthy",
                cache_type=str(llm.cache.type),
                ping_response=True,
                set_cache_response="success",
                llm_cache_params=safe_dumps(llm_cache_params),
                health_check_cache_params=cleaned_cache_params,
            )
        else:
            return CachePingResponse(
                status="healthy",
                cache_type=str(llm.cache.type),
                llm_cache_params=safe_dumps(llm_cache_params),
            )
    except Exception as e:
        import traceback

        traceback.print_exc()
        error_message = {
            "message": f"Service Unhealthy ({str(e)})",
            "llm_cache_params": safe_dumps(llm_cache_params),
            "health_check_cache_params": safe_dumps(cleaned_cache_params),
            "traceback": traceback.format_exc(),
        }
        raise ProxyException(
            message=safe_dumps(error_message),
            type=ProxyErrorTypes.cache_ping_error,
            param="cache_ping",
            code=503,
        )


@router.post(
    "/delete",
    tags=["caching"],
    dependencies=[Depends(user_api_key_auth)],
)
async def cache_delete(request: Request):
    """
    Endpoint for deleting a key from the cache. All responses from llm proxy have `x-llm-cache-key` in the headers

    Parameters:
    - **keys**: *Optional[List[str]]* - A list of keys to delete from the cache. Example {"keys": ["key1", "key2"]}

    ```shell
    curl -X POST "http://0.0.0.0:4000/cache/delete" \
    -H "Authorization: Bearer sk-1234" \
    -d '{"keys": ["key1", "key2"]}'
    ```

    """
    try:
        if llm.cache is None:
            raise HTTPException(
                status_code=503, detail="Cache not initialized. llm.cache is None"
            )

        request_data = await request.json()
        keys = request_data.get("keys", None)

        if llm.cache.type == "redis":
            await llm.cache.delete_cache_keys(keys=keys)
            return {
                "status": "success",
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Cache type {llm.cache.type} does not support deleting a key. only `redis` is supported",
            )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Cache Delete Failed({str(e)})",
        )


@router.get(
    "/redis/info",
    dependencies=[Depends(user_api_key_auth)],
)
async def cache_redis_info():
    """
    Endpoint for getting /redis/info
    """
    try:
        if llm.cache is None:
            raise HTTPException(
                status_code=503, detail="Cache not initialized. llm.cache is None"
            )
        if llm.cache.type == "redis" and isinstance(
            llm.cache.cache, RedisCache
        ):
            client_list = llm.cache.cache.client_list()
            redis_info = llm.cache.cache.info()
            num_clients = len(client_list)
            return {
                "num_clients": num_clients,
                "clients": client_list,
                "info": redis_info,
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Cache type {llm.cache.type} does not support flushing",
            )
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Service Unhealthy ({str(e)})",
        )


@router.post(
    "/flushall",
    tags=["caching"],
    dependencies=[Depends(user_api_key_auth)],
)
async def cache_flushall():
    """
    A function to flush all items from the cache. (All items will be deleted from the cache with this)
    Raises HTTPException if the cache is not initialized or if the cache type does not support flushing.
    Returns a dictionary with the status of the operation.

    Usage:
    ```
    curl -X POST http://0.0.0.0:4000/cache/flushall -H "Authorization: Bearer sk-1234"
    ```
    """
    try:
        if llm.cache is None:
            raise HTTPException(
                status_code=503, detail="Cache not initialized. llm.cache is None"
            )
        if llm.cache.type == "redis" and isinstance(
            llm.cache.cache, RedisCache
        ):
            llm.cache.cache.flushall()
            return {
                "status": "success",
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Cache type {llm.cache.type} does not support flushing",
            )
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Service Unhealthy ({str(e)})",
        )
