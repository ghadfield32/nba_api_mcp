"""
Cache Adapter for basketball_mcp_core Compatibility.

Provides an adapter that wraps the existing RedisCache to implement
the basketball_mcp_core CacheInterface protocol.

This enables:
1. Using the unified CacheTier and SWR_WINDOWS from basketball_mcp_core
2. Maintaining backward compatibility with existing nba_api_mcp code
3. Consistent caching patterns across both MCP servers

Usage:
    from nba_api_mcp.cache.cache_adapter import (
        AsyncCacheAdapter,
        get_async_cache,
        CacheTier,
    )

    # Get async-compatible cache
    cache = get_async_cache()
    await cache.set("key", value, ttl=CacheTier.DAILY.value)
    value = await cache.get("key")
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

from nba_api_mcp.cache.redis_cache import RedisCache, get_cache, initialize_cache

logger = logging.getLogger(__name__)

# Try to import from basketball_mcp_core for unified types
try:
    from basketball_mcp_core.caching.interface import (
        CacheInterface,
        CacheTier,
        SWR_WINDOWS,
        get_ttl_for_data_type,
    )

    CORE_AVAILABLE = True
    logger.info("Using CacheTier from basketball_mcp_core")
except ImportError:
    # Fallback to local definitions
    CORE_AVAILABLE = False
    from nba_api_mcp.cache.redis_cache import CacheTier, SWR_WINDOWS

    # Stub for get_ttl_for_data_type
    def get_ttl_for_data_type(data_type: str) -> int:
        """Get TTL based on data type (fallback implementation)."""
        LIVE_DATA = {"live_scores", "in_progress", "scoreboard"}
        DAILY_DATA = {"standings", "today_games", "schedule_today"}
        STATIC_DATA = {"player_info", "team_info", "entities", "roster"}

        if data_type in LIVE_DATA:
            return CacheTier.LIVE.value
        elif data_type in DAILY_DATA:
            return CacheTier.DAILY.value
        elif data_type in STATIC_DATA:
            return CacheTier.STATIC.value
        else:
            return CacheTier.HISTORICAL.value

    logger.debug("Using local CacheTier (basketball_mcp_core not installed)")


class AsyncCacheAdapter:
    """
    Async wrapper around RedisCache implementing CacheInterface protocol.

    This adapter converts the synchronous RedisCache methods to async,
    enabling compatibility with the basketball_mcp_core CacheInterface.

    Example:
        adapter = AsyncCacheAdapter()
        await adapter.set("player:123", data, ttl=CacheTier.DAILY.value)
        result = await adapter.get("player:123")
    """

    def __init__(self, redis_cache: Optional[RedisCache] = None):
        """
        Initialize async cache adapter.

        Args:
            redis_cache: Existing RedisCache instance (uses global if None)
        """
        self._cache = redis_cache or get_cache()
        if self._cache is None:
            # Initialize default cache if none exists
            self._cache = initialize_cache()
        logger.info("AsyncCacheAdapter initialized")

    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache (async).

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        # Run sync method in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._cache.get, key)

    async def set(self, key: str, value: Any, ttl: int) -> None:
        """
        Set value in cache with TTL (async).

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
        """
        loop = asyncio.get_event_loop()

        def _set():
            # Determine tier from TTL for logging
            tier = None
            for t in CacheTier:
                if t.value == ttl:
                    tier = t
                    break
            self._cache.set(key, value, ttl, tier)

        await loop.run_in_executor(None, _set)

    async def has(self, key: str) -> bool:
        """
        Check if key exists in cache (async).

        Args:
            key: Cache key

        Returns:
            True if key exists and not expired
        """
        result = await self.get(key)
        return result is not None

    async def delete(self, key: str) -> None:
        """
        Delete key from cache (async).

        Args:
            key: Cache key
        """
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._cache.delete, key)

    async def clear(self) -> None:
        """Clear all cache entries (async)."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._cache.clear)

    async def get_stats(self) -> dict:
        """Get cache statistics (async)."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._cache.get_stats)

    # SWR (Stale-While-Revalidate) methods
    async def set_with_swr(
        self,
        key: str,
        value: Any,
        ttl: int,
        tier: CacheTier,
    ) -> None:
        """
        Set value with SWR support (async).

        Args:
            key: Cache key
            value: Value to cache
            ttl: Fresh TTL in seconds
            tier: Cache tier (for SWR window lookup)
        """
        loop = asyncio.get_event_loop()

        def _set_swr():
            self._cache.set_with_swr(key, value, ttl, tier)

        await loop.run_in_executor(None, _set_swr)

    async def get_with_swr(
        self,
        key: str,
        tier: CacheTier,
    ) -> tuple[Optional[Any], bool, bool]:
        """
        Get value with SWR support (async).

        Args:
            key: Cache key
            tier: Cache tier

        Returns:
            Tuple of (value, is_fresh, needs_refresh)
        """
        loop = asyncio.get_event_loop()

        def _get_swr():
            return self._cache.get_with_swr(key, tier)

        return await loop.run_in_executor(None, _get_swr)

    @property
    def is_available(self) -> bool:
        """Check if cache backend is available."""
        return self._cache is not None and self._cache.redis_available


# Module-level singleton
_async_cache: Optional[AsyncCacheAdapter] = None


def get_async_cache() -> AsyncCacheAdapter:
    """
    Get global async cache adapter instance.

    Returns:
        AsyncCacheAdapter singleton
    """
    global _async_cache
    if _async_cache is None:
        _async_cache = AsyncCacheAdapter()
    return _async_cache


def reset_async_cache() -> None:
    """Reset global async cache adapter (useful for testing)."""
    global _async_cache
    _async_cache = None


# Re-export for convenience
__all__ = [
    "AsyncCacheAdapter",
    "CacheTier",
    "SWR_WINDOWS",
    "get_async_cache",
    "get_ttl_for_data_type",
    "reset_async_cache",
    "CORE_AVAILABLE",
]
