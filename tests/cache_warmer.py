"""
Cache warmer for NBA MCP tests.

Pre-populates the Parquet cache with commonly accessed data to ensure:
1. Tests run fast (no API calls needed)
2. Rate limits are never hit
3. CI/CD pipelines are reliable

Usage:
    # Warm cache with essential data (fast, ~2 minutes)
    python tests/cache_warmer.py

    # Warm cache with all test data (comprehensive, ~10 minutes)
    python tests/cache_warmer.py --comprehensive

    # Check cache status
    python tests/cache_warmer.py --status

This script respects rate limits (1 request every 6 seconds = 10/minute).
"""

import asyncio
import logging
import time
from pathlib import Path
from typing import List, Dict, Any
import sys
import argparse

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from nba_api_mcp.data.parquet_cache import ParquetCacheBackend, ParquetCacheConfig
from nba_api_mcp.cache import initialize_cache
from nba_api.stats.endpoints import (
    leaguegamefinder,
    playergamelogs,
    leagueleaders,
    commonplayerinfo,
    commonteamroster,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


# ============================================================================
# CACHE WARMING DATASETS
# ============================================================================

# Essential datasets for basic tests (fast to fetch)
ESSENTIAL_DATASETS = [
    {
        "name": "LeagueLeaders_2023-24_PTS",
        "endpoint": leagueleaders.LeagueLeaders,
        "params": {
            "season": "2023-24",
            "stat_category_abbreviation": "PTS",
            "per_mode48": "PerGame"
        }
    },
    {
        "name": "PlayerGameLogs_LeBron_2023-24",
        "endpoint": playergamelogs.PlayerGameLogs,
        "params": {
            "season_nullable": "2023-24",
            "player_id_nullable": "2544"  # LeBron James
        }
    },
    {
        "name": "CommonPlayerInfo_LeBron",
        "endpoint": commonplayerinfo.CommonPlayerInfo,
        "params": {
            "player_id": "2544"  # LeBron James
        }
    },
    {
        "name": "CommonTeamRoster_Lakers_2023-24",
        "endpoint": commonteamroster.CommonTeamRoster,
        "params": {
            "team_id": "1610612747",  # Lakers
            "season": "2023-24"
        }
    },
]

# Comprehensive datasets for thorough testing (slower)
COMPREHENSIVE_DATASETS = ESSENTIAL_DATASETS + [
    {
        "name": "LeagueLeaders_2023-24_AST",
        "endpoint": leagueleaders.LeagueLeaders,
        "params": {
            "season": "2023-24",
            "stat_category_abbreviation": "AST",
            "per_mode48": "PerGame"
        }
    },
    {
        "name": "LeagueLeaders_2023-24_REB",
        "endpoint": leagueleaders.LeagueLeaders,
        "params": {
            "season": "2023-24",
            "stat_category_abbreviation": "REB",
            "per_mode48": "PerGame"
        }
    },
    {
        "name": "PlayerGameLogs_Curry_2023-24",
        "endpoint": playergamelogs.PlayerGameLogs,
        "params": {
            "season_nullable": "2023-24",
            "player_id_nullable": "201939"  # Stephen Curry
        }
    },
    {
        "name": "PlayerGameLogs_Giannis_2023-24",
        "endpoint": playergamelogs.PlayerGameLogs,
        "params": {
            "season_nullable": "2023-24",
            "player_id_nullable": "203507"  # Giannis Antetokounmpo
        }
    },
    {
        "name": "CommonPlayerInfo_Curry",
        "endpoint": commonplayerinfo.CommonPlayerInfo,
        "params": {
            "player_id": "201939"  # Stephen Curry
        }
    },
    {
        "name": "CommonPlayerInfo_Giannis",
        "endpoint": commonplayerinfo.CommonPlayerInfo,
        "params": {
            "player_id": "203507"  # Giannis
        }
    },
    {
        "name": "CommonTeamRoster_Warriors_2023-24",
        "endpoint": commonteamroster.CommonTeamRoster,
        "params": {
            "team_id": "1610612744",  # Warriors
            "season": "2023-24"
        }
    },
    {
        "name": "CommonTeamRoster_Celtics_2023-24",
        "endpoint": commonteamroster.CommonTeamRoster,
        "params": {
            "team_id": "1610612738",  # Celtics
            "season": "2023-24"
        }
    },
    {
        "name": "LeagueGameFinder_Lakers_Recent",
        "endpoint": leaguegamefinder.LeagueGameFinder,
        "params": {
            "team_id_nullable": "1610612747",  # Lakers
            "season_nullable": "2023-24",
            "league_id_nullable": "00"
        }
    },
]


# ============================================================================
# CACHE WARMING LOGIC
# ============================================================================

# Rate limiting: 1 request every 6 seconds = 10 per minute (safe)
RATE_LIMIT_DELAY = 6.0  # seconds between requests


async def fetch_and_cache_dataset(
    dataset: Dict[str, Any],
    parquet_cache: ParquetCacheBackend,
    delay: float = RATE_LIMIT_DELAY
) -> bool:
    """
    Fetch dataset from NBA API and cache it.

    Args:
        dataset: Dataset configuration dict
        parquet_cache: Parquet cache backend
        delay: Delay in seconds before making API call (rate limiting)

    Returns:
        True if cached successfully, False otherwise
    """
    try:
        logger.info(f"Warming cache: {dataset['name']}")

        # Check if already cached
        cache_key = f"{dataset['endpoint'].__name__}_{hash(frozenset(dataset['params'].items()))}"

        # Rate limiting delay
        await asyncio.sleep(delay)

        # Fetch from NBA API
        start_time = time.time()
        endpoint_instance = dataset["endpoint"](**dataset["params"])

        # Get the data (this will hit cache or API)
        df = endpoint_instance.get_data_frames()[0]

        elapsed = time.time() - start_time

        logger.info(
            f"  ✓ Fetched {len(df)} rows in {elapsed:.2f}s "
            f"[{dataset['endpoint'].__name__}]"
        )

        return True

    except Exception as e:
        logger.error(f"  ✗ Failed to cache {dataset['name']}: {e}")
        return False


async def warm_cache(
    datasets: List[Dict[str, Any]],
    cache_dir: Path,
    delay: float = RATE_LIMIT_DELAY
) -> Dict[str, int]:
    """
    Warm cache with specified datasets.

    Args:
        datasets: List of dataset configurations
        cache_dir: Cache directory path
        delay: Delay between requests (rate limiting)

    Returns:
        Statistics dict with success/failure counts
    """
    # Initialize caches
    logger.info(f"Initializing caches (cache_dir={cache_dir})")

    # Initialize LRU cache
    initialize_cache(redis_url=None, lru_size=1000)

    # Initialize Parquet cache
    config = ParquetCacheConfig(
        enabled=True,
        cache_dir=cache_dir / "parquet",
        compression="SNAPPY",
        max_size_mb=5000,
        background_writes=True
    )
    parquet_cache = ParquetCacheBackend(config)

    # Warm cache
    stats = {"success": 0, "failure": 0, "total": len(datasets)}

    logger.info(f"\nWarming cache with {len(datasets)} datasets...")
    logger.info(f"Rate limit: {60/delay:.1f} requests/minute")
    logger.info(f"Estimated time: {len(datasets) * delay / 60:.1f} minutes\n")

    start_time = time.time()

    for i, dataset in enumerate(datasets, 1):
        logger.info(f"[{i}/{len(datasets)}] Processing {dataset['name']}")

        success = await fetch_and_cache_dataset(
            dataset,
            parquet_cache,
            delay=delay if i > 1 else 0  # No delay for first request
        )

        if success:
            stats["success"] += 1
        else:
            stats["failure"] += 1

    elapsed = time.time() - start_time

    # Report statistics
    logger.info(f"\n{'='*60}")
    logger.info(f"CACHE WARMING COMPLETE")
    logger.info(f"{'='*60}")
    logger.info(f"Total datasets:  {stats['total']}")
    logger.info(f"Successfully cached: {stats['success']}")
    logger.info(f"Failed:          {stats['failure']}")
    logger.info(f"Time elapsed:    {elapsed/60:.1f} minutes")
    logger.info(f"{'='*60}\n")

    # Cache size
    cache_size = sum(f.stat().st_size for f in cache_dir.rglob("*.parquet"))
    cache_size_mb = cache_size / 1024 / 1024
    logger.info(f"Cache size: {cache_size_mb:.1f} MB")

    return stats


async def show_cache_status(cache_dir: Path):
    """
    Show current cache status.

    Args:
        cache_dir: Cache directory path
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"CACHE STATUS")
    logger.info(f"{'='*60}")
    logger.info(f"Cache directory: {cache_dir}")

    # Count files
    parquet_files = list(cache_dir.rglob("*.parquet"))
    logger.info(f"Parquet files:   {len(parquet_files)}")

    # Calculate size
    cache_size = sum(f.stat().st_size for f in parquet_files)
    cache_size_mb = cache_size / 1024 / 1024
    logger.info(f"Cache size:      {cache_size_mb:.1f} MB")

    # Show recent files
    if parquet_files:
        logger.info(f"\nRecent cache entries:")
        recent_files = sorted(parquet_files, key=lambda f: f.stat().st_mtime, reverse=True)[:5]
        for f in recent_files:
            size_mb = f.stat().st_size / 1024 / 1024
            mod_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(f.stat().st_mtime))
            logger.info(f"  {f.name[:50]:50s} {size_mb:6.2f} MB  {mod_time}")

    logger.info(f"{'='*60}\n")


# ============================================================================
# MAIN
# ============================================================================

async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Warm NBA MCP test cache with real API data"
    )
    parser.add_argument(
        "--comprehensive",
        action="store_true",
        help="Warm cache with comprehensive dataset (slower, more thorough)"
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show current cache status and exit"
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path(".cache/nba_mcp_test_cache"),
        help="Cache directory path (default: .cache/nba_mcp_test_cache)"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=RATE_LIMIT_DELAY,
        help=f"Delay between requests in seconds (default: {RATE_LIMIT_DELAY})"
    )

    args = parser.parse_args()

    # Ensure cache directory exists
    args.cache_dir.mkdir(parents=True, exist_ok=True)

    # Show status if requested
    if args.status:
        await show_cache_status(args.cache_dir)
        return

    # Select datasets
    datasets = COMPREHENSIVE_DATASETS if args.comprehensive else ESSENTIAL_DATASETS

    # Warm cache
    stats = await warm_cache(datasets, args.cache_dir, delay=args.delay)

    # Exit with error code if failures
    if stats["failure"] > 0:
        logger.warning(f"⚠️  {stats['failure']} datasets failed to cache")
        sys.exit(1)
    else:
        logger.info(f"✓ All {stats['success']} datasets cached successfully")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
