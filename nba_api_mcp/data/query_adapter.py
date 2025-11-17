"""
Query adapter for NBA API MCP unified query system.

Provides the main entry point for executing queries, routing to either:
- Simple unified_fetch for single-entity queries
- expand_scope_and_fetch for multi-entity/range queries

Design Principles:
- Transparent routing (user doesn't need to know which path is taken)
- Backward compatible (works with existing unified_fetch)
- Efficient (only expands when necessary)
- Type-safe (Query model validation)
"""

import logging
from typing import Union, Dict, Any

from nba_api_mcp.data.entity_lists import expand_season_range
from nba_api_mcp.data.expand_scope import expand_scope_and_fetch
from nba_api_mcp.data.models.query import Query, QueryResult, Scope, Range
from nba_api_mcp.data.param_aliases import normalize_params
from nba_api_mcp.data.unified_fetch import unified_fetch

logger = logging.getLogger(__name__)


async def execute_query(query: Query, max_concurrent: int = 5) -> QueryResult:
    """
    Universal query executor - routes to appropriate handler.

    Automatically determines whether scope/range expansion is needed and
    routes to the appropriate execution path:
    - Simple single-entity → unified_fetch (fast, direct)
    - Multi-entity/ranges → expand_scope_and_fetch (fan-out, parallel)

    Args:
        query: Query object with scope/range/filter specifications
        max_concurrent: Max concurrent queries for fan-out (default: 5)

    Returns:
        QueryResult with data and metadata

    Examples:
        # Simple query (no expansion needed)
        result = await execute_query(Query(
            endpoint="player_career_stats",
            scope=Scope(player="LeBron James"),
            range=Range(season="2023-24")
        ))
        # Routes to: unified_fetch

        # Fan-out query (expansion needed)
        result = await execute_query(Query(
            endpoint="player_career_stats",
            scope=Scope(player="ALL_ACTIVE"),
            range=Range(season="2021-24")
        ))
        # Routes to: expand_scope_and_fetch (450 players × 3 seasons)

        # Backward compatible (params dict)
        result = await execute_query(Query(
            endpoint="player_career_stats",
            params={"player_name": "LeBron James", "season": "2023-24"}
        ))
        # Routes to: unified_fetch
    """
    # Check if expansion is needed
    needs_expansion = _needs_expansion(query)

    if needs_expansion:
        logger.info(f"Query requires expansion - routing to expand_scope_and_fetch")
        return await expand_scope_and_fetch(query, max_concurrent=max_concurrent)

    else:
        logger.info(f"Simple query - routing to unified_fetch")
        return await _execute_simple_query(query)


def _needs_expansion(query: Query) -> bool:
    """
    Determine if query needs scope/range expansion.

    Returns True if:
    - Scope player is "ALL" or "ALL_ACTIVE"
    - Scope player is a list with > 1 players
    - Scope team is "ALL"
    - Scope team is a list with > 1 teams
    - Range season is a range (e.g., "2021-24")
    - Range season is a list with > 1 seasons

    Returns:
        True if expansion needed, False otherwise
    """
    if not query.scope and not query.range:
        # No scope or range specified
        return False

    # Check scope expansion needs
    if query.scope:
        # Player scope
        if query.scope.player:
            if query.scope.player in ["ALL", "ALL_ACTIVE"]:
                return True

            if isinstance(query.scope.player, list) and len(query.scope.player) > 1:
                return True

        # Team scope
        if query.scope.team:
            if query.scope.team == "ALL":
                return True

            if isinstance(query.scope.team, list) and len(query.scope.team) > 1:
                return True

    # Check range expansion needs
    if query.range:
        # Season range
        if query.range.season:
            if isinstance(query.range.season, str):
                # Check if it's a range format (e.g., "2021-24")
                expanded = expand_season_range(query.range.season)
                if len(expanded) > 1:
                    return True

            elif isinstance(query.range.season, list) and len(query.range.season) > 1:
                return True

    return False


async def _execute_simple_query(query: Query) -> QueryResult:
    """
    Execute a simple query using unified_fetch.

    Converts Query model to unified_fetch parameters.

    Args:
        query: Query object

    Returns:
        QueryResult
    """
    # Merge scope/range into params
    params = _merge_scope_range_to_params(query)

    # Normalize params (apply aliases)
    params = normalize_params(params)

    # Convert filters to dict format
    filters = _convert_filters(query.filters)

    # Execute with unified_fetch
    result = await unified_fetch(
        endpoint=query.endpoint,
        params=params,
        filters=filters,
        use_cache=query.use_cache,
        force_refresh=query.force_refresh,
    )

    # Convert UnifiedFetchResult to QueryResult
    return QueryResult(
        data=result.data,
        query=query,
        execution_time_ms=result.execution_time_ms,
        from_cache=result.from_cache,
        warnings=result.warnings,
        transformations=result.transformations,
        metadata={
            "rows": result.data.num_rows,
            "columns": result.data.num_columns,
        },
    )


