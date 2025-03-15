import openai

client = openai.OpenAI(api_key="sk-1234", base_url="http://0.0.0.0:4000")

# # request sent to model set on llm proxy, `llm --model`
response = client.embeddings.create(
    model="text-embedding-ada-002", input=["test"], encoding_format="base64"
)

print(response)
