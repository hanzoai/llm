import asyncio
import os
import subprocess
import sys
import time
import traceback

import pytest

sys.path.insert(
    0, os.path.abspath("../..")
)  # Adds the parent directory to the system path


def test_using_llm():
    try:
        import llm

        print("llm imported successfully")
    except Exception as e:
        pytest.fail(
            f"Error occurred: {e}. Installing llm on python3.8 failed please retry"
        )


def test_llm_proxy_server():
    # Install the llm[proxy] package
    subprocess.run(["pip", "install", "llm[proxy]"])

    # Import the proxy_server module
    try:
        import llm.proxy.proxy_server
    except ImportError:
        pytest.fail("Failed to import llm.proxy_server")

    # Assertion to satisfy the test, you can add other checks as needed
    assert True


def test_package_dependencies():
    try:
        import tomli
        import pathlib
        import llm

        # Get the llm package root path
        llm_path = pathlib.Path(llm.__file__).parent.parent
        pyproject_path = llm_path / "pyproject.toml"

        # Read and parse pyproject.toml
        with open(pyproject_path, "rb") as f:
            pyproject = tomli.load(f)

        # Get all optional dependencies from poetry.dependencies
        poetry_deps = pyproject["tool"]["poetry"]["dependencies"]
        optional_deps = {
            name.lower()
            for name, value in poetry_deps.items()
            if isinstance(value, dict) and value.get("optional", False)
        }
        print(optional_deps)
        # Get all packages listed in extras
        extras = pyproject["tool"]["poetry"]["extras"]
        all_extra_deps = set()
        for extra_group in extras.values():
            all_extra_deps.update(dep.lower() for dep in extra_group)
        print(all_extra_deps)
        # Check that all optional dependencies are in some extras group
        missing_from_extras = optional_deps - all_extra_deps
        assert (
            not missing_from_extras
        ), f"Optional dependencies missing from extras: {missing_from_extras}"

        print(
            f"All {len(optional_deps)} optional dependencies are correctly specified in extras"
        )

    except Exception as e:
        pytest.fail(
            f"Error occurred while checking dependencies: {str(e)}\n"
            + traceback.format_exc()
        )


import os
import subprocess
import time

import pytest
import requests


def test_llm_proxy_server_config_no_general_settings():
    # Install the llm[proxy] package
    # Start the server
    try:
        subprocess.run(["pip", "install", "llm[proxy]"])
        subprocess.run(["pip", "install", "llm[extra_proxy]"])
        filepath = os.path.dirname(os.path.abspath(__file__))
        config_fp = f"{filepath}/test_configs/test_config_no_auth.yaml"
        server_process = subprocess.Popen(
            [
                "python",
                "-m",
                "llm.proxy.proxy_cli",
                "--config",
                config_fp,
            ]
        )

        # Allow some time for the server to start
        time.sleep(60)  # Adjust the sleep time if necessary

        # Send a request to the /health/liveliness endpoint
        response = requests.get("http://localhost:4000/health/liveliness")

        # Check if the response is successful
        assert response.status_code == 200
        assert response.json() == "I'm alive!"

        # Test /chat/completions
        response = requests.post(
            "http://localhost:4000/chat/completions",
            headers={"Authorization": "Bearer 1234567890"},
            json={
                "model": "test_openai_models",
                "messages": [{"role": "user", "content": "Hello, how are you?"}],
            },
        )

        assert response.status_code == 200

    except ImportError:
        pytest.fail("Failed to import llm.proxy_server")
    except requests.ConnectionError:
        pytest.fail("Failed to connect to the server")
    finally:
        # Shut down the server
        server_process.terminate()
        server_process.wait()

    # Additional assertions can be added here
    assert True