def _merge_scope_range_to_params(query: Query) -> Dict[str, Any]:
    """
    Merge scope and range into params dict for unified_fetch.

    Takes scope/range from Query model and converts to flat params dict
    compatible with existing unified_fetch API.

    Args:
        query: Query object

    Returns:
        Merged params dictionary
    """
    params = query.params.copy() if query.params else {}

    # Add scope params
    if query.scope:
        if query.scope.player and isinstance(query.scope.player, str):
            params["player_name"] = query.scope.player

        if query.scope.team and isinstance(query.scope.team, str):
            params["team"] = query.scope.team

        if query.scope.game and isinstance(query.scope.game, str):
            params["game_id"] = query.scope.game

    # Add range params
    if query.range:
        if query.range.season and isinstance(query.range.season, str):
            params["season"] = query.range.season

        if query.range.dates:
            # Parse date range "YYYY-MM-DD..YYYY-MM-DD"
            if ".." in query.range.dates:
                start_date, end_date = query.range.dates.split("..")
                params["date_from"] = start_date.strip()
                params["date_to"] = end_date.strip()
            else:
                params["date_from"] = query.range.dates
                params["date_to"] = query.range.dates

    return params


def _convert_filters(filters: Any) -> Union[Dict, None]:
    """
    Convert filters to dict format for unified_fetch.

    Handles:
    - Dict format (pass through)
    - String DSL (TODO: parse to dict)
    - List of FilterExpression (convert to dict)

    Args:
        filters: Filters (dict, list, or string)

    Returns:
        Dict format filters, or None
    """
    if filters is None:
        return None

    if isinstance(filters, dict):
        return filters

    if isinstance(filters, str):
        # TODO: Parse filter DSL string to dict
        # For now, log warning and return None
        logger.warning("Filter DSL strings not yet supported in query_adapter")
        return None

    if isinstance(filters, list):
        # Convert list of FilterExpression to dict
        result = {}
        for expr in filters:
            if hasattr(expr, "column") and hasattr(expr, "operator") and hasattr(expr, "value"):
                result[expr.column] = [expr.operator, expr.value]

        return result

    return None


# Convenience functions for common patterns


async def query_all_active_players(
    endpoint: str,
    season: str = "2023-24",
    filters: Union[Dict, None] = None,
    **kwargs
) -> QueryResult:
    """
    Convenience function to query all active players.

    Examples:
        # All active players career stats
        result = await query_all_active_players(
            "player_career_stats",
            season="2023-24",
            filters={"GP": [">=", 50]}
        )

        # All active players advanced stats
        result = await query_all_active_players(
            "player_advanced_stats",
            season="2023-24",
            filters={"PTS": [">=", 20]}
        )
    """
    query = Query(
        endpoint=endpoint,
        scope=Scope(player="ALL_ACTIVE"),
        range=Range(season=season),
        filters=filters,
        **kwargs
    )

    return await execute_query(query)


async def query_season_range(
    endpoint: str,
    player: str,
    season_range: str,
    filters: Union[Dict, None] = None,
    **kwargs
) -> QueryResult:
    """
    Convenience function to query a season range for a player.

    Examples:
        # LeBron's stats over 3 seasons
        result = await query_season_range(
            "player_game_logs",
            player="LeBron James",
            season_range="2021-24",
            filters={"PTS": [">=", 25]}
        )
    """
    query = Query(
        endpoint=endpoint,
        scope=Scope(player=player),
        range=Range(season=season_range),
        filters=filters,
        **kwargs
    )

    return await execute_query(query)


async def query_multiple_players(
    endpoint: str,
    players: list,
    season: str = "2023-24",
    filters: Union[Dict, None] = None,
    **kwargs
) -> QueryResult:
    """
    Convenience function to query multiple players.

    Examples:
        # Compare 3 players
        result = await query_multiple_players(
            "player_career_stats",
            players=["LeBron James", "Stephen Curry", "Kevin Durant"],
            season="2023-24"
        )
    """
    query = Query(
        endpoint=endpoint,
        scope=Scope(player=players),
        range=Range(season=season),
        filters=filters,
        **kwargs
    )

    return await execute_query(query)
