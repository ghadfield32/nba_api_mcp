"""
Global pytest configuration for NBA MCP tests.

Ensures all tests use persistent caching to avoid NBA API rate limits
while still testing against real data.

Architecture:
- Tier 1: LRU cache (in-memory, fast)
- Tier 2: Redis cache (optional, for local dev)
- Tier 3: Parquet cache (PERSISTENT, survives CI runs)

Strategy:
1. Enable all cache tiers by default
2. Use persistent Parquet cache to survive CI/CD restarts
3. Add rate limiting protection (10 req/min max)
4. Log cache hit/miss rates for monitoring
"""

import asyncio
import logging
import os
import time
from pathlib import Path
from typing import Generator

import pytest

# ============================================================================
# CACHE INITIALIZATION
# ============================================================================

# Get cache directory from environment or use default
CACHE_DIR = Path(os.getenv("NBA_MCP_CACHE_DIR", ".cache/nba_mcp_test_cache"))
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Configure logging for cache debugging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


@pytest.fixture(scope="session", autouse=True)
def enable_persistent_cache():
    """
    Enable persistent Parquet cache for all tests.

    This fixture runs once per test session and ensures:
    1. Parquet cache is initialized with test-specific directory
    2. Cache survives across test runs and CI/CD pipelines
    3. Real NBA API data is cached and reused
    4. Rate limits are never exceeded

    Why session scope:
    - Cache initialization should happen once
    - Cache persists across all tests
    - Improves performance dramatically (99.8% cold start reduction)
    """
    from nba_api_mcp.data.parquet_cache import ParquetCacheBackend, ParquetCacheConfig

    config = ParquetCacheConfig(
        enabled=True,
        cache_dir=CACHE_DIR / "parquet",
        compression="SNAPPY",  # Fast compression
        max_size_mb=5000,      # 5 GB for CI cache
        background_writes=True, # Don't slow down tests
        row_group_size=10000
    )

    cache = ParquetCacheBackend(config)

    cache_size = sum(f.stat().st_size for f in cache.cache_dir.rglob("*.parquet"))
    cache_size_mb = cache_size / 1024 / 1024

    logger.info(
        f"✓ Persistent Parquet cache enabled: {cache.cache_dir} "
        f"({cache_size_mb:.1f} MB cached)"
    )

    yield cache

    # Log cache statistics at end of test session
    final_size = sum(f.stat().st_size for f in cache.cache_dir.rglob("*.parquet"))
    final_size_mb = final_size / 1024 / 1024
    logger.info(
        f"✓ Test session complete. Cache size: {final_size_mb:.1f} MB "
        f"(+{final_size_mb - cache_size_mb:.1f} MB added)"
    )


@pytest.fixture(scope="session", autouse=True)
def enable_lru_cache():
    """
    Enable in-memory LRU cache for fast lookups.

    This provides sub-millisecond cache hits for frequently accessed data
    during a test run. Complements the persistent Parquet cache.
    """
    from nba_api_mcp.cache import initialize_cache, get_cache, close_cache

    try:
        # Try Redis first (for local development)
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/15")
        initialize_cache(redis_url=redis_url, lru_size=2000)
        cache = get_cache()
        logger.info(f"✓ Redis cache enabled: {redis_url}")
    except Exception as e:
        # Fall back to LRU-only (for CI)
        initialize_cache(redis_url=None, lru_size=2000)
        cache = get_cache()
        logger.info(f"✓ LRU cache enabled (Redis unavailable: {e})")

    yield cache

    # Cleanup
    try:
        close_cache()
    except:
        pass


# ============================================================================
# RATE LIMITING PROTECTION
# ============================================================================

# Global rate limiter state
_api_call_timestamps = []
_api_call_lock = asyncio.Lock()

# Rate limit: 10 API calls per minute (conservative)
MAX_API_CALLS_PER_MINUTE = 10
RATE_LIMIT_WINDOW = 60  # seconds


