"""
Concurrency control for NBA MCP Server.

Provides per-endpoint concurrency limits to protect upstream NBA API
and maintain server responsiveness.

Features:
- Per-endpoint semaphores
- Configurable limits by endpoint type (live/standard/heavy)
- Request queuing with timeouts
- Metrics collection
- Graceful handling of limit exceeded

Usage:
    from nba_api_mcp.concurrency import with_concurrency_limit, get_concurrency_stats

    # Wrap async operation with concurrency limit
    result = await with_concurrency_limit(
        endpoint="player_career_stats",
        operation=fetch_data_from_api()
    )

    # Check current concurrency stats
    stats = get_concurrency_stats()
"""

import asyncio
import logging
import time
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, Optional

from nba_api_mcp.config import settings

logger = logging.getLogger(__name__)

# Context variable for tracking current endpoint
current_endpoint_ctx: ContextVar[Optional[str]] = ContextVar(
    "current_endpoint", default=None
)


class EndpointType(str, Enum):
    """
    Endpoint types for concurrency grouping.

    Different endpoint types have different concurrency limits
    based on their load and latency characteristics.
    """

    LIVE = "live"  # Real-time data (scoreboard, play-by-play)
    STANDARD = "standard"  # Regular queries (player stats, standings)
    HEAVY = "heavy"  # Heavy operations (shot charts, detailed game logs)


# Endpoint type mapping
# Maps endpoint names to their concurrency type
ENDPOINT_TYPE_MAP: Dict[str, EndpointType] = {
    # Live endpoints (real-time data)
    "live_scoreboard": EndpointType.LIVE,
    "scoreboard": EndpointType.LIVE,
    "live_scores": EndpointType.LIVE,
    "play_by_play": EndpointType.HEAVY,  # Heavy due to data volume
    # Standard endpoints
    "player_career_stats": EndpointType.STANDARD,
    "player_game_logs": EndpointType.STANDARD,
    "team_standings": EndpointType.STANDARD,
    "league_leaders": EndpointType.STANDARD,
    "player_info": EndpointType.STANDARD,
    "team_info": EndpointType.STANDARD,
    # Heavy endpoints (large data or complex processing)
    "shot_chart": EndpointType.HEAVY,
    "shot_chart_detail": EndpointType.HEAVY,
    "detailed_game_log": EndpointType.HEAVY,
    "hustle_stats": EndpointType.HEAVY,
}

# Concurrency limits by endpoint type
CONCURRENCY_LIMITS: Dict[EndpointType, int] = {
    EndpointType.LIVE: settings.NBA_MCP_MAX_CONCURRENT_LIVE,
    EndpointType.STANDARD: settings.NBA_MCP_MAX_CONCURRENT_STANDARD,
    EndpointType.HEAVY: settings.NBA_MCP_MAX_CONCURRENT_HEAVY,
}


@dataclass
class ConcurrencyStats:
    """
    Statistics for concurrency control.

    Tracks active requests, queued requests, and historical metrics.
    """

    endpoint_type: EndpointType
    limit: int
    active: int = 0
    queued: int = 0
    total_acquired: int = 0
    total_released: int = 0
    total_timeouts: int = 0
    total_wait_time_ms: float = 0.0
    max_wait_time_ms: float = 0.0
    last_updated: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "endpoint_type": self.endpoint_type.value,
            "limit": self.limit,
            "active": self.active,
            "queued": self.queued,
            "utilization": self.active / self.limit if self.limit > 0 else 0.0,
            "total_acquired": self.total_acquired,
            "total_released": self.total_released,
            "total_timeouts": self.total_timeouts,
            "avg_wait_time_ms": (
                self.total_wait_time_ms / self.total_acquired
                if self.total_acquired > 0
                else 0.0
            ),
            "max_wait_time_ms": self.max_wait_time_ms,
            "last_updated": self.last_updated.isoformat(),
        }


