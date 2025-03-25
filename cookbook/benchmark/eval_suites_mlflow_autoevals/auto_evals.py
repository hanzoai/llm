from dotenv import load_dotenv

load_dotenv()

import llm

from autoevals.llm import *

###################

# llm completion call
question = "which country has the highest population"
response = llm.completion(
    model="gpt-3.5-turbo",
    messages=[{"role": "user", "content": question}],
)
print(response)
# use the auto eval Factuality() evaluator

print("calling evaluator")
evaluator = Factuality()
result = evaluator(
    output=response.choices[0]["message"][
        "content"
    ],  # response from llm.completion()
    expected="India",  # expected output
    input=question,  # question passed to llm.completion
)

print(result)
