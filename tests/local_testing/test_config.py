# What is this?
## Unit tests for ProxyConfig class


import os
import sys
import traceback

from dotenv import load_dotenv

load_dotenv()
import io
import os

sys.path.insert(
    0, os.path.abspath("../..")
)  # Adds the parent directory to the system path
from typing import Literal

import pytest
from pydantic import BaseModel, ConfigDict

import llm
from llm.proxy.common_utils.encrypt_decrypt_utils import encrypt_value
from llm.proxy.proxy_server import ProxyConfig
from llm.proxy.utils import DualCache, ProxyLogging
from llm.types.router import Deployment, LLM_Params, ModelInfo


class DBModel(BaseModel):
    model_id: str
    model_name: str
    model_info: dict
    llm_params: dict

    model_config = ConfigDict(protected_namespaces=())


@pytest.mark.asyncio
async def test_delete_deployment():
    """
    - Ensure the global llm router is not being reset
    - Ensure invalid model is deleted
    - Check if model id != model_info["id"], the model_info["id"] is picked
    """
    import base64

    llm_params = LLM_Params(
        model="azure/chatgpt-v-2",
        api_key=os.getenv("AZURE_API_KEY"),
        api_base=os.getenv("AZURE_API_BASE"),
        api_version=os.getenv("AZURE_API_VERSION"),
    )
    encrypted_llm_params = llm_params.dict(exclude_none=True)

    master_key = "sk-1234"

    setattr(llm.proxy.proxy_server, "master_key", master_key)

    for k, v in encrypted_llm_params.items():
        if isinstance(v, str):
            encrypted_value = encrypt_value(v, master_key)
            encrypted_llm_params[k] = base64.b64encode(encrypted_value).decode(
                "utf-8"
            )

    deployment = Deployment(model_name="gpt-3.5-turbo", llm_params=llm_params)
    deployment_2 = Deployment(
        model_name="gpt-3.5-turbo-2", llm_params=llm_params
    )

    llm_router = llm.Router(
        model_list=[
            deployment.to_json(exclude_none=True),
            deployment_2.to_json(exclude_none=True),
        ]
    )
    setattr(llm.proxy.proxy_server, "llm_router", llm_router)
    print(f"llm_router: {llm_router}")

    pc = ProxyConfig()

    db_model = DBModel(
        model_id=deployment.model_info.id,
        model_name="gpt-3.5-turbo",
        llm_params=encrypted_llm_params,
        model_info={"id": deployment.model_info.id},
    )

    db_models = [db_model]
    deleted_deployments = await pc._delete_deployment(db_models=db_models)

    assert deleted_deployments == 1
    assert len(llm_router.model_list) == 1

    """
    Scenario 2 - if model id != model_info["id"]
    """

    llm_router = llm.Router(
        model_list=[
            deployment.to_json(exclude_none=True),
            deployment_2.to_json(exclude_none=True),
        ]
    )
    print(f"llm_router: {llm_router}")
    setattr(llm.proxy.proxy_server, "llm_router", llm_router)
    pc = ProxyConfig()

    db_model = DBModel(
        model_id=deployment.model_info.id,
        model_name="gpt-3.5-turbo",
        llm_params=encrypted_llm_params,
        model_info={"id": deployment.model_info.id},
    )

    db_models = [db_model]
    deleted_deployments = await pc._delete_deployment(db_models=db_models)

    assert deleted_deployments == 1
    assert len(llm_router.model_list) == 1


