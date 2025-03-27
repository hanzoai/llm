# ✨ Temporary Budget Increase

Set temporary budget increase for a LLM Virtual Key. Use this if you get asked to increase the budget for a key temporarily.


| Heirarchy | Supported | 
|-----------|-----------|
| LLM Virtual Key | ✅ |
| User | ❌ |
| Team | ❌ |
| Organization | ❌ |

:::note

✨ Temporary Budget Increase is a LLM Enterprise feature.

[Enterprise Pricing](https://www.hanzo.ai/#pricing)

[Get free 7-day trial key](https://www.hanzo.ai/#trial)

:::


1. Create a LLM Virtual Key with budget

```bash
curl -L -X POST 'http://localhost:4000/key/generate' \
-H 'Content-Type: application/json' \
-H 'Authorization: Bearer LLM_MASTER_KEY' \
-d '{
    "max_budget": 0.0000001
}'
```

Expected response:

```json
{
    "key": "sk-your-new-key"
}
```

2. Update key with temporary budget increase

```bash
curl -L -X POST 'http://localhost:4000/key/update' \
-H 'Authorization: Bearer LLM_MASTER_KEY' \
-H 'Content-Type: application/json' \
-d '{
    "key": "sk-your-new-key",
    "temp_budget_increase": 100, 
    "temp_budget_expiry": "2025-01-15"
}'
```

3. Test it! 

```bash
curl -L -X POST 'http://localhost:4000/chat/completions' \
-H 'Authorization: Bearer sk-your-new-key' \
-H 'Content-Type: application/json' \
-d '{
    "model": "gpt-4o",
    "messages": [{"role": "user", "content": "Hello, world!"}]
}'
```

Expected Response Header:

```
x-llm-key-max-budget: 100.0000001
```


