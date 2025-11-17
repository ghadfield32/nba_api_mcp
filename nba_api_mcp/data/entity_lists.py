"""
Entity list management for NBA API MCP.

Provides functions to get and cache lists of NBA entities (players, teams)
and expand scope specifications (ALL, ALL_ACTIVE, etc.) into concrete entity lists.

Key Features:
- Caching (24h for active players, 7d for historical data)
- Scope expansion (ALL_ACTIVE → list of 450+ players)
- Season range expansion (2021-24 → ["2021-22", "2022-23", "2023-24"])
- Team list management

Design Principles:
- Minimize API calls (aggressive caching)
- Fast lookups (pre-computed lists)
- Deterministic expansion (same input → same output)
"""

import asyncio
from typing import List, Dict, Union
from nba_api.stats.static import players, teams
import logging

logger = logging.getLogger(__name__)

# In-memory cache (since we don't have Redis dependency here)
_entity_cache: Dict[str, any] = {}


async def get_all_active_players() -> List[Dict]:
    """
    Get all active NBA players.

    Returns list of dicts with keys: id, full_name, first_name, last_name, is_active

    Cached for 24 hours (active roster changes during season).

    Examples:
        players = await get_all_active_players()
        # Returns: [
        #     {"id": 2544, "full_name": "LeBron James", ...},
        #     {"id": 201939, "full_name": "Stephen Curry", ...},
        #     ...
        # ]
    """
    cache_key = "entity_list:all_active_players"

    if cache_key in _entity_cache:
        logger.debug(f"Cache hit: {cache_key}")
        return _entity_cache[cache_key]

    logger.info("Fetching all active players from nba_api")

    # Use nba_api static method (does not hit NBA API)
    all_players = players.get_players()
    active = [p for p in all_players if p.get("is_active", False)]

    _entity_cache[cache_key] = active

    logger.info(f"Cached {len(active)} active players")
    return active


async def get_all_players() -> List[Dict]:
    """
    Get all NBA players (active + historical).

    Returns list of dicts with keys: id, full_name, first_name, last_name, is_active

    Cached for 7 days (historical data changes rarely).

    Examples:
        players = await get_all_players()
        # Returns: [
        #     {"id": 2544, "full_name": "LeBron James", "is_active": True},
        #     {"id": 76001, "full_name": "Kareem Abdul-Jabbar", "is_active": False},
        #     ...
        # ]
    """
    cache_key = "entity_list:all_players"

    if cache_key in _entity_cache:
        logger.debug(f"Cache hit: {cache_key}")
        return _entity_cache[cache_key]

    logger.info("Fetching all players (historical) from nba_api")

    # Use nba_api static method
    all_players = players.get_players()

    _entity_cache[cache_key] = all_players

    logger.info(f"Cached {len(all_players)} players")
    return all_players


async def get_all_teams() -> List[Dict]:
    """
    Get all NBA teams.

    Returns list of dicts with keys: id, full_name, abbreviation, nickname, city, state, year_founded

    Cached for 7 days (team list changes very rarely).

    Examples:
        teams_list = await get_all_teams()
        # Returns: [
        #     {"id": 1610612747, "full_name": "Los Angeles Lakers", "abbreviation": "LAL", ...},
        #     {"id": 1610612744, "full_name": "Golden State Warriors", "abbreviation": "GSW", ...},
        #     ...
        # ]
    """
    cache_key = "entity_list:all_teams"

    if cache_key in _entity_cache:
        logger.debug(f"Cache hit: {cache_key}")
        return _entity_cache[cache_key]

    logger.info("Fetching all teams from nba_api")

    # Use nba_api static method
    all_teams = teams.get_teams()

    _entity_cache[cache_key] = all_teams

    logger.info(f"Cached {len(all_teams)} teams")
    return all_teams


async def expand_player_scope(
    scope_value: Union[str, List[str]]
) -> List[str]:
    """
    Expand player scope to list of player names/IDs.

    Handles:
    - Single player: "LeBron James" → ["LeBron James"]
    - Multiple players: ["LeBron James", "Stephen Curry"] → ["LeBron James", "Stephen Curry"]
    - All active: "ALL_ACTIVE" → [all active player names]
    - All historical: "ALL" → [all player names]

    Examples:
        # Single player
        names = await expand_player_scope("LeBron James")
        # Returns: ["LeBron James"]

        # Multiple players
        names = await expand_player_scope(["LeBron James", "Stephen Curry"])
        # Returns: ["LeBron James", "Stephen Curry"]

        # All active (450+ players)
        names = await expand_player_scope("ALL_ACTIVE")
        # Returns: ["LeBron James", "Stephen Curry", "Giannis Antetokounmpo", ...]

        # All historical (4000+ players)
        names = await expand_player_scope("ALL")
        # Returns: ["LeBron James", ..., "Michael Jordan", ..., "Kareem Abdul-Jabbar", ...]
    """
    if isinstance(scope_value, list):
        # Already a list
        return scope_value

    if scope_value == "ALL_ACTIVE":
        logger.info("Expanding player scope: ALL_ACTIVE")
        players_list = await get_all_active_players()
        return [p["full_name"] for p in players_list]

    elif scope_value == "ALL":
        logger.info("Expanding player scope: ALL")
        players_list = await get_all_players()
        return [p["full_name"] for p in players_list]

    else:
        # Single player name
        return [scope_value]


