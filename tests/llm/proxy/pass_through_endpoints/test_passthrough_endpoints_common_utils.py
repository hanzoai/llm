import json
import os
import sys
import traceback
from unittest import mock
from unittest.mock import MagicMock, patch

import httpx
import pytest
from fastapi import Request, Response
from fastapi.testclient import TestClient

sys.path.insert(
    0, os.path.abspath("../../../..")
)  # Adds the parent directory to the system path

from unittest.mock import Mock

from llm.proxy.pass_through_endpoints.common_utils import get_llm_virtual_key


@pytest.mark.asyncio
async def test_get_llm_virtual_key():
    """
    Test that the get_llm_virtual_key function correctly handles the API key authentication
    """
    # Test with x-llm-api-key
    mock_request = Mock()
    mock_request.headers = {"x-llm-api-key": "test-key-123"}
    result = get_llm_virtual_key(mock_request)
    assert result == "Bearer test-key-123"

    # Test with Authorization header
    mock_request.headers = {"Authorization": "Bearer auth-key-456"}
    result = get_llm_virtual_key(mock_request)
    assert result == "Bearer auth-key-456"

    # Test with both headers (x-llm-api-key should take precedence)
    mock_request.headers = {
        "x-llm-api-key": "test-key-123",
        "Authorization": "Bearer auth-key-456",
    }
    result = get_llm_virtual_key(mock_request)
    assert result == "Bearer test-key-123"
