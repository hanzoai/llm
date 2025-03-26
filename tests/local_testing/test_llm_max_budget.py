# #### What this tests ####
# #    This tests calling llm.max_budget by making back-to-back gpt-4 calls
# # commenting out this test for circle ci, as it causes other tests to fail, since llm.max_budget would impact other llm imports
# import sys, os, json
# import traceback
# import pytest

# sys.path.insert(
#     0, os.path.abspath("../..")
# )  # Adds the parent directory to the system path
# import llm
# # llm.set_verbose = True
# from llm import completion, BudgetExceededError

# def test_max_budget():
#     try:
#         llm.max_budget = 0.001 # sets a max budget of $0.001

#         messages = [{"role": "user", "content": "Hey, how's it going"}]
#         response = completion(model="gpt-4", messages=messages, stream=True)
#         for chunk in response:
#             continue
#         print(llm._current_cost)
#         completion(model="gpt-4", messages=messages, stream=True)
#         llm.max_budget = float('inf')
#     except BudgetExceededError as e:
#         pass
#     except Exception as e:
#         pytest.fail(f"An error occured: {str(e)}")
