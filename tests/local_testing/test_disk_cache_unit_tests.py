from cache_unit_tests import LLMCachingUnitTests
from llm.caching import LLMCacheType


class TestDiskCacheUnitTests(LLMCachingUnitTests):
    def get_cache_type(self) -> LLMCacheType:
        return LLMCacheType.DISK


# if __name__ == "__main__":
#     pytest.main([__file__, "-v", "-s"])
