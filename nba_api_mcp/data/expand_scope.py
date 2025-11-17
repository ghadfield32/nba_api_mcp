"""
Scope expansion and fan-out query execution for NBA API MCP.

Handles expansion of scope specifications (ALL players, season ranges) into
multiple concrete queries, executes them in parallel, and merges results.

Key Features:
- ALL_ACTIVE/ALL player expansion (450+ players → 450+ queries)
- Season range expansion (2021-24 → 3 seasons)
- Team scope expansion (ALL → 30 teams)
- Parallel execution with concurrency control (semaphore)
- Composite caching (cache merged results)
- Progress tracking and fan-out metadata

Design Principles:
- Minimize API calls (cache at multiple levels)
- Respect rate limits (configurable concurrency)
- Fast merging (PyArrow concat_tables)
- Transparent (provide fan-out details in result)
"""

import asyncio
import hashlib
import json
import logging
import time
from asyncio import Semaphore
from typing import Any, Dict, List, Optional

import pyarrow as pa

from nba_api_mcp.data.cache_integration import get_cache_manager
from nba_api_mcp.data.entity_lists import (
    expand_player_scope,
    expand_season_range,
    expand_team_scope,
    estimate_fanout_queries,
)
from nba_api_mcp.data.models.query import Query, QueryResult, Scope, Range
from nba_api_mcp.data.unified_fetch import unified_fetch

logger = logging.getLogger(__name__)

# Default concurrency limit (can be overridden)
DEFAULT_MAX_CONCURRENT = 5


