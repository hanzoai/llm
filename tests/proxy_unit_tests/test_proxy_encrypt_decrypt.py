import os
import sys

import pytest
from dotenv import load_dotenv

load_dotenv()
import io
import os

sys.path.insert(
    0, os.path.abspath("../..")
)  # Adds-the parent directory to the system path

from llm.proxy import proxy_server
from llm.proxy.common_utils.encrypt_decrypt_utils import (
    decrypt_value_helper,
    encrypt_value_helper,
)


def test_encrypt_decrypt_with_master_key():
    setattr(proxy_server, "master_key", "sk-1234")
    assert decrypt_value_helper(encrypt_value_helper("test")) == "test"
    assert decrypt_value_helper(encrypt_value_helper(10)) == 10
    assert decrypt_value_helper(encrypt_value_helper(True)) is True
    assert decrypt_value_helper(encrypt_value_helper(None)) is None
    assert decrypt_value_helper(encrypt_value_helper({"rpm": 10})) == {"rpm": 10}

    # encryption should actually occur for strings
    assert encrypt_value_helper("test") != "test"


def test_encrypt_decrypt_with_salt_key():
    os.environ["LLM_SALT_KEY"] = "sk-salt-key2222"
    print(f"LLM_SALT_KEY: {os.environ['LLM_SALT_KEY']}")
    assert decrypt_value_helper(encrypt_value_helper("test")) == "test"
    assert decrypt_value_helper(encrypt_value_helper(10)) == 10
    assert decrypt_value_helper(encrypt_value_helper(True)) is True
    assert decrypt_value_helper(encrypt_value_helper(None)) is None
    assert decrypt_value_helper(encrypt_value_helper({"rpm": 10})) == {"rpm": 10}

    # encryption should actually occur for strings
    assert encrypt_value_helper("test") != "test"

    os.environ.pop("LLM_SALT_KEY", None)