async def expand_team_scope(
    scope_value: Union[str, List[str]]
) -> List[str]:
    """
    Expand team scope to list of team names/abbreviations.

    Handles:
    - Single team: "Lakers" → ["Lakers"]
    - Multiple teams: ["Lakers", "Warriors"] → ["Lakers", "Warriors"]
    - All teams: "ALL" → [all team names]

    Examples:
        # Single team
        names = await expand_team_scope("Lakers")
        # Returns: ["Lakers"]

        # Multiple teams
        names = await expand_team_scope(["Lakers", "Warriors", "Celtics"])
        # Returns: ["Lakers", "Warriors", "Celtics"]

        # All teams (30 teams)
        names = await expand_team_scope("ALL")
        # Returns: ["Lakers", "Warriors", "Celtics", "Heat", ...]
    """
    if isinstance(scope_value, list):
        return scope_value

    if scope_value == "ALL":
        logger.info("Expanding team scope: ALL")
        teams_list = await get_all_teams()
        # Return abbreviations (more common in API params)
        return [t["abbreviation"] for t in teams_list]

    else:
        # Single team
        return [scope_value]


def expand_season_range(season: Union[str, List[str]]) -> List[str]:
    """
    Expand season range to list of seasons.

    Handles:
    - Single season: "2023-24" → ["2023-24"]
    - Season range: "2021-24" → ["2021-22", "2022-23", "2023-24"]
    - Multiple seasons: ["2022-23", "2023-24"] → ["2022-23", "2023-24"]

    Examples:
        # Single season
        seasons = expand_season_range("2023-24")
        # Returns: ["2023-24"]

        # Season range (expands to 3 seasons)
        seasons = expand_season_range("2021-24")
        # Returns: ["2021-22", "2022-23", "2023-24"]

        # Already a list
        seasons = expand_season_range(["2021-22", "2023-24"])
        # Returns: ["2021-22", "2023-24"]

        # Invalid format
        seasons = expand_season_range("2021")
        # Returns: ["2021"] (no expansion)
    """
    if isinstance(season, list):
        return season

    # Single season "2023-24"
    if len(season) == 7 and season[4] == "-":
        return [season]

    # Range format "2021-24" (expand to multiple seasons)
    if len(season) == 5 and season[4] == "-":
        try:
            start_year = int(season[:4])
            end_year_short = int(season[-2:])

            # Handle century rollover (e.g., "1999-01" means 1999-2000, 2000-01)
            if end_year_short < 50:
                end_year = 2000 + end_year_short
            else:
                end_year = 1900 + end_year_short

            # Generate season strings
            seasons = []
            current_year = start_year
            while current_year <= end_year:
                season_str = f"{current_year}-{str(current_year + 1)[-2:]}"
                seasons.append(season_str)
                current_year += 1

            logger.info(f"Expanded season range {season} → {len(seasons)} seasons")
            return seasons

        except ValueError:
            logger.warning(f"Invalid season range format: {season}")
            return [season]

    # Unknown format
    logger.warning(f"Unknown season format: {season}")
    return [season]


def expand_date_range(date_range: str) -> tuple[str, str]:
    """
    Parse date range string into start and end dates.

    Format: "YYYY-MM-DD..YYYY-MM-DD"

    Examples:
        # Standard range
        start, end = expand_date_range("2024-01-01..2024-03-31")
        # Returns: ("2024-01-01", "2024-03-31")

        # Single date (no range)
        start, end = expand_date_range("2024-01-01")
        # Returns: ("2024-01-01", "2024-01-01")
    """
    if ".." in date_range:
        parts = date_range.split("..")
        if len(parts) == 2:
            return (parts[0].strip(), parts[1].strip())

    # Single date or invalid format
    return (date_range, date_range)


def estimate_fanout_queries(
    player_count: int,
    team_count: int,
    season_count: int
) -> int:
    """
    Estimate number of API queries that will be made.

    Used for:
    - Warning users before expensive operations
    - Rate limit planning
    - Progress estimation

    Examples:
        # Single player, single season
        count = estimate_fanout_queries(1, 0, 1)
        # Returns: 1

        # All active players (450), 3 seasons
        count = estimate_fanout_queries(450, 0, 3)
        # Returns: 1350

        # 3 teams, 1 season
        count = estimate_fanout_queries(0, 3, 1)
        # Returns: 3

        # All active players (450), all teams (30), 1 season
        count = estimate_fanout_queries(450, 30, 1)
        # Returns: 13500 (likely too many!)
    """
    player_count = max(1, player_count)
    team_count = max(1, team_count)
    season_count = max(1, season_count)

    return player_count * team_count * season_count


# Utility function to clear cache (for testing)
def clear_entity_cache():
    """Clear the in-memory entity cache"""
    global _entity_cache
    _entity_cache = {}
    logger.info("Entity cache cleared")
