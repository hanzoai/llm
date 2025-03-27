# Caching on LLM

LLM supports multiple caching mechanisms. This allows users to choose the most suitable caching solution for their use case.

The following caching mechanisms are supported:

1. **RedisCache**
2. **RedisSemanticCache**
3. **QdrantSemanticCache**
4. **InMemoryCache**
5. **DiskCache**
6. **S3Cache**
7. **DualCache** (updates both Redis and an in-memory cache simultaneously)

## Folder Structure

```
llm/caching/
├── base_cache.py
├── caching.py
├── caching_handler.py
├── disk_cache.py
├── dual_cache.py
├── in_memory_cache.py
├── qdrant_semantic_cache.py
├── redis_cache.py
├── redis_semantic_cache.py
├── s3_cache.py
```

## Documentation
- [Caching on LLM Gateway](https://docs.hanzo.ai/docs/proxy/caching)
- [Caching on LLM Python](https://docs.hanzo.ai/docs/caching/all_caches)