class ConcurrencyManager:
    """
    Manages concurrency limits across endpoint types.

    Uses asyncio.Semaphore per endpoint type to limit concurrent requests.
    Tracks statistics and provides observability.
    """

    def __init__(self):
        """Initialize concurrency manager with semaphores per type."""
        self.semaphores: Dict[EndpointType, asyncio.Semaphore] = {}
        self.stats: Dict[EndpointType, ConcurrencyStats] = {}

        # Initialize semaphores and stats for each type
        for endpoint_type, limit in CONCURRENCY_LIMITS.items():
            self.semaphores[endpoint_type] = asyncio.Semaphore(limit)
            self.stats[endpoint_type] = ConcurrencyStats(
                endpoint_type=endpoint_type, limit=limit
            )

        logger.info(
            f"Concurrency manager initialized: "
            f"LIVE={CONCURRENCY_LIMITS[EndpointType.LIVE]}, "
            f"STANDARD={CONCURRENCY_LIMITS[EndpointType.STANDARD]}, "
            f"HEAVY={CONCURRENCY_LIMITS[EndpointType.HEAVY]}"
        )

    def get_endpoint_type(self, endpoint: str) -> EndpointType:
        """
        Get endpoint type for concurrency grouping.

        Args:
            endpoint: Endpoint name

        Returns:
            EndpointType (defaults to STANDARD if not mapped)
        """
        return ENDPOINT_TYPE_MAP.get(endpoint, EndpointType.STANDARD)

    def get_semaphore(self, endpoint: str) -> asyncio.Semaphore:
        """
        Get semaphore for endpoint.

        Args:
            endpoint: Endpoint name

        Returns:
            Semaphore for the endpoint's type
        """
        endpoint_type = self.get_endpoint_type(endpoint)
        return self.semaphores[endpoint_type]

    def get_stats(self, endpoint_type: Optional[EndpointType] = None) -> Dict[str, Any]:
        """
        Get concurrency statistics.

        Args:
            endpoint_type: Optional type to filter (None = all types)

        Returns:
            Dictionary of stats by endpoint type
        """
        if endpoint_type:
            return {endpoint_type.value: self.stats[endpoint_type].to_dict()}

        return {
            endpoint_type.value: stats.to_dict()
            for endpoint_type, stats in self.stats.items()
        }

    async def acquire(
        self, endpoint: str, timeout: Optional[float] = None
    ) -> "ConcurrencyToken":
        """
        Acquire concurrency slot for endpoint.

        Args:
            endpoint: Endpoint name
            timeout: Optional timeout in seconds

        Returns:
            ConcurrencyToken context manager

        Raises:
            asyncio.TimeoutError: If timeout exceeded
        """
        endpoint_type = self.get_endpoint_type(endpoint)
        semaphore = self.semaphores[endpoint_type]
        stats = self.stats[endpoint_type]

        # Track queue entry
        stats.queued += 1
        start_time = time.perf_counter()

        try:
            # Acquire with optional timeout
            if timeout:
                await asyncio.wait_for(semaphore.acquire(), timeout=timeout)
            else:
                await semaphore.acquire()

            # Track acquisition
            wait_time_ms = (time.perf_counter() - start_time) * 1000
            stats.queued -= 1
            stats.active += 1
            stats.total_acquired += 1
            stats.total_wait_time_ms += wait_time_ms
            stats.max_wait_time_ms = max(stats.max_wait_time_ms, wait_time_ms)
            stats.last_updated = datetime.now()

            logger.debug(
                f"Concurrency acquired: {endpoint} (type={endpoint_type.value}, "
                f"active={stats.active}/{stats.limit}, wait={wait_time_ms:.1f}ms)"
            )

            return ConcurrencyToken(self, endpoint_type, semaphore)

        except asyncio.TimeoutError:
            # Track timeout
            stats.queued -= 1
            stats.total_timeouts += 1
            stats.last_updated = datetime.now()

            logger.warning(
                f"Concurrency timeout: {endpoint} (type={endpoint_type.value}, "
                f"queued={stats.queued}, timeout={timeout}s)"
            )
            raise

    def release(self, endpoint_type: EndpointType, semaphore: asyncio.Semaphore):
        """
        Release concurrency slot.

        Args:
            endpoint_type: Endpoint type
            semaphore: Semaphore to release
        """
        semaphore.release()

        stats = self.stats[endpoint_type]
        stats.active -= 1
        stats.total_released += 1
        stats.last_updated = datetime.now()

        logger.debug(
            f"Concurrency released: type={endpoint_type.value}, "
            f"active={stats.active}/{stats.limit}"
        )