@pytest.mark.asyncio
async def test_add_existing_deployment():
    """
    - Only add new models
    - don't re-add existing models
    """
    import base64

    llm_params = LLM_Params(
        model="gpt-3.5-turbo",
        api_key=os.getenv("AZURE_API_KEY"),
        api_base=os.getenv("AZURE_API_BASE"),
        api_version=os.getenv("AZURE_API_VERSION"),
    )
    deployment = Deployment(model_name="gpt-3.5-turbo", llm_params=llm_params)
    deployment_2 = Deployment(
        model_name="gpt-3.5-turbo-2", llm_params=llm_params
    )

    llm_router = llm.Router(
        model_list=[
            deployment.to_json(exclude_none=True),
            deployment_2.to_json(exclude_none=True),
        ]
    )

    init_len_list = len(llm_router.model_list)
    print(f"llm_router: {llm_router}")
    master_key = "sk-1234"
    setattr(llm.proxy.proxy_server, "llm_router", llm_router)
    setattr(llm.proxy.proxy_server, "master_key", master_key)
    pc = ProxyConfig()

    encrypted_llm_params = llm_params.dict(exclude_none=True)

    for k, v in encrypted_llm_params.items():
        if isinstance(v, str):
            encrypted_value = encrypt_value(v, master_key)
            encrypted_llm_params[k] = base64.b64encode(encrypted_value).decode(
                "utf-8"
            )
    db_model = DBModel(
        model_id=deployment.model_info.id,
        model_name="gpt-3.5-turbo",
        llm_params=encrypted_llm_params,
        model_info={"id": deployment.model_info.id},
    )

    db_models = [db_model]
    num_added = pc._add_deployment(db_models=db_models)

    assert init_len_list == len(llm_router.model_list)


@pytest.mark.asyncio
async def test_db_error_new_model_check():
    """
    - if error in db, don't delete existing models

    Relevant issue: https://github.com/hanzoai/llm/blob/ddfe687b13e9f31db2fb2322887804e3d01dd467/llm/proxy/proxy_server.py#L2461
    """
    import base64

    llm_params = LLM_Params(
        model="gpt-3.5-turbo",
        api_key=os.getenv("AZURE_API_KEY"),
        api_base=os.getenv("AZURE_API_BASE"),
        api_version=os.getenv("AZURE_API_VERSION"),
    )
    deployment = Deployment(model_name="gpt-3.5-turbo", llm_params=llm_params)
    deployment_2 = Deployment(
        model_name="gpt-3.5-turbo-2", llm_params=llm_params
    )

    llm_router = llm.Router(
        model_list=[
            deployment.to_json(exclude_none=True),
            deployment_2.to_json(exclude_none=True),
        ]
    )

    init_len_list = len(llm_router.model_list)
    print(f"llm_router: {llm_router}")
    master_key = "sk-1234"
    setattr(llm.proxy.proxy_server, "llm_router", llm_router)
    setattr(llm.proxy.proxy_server, "master_key", master_key)
    pc = ProxyConfig()

    encrypted_llm_params = llm_params.dict(exclude_none=True)

    for k, v in encrypted_llm_params.items():
        if isinstance(v, str):
            encrypted_value = encrypt_value(v, master_key)
            encrypted_llm_params[k] = base64.b64encode(encrypted_value).decode(
                "utf-8"
            )
    db_model = DBModel(
        model_id=deployment.model_info.id,
        model_name="gpt-3.5-turbo",
        llm_params=encrypted_llm_params,
        model_info={"id": deployment.model_info.id},
    )

    db_models = []
    deleted_deployments = await pc._delete_deployment(db_models=db_models)
    assert deleted_deployments == 0

    assert init_len_list == len(llm_router.model_list)


llm_params = LLM_Params(
    model="azure/chatgpt-v-2",
    api_key=os.getenv("AZURE_API_KEY"),
    api_base=os.getenv("AZURE_API_BASE"),
    api_version=os.getenv("AZURE_API_VERSION"),
)

deployment = Deployment(model_name="gpt-3.5-turbo", llm_params=llm_params)
deployment_2 = Deployment(model_name="gpt-3.5-turbo-2", llm_params=llm_params)


def _create_model_list(flag_value: Literal[0, 1], master_key: str):
    """
    0 - empty list
    1 - list with an element
    """
    import base64

    new_llm_params = LLM_Params(
        model="azure/chatgpt-v-2-3",
        api_key=os.getenv("AZURE_API_KEY"),
        api_base=os.getenv("AZURE_API_BASE"),
        api_version=os.getenv("AZURE_API_VERSION"),
    )

    encrypted_llm_params = new_llm_params.dict(exclude_none=True)

    for k, v in encrypted_llm_params.items():
        if isinstance(v, str):
            encrypted_value = encrypt_value(v, master_key)
            encrypted_llm_params[k] = base64.b64encode(encrypted_value).decode(
                "utf-8"
            )
    db_model = DBModel(
        model_id="12345",
        model_name="gpt-3.5-turbo",
        llm_params=encrypted_llm_params,
        model_info={"id": "12345"},
    )

    db_models = [db_model]

    if flag_value == 0:
        return []
    elif flag_value == 1:
        return db_models


