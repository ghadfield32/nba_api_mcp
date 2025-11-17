"""
Query models for NBA API MCP unified fetch system.

Provides structured query models that support:
- Scope-based queries (ALL players, ALL teams, multi-entity)
- Temporal ranges (season ranges, date ranges)
- Flexible filtering (dict, list, string DSL)
- Column selection, ordering, and pagination

Design Principles:
- Backward compatible: All fields optional, works with existing params dict
- Progressive enhancement: New features additive, not breaking
- Type-safe: Full Pydantic validation
- Flexible: Multiple filter formats supported
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Union, Literal
from enum import Enum


class Scope(BaseModel):
    """
    Entity scope for queries.

    Supports:
    - Single entity: player="LeBron James"
    - Multiple entities: player=["LeBron James", "Stephen Curry"]
    - All active: player="ALL_ACTIVE"
    - All historical: player="ALL"
    - All teams: team="ALL"

    Examples:
        # Single player
        Scope(player="LeBron James")

        # Multiple players
        Scope(player=["LeBron James", "Stephen Curry", "Kevin Durant"])

        # All active players
        Scope(player="ALL_ACTIVE")

        # All teams
        Scope(team="ALL")

        # Specific team
        Scope(team="Lakers")
    """

    player: Optional[Union[str, List[str]]] = Field(
        None,
        description="Player name(s), 'ALL', or 'ALL_ACTIVE'",
        example="LeBron James",
    )
    team: Optional[Union[str, List[str]]] = Field(
        None,
        description="Team name(s) or 'ALL'",
        example="Lakers",
    )
    game: Optional[Union[str, List[str]]] = Field(
        None,
        description="Game ID(s)",
        example="0022300515",
    )
    league: Optional[str] = Field(
        None,
        description="League identifier (usually NBA)",
        example="NBA",
    )


class Range(BaseModel):
    """
    Temporal ranges for queries.

    Supports:
    - Single season: season="2023-24"
    - Season range: season="2021-24" (auto-expands to 3 seasons)
    - Multiple seasons: season=["2022-23", "2023-24"]
    - Date range: dates="2024-10-01..2025-04-01"

    Examples:
        # Single season
        Range(season="2023-24")

        # Season range (expands to ["2021-22", "2022-23", "2023-24"])
        Range(season="2021-24")

        # Multiple specific seasons
        Range(season=["2021-22", "2023-24"])

        # Date range
        Range(dates="2024-10-01..2025-04-01")

        # Both
        Range(season="2023-24", dates="2024-01-01..2024-03-31")
    """

    season: Optional[Union[str, List[str]]] = Field(
        None,
        description="Season(s) in 'YYYY-YY' format or range 'YYYY-YY' format",
        example="2023-24",
    )
    dates: Optional[str] = Field(
        None,
        description="Date range in 'YYYY-MM-DD..YYYY-MM-DD' format",
        example="2024-01-01..2024-03-31",
    )
    game_date: Optional[str] = Field(
        None,
        description="Alias for dates (for backward compatibility)",
        example="2024-01-01..2024-03-31",
    )

    @validator("dates", "game_date")
    def validate_date_format(cls, v):
        """Validate date range format"""
        if v and ".." in v:
            parts = v.split("..")
            if len(parts) != 2:
                raise ValueError("Date range must be in format 'YYYY-MM-DD..YYYY-MM-DD'")
        return v


class FilterOperator(str, Enum):
    """Supported filter operators"""

    EQ = "=="
    NE = "!="
    GT = ">"
    GTE = ">="
    LT = "<"
    LTE = "<="
    IN = "IN"
    BETWEEN = "BETWEEN"
    LIKE = "LIKE"


class FilterExpression(BaseModel):
    """
    Structured filter expression.

    Examples:
        # Greater than
        FilterExpression(column="PTS", operator=">=", value=25)

        # Equality
        FilterExpression(column="WL", operator="==", value="W")

        # In list
        FilterExpression(column="TEAM_ABBREVIATION", operator="IN", value=["LAL", "GSW", "BOS"])

        # Between
        FilterExpression(column="PTS", operator="BETWEEN", value=[25, 40])

        # Like (pattern)
        FilterExpression(column="PLAYER_NAME", operator="LIKE", value="%James%")
    """

    column: str = Field(..., description="Column name to filter on")
    operator: Union[FilterOperator, str] = Field(..., description="Filter operator")
    value: Union[str, int, float, List[Any], bool] = Field(
        ..., description="Value(s) to filter by"
    )


class Query(BaseModel):
    """
    Universal query model for NBA data.

    Provides a unified interface for all NBA data fetching with support for:
    - Scope-based queries (single/multi/ALL entities)
    - Temporal ranges (seasons, dates)
    - Flexible filtering (dict/list/string)
    - Column selection and ordering
    - Caching control

    Examples:
        # Simple query
        Query(
            endpoint="player_career_stats",
            scope=Scope(player="LeBron James")
        )

        # All active players with filters
        Query(
            endpoint="player_career_stats",
            scope=Scope(player="ALL_ACTIVE"),
            filters={"GP": [">=", 50], "PTS": [">=", 20]}
        )

        # Season range query
        Query(
            endpoint="player_game_logs",
            scope=Scope(player="Stephen Curry"),
            range=Range(season="2021-24"),  # 3 seasons
            filters=[
                FilterExpression(column="PTS", operator=">=", value=30),
                FilterExpression(column="FG3M", operator=">=", value=5)
            ]
        )

        # Team query with date range
        Query(
            endpoint="team_game_log",
            scope=Scope(team="Lakers"),
            range=Range(dates="2024-01-01..2024-03-31"),
            filters={"WL": ["==", "W"]}
        )

        # League leaders with selection and ordering
        Query(
            endpoint="league_leaders",
            params={"stat_category": "PTS"},
            filters="PTS >= 25",  # String DSL
            select=["PLAYER_NAME", "TEAM_ABBREVIATION", "PTS"],
            order_by=["PTS DESC"],
            limit=10
        )
    """

    endpoint: str = Field(..., description="Endpoint name to query")

    scope: Optional[Scope] = Field(
        None, description="Entity scope (player/team/game)"
    )

    range: Optional[Range] = Field(
        None, description="Temporal range (seasons/dates)"
    )

    params: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional endpoint-specific parameters",
    )

    filters: Optional[Union[Dict, List[FilterExpression], str]] = Field(
        None,
        description="Filters (dict, list of expressions, or string DSL)",
    )

    select: Optional[List[str]] = Field(
        None,
        description="Columns to select (if not specified, all columns returned)",
    )

    order_by: Optional[List[str]] = Field(
        None,
        description="Sort specification (e.g., ['PTS DESC', 'PLAYER_NAME ASC'])",
    )

    limit: Optional[int] = Field(
        None,
        description="Maximum number of rows to return",
        gt=0,
    )

    offset: Optional[int] = Field(
        None,
        description="Number of rows to skip (for pagination)",
        ge=0,
    )

    use_cache: bool = Field(
        True,
        description="Whether to use cache for this query",
    )

    force_refresh: bool = Field(
        False,
        description="Force refresh even if cached",
    )

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "endpoint": "player_career_stats",
                    "scope": {"player": "LeBron James"},
                    "range": {"season": "2023-24"},
                },
                {
                    "endpoint": "player_game_logs",
                    "scope": {"player": "ALL_ACTIVE"},
                    "range": {"season": "2021-24"},
                    "filters": {"PTS": [">=", 25], "FG3M": [">=", 5]},
                    "limit": 100,
                },
            ]
        }


class QueryResult(BaseModel):
    """
    Query execution result with metadata.

    Contains:
    - data: PyArrow Table (or dict for JSON serialization)
    - query: Original query
    - execution_time_ms: Execution time
    - from_cache: Whether result came from cache
    - warnings: Any warnings during execution
    - transformations: Applied transformations
    - expanded_queries: Fan-out details (if scope expansion occurred)

    Examples:
        result = await execute_query(query)
        print(f"Rows: {result.metadata['rows']}")
        print(f"Time: {result.execution_time_ms:.2f}ms")
        print(f"Cached: {result.from_cache}")

        if result.expanded_queries:
            print(f"Fan-out: {len(result.expanded_queries)} queries")
    """

    data: Any = Field(
        ...,
        description="Query result data (PyArrow Table or dict)",
    )

    query: Query = Field(
        ...,
        description="Original query",
    )

    execution_time_ms: float = Field(
        ...,
        description="Execution time in milliseconds",
    )

    from_cache: bool = Field(
        ...,
        description="Whether result came from cache",
    )

    cache_key: Optional[str] = Field(
        None,
        description="Cache key used (if cached)",
    )

    warnings: List[str] = Field(
        default_factory=list,
        description="Warnings during execution",
    )

    transformations: List[str] = Field(
        default_factory=list,
        description="Applied transformations (filter pushdown, etc.)",
    )

    expanded_queries: Optional[List[Dict]] = Field(
        None,
        description="Details of fan-out queries (if scope expansion occurred)",
    )

    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional result metadata",
    )

    class Config:
        arbitrary_types_allowed = True  # Allow PyArrow Table


# Catalog Metadata Models (for endpoint capabilities)


class ScopeCapability(BaseModel):
    """
    Scope capabilities for an endpoint.

    Defines what types of scope queries an endpoint supports.

    Examples:
        # Player endpoint
        ScopeCapability(
            supports_all_players=True,
            supports_multi_players=True,
            required_scope="player"
        )

        # Team endpoint
        ScopeCapability(
            supports_all_teams=True,
            supports_multi_teams=True,
            required_scope="team"
        )

        # League endpoint (no scope required)
        ScopeCapability(
            supports_all_players=False,
            required_scope=None
        )
    """

    supports_all_players: bool = Field(
        False,
        description="Supports 'ALL' and 'ALL_ACTIVE' player queries",
    )

    supports_multi_players: bool = Field(
        False,
        description="Supports multiple players in one query",
    )

    supports_all_teams: bool = Field(
        False,
        description="Supports 'ALL' team queries",
    )

    supports_multi_teams: bool = Field(
        False,
        description="Supports multiple teams in one query",
    )

    required_scope: Optional[Literal["player", "team", "game", "none"]] = Field(
        None,
        description="Required scope type (if any)",
    )


class RangeCapability(BaseModel):
    """
    Temporal range capabilities for an endpoint.

    Defines what types of temporal ranges an endpoint supports.

    Examples:
        # Supports season ranges
        RangeCapability(
            supports_season_range=True,
            supports_date_range=False,
            season_format="YYYY-YY"
        )

        # Supports date ranges
        RangeCapability(
            supports_season_range=False,
            supports_date_range=True,
            date_format="YYYY-MM-DD"
        )

        # Supports both
        RangeCapability(
            supports_season_range=True,
            supports_date_range=True
        )
    """

    supports_season_range: bool = Field(
        False,
        description="Supports season range queries (e.g., '2021-24')",
    )

    supports_date_range: bool = Field(
        False,
        description="Supports date range queries (e.g., '2024-01-01..2024-03-31')",
    )

    season_format: Optional[str] = Field(
        "YYYY-YY",
        description="Season format string",
    )

    date_format: Optional[str] = Field(
        "YYYY-MM-DD",
        description="Date format string",
    )


class FilterCapability(BaseModel):
    """
    Filter capability metadata for a column.

    Defines what types of filters are supported for a specific column.

    Examples:
        # Integer column
        FilterCapability(
            column="PTS",
            type="integer",
            pushable=False,
            operators=["==", "!=", ">", ">=", "<", "<=", "IN", "BETWEEN"],
            examples=[25, 30, 40]
        )

        # String column with enum
        FilterCapability(
            column="WL",
            type="string",
            pushable=True,  # Can be pushed to API
            operators=["==", "!="],
            enum_values=["W", "L"]
        )

        # Date column
        FilterCapability(
            column="GAME_DATE",
            type="date",
            pushable=True,
            operators=["==", ">", ">=", "<", "<=", "BETWEEN"]
        )
    """

    column: str = Field(..., description="Column name")

    type: Literal["string", "integer", "float", "boolean", "date"] = Field(
        ..., description="Column data type"
    )

    pushable: bool = Field(
        False,
        description="Whether filter can be pushed to API level (faster)",
    )

    operators: List[str] = Field(
        ...,
        description="Supported filter operators for this column",
    )

    examples: Optional[List[Any]] = Field(
        None,
        description="Example values for this column",
    )

    enum_values: Optional[List[Any]] = Field(
        None,
        description="Enumerated values (if column has fixed set of values)",
    )

    description: Optional[str] = Field(
        None,
        description="Human-readable description of the column",
    )
