import os
import sys
import traceback

sys.path.insert(
    0, os.path.abspath("../..")
)  # Adds the parent directory to the system path
import llm
from llm.proxy.guardrails.init_guardrails import init_guardrails_v2


def test_guardrails_ai():
    llm.set_verbose = True
    llm.guardrail_name_config_map = {}

    init_guardrails_v2(
        all_guardrails=[
            {
                "guardrail_name": "gibberish-guard",
                "llm_params": {
                    "guardrail": "guardrails_ai",
                    "guard_name": "gibberish_guard",
                    "mode": "post_call",
                },
            }
        ],
        config_file_path="",
    )