@pytest.mark.parametrize(
    "llm_router",
    [
        None,
        llm.Router(),
        llm.Router(
            model_list=[
                deployment.to_json(exclude_none=True),
                deployment_2.to_json(exclude_none=True),
            ]
        ),
    ],
)
@pytest.mark.parametrize(
    "model_list_flag_value",
    [0, 1],
)
@pytest.mark.asyncio
async def test_add_and_delete_deployments(llm_router, model_list_flag_value):
    """
    Test add + delete logic in 3 scenarios
    - when router is none
    - when router is init but empty
    - when router is init and not empty
    """

    master_key = "sk-1234"
    setattr(llm.proxy.proxy_server, "llm_router", llm_router)
    setattr(llm.proxy.proxy_server, "master_key", master_key)
    pc = ProxyConfig()
    pl = ProxyLogging(DualCache())

    async def _monkey_patch_get_config(*args, **kwargs):
        print(f"ENTERS MP GET CONFIG")
        if llm_router is None:
            return {}
        else:
            print(f"llm_router.model_list: {llm_router.model_list}")
            return {"model_list": llm_router.model_list}

    pc.get_config = _monkey_patch_get_config

    model_list = _create_model_list(
        flag_value=model_list_flag_value, master_key=master_key
    )

    if llm_router is None:
        prev_llm_router_val = None
    else:
        prev_llm_router_val = len(llm_router.model_list)

    await pc._update_llm_router(new_models=model_list, proxy_logging_obj=pl)

    llm_router = getattr(llm.proxy.proxy_server, "llm_router")

    if model_list_flag_value == 0:
        if prev_llm_router_val is None:
            assert prev_llm_router_val == llm_router
        else:
            assert prev_llm_router_val == len(llm_router.model_list)
    else:
        if prev_llm_router_val is None:
            assert len(llm_router.model_list) == len(model_list)
        else:
            assert len(llm_router.model_list) == len(model_list) + prev_llm_router_val


from llm import LLM_CHAT_PROVIDERS, LLMProviders
from llm.utils import ProviderConfigManager
from llm.llms.base_llm.chat.transformation import BaseConfig


def _check_provider_config(config: BaseConfig, provider: LLMProviders):
    assert isinstance(
        config,
        BaseConfig,
    ), f"Provider {provider} is not a subclass of BaseConfig. Got={config}"

    if (
        provider != llm.LLMProviders.OPENAI
        and provider != llm.LLMProviders.OPENAI_LIKE
        and provider != llm.LLMProviders.CUSTOM_OPENAI
    ):
        assert (
            config.__class__.__name__ != "OpenAIGPTConfig"
        ), f"Provider {provider} is an instance of OpenAIGPTConfig"

    assert "_abc_impl" not in config.get_config(), f"Provider {provider} has _abc_impl"


def test_provider_config_manager_bedrock_converse_like():
    from llm.llms.bedrock.chat.converse_transformation import AmazonConverseConfig

    config = ProviderConfigManager.get_provider_chat_config(
        model="bedrock/converse_like/us.amazon.nova-pro-v1:0",
        provider=LLMProviders.BEDROCK,
    )
    print(f"config: {config}")
    assert isinstance(config, AmazonConverseConfig)


# def test_provider_config_manager():
#     from llm.llms.openai.chat.gpt_transformation import OpenAIGPTConfig

#     for provider in LLM_CHAT_PROVIDERS:
#         if (
#             provider == LLMProviders.VERTEX_AI
#             or provider == LLMProviders.VERTEX_AI_BETA
#             or provider == LLMProviders.BEDROCK
#             or provider == LLMProviders.BASETEN
#             or provider == LLMProviders.PETALS
#             or provider == LLMProviders.SAGEMAKER
#             or provider == LLMProviders.SAGEMAKER_CHAT
#             or provider == LLMProviders.VLLM
#             or provider == LLMProviders.OLLAMA
#         ):
#             continue

#         config = ProviderConfigManager.get_provider_chat_config(
#             model="gpt-3.5-turbo", provider=LLMProviders(provider)
#         )
#         _check_provider_config(config, provider)