@dataclass
class ConcurrencyToken:
    """
    Token representing acquired concurrency slot.

    Use as context manager to automatically release.
    """

    manager: ConcurrencyManager
    endpoint_type: EndpointType
    semaphore: asyncio.Semaphore

    async def __aenter__(self):
        """Enter context (already acquired)."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit context, releasing semaphore."""
        self.manager.release(self.endpoint_type, self.semaphore)


# Global concurrency manager instance
_concurrency_manager: Optional[ConcurrencyManager] = None


def get_concurrency_manager() -> ConcurrencyManager:
    """
    Get global concurrency manager instance (singleton).

    Returns:
        ConcurrencyManager instance
    """
    global _concurrency_manager
    if _concurrency_manager is None:
        _concurrency_manager = ConcurrencyManager()
    return _concurrency_manager


# Public API


async def with_concurrency_limit(
    endpoint: str,
    operation: Callable[..., Any],
    timeout: Optional[float] = None,
    **kwargs,
) -> Any:
    """
    Execute operation with concurrency limit.

    Wraps async operation with endpoint-specific concurrency control.

    Args:
        endpoint: Endpoint name
        operation: Async callable to execute
        timeout: Optional timeout for acquiring slot
        **kwargs: Arguments to pass to operation

    Returns:
        Result from operation

    Raises:
        asyncio.TimeoutError: If concurrency slot acquisition times out

    Example:
        result = await with_concurrency_limit(
            endpoint="player_career_stats",
            operation=fetch_player_data,
            player_id=2544
        )
    """
    manager = get_concurrency_manager()

    # Acquire concurrency slot
    async with await manager.acquire(endpoint, timeout=timeout):
        # Set context for logging
        token = current_endpoint_ctx.set(endpoint)

        try:
            # Execute operation
            if asyncio.iscoroutinefunction(operation):
                result = await operation(**kwargs)
            else:
                result = operation(**kwargs)

            return result

        finally:
            # Reset context
            current_endpoint_ctx.reset(token)


async def with_concurrency_limit_coro(
    endpoint: str,
    coro: Any,
    timeout: Optional[float] = None,
) -> Any:
    """
    Execute coroutine with concurrency limit.

    Similar to with_concurrency_limit but for coroutines (already created).

    Args:
        endpoint: Endpoint name
        coro: Coroutine to await
        timeout: Optional timeout for acquiring slot

    Returns:
        Result from coroutine

    Example:
        coro = fetch_player_data(player_id=2544)
        result = await with_concurrency_limit_coro(
            endpoint="player_career_stats",
            coro=coro
        )
    """
    manager = get_concurrency_manager()

    # Acquire concurrency slot
    async with await manager.acquire(endpoint, timeout=timeout):
        # Set context
        token = current_endpoint_ctx.set(endpoint)

        try:
            # Await coroutine
            return await coro

        finally:
            # Reset context
            current_endpoint_ctx.reset(token)


def get_concurrency_stats(
    endpoint_type: Optional[EndpointType] = None,
) -> Dict[str, Any]:
    """
    Get concurrency statistics.

    Args:
        endpoint_type: Optional type to filter (None = all types)

    Returns:
        Dictionary of stats by endpoint type

    Example:
        stats = get_concurrency_stats()
        print(f"Live endpoints: {stats['live']['active']}/{stats['live']['limit']}")
    """
    manager = get_concurrency_manager()
    return manager.get_stats(endpoint_type)


def get_endpoint_type(endpoint: str) -> EndpointType:
    """
    Get endpoint type for concurrency grouping.

    Args:
        endpoint: Endpoint name

    Returns:
        EndpointType

    Example:
        endpoint_type = get_endpoint_type("player_career_stats")
        # Returns: EndpointType.STANDARD
    """
    manager = get_concurrency_manager()
    return manager.get_endpoint_type(endpoint)


# Export public API
__all__ = [
    "EndpointType",
    "ConcurrencyStats",
    "with_concurrency_limit",
    "with_concurrency_limit_coro",
    "get_concurrency_stats",
    "get_endpoint_type",
    "get_concurrency_manager",
]
