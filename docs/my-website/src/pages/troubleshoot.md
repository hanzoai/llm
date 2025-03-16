# Troubleshooting 

## Stable Version

If you're running into problems with installation / Usage 
Use the stable version of llm 

```
pip install llm==0.1.345
```

## Rename from litellm to llm

If you're experiencing issues after the rename from `litellm` to `llm`, please check the following:

1. Make sure you're using the correct import statements in your code:
   ```python
   # Old
   import litellm
   
   # New
   import llm
   ```

2. Update any references in your configuration files or environment variables:
   ```
   # Old
   LITELLM_API_KEY=...
   
   # New
   LLM_API_KEY=...
   ```

3. If you're using Docker, make sure to pull the latest image with the new name.

4. Check your requirements.txt or pyproject.toml files to ensure they reference the new package name.

If you continue to experience issues, please open an issue on our GitHub repository.