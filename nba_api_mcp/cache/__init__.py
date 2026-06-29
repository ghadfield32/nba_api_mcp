# nba_mcp/cache/__init__.py
"""
Caching layer for NBA MCP.

Provides Redis-based caching with TTL tiers, fallback cache, and compression.

Features:
- Redis cache with connection pooling
- In-memory LRU fallback cache
- Automatic compression for large payloads
- Smart TTL selection based on season
- Cache statistics and monitoring
- Async adapter compatible with basketball_mcp_core CacheInterface
"""

from .redis_cache import (
    CacheTier,
    LRUCache,
    RedisCache,
    cached,
    close_cache,
    compress_value,
    decompress_value,
    generate_cache_key,
    get_cache,
    get_smart_tier,
    initialize_cache,
    with_cache,
)

# Async adapter for basketball_mcp_core compatibility
from .cache_adapter import (
    AsyncCacheAdapter,
    get_async_cache,
    get_ttl_for_data_type,
    reset_async_cache,
    CORE_AVAILABLE as CACHE_CORE_AVAILABLE,
)

__all__ = [
    # Original exports
    "RedisCache",
    "LRUCache",
    "CacheTier",
    "cached",
    "with_cache",
    "generate_cache_key",
    "get_smart_tier",
    "compress_value",
    "decompress_value",
    "initialize_cache",
    "get_cache",
    "close_cache",
    # New async adapter exports
    "AsyncCacheAdapter",
    "get_async_cache",
    "get_ttl_for_data_type",
    "reset_async_cache",
    "CACHE_CORE_AVAILABLE",
]