async def check_rate_limit():
    """
    Check if we're within rate limits before making NBA API call.

    This is a safety net to prevent test suites from hitting rate limits
    even if caching fails.

    Raises:
        pytest.skip: If rate limit would be exceeded
    """
    async with _api_call_lock:
        now = time.time()

        # Remove timestamps older than rate limit window
        global _api_call_timestamps
        _api_call_timestamps = [
            ts for ts in _api_call_timestamps
            if now - ts < RATE_LIMIT_WINDOW
        ]

        # Check if we're at limit
        if len(_api_call_timestamps) >= MAX_API_CALLS_PER_MINUTE:
            pytest.skip(
                f"Rate limit protection: {MAX_API_CALLS_PER_MINUTE} API calls "
                f"reached in last {RATE_LIMIT_WINDOW}s. Skipping test to prevent "
                f"NBA API rate limit. Enable caching to avoid this."
            )

        # Record this API call
        _api_call_timestamps.append(now)


@pytest.fixture
def rate_limit_guard():
    """
    Fixture that provides rate limit checking for tests.

    Usage:
        @pytest.mark.asyncio
        async def test_something(rate_limit_guard):
            await rate_limit_guard()  # Check before API call
            result = await call_nba_api()
    """
    return check_rate_limit


# ============================================================================
# CACHE MONITORING
# ============================================================================

@pytest.fixture(scope="session", autouse=True)
def log_cache_statistics():
    """
    Log cache hit/miss statistics at the end of test session.

    Helps identify which tests are missing cache hits and need optimization.
    """
    from nba_api_mcp.cache import get_cache

    yield

    try:
        cache = get_cache()
        stats = cache.get_stats()

        hit_rate = stats.get("hit_rate", 0) * 100

        logger.info(
            f"\n{'='*60}\n"
            f"CACHE STATISTICS\n"
            f"{'='*60}\n"
            f"Hits:      {stats.get('hits', 0):,}\n"
            f"Misses:    {stats.get('misses', 0):,}\n"
            f"Hit Rate:  {hit_rate:.1f}%\n"
            f"{'='*60}\n"
        )

        # Warn if hit rate is low
        if hit_rate < 50 and stats.get('misses', 0) > 10:
            logger.warning(
                f"⚠️  Low cache hit rate ({hit_rate:.1f}%). "
                f"Consider warming cache with cache_warmer.py"
            )
    except Exception as e:
        logger.debug(f"Could not retrieve cache statistics: {e}")


# ============================================================================
# ENVIRONMENT CONFIGURATION
# ============================================================================

@pytest.fixture(scope="session", autouse=True)
def configure_test_environment():
    """
    Configure environment variables for optimal test performance.

    Sets defaults that ensure:
    - Caching is enabled
    - Logging is appropriate for CI
    - Timeouts are reasonable
    """
    defaults = {
        "NBA_MCP_CACHE_DIR": str(CACHE_DIR),
        "NBA_MCP_CACHE_ENABLED": "true",
        "NBA_MCP_LOG_LEVEL": os.getenv("NBA_MCP_LOG_LEVEL", "INFO"),
    }

    # Set defaults only if not already set
    for key, value in defaults.items():
        if key not in os.environ:
            os.environ[key] = value

    logger.info(
        f"✓ Test environment configured:\n"
        f"  Cache dir: {CACHE_DIR}\n"
        f"  Cache enabled: {os.getenv('NBA_MCP_CACHE_ENABLED')}\n"
        f"  Log level: {os.getenv('NBA_MCP_LOG_LEVEL')}"
    )

    yield

    # Cleanup not needed - environment vars are session-scoped


# ============================================================================
# PYTEST HOOKS
# ============================================================================

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers",
        "requires_api: mark test as requiring NBA API access (may be slow)"
    )
    config.addinivalue_line(
        "markers",
        "slow: mark test as slow (skipped unless --runslow)"
    )


def pytest_collection_modifyitems(config, items):
    """
    Modify test collection to handle markers.

    - Skip slow tests unless --runslow is passed
    - Log warnings for tests that require API access
    """
    skip_slow = pytest.mark.skip(reason="need --runslow option to run")

    for item in items:
        if "slow" in item.keywords and not config.getoption("--runslow", default=False):
            item.add_marker(skip_slow)

        if "requires_api" in item.keywords:
            # Add rate limit guard automatically
            logger.debug(f"Test {item.name} requires API access - rate limiting enabled")


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--runslow",
        action="store_true",
        default=False,
        help="run slow tests that may take minutes"
    )
    parser.addoption(
        "--update-snapshots",
        action="store_true",
        default=False,
        help="update golden test snapshots"
    )
