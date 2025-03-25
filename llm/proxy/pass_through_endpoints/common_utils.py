from fastapi import Request


def get_litellm_virtual_key(request: Request) -> str:
    """
    Extract and format API key from request headers.
    Prioritizes x-llm-api-key over Authorization header.


    Vertex JS SDK uses `Authorization` header, we use `x-llm-api-key` to pass llm virtual key

    """
    llm_api_key = request.headers.get("x-llm-api-key")
    if llm_api_key:
        return f"Bearer {llm_api_key}"
    return request.headers.get("Authorization", "")
