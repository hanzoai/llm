# What is this?
## This tests the blocked user pre call hook for the proxy server


import sys, os, asyncio, time, random
from datetime import datetime
import traceback
from dotenv import load_dotenv

load_dotenv()
import os

sys.path.insert(
    0, os.path.abspath("../..")
)  # Adds the parent directory to the system path
import pytest
import llm
from llm.proxy.enterprise.enterprise_hooks.banned_keywords import (
    _ENTERPRISE_BannedKeywords,
)
from llm import Router, mock_completion
from llm.proxy.utils import ProxyLogging, hash_token
from llm.proxy._types import UserAPIKeyAuth
from llm.caching.caching import DualCache


@pytest.mark.asyncio
async def test_banned_keywords_check():
    """
    - Set some banned keywords as a llm module value
    - Test to see if a call with banned keywords is made, an error is raised
    - Test to see if a call without banned keywords is made it passes
    """
    llm.banned_keywords_list = ["hello"]

    banned_keywords_obj = _ENTERPRISE_BannedKeywords()

    _api_key = "sk-12345"
    _api_key = hash_token("sk-12345")
    user_api_key_dict = UserAPIKeyAuth(api_key=_api_key)
    local_cache = DualCache()

    ## Case 1: blocked user id passed
    try:
        await banned_keywords_obj.async_pre_call_hook(
            user_api_key_dict=user_api_key_dict,
            cache=local_cache,
            call_type="completion",
            data={"messages": [{"role": "user", "content": "Hello world"}]},
        )
        pytest.fail(f"Expected call to fail")
    except Exception as e:
        pass

    ## Case 2: normal user id passed
    try:
        await banned_keywords_obj.async_pre_call_hook(
            user_api_key_dict=user_api_key_dict,
            cache=local_cache,
            call_type="completion",
            data={"messages": [{"role": "user", "content": "Hey, how's it going?"}]},
        )
    except Exception as e:
        pytest.fail(f"An error occurred - {str(e)}")
