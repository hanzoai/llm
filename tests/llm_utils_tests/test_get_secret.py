import json
import os
import sys
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

sys.path.insert(
    0, os.path.abspath("../..")
)  # Adds the parent directory to the system path
import pytest

import llm
from llm.proxy._types import KeyManagementSystem
from llm.secret_managers.main import get_secret


class MockSecretClient:
    def get_secret(self, secret_name):
        return Mock(value="mocked_secret_value")


@pytest.mark.asyncio
async def test_azure_kms():
    """
    Basic asserts that the value from get secret is from Azure Key Vault when Key Management System is Azure Key Vault
    """
    with patch("llm.secret_manager_client", new=MockSecretClient()):
        llm._key_management_system = KeyManagementSystem.AZURE_KEY_VAULT
        secret = get_secret(secret_name="z-test-key")
        assert secret == "mocked_secret_value"