async def expand_scope_and_fetch(
    query: Query,
    max_concurrent: int = DEFAULT_MAX_CONCURRENT,
) -> QueryResult:
    """
    Expand scope (ALL players, multi-seasons) and fetch all data in parallel.

    This function handles fan-out queries where a single query specification
    expands into multiple concrete API calls. Examples:
    - ALL_ACTIVE players → 450+ player queries
    - Season range 2021-24 → 3 season queries
    - Multiple players × multiple seasons → N×M queries

    The function:
    1. Expands scope/range specifications into concrete entity lists
    2. Generates all query combinations (players × teams × seasons)
    3. Checks composite cache for merged result
    4. If not cached, executes queries in parallel with semaphore
    5. Merges PyArrow Tables
    6. Applies post-merge filters/select/order/limit
    7. Caches merged result

    Args:
        query: Query object with scope/range specifications
        max_concurrent: Maximum concurrent API calls (default: 5)

    Returns:
        QueryResult with merged data and fan-out metadata

    Examples:
        # All active players career stats
        result = await expand_scope_and_fetch(Query(
            endpoint="player_career_stats",
            scope=Scope(player="ALL_ACTIVE"),
            range=Range(season="2023-24")
        ))
        # Fan-out: 450+ queries (one per player)

        # Multi-season query
        result = await expand_scope_and_fetch(Query(
            endpoint="player_game_logs",
            scope=Scope(player="LeBron James"),
            range=Range(season="2021-24")  # 3 seasons
        ))
        # Fan-out: 3 queries (one per season)

        # Complex fan-out
        result = await expand_scope_and_fetch(Query(
            endpoint="player_advanced_stats",
            scope=Scope(player=["LeBron James", "Stephen Curry", "Giannis Antetokounmpo"]),
            range=Range(season="2020-24")  # 4 seasons
        ))
        # Fan-out: 12 queries (3 players × 4 seasons)
    """
    start_time = time.time()

    # Step 1: Expand scope entities
    expanded_players = []
    expanded_teams = []

    if query.scope:
        if query.scope.player:
            expanded_players = await expand_player_scope(query.scope.player)
            logger.info(f"Expanded player scope: {len(expanded_players)} players")

        if query.scope.team:
            expanded_teams = await expand_team_scope(query.scope.team)
            logger.info(f"Expanded team scope: {len(expanded_teams)} teams")

    # If no scope expansion, use None to indicate no fanout needed
    if not expanded_players:
        expanded_players = [None]
    if not expanded_teams:
        expanded_teams = [None]

    # Step 2: Expand temporal ranges
    expanded_seasons = []

    if query.range:
        if query.range.season:
            expanded_seasons = expand_season_range(query.range.season)
            logger.info(f"Expanded season range: {len(expanded_seasons)} seasons")

    if not expanded_seasons:
        expanded_seasons = [None]

    # Step 3: Generate all query combinations
    expanded_queries = []

    for player in expanded_players:
        for team in expanded_teams:
            for season in expanded_seasons:
                # Build params for this combination
                params = query.params.copy() if query.params else {}

                # Add scope params
                if player:
                    params["player_name"] = player
                if team:
                    params["team"] = team

                # Add range params
                if season:
                    params["season"] = season

                # Handle date ranges
                if query.range and query.range.dates:
                    # Parse date range "YYYY-MM-DD..YYYY-MM-DD"
                    if ".." in query.range.dates:
                        start_date, end_date = query.range.dates.split("..")
                        params["date_from"] = start_date.strip()
                        params["date_to"] = end_date.strip()
                    else:
                        params["date_from"] = query.range.dates
                        params["date_to"] = query.range.dates

                expanded_queries.append({
                    "endpoint": query.endpoint,
                    "params": params,
                    "filters": query.filters,
                    "use_cache": query.use_cache,
                    "force_refresh": query.force_refresh,
                })

    total_queries = len(expanded_queries)
    logger.info(f"Generated {total_queries} expanded queries")

    # Step 4: Check composite cache first
    composite_cache_key = _generate_composite_cache_key(query, expanded_queries)

    if query.use_cache and not query.force_refresh:
        cache_manager = get_cache_manager()
        cached_result = await cache_manager.get(composite_cache_key)

        if cached_result:
            logger.info(f"Composite cache hit: {composite_cache_key}")

            execution_time = (time.time() - start_time) * 1000

            return QueryResult(
                data=cached_result["data"],
                query=query,
                execution_time_ms=execution_time,
                from_cache=True,
                cache_key=composite_cache_key,
                expanded_queries=expanded_queries,
                metadata={
                    "total_queries": total_queries,
                    "rows": cached_result["data"].num_rows if hasattr(cached_result["data"], "num_rows") else 0,
                },
            )

    # Step 5: Execute all queries in parallel with semaphore
    logger.info(f"Executing {total_queries} queries in parallel (max_concurrent={max_concurrent})")

    semaphore = Semaphore(max_concurrent)

    async def fetch_one(req, index):
        """Fetch a single query with semaphore control"""
        async with semaphore:
            try:
                logger.debug(f"Executing query {index + 1}/{total_queries}: {req['endpoint']}")

                result = await unified_fetch(
                    endpoint=req["endpoint"],
                    params=req["params"],
                    filters=_convert_filters_to_dict(req.get("filters")),
                    use_cache=req.get("use_cache", True),
                    force_refresh=req.get("force_refresh", False),
                )

                return result

            except Exception as e:
                logger.error(f"Query {index + 1}/{total_queries} failed: {e}")
                # Return empty result on failure (graceful degradation)
                return None

    # Execute all queries
    results = await asyncio.gather(*[fetch_one(req, i) for i, req in enumerate(expanded_queries)])

    # Step 6: Merge PyArrow Tables
    tables = []
    warnings = []
    transformations = []

    for i, result in enumerate(results):
        if result is None:
            warnings.append(f"Query {i + 1} failed")
            continue

        if result.data.num_rows > 0:
            tables.append(result.data)

        # Collect warnings and transformations
        warnings.extend(result.warnings)
        transformations.extend(result.transformations)

    if not tables:
        logger.warning("No successful queries - returning empty table")
        merged_table = pa.table({})
    else:
        logger.info(f"Merging {len(tables)} tables")
        merged_table = pa.concat_tables(tables)

    # Step 7: Apply post-merge operations
    if query.filters:
        merged_table = _apply_filters(merged_table, query.filters)
        transformations.append(f"Applied post-merge filters")

    if query.select:
        # Select specific columns
        available_columns = merged_table.schema.names
        valid_columns = [col for col in query.select if col in available_columns]

        if valid_columns:
            merged_table = merged_table.select(valid_columns)
            transformations.append(f"Selected {len(valid_columns)} columns")
        else:
            warnings.append(f"None of the requested columns found in result")

    if query.order_by:
        merged_table = _apply_sort(merged_table, query.order_by)
        transformations.append(f"Sorted by {', '.join(query.order_by)}")

    if query.limit:
        merged_table = merged_table.slice(0, query.limit)
        transformations.append(f"Limited to {query.limit} rows")

    # Step 8: Cache merged result
    if query.use_cache:
        cache_manager = get_cache_manager()
        await cache_manager.set(
            composite_cache_key,
            {"data": merged_table},
            ttl=3600,  # 1 hour for merged results
        )
        logger.info(f"Cached merged result: {composite_cache_key}")

    execution_time = (time.time() - start_time) * 1000

    transformations.insert(0, f"Expanded to {total_queries} queries")
    transformations.append(f"Merged {len(tables)} result tables")
    transformations.append(f"Total execution time: {execution_time:.2f}ms")

    return QueryResult(
        data=merged_table,
        query=query,
        execution_time_ms=execution_time,
        from_cache=False,
        cache_key=composite_cache_key,
        warnings=warnings,
        transformations=transformations,
        expanded_queries=expanded_queries,
        metadata={
            "total_queries": total_queries,
            "successful_queries": len(tables),
            "failed_queries": total_queries - len(tables),
            "rows": merged_table.num_rows,
            "columns": merged_table.num_columns,
        },
    )


