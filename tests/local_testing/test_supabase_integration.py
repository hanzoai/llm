#### What this tests ####
#    This tests if logging to the supabase integration actually works
import sys, os
import traceback
import pytest

sys.path.insert(
    0, os.path.abspath("../..")
)  # Adds the parent directory to the system path
import llm
from llm import embedding, completion

llm.input_callback = ["supabase"]
llm.success_callback = ["supabase"]
llm.failure_callback = ["supabase"]


llm.set_verbose = False


def test_supabase_logging():
    try:
        response = completion(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Hello tell me hi"}],
            user="zRegular",
            max_tokens=10,
        )
        print(response)
    except Exception as e:
        print(e)


# test_supabase_logging()


def test_acompletion_sync():
    import asyncio
    import time

    async def completion_call():
        try:
            response = await llm.acompletion(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "write a poem"}],
                max_tokens=10,
                stream=True,
                user="zStreamingUser",
                timeout=5,
            )
            complete_response = ""
            start_time = time.time()
            async for chunk in response:
                chunk_time = time.time()
                # print(chunk)
                complete_response += chunk["choices"][0]["delta"].get("content", "")
                # print(complete_response)
                # print(f"time since initial request: {chunk_time - start_time:.5f}")

                if chunk["choices"][0].get("finish_reason", None) != None:
                    print("🤗🤗🤗 DONE")
                    return

        except llm.Timeout as e:
            pass
        except Exception:
            print(f"error occurred: {traceback.format_exc()}")
            pass

    asyncio.run(completion_call())


# test_acompletion_sync()


# reset callbacks
llm.input_callback = []
llm.success_callback = []
llm.failure_callback = []
