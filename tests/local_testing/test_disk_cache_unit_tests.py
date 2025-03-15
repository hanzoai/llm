from cache_unit_tests import LLMCachingUnitTests
from llm.caching import HanzoCacheType


class TestDiskCacheUnitTests(LLMCachingUnitTests):
    def get_cache_type(self) -> HanzoCacheType:
        return HanzoCacheType.DISK


# if __name__ == "__main__":
#     pytest.main([__file__, "-v", "-s"])