def _generate_composite_cache_key(query: Query, expanded_queries: List[Dict]) -> str:
    """
    Generate deterministic cache key for composite query.

    Includes:
    - Endpoint
    - Expanded query count
    - Hash of all expanded queries
    - Filters, select, order_by, limit

    Returns:
        Cache key string
    """
    # Sort expanded queries for deterministic ordering
    sorted_queries = sorted(expanded_queries, key=lambda x: json.dumps(x, sort_keys=True))

    # Create hash of expanded queries
    queries_json = json.dumps(sorted_queries, sort_keys=True)
    queries_hash = hashlib.md5(queries_json.encode()).hexdigest()[:16]

    # Build cache key
    parts = [
        "composite",
        query.endpoint,
        f"n{len(expanded_queries)}",
        queries_hash,
    ]

    if query.filters:
        filters_str = json.dumps(query.filters, sort_keys=True)
        filters_hash = hashlib.md5(filters_str.encode()).hexdigest()[:8]
        parts.append(f"f{filters_hash}")

    if query.select:
        parts.append(f"sel{len(query.select)}")

    if query.order_by:
        parts.append(f"ord{len(query.order_by)}")

    if query.limit:
        parts.append(f"lim{query.limit}")

    return ":".join(parts)


def _convert_filters_to_dict(filters: Any) -> Optional[Dict]:
    """
    Convert filters to dict format for unified_fetch.

    Handles:
    - Dict format (pass through)
    - String DSL (TODO: parse to dict)
    - List of FilterExpression (convert to dict)
    """
    if filters is None:
        return None

    if isinstance(filters, dict):
        return filters

    if isinstance(filters, str):
        # TODO: Parse filter DSL string to dict
        # For now, log warning and return None
        logger.warning("Filter DSL strings not yet supported in expand_scope_and_fetch")
        return None

    if isinstance(filters, list):
        # Convert list of FilterExpression to dict
        result = {}
        for expr in filters:
            if hasattr(expr, "column") and hasattr(expr, "operator") and hasattr(expr, "value"):
                result[expr.column] = [expr.operator, expr.value]

        return result

    return None


def _apply_filters(table: pa.Table, filters: Any) -> pa.Table:
    """
    Apply filters to PyArrow Table using DuckDB.

    Args:
        table: PyArrow Table
        filters: Filters (dict, list, or string)

    Returns:
        Filtered PyArrow Table
    """
    if not filters or table.num_rows == 0:
        return table

    try:
        import duckdb

        # Convert to dict format
        filters_dict = _convert_filters_to_dict(filters)

        if not filters_dict:
            return table

        # Build WHERE clause
        conditions = []
        for column, (operator, value) in filters_dict.items():
            if column not in table.schema.names:
                logger.warning(f"Filter column '{column}' not found in table")
                continue

            if operator in ["==", "="]:
                conditions.append(f'"{column}" = {_quote_value(value)}')
            elif operator == "!=":
                conditions.append(f'"{column}" != {_quote_value(value)}')
            elif operator == ">":
                conditions.append(f'"{column}" > {_quote_value(value)}')
            elif operator == ">=":
                conditions.append(f'"{column}" >= {_quote_value(value)}')
            elif operator == "<":
                conditions.append(f'"{column}" < {_quote_value(value)}')
            elif operator == "<=":
                conditions.append(f'"{column}" <= {_quote_value(value)}')
            elif operator == "IN":
                values_str = ", ".join([_quote_value(v) for v in value])
                conditions.append(f'"{column}" IN ({values_str})')
            elif operator == "BETWEEN":
                conditions.append(f'"{column}" BETWEEN {_quote_value(value[0])} AND {_quote_value(value[1])}')
            elif operator == "LIKE":
                conditions.append(f'"{column}" LIKE {_quote_value(value)}')

        if not conditions:
            return table

        where_clause = " AND ".join(conditions)

        # Execute filter with DuckDB
        filtered_df = duckdb.query(f"SELECT * FROM table WHERE {where_clause}").to_df()

        return pa.Table.from_pandas(filtered_df)

    except Exception as e:
        logger.error(f"Filter application failed: {e}")
        return table


def _apply_sort(table: pa.Table, order_by: List[str]) -> pa.Table:
    """
    Apply sorting to PyArrow Table using DuckDB.

    Args:
        table: PyArrow Table
        order_by: List of sort specifications (e.g., ["PTS DESC", "PLAYER_NAME ASC"])

    Returns:
        Sorted PyArrow Table
    """
    if not order_by or table.num_rows == 0:
        return table

    try:
        import duckdb

        # Build ORDER BY clause
        order_clause = ", ".join([f'"{spec}"' for spec in order_by])

        # Execute sort with DuckDB
        sorted_df = duckdb.query(f"SELECT * FROM table ORDER BY {order_clause}").to_df()

        return pa.Table.from_pandas(sorted_df)

    except Exception as e:
        logger.error(f"Sorting failed: {e}")
        return table


def _quote_value(value: Any) -> str:
    """
    Quote a value for SQL.

    Args:
        value: Value to quote

    Returns:
        Quoted string
    """
    if isinstance(value, str):
        # Escape single quotes
        escaped = value.replace("'", "''")
        return f"'{escaped}'"
    elif value is None:
        return "NULL"
    else:
        return str(value)
