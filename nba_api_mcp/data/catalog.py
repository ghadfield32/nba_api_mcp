"""
Data catalog for NBA MCP endpoints.

Provides comprehensive metadata about all available endpoints including:
- Parameter schemas
- Primary and foreign keys
- Join relationships
- Example queries
- Data dictionary

This module serves as the single source of truth for endpoint metadata.
"""

from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

# Phase 2 Enhancement: Import capability models from Phase 1
from nba_api_mcp.data.models.query import (
    ScopeCapability,
    RangeCapability,
    FilterCapability,
)


class EndpointCategory(str, Enum):
    """Categories for organizing endpoints."""

    PLAYER_STATS = "player_stats"
    TEAM_STATS = "team_stats"
    GAME_DATA = "game_data"
    LEAGUE_DATA = "league_data"
    ADVANCED_ANALYTICS = "advanced_analytics"


class ParameterSchema(BaseModel):
    """Schema definition for an endpoint parameter."""

    name: str
    type: str  # "string", "integer", "boolean", "array", "date"
    required: bool = False
    description: str = ""
    default: Optional[Any] = None
    enum: Optional[List[str]] = None
    example: Optional[Any] = None


class EndpointMetadata(BaseModel):
    """Comprehensive metadata for an NBA API endpoint."""

    name: str = Field(description="Unique endpoint identifier")
    display_name: str = Field(description="Human-readable name")
    category: EndpointCategory
    description: str
    parameters: List[ParameterSchema] = Field(default_factory=list)
    primary_keys: List[str] = Field(default_factory=list)
    output_columns: List[str] = Field(default_factory=list)
    sample_params: Dict[str, Any] = Field(default_factory=dict)
    notes: Optional[str] = None

    # New pagination/chunking metadata
    supports_date_range: bool = False
    supports_season_filter: bool = False
    supports_pagination: bool = False
    typical_row_count: Optional[int] = None
    max_row_count: Optional[int] = None
    available_seasons: Optional[List[str]] = None
    chunk_strategy: Optional[str] = None  # "date", "season", "game", "none"
    min_date: Optional[str] = None  # Format: "YYYY-MM-DD"
    max_date: Optional[str] = None  # Format: "YYYY-MM-DD"

    # Phase 2 Enhancement: Query capability metadata
    scope_capability: Optional[ScopeCapability] = None
    range_capability: Optional[RangeCapability] = None
    filterable_columns: Dict[str, FilterCapability] = Field(default_factory=dict)
    rate_cost: int = 1  # Relative cost (1=simple, 3=moderate, 5=expensive)

    # Phase 4H: Filter presets for quick query building
    filter_presets: List[Dict[str, Any]] = Field(default_factory=list)


class JoinRelationship(BaseModel):
    """Defines a join relationship between two endpoints."""

    from_endpoint: str
    to_endpoint: str
    join_keys: Dict[str, str] = Field(description="Mapping of {from_column: to_column}")
    join_type: Literal["inner", "left", "right", "outer"] = "left"
    description: str
    example_use_case: str


class JoinExample(BaseModel):
    """Complete example of a multi-step dataset build."""

    name: str
    description: str
    steps: List[Dict[str, Any]]
    expected_output: str


class DataCatalog:
    """
    Central catalog of all NBA MCP endpoints and their relationships.

    This class provides:
    1. Endpoint discovery and enumeration
    2. Parameter schema information
    3. Primary/foreign key relationships
    4. Join recommendations
    5. Example queries
    """

    def __init__(self):
        """Initialize the data catalog with all endpoint metadata."""
        self._endpoints: Dict[str, EndpointMetadata] = {}
        self._relationships: List[JoinRelationship] = []
        self._join_examples: List[JoinExample] = []
        self._initialize_catalog()

    def _initialize_catalog(self):
        """Populate the catalog with all endpoint definitions."""
        # Player Stats Endpoints
        self._add_endpoint(
            EndpointMetadata(
                name="player_career_stats",
                display_name="Player Career Statistics",
                category=EndpointCategory.PLAYER_STATS,
                description="Comprehensive career statistics for a player across all seasons",
                parameters=[
                    ParameterSchema(
                        name="player_name",
                        type="string",
                        required=True,
                        description="Player name (fuzzy matching supported)",
                        example="LeBron James",
                    ),
                    ParameterSchema(
                        name="season",
                        type="string",
                        required=False,
                        description="Specific season in YYYY-YY format",
                        example="2023-24",
                    ),
                ],
                primary_keys=["PLAYER_ID", "SEASON_ID"],
                output_columns=[
                    "PLAYER_ID",
                    "PLAYER_NAME",
                    "SEASON_ID",
                    "TEAM_ID",
                    "TEAM_ABBREVIATION",
                    "GP",
                    "GS",
                    "MIN",
                    "FGM",
                    "FGA",
                    "FG_PCT",
                    "FG3M",
                    "FG3A",
                    "FG3_PCT",
                    "FTM",
                    "FTA",
                    "FT_PCT",
                    "OREB",
                    "DREB",
                    "REB",
                    "AST",
                    "STL",
                    "BLK",
                    "TOV",
                    "PF",
                    "PTS",
                ],
                sample_params={"player_name": "LeBron James"},
                notes="Returns all seasons if season not specified",
                # Phase 2: Capability metadata
                scope_capability=ScopeCapability(
                    supports_all_players=True,
                    supports_multi_players=True,
                    required_scope="player",
                ),
                range_capability=RangeCapability(
                    supports_season_range=True,
                    supports_date_range=False,
                ),
                filterable_columns={
                    "GP": FilterCapability(
                        column="GP",
                        type="integer",
                        pushable=False,
                        operators=["==", "!=", ">", ">=", "<", "<=", "IN", "BETWEEN"],
                        examples=[82, 60, 40],
                    ),
                    "PTS": FilterCapability(
                        column="PTS",
                        type="float",
                        pushable=False,
                        operators=["==", "!=", ">", ">=", "<", "<=", "BETWEEN"],
                        examples=[25.0, 20.0, 15.0],
                    ),
                    "AST": FilterCapability(
                        column="AST",
                        type="float",
                        pushable=False,
                        operators=["==", "!=", ">", ">=", "<", "<=", "BETWEEN"],
                        examples=[7.0, 5.0, 3.0],
                    ),
                    "REB": FilterCapability(
                        column="REB",
                        type="float",
                        pushable=False,
                        operators=["==", "!=", ">", ">=", "<", "<=", "BETWEEN"],
                        examples=[10.0, 7.0, 5.0],
                    ),
                    "FG_PCT": FilterCapability(
                        column="FG_PCT",
                        type="float",
                        pushable=False,
                        operators=[">", ">=", "<", "<=", "BETWEEN"],
                        examples=[0.500, 0.450, 0.400],
                        description="Field Goal Percentage",
                    ),
                },
                rate_cost=3,  # Higher cost due to ALL_ACTIVE support
                # Phase 4H: Filter presets
                filter_presets=[
                    {
                        "name": "High Scorers (25+ PPG)",
                        "description": "Players averaging 25+ points in 50+ games",
                        "filters": {"PTS": [">=", 25], "GP": [">=", 50]},
                    },
                    {
                        "name": "Efficient Shooters",
                        "description": "50%+ FG and 40%+ 3PT shooting",
                        "filters": {"FG_PCT": [">=", 0.50], "FG3_PCT": [">=", 0.40]},
                    },
                    {
                        "name": "All-Around Players",
                        "description": "20+ pts, 5+ ast, 5+ reb",
                        "filters": {"PTS": [">=", 20], "AST": [">=", 5], "REB": [">=", 5]},
                    },
                    {
                        "name": "Iron Men (70+ Games)",
                        "description": "Played 70+ games with 30+ minutes",
                        "filters": {"GP": [">=", 70], "MIN": [">=", 30]},
                    },
                ],
            )
        )

        self._add_endpoint(
            EndpointMetadata(
                name="player_advanced_stats",
                display_name="Player Advanced Statistics",
                category=EndpointCategory.ADVANCED_ANALYTICS,
                description="Advanced efficiency metrics for a player (TS%, Usage%, PER, etc.)",
                parameters=[
                    ParameterSchema(
                        name="player_name",
                        type="string",
                        required=True,
                        description="Player name",
                        example="Stephen Curry",
                    ),
                    ParameterSchema(
                        name="season",
                        type="string",
                        required=False,
                        description="Season in YYYY-YY format",
                        example="2023-24",
                    ),
                ],
                primary_keys=["PLAYER_ID", "SEASON"],
                output_columns=[
                    "PLAYER_ID",
                    "PLAYER_NAME",
                    "SEASON",
                    "TEAM_ID",
                    "GP",
                    "MIN",
                    "TS_PCT",
                    "EFG_PCT",
                    "USAGE_PCT",
                    "PIE",
                    "OFF_RATING",
                    "DEF_RATING",
                    "NET_RATING",
                    "AST_PCT",
                    "REB_PCT",
                    "TOV_PCT",
                ],
                sample_params={"player_name": "Stephen Curry", "season": "2023-24"},
                # Phase 2: Capability metadata
                scope_capability=ScopeCapability(
                    supports_all_players=True,
                    supports_multi_players=True,
                    required_scope="player",
                ),
                range_capability=RangeCapability(
                    supports_season_range=True,
                    supports_date_range=False,
                ),
                filterable_columns={
                    "GP": FilterCapability(
                        column="GP",
                        type="integer",
                        pushable=False,
                        operators=[">=", "<=", "BETWEEN"],
                        examples=[60, 50, 40],
                    ),
                    "TS_PCT": FilterCapability(
                        column="TS_PCT",
                        type="float",
                        pushable=False,
                        operators=[">", ">=", "<", "<="],
                        examples=[0.600, 0.550, 0.500],
                        description="True Shooting Percentage",
                    ),
                    "USG_PCT": FilterCapability(
                        column="USAGE_PCT",
                        type="float",
                        pushable=False,
                        operators=[">", ">=", "<", "<="],
                        examples=[30.0, 25.0, 20.0],
                        description="Usage Percentage",
                    ),
                    "OFF_RATING": FilterCapability(
                        column="OFF_RATING",
                        type="float",
                        pushable=False,
                        operators=[">", ">=", "<", "<="],
                        examples=[120.0, 115.0, 110.0],
                        description="Offensive Rating",
                    ),
                    "DEF_RATING": FilterCapability(
                        column="DEF_RATING",
                        type="float",
                        pushable=False,
                        operators=[">", ">=", "<", "<="],
                        examples=[100.0, 105.0, 110.0],
                        description="Defensive Rating (lower is better)",
                    ),
                },
                rate_cost=3,  # Higher cost due to ALL_ACTIVE support
            )
        )

        # Team Stats Endpoints
        self._add_endpoint(
            EndpointMetadata(
                name="team_standings",
                display_name="Team Standings",
                category=EndpointCategory.TEAM_STATS,
                description="Conference and division standings with win/loss records",
                parameters=[
                    ParameterSchema(
                        name="season",
                        type="string",
                        required=False,
                        description="Season in YYYY-YY format (defaults to current)",
                        example="2023-24",
                    ),
                    ParameterSchema(
                        name="conference",
                        type="string",
                        required=False,
                        description="Filter by conference",
                        enum=["East", "West"],
                        example="East",
                    ),
                ],
                primary_keys=["TEAM_ID", "SEASON"],
                output_columns=[
                    "TEAM_ID",
                    "TEAM_NAME",
                    "SEASON",
                    "CONFERENCE",
                    "CONFERENCE_RANK",
                    "DIVISION",
                    "DIVISION_RANK",
                    "W",
                    "L",
                    "W_PCT",
                    "GB",
                    "HOME_RECORD",
                    "ROAD_RECORD",
                    "LAST_10",
                    "STREAK",
                ],
                sample_params={"season": "2023-24", "conference": "East"},
                # Phase 2: Capability metadata
                scope_capability=ScopeCapability(
                    supports_all_teams=False,  # Already returns all teams by default
                    supports_multi_teams=False,
                    required_scope=None,
                ),
                range_capability=RangeCapability(
                    supports_season_range=True,
                    supports_date_range=False,
                ),
                filterable_columns={
                    "CONFERENCE": FilterCapability(
                        column="CONFERENCE",
                        type="string",
                        pushable=True,  # Can be pushed to API via conference parameter
                        operators=["==", "!="],
                        enum_values=["East", "West"],
                        description="Conference filter",
                    ),
                    "W": FilterCapability(
                        column="W",
                        type="integer",
                        pushable=False,
                        operators=[">", ">=", "<", "<=", "BETWEEN"],
                        examples=[50, 40, 30],
                        description="Wins",
                    ),
                    "W_PCT": FilterCapability(
                        column="W_PCT",
                        type="float",
                        pushable=False,
                        operators=[">", ">=", "<", "<=", "BETWEEN"],
                        examples=[0.600, 0.500, 0.400],
                        description="Win Percentage",
                    ),
                },
                rate_cost=1,  # Low cost - single API call
            )
        )

        self._add_endpoint(
            EndpointMetadata(
                name="team_advanced_stats",
                display_name="Team Advanced Statistics",
                category=EndpointCategory.ADVANCED_ANALYTICS,
                description="Team efficiency metrics (OffRtg, DefRtg, Pace, Four Factors)",
                parameters=[
                    ParameterSchema(
                        name="team_name",
                        type="string",
                        required=True,
                        description="Team name or abbreviation",
                        example="Lakers",
                    ),
                    ParameterSchema(
                        name="season",
                        type="string",
                        required=False,
                        description="Season in YYYY-YY format",
                        example="2023-24",
                    ),
                ],
                primary_keys=["TEAM_ID", "SEASON"],
                output_columns=[
                    "TEAM_ID",
                    "TEAM_NAME",
                    "SEASON",
                    "GP",
                    "W",
                    "L",
                    "W_PCT",
                    "OFF_RATING",
                    "DEF_RATING",
                    "NET_RATING",
                    "PACE",
                    "TS_PCT",
                    "EFG_PCT",
                    "TOV_PCT",
                    "OREB_PCT",
                    "FTA_RATE",
                    "OPP_EFG_PCT",
                    "OPP_TOV_PCT",
                    "OPP_OREB_PCT",
                    "OPP_FTA_RATE",
                ],
                sample_params={"team_name": "Lakers", "season": "2023-24"},
            )
        )

        self._add_endpoint(
            EndpointMetadata(
                name="team_game_log",
                display_name="Team Game Log",
                category=EndpointCategory.TEAM_STATS,
                description="Historical game-by-game results for a team",
                parameters=[
                    ParameterSchema(
                        name="team",
                        type="string",
                        required=True,
                        description="Team name or abbreviation",
                        example="Lakers",
                    ),
                    ParameterSchema(
                        name="season",
                        type="string",
                        required=True,
                        description="Season in YYYY-YY format",
                        example="2023-24",
                    ),
                    ParameterSchema(
                        name="date_from",
                        type="date",
                        required=False,
                        description="Start date (YYYY-MM-DD)",
                        example="2024-01-01",
                    ),
                    ParameterSchema(
                        name="date_to",
                        type="date",
                        required=False,
                        description="End date (YYYY-MM-DD)",
                        example="2024-01-31",
                    ),
                ],
                primary_keys=["GAME_ID"],
                output_columns=[
                    "GAME_ID",
                    "GAME_DATE",
                    "TEAM_ID",
                    "TEAM_NAME",
                    "MATCHUP",
                    "WL",
                    "PTS",
                    "FGM",
                    "FGA",
                    "FG_PCT",
                    "FG3M",
                    "FG3A",
                    "FG3_PCT",
                    "FTM",
                    "FTA",
                    "FT_PCT",
                    "OREB",
                    "DREB",
                    "REB",
                    "AST",
                    "STL",
                    "BLK",
                    "TOV",
                    "PF",
                    "PLUS_MINUS",
                ],
                sample_params={
                    "team": "Lakers",
                    "season": "2023-24",
                    "date_from": "2024-01-01",
                },
                # Phase 2: Capability metadata
                scope_capability=ScopeCapability(
                    supports_all_teams=True,  # Can query all teams
                    supports_multi_teams=True,
                    required_scope="team",
                ),
                range_capability=RangeCapability(
                    supports_season_range=True,
                    supports_date_range=True,  # Supports date_from/date_to
                ),
                filterable_columns={
                    "GAME_DATE": FilterCapability(
                        column="GAME_DATE",
                        type="date",
                        pushable=True,  # Can be pushed to API via date_from/date_to
                        operators=["==", ">", ">=", "<", "<=", "BETWEEN"],
                        examples=["2024-01-01", "2024-02-15"],
                        description="Game date",
                    ),
                    "WL": FilterCapability(
                        column="WL",
                        type="string",
                        pushable=True,  # NBA API might support this
                        operators=["==", "!="],
                        enum_values=["W", "L"],
                        description="Win/Loss result",
                    ),
                    "PTS": FilterCapability(
                        column="PTS",
                        type="integer",
                        pushable=False,
                        operators=[">", ">=", "<", "<=", "BETWEEN"],
                        examples=[120, 110, 100],
                        description="Points scored",
                    ),
                    "PLUS_MINUS": FilterCapability(
                        column="PLUS_MINUS",
                        type="integer",
                        pushable=False,
                        operators=[">", ">=", "<", "<=", "BETWEEN"],
                        examples=[10, 0, -10],
                        description="Plus/Minus differential",
                    ),
                },
                rate_cost=2,  # Moderate cost
                # Phase 4H: Filter presets
                filter_presets=[
                    {
                        "name": "Winning Teams",
                        "description": "Wins scoring 110+ points",
                        "filters": {"WL": ["==", "W"], "PTS": [">=", 110]},
                    },
                    {
                        "name": "Close Games",
                        "description": "Games decided by 5 points or less",
                        "filters": {"PLUS_MINUS": ["BETWEEN", -5, 5]},
                    },
                    {
                        "name": "Blowouts (20+ Margin)",
                        "description": "Wins by 20+ points",
                        "filters": {"PLUS_MINUS": [">", 20], "WL": ["==", "W"]},
                    },
                ],
            )
        )

        # Game Data Endpoints
        self._add_endpoint(
            EndpointMetadata(
                name="live_scores",
                display_name="Live Game Scores",
                category=EndpointCategory.GAME_DATA,
                description="Current or historical game scores and status",
                parameters=[
                    ParameterSchema(
                        name="target_date",
                        type="date",
                        required=False,
                        description="Date for scores (YYYY-MM-DD), defaults to today",
                        example="2024-03-15",
                    )
                ],
                primary_keys=["GAME_ID"],
                output_columns=[
                    "GAME_ID",
                    "GAME_DATE",
                    "HOME_TEAM_ID",
                    "HOME_TEAM_NAME",
                    "HOME_TEAM_SCORE",
                    "AWAY_TEAM_ID",
                    "AWAY_TEAM_NAME",
                    "AWAY_TEAM_SCORE",
                    "GAME_STATUS",
                    "PERIOD",
                    "TIME_REMAINING",
                ],
                sample_params={"target_date": "2024-03-15"},
            )
        )

        self._add_endpoint(
            EndpointMetadata(
                name="play_by_play",
                display_name="Play-by-Play Data",
                category=EndpointCategory.GAME_DATA,
                description="Detailed play-by-play action for a game",
                parameters=[
                    ParameterSchema(
                        name="game_date",
                        type="date",
                        required=False,
                        description="Game date (YYYY-MM-DD)",
                        example="2024-03-15",
                    ),
                    ParameterSchema(
                        name="team",
                        type="string",
                        required=False,
                        description="Filter by team",
                        example="Lakers",
                    ),
                    ParameterSchema(
                        name="start_period",
                        type="integer",
                        required=False,
                        description="Starting period",
                        default=1,
                    ),
                    ParameterSchema(
                        name="end_period",
                        type="integer",
                        required=False,
                        description="Ending period",
                        default=4,
                    ),
                ],
                primary_keys=["GAME_ID", "EVENT_NUM"],
                output_columns=[
                    "GAME_ID",
                    "EVENT_NUM",
                    "PERIOD",
                    "CLOCK",
                    "TEAM_ID",
                    "PLAYER_ID",
                    "EVENT_TYPE",
                    "ACTION_TYPE",
                    "DESCRIPTION",
                    "SCORE",
                ],
                sample_params={"game_date": "2024-03-15", "team": "Lakers"},
            )
        )

        # League Data Endpoints
        self._add_endpoint(
            EndpointMetadata(
                name="league_leaders",
                display_name="League Leaders",
                category=EndpointCategory.LEAGUE_DATA,
                description="Top performers in any statistical category",
                parameters=[
                    ParameterSchema(
                        name="stat_category",
                        type="string",
                        required=True,
                        description="Statistical category",
                        enum=[
                            "PTS",
                            "REB",
                            "AST",
                            "STL",
                            "BLK",
                            "FG_PCT",
                            "FG3_PCT",
                            "FT_PCT",
                        ],
                        example="PTS",
                    ),
                    ParameterSchema(
                        name="season",
                        type="string",
                        required=False,
                        description="Season in YYYY-YY format",
                        example="2023-24",
                    ),
                    ParameterSchema(
                        name="per_mode",
                        type="string",
                        required=False,
                        description="Per-game, totals, or per-48 minutes",
                        enum=["PerGame", "Totals", "Per48"],
                        default="PerGame",
                    ),
                    ParameterSchema(
                        name="limit",
                        type="integer",
                        required=False,
                        description="Number of leaders to return",
                        default=10,
                    ),
                ],
                primary_keys=["PLAYER_ID", "SEASON", "STAT_CATEGORY"],
                output_columns=[
                    "RANK",
                    "PLAYER_ID",
                    "PLAYER_NAME",
                    "TEAM_ID",
                    "TEAM_ABBREVIATION",
                    "GP",
                    "MIN",
                    "STAT_VALUE",
                    "PTS",
                    "REB",
                    "AST",
                ],
                sample_params={
                    "stat_category": "PTS",
                    "season": "2023-24",
                    "per_mode": "PerGame",
                    "limit": 10,
                },
                # Phase 2: Capability metadata
                scope_capability=ScopeCapability(
                    supports_all_players=False,  # Already top N players
                    supports_multi_players=False,
                    required_scope=None,
                ),
                range_capability=RangeCapability(
                    supports_season_range=True,
                    supports_date_range=False,
                ),
                filterable_columns={
                    "PTS": FilterCapability(
                        column="PTS",
                        type="float",
                        pushable=False,
                        operators=[">", ">=", "<", "<=", "BETWEEN"],
                        examples=[30.0, 25.0, 20.0],
                        description="Points per game",
                    ),
                    "AST": FilterCapability(
                        column="AST",
                        type="float",
                        pushable=False,
                        operators=[">", ">=", "<", "<=", "BETWEEN"],
                        examples=[10.0, 8.0, 6.0],
                        description="Assists per game",
                    ),
                    "REB": FilterCapability(
                        column="REB",
                        type="float",
                        pushable=False,
                        operators=[">", ">=", "<", "<=", "BETWEEN"],
                        examples=[12.0, 10.0, 8.0],
                        description="Rebounds per game",
                    ),
                },
                rate_cost=1,  # Low cost - single API call
            )
        )

        # Phase 2H-C: League-wide game logs
        self._add_endpoint(
            EndpointMetadata(
                name="league_player_games",
                display_name="League Player Games",
                category=EndpointCategory.LEAGUE_DATA,
                description="Game-by-game statistics for ALL players in a season (league-wide)",
                parameters=[
                    ParameterSchema(
                        name="season",
                        type="string",
                        required=True,
                        description="Season in YYYY-YY format",
                        example="2023-24",
                    ),
                    ParameterSchema(
                        name="season_type",
                        type="string",
                        required=False,
                        description="Regular Season or Playoffs",
                        enum=["Regular Season", "Playoffs"],
                        default="Regular Season",
                    ),
                    ParameterSchema(
                        name="date_from",
                        type="string",
                        required=False,
                        description="Start date for filtering",
                        example="2024-01-01",
                    ),
                    ParameterSchema(
                        name="date_to",
                        type="string",
                        required=False,
                        description="End date for filtering",
                        example="2024-01-31",
                    ),
                    ParameterSchema(
                        name="outcome",
                        type="string",
                        required=False,
                        description="Filter by win/loss",
                        enum=["W", "L"],
                    ),
                    ParameterSchema(
                        name="location",
                        type="string",
                        required=False,
                        description="Filter by home/away games",
                        enum=["Home", "Road"],
                    ),
                ],
                primary_keys=["PLAYER_ID", "GAME_ID"],
                output_columns=[
                    "PLAYER_ID",
                    "PLAYER_NAME",
                    "GAME_ID",
                    "GAME_DATE",
                    "MATCHUP",
                    "WL",
                    "MIN",
                    "PTS",
                    "REB",
                    "AST",
                    "FG_PCT",
                    "FG3_PCT",
                    "FT_PCT",
                ],
                sample_params={
                    "season": "2023-24",
                    "date_from": "2024-01-01",
                    "date_to": "2024-01-05",
                },
                supports_date_range=True,
                supports_season_filter=True,
                typical_row_count=15000,
                chunk_strategy="date",
            )
        )

        self._add_endpoint(
            EndpointMetadata(
                name="league_team_games",
                display_name="League Team Games",
                category=EndpointCategory.LEAGUE_DATA,
                description="Game-by-game results for ALL teams in a season (league-wide)",
                parameters=[
                    ParameterSchema(
                        name="season",
                        type="string",
                        required=True,
                        description="Season in YYYY-YY format",
                        example="2023-24",
                    ),
                    ParameterSchema(
                        name="season_type",
                        type="string",
                        required=False,
                        description="Regular Season or Playoffs",
                        enum=["Regular Season", "Playoffs"],
                        default="Regular Season",
                    ),
                    ParameterSchema(
                        name="date_from",
                        type="string",
                        required=False,
                        description="Start date for filtering",
                        example="2024-01-01",
                    ),
                    ParameterSchema(
                        name="date_to",
                        type="string",
                        required=False,
                        description="End date for filtering",
                        example="2024-01-31",
                    ),
                    ParameterSchema(
                        name="outcome",
                        type="string",
                        required=False,
                        description="Filter by win/loss",
                        enum=["W", "L"],
                    ),
                ],
                primary_keys=["TEAM_ID", "GAME_ID"],
                output_columns=[
                    "TEAM_ID",
                    "TEAM_NAME",
                    "GAME_ID",
                    "GAME_DATE",
                    "MATCHUP",
                    "WL",
                    "PTS",
                    "PLUS_MINUS",
                ],
                sample_params={
                    "season": "2023-24",
                    "date_from": "2024-01-01",
                    "date_to": "2024-01-05",
                },
                supports_date_range=True,
                supports_season_filter=True,
                typical_row_count=2500,
                chunk_strategy="date",
            )
        )

        # Session 254E: League-wide player season stats (bulk season stats endpoint)
        self._add_endpoint(
            EndpointMetadata(
                name="league_dash_player_stats",
                display_name="League Dashboard Player Stats",
                category=EndpointCategory.LEAGUE_DATA,
                description="Season statistics for ALL players in a season (league-wide dashboard). Returns full stat columns (GP, PTS, REB, AST, FG_PCT, etc.) for every player.",
                parameters=[
                    ParameterSchema(
                        name="season",
                        type="string",
                        required=True,
                        description="Season in YYYY-YY format",
                        example="2023-24",
                    ),
                    ParameterSchema(
                        name="season_type",
                        type="string",
                        required=False,
                        description="Regular Season or Playoffs",
                        enum=["Regular Season", "Playoffs"],
                        default="Regular Season",
                    ),
                    ParameterSchema(
                        name="per_mode",
                        type="string",
                        required=False,
                        description="Stat aggregation mode",
                        enum=["PerGame", "Totals", "Per36", "Per48"],
                        default="PerGame",
                    ),
                ],
                primary_keys=["PLAYER_ID"],
                output_columns=[
                    "PLAYER_ID",
                    "PLAYER_NAME",
                    "TEAM_ID",
                    "TEAM_ABBREVIATION",
                    "GP",
                    "MIN",
                    "FGM",
                    "FGA",
                    "FG_PCT",
                    "FG3M",
                    "FG3A",
                    "FG3_PCT",
                    "FTM",
                    "FTA",
                    "FT_PCT",
                    "OREB",
                    "DREB",
                    "REB",
                    "AST",
                    "TOV",
                    "STL",
                    "BLK",
                    "PTS",
                    "PLUS_MINUS",
                ],
                sample_params={
                    "season": "2023-24",
                    "season_type": "Regular Season",
                    "per_mode": "PerGame",
                },
                supports_date_range=False,
                supports_season_filter=True,
                typical_row_count=500,  # ~476 players per season
                chunk_strategy="none",
            )
        )

        self._add_endpoint(
            EndpointMetadata(
                name="shot_chart",
                display_name="Shot Chart Data",
                category=EndpointCategory.ADVANCED_ANALYTICS,
                description="Shot location data with optional hexagonal binning. Use entity_type='league' for all players league-wide (fast bulk fetch).",
                parameters=[
                    ParameterSchema(
                        name="entity_name",
                        type="string",
                        required=False,  # Not required when entity_type='league'
                        description="Player or team name (not required when entity_type='league')",
                        example="Stephen Curry",
                    ),
                    ParameterSchema(
                        name="entity_type",
                        type="string",
                        required=False,
                        description="Entity type: 'player' for single player, 'team' for all players on a team, 'league' for all players league-wide (219K+ shots in ~2s)",
                        enum=["player", "team", "league"],
                        default="player",
                    ),
                    ParameterSchema(
                        name="season",
                        type="string",
                        required=False,
                        description="Season in YYYY-YY format",
                        example="2023-24",
                    ),
                    ParameterSchema(
                        name="granularity",
                        type="string",
                        required=False,
                        description="Output granularity",
                        enum=["raw", "hexbin", "both", "summary"],
                        default="both",
                    ),
                ],
                primary_keys=["SHOT_ID"],
                output_columns=[
                    "SHOT_ID",
                    "PLAYER_ID",
                    "TEAM_ID",
                    "LOC_X",
                    "LOC_Y",
                    "SHOT_MADE_FLAG",
                    "SHOT_DISTANCE",
                    "SHOT_TYPE",
                    "SHOT_ZONE_BASIC",
                    "SHOT_ZONE_AREA",
                ],
                sample_params={
                    "entity_name": "Stephen Curry",
                    "season": "2023-24",
                    "granularity": "hexbin",
                },
            )
        )

        # Additional Player Endpoints
        self._add_endpoint(
            EndpointMetadata(
                name="player_game_log",
                display_name="Player Game Log",
                category=EndpointCategory.PLAYER_STATS,
                description="Game-by-game statistics for a specific player",
                parameters=[
                    ParameterSchema(
                        name="player_name",
                        type="string",
                        required=True,
                        description="Player name",
                        example="LeBron James",
                    ),
                    ParameterSchema(
                        name="season",
                        type="string",
                        required=False,
                        description="Season in YYYY-YY format",
                        example="2023-24",
                    ),
                    ParameterSchema(
                        name="season_type",
                        type="string",
                        required=False,
                        description="Season type",
                        enum=["Regular Season", "Playoffs"],
                        default="Regular Season",
                    ),
                    ParameterSchema(
                        name="last_n_games",
                        type="integer",
                        required=False,
                        description="Limit to most recent N games",
                        example=10,
                    ),
                ],
                primary_keys=["PLAYER_ID", "GAME_ID"],
                output_columns=[
                    "PLAYER_ID",
                    "PLAYER_NAME",
                    "GAME_ID",
                    "GAME_DATE",
                    "MATCHUP",
                    "WL",
                    "MIN",
                    "PTS",
                    "REB",
                    "AST",
                    "FGM",
                    "FGA",
                    "FG_PCT",
                    "FG3M",
                    "FG3A",
                    "FG3_PCT",
                    "FTM",
                    "FTA",
                    "FT_PCT",
                    "STL",
                    "BLK",
                    "TOV",
                    "PF",
                    "PLUS_MINUS",
                ],
                sample_params={
                    "player_name": "LeBron James",
                    "season": "2023-24",
                    "last_n_games": 10,
                },
                # Phase 2: Capability metadata
                scope_capability=ScopeCapability(
                    supports_all_players=True,
                    supports_multi_players=True,
                    required_scope="player",
                ),
                range_capability=RangeCapability(
                    supports_season_range=True,
                    supports_date_range=True,  # Supports date filtering
                ),
                filterable_columns={
                    "GAME_DATE": FilterCapability(
                        column="GAME_DATE",
                        type="date",
                        pushable=True,  # Can be pushed via date parameters
                        operators=["==", ">", ">=", "<", "<=", "BETWEEN"],
                        examples=["2024-01-01", "2024-02-15"],
                        description="Game date",
                    ),
                    "WL": FilterCapability(
                        column="WL",
                        type="string",
                        pushable=True,  # May be pushable via NBA API
                        operators=["==", "!="],
                        enum_values=["W", "L"],
                        description="Win/Loss result",
                    ),
                    "PTS": FilterCapability(
                        column="PTS",
                        type="integer",
                        pushable=False,
                        operators=[">", ">=", "<", "<=", "BETWEEN"],
                        examples=[30, 25, 20],
                        description="Points scored",
                    ),
                    "FG3M": FilterCapability(
                        column="FG3M",
                        type="integer",
                        pushable=False,
                        operators=[">", ">=", "<", "<=", "BETWEEN"],
                        examples=[5, 4, 3],
                        description="Three-pointers made",
                    ),
                },
                rate_cost=3,  # Higher cost due to ALL_ACTIVE support
                # Phase 4H: Filter presets
                filter_presets=[
                    {
                        "name": "Recent Games (Last 30 Days)",
                        "description": "Games from the last 30 days",
                        "filters": {"GAME_DATE": [">=", "2024-10-12"]},  # Dynamic date in UI
                    },
                    {
                        "name": "Wins Only",
                        "description": "Games won by the player's team",
                        "filters": {"WL": ["==", "W"]},
                    },
                    {
                        "name": "High Scoring Games (30+ PTS)",
                        "description": "Games with 30+ points scored",
                        "filters": {"PTS": [">=", 30]},
                    },
                    {
                        "name": "Elite 3PT Games (5+ made)",
                        "description": "Games with 5+ three-pointers made",
                        "filters": {"FG3M": [">=", 5]},
                    },
                ],
            )
        )

        self._add_endpoint(
            EndpointMetadata(
                name="box_score",
                display_name="Box Score",
                category=EndpointCategory.GAME_DATA,
                description="Full box score with player stats and quarter-by-quarter breakdowns",
                parameters=[
                    ParameterSchema(
                        name="game_id",
                        type="string",
                        required=True,
                        description="10-digit game ID",
                        example="0022300500",
                    ),
                ],
                primary_keys=["GAME_ID", "PLAYER_ID"],
                output_columns=[
                    "GAME_ID",
                    "TEAM_ID",
                    "TEAM_ABBREVIATION",
                    "PLAYER_ID",
                    "PLAYER_NAME",
                    "START_POSITION",
                    "MIN",
                    "PTS",
                    "REB",
                    "AST",
                    "FGM",
                    "FGA",
                    "FG_PCT",
                    "FG3M",
                    "FG3A",
                    "FG3_PCT",
                    "FTM",
                    "FTA",
                    "FT_PCT",
                    "OREB",
                    "DREB",
                    "STL",
                    "BLK",
                    "TOV",
                    "PF",
                    "PLUS_MINUS",
                ],
                sample_params={"game_id": "0022300500"},
            )
        )

        self._add_endpoint(
            EndpointMetadata(
                name="clutch_stats",
                display_name="Clutch Statistics",
                category=EndpointCategory.ADVANCED_ANALYTICS,
                description="Clutch time statistics (final 5 minutes, score within 5 points)",
                parameters=[
                    ParameterSchema(
                        name="entity_name",
                        type="string",
                        required=True,
                        description="Player or team name",
                        example="LeBron James",
                    ),
                    ParameterSchema(
                        name="entity_type",
                        type="string",
                        required=False,
                        description="Entity type",
                        enum=["player", "team"],
                        default="player",
                    ),
                    ParameterSchema(
                        name="season",
                        type="string",
                        required=False,
                        description="Season in YYYY-YY format",
                        example="2023-24",
                    ),
                    ParameterSchema(
                        name="per_mode",
                        type="string",
                        required=False,
                        description="Per-game or totals",
                        enum=["PerGame", "Totals"],
                        default="PerGame",
                    ),
                ],
                primary_keys=["PLAYER_ID", "SEASON"],
                output_columns=[
                    "PLAYER_ID",
                    "PLAYER_NAME",
                    "TEAM_ID",
                    "GP",
                    "MIN",
                    "PTS",
                    "REB",
                    "AST",
                    "FGM",
                    "FGA",
                    "FG_PCT",
                    "FG3M",
                    "FG3A",
                    "FG3_PCT",
                    "FTM",
                    "FTA",
                    "FT_PCT",
                    "STL",
                    "BLK",
                    "TOV",
                    "W",
                    "L",
                    "WIN_PCT",
                ],
                sample_params={
                    "entity_name": "LeBron James",
                    "entity_type": "player",
                    "season": "2023-24",
                },
            )
        )

        self._add_endpoint(
            EndpointMetadata(
                name="player_head_to_head",
                display_name="Player Head-to-Head",
                category=EndpointCategory.PLAYER_STATS,
                description="Head-to-head matchup stats for two players",
                parameters=[
                    ParameterSchema(
                        name="player1_name",
                        type="string",
                        required=True,
                        description="First player name",
                        example="LeBron James",
                    ),
                    ParameterSchema(
                        name="player2_name",
                        type="string",
                        required=True,
                        description="Second player name",
                        example="Kevin Durant",
                    ),
                    ParameterSchema(
                        name="season",
                        type="string",
                        required=False,
                        description="Season in YYYY-YY format",
                        example="2023-24",
                    ),
                ],
                primary_keys=["PLAYER_ID", "GAME_ID"],
                output_columns=[
                    "PLAYER_ID",
                    "PLAYER_NAME",
                    "GAME_ID",
                    "GAME_DATE",
                    "MATCHUP",
                    "WL",
                    "MIN",
                    "PTS",
                    "REB",
                    "AST",
                    "FGM",
                    "FGA",
                    "FG_PCT",
                    "FG3M",
                    "FG3A",
                    "FG3_PCT",
                    "FTM",
                    "FTA",
                    "FT_PCT",
                    "STL",
                    "BLK",
                    "TOV",
                    "PF",
                    "PLUS_MINUS",
                ],
                sample_params={
                    "player1_name": "LeBron James",
                    "player2_name": "Kevin Durant",
                    "season": "2023-24",
                },
            )
        )

        self._add_endpoint(
            EndpointMetadata(
                name="player_performance_splits",
                display_name="Player Performance Splits",
                category=EndpointCategory.ADVANCED_ANALYTICS,
                description="Performance splits with home/away, win/loss, and trend analysis",
                parameters=[
                    ParameterSchema(
                        name="player_name",
                        type="string",
                        required=True,
                        description="Player name",
                        example="LeBron James",
                    ),
                    ParameterSchema(
                        name="season",
                        type="string",
                        required=False,
                        description="Season in YYYY-YY format",
                        example="2023-24",
                    ),
                    ParameterSchema(
                        name="last_n_games",
                        type="integer",
                        required=False,
                        description="Analyze last N games",
                        default=10,
                    ),
                ],
                primary_keys=["SPLIT_TYPE"],
                output_columns=[
                    "split_type",
                    "games",
                    "ppg",
                    "rpg",
                    "apg",
                    "spg",
                    "bpg",
                    "fg_pct",
                    "fg3_pct",
                    "ft_pct",
                    "min_pg",
                    "plus_minus",
                ],
                sample_params={
                    "player_name": "LeBron James",
                    "season": "2023-24",
                    "last_n_games": 10,
                },
            )
        )

        # Add join relationships
        self._add_relationships()

        # Add join examples
        self._add_join_examples()

    def _add_endpoint(self, endpoint: EndpointMetadata):
        """Add an endpoint to the catalog."""
        self._endpoints[endpoint.name] = endpoint

    def _add_relationships(self):
        """Define all join relationships between endpoints."""
        # Player stats to team stats
        self._relationships.append(
            JoinRelationship(
                from_endpoint="player_career_stats",
                to_endpoint="team_standings",
                join_keys={"TEAM_ID": "TEAM_ID", "SEASON_ID": "SEASON"},
                join_type="left",
                description="Enrich player stats with team standings",
                example_use_case="Get player performance in context of team success",
            )
        )

        self._relationships.append(
            JoinRelationship(
                from_endpoint="player_career_stats",
                to_endpoint="team_advanced_stats",
                join_keys={"TEAM_ID": "TEAM_ID", "SEASON_ID": "SEASON"},
                join_type="left",
                description="Enrich player stats with team efficiency metrics",
                example_use_case="Analyze player performance vs team pace and ratings",
            )
        )

        # Player basic to advanced stats
        self._relationships.append(
            JoinRelationship(
                from_endpoint="player_career_stats",
                to_endpoint="player_advanced_stats",
                join_keys={"PLAYER_ID": "PLAYER_ID", "SEASON_ID": "SEASON"},
                join_type="inner",
                description="Combine basic and advanced player metrics",
                example_use_case="Complete player profile with efficiency and volume stats",
            )
        )

        # League leaders to advanced stats
        self._relationships.append(
            JoinRelationship(
                from_endpoint="league_leaders",
                to_endpoint="player_advanced_stats",
                join_keys={"PLAYER_ID": "PLAYER_ID"},
                join_type="inner",
                description="Enrich league leaders with advanced metrics",
                example_use_case="Find most efficient high-volume scorers",
            )
        )

        # Game data to team info
        self._relationships.append(
            JoinRelationship(
                from_endpoint="live_scores",
                to_endpoint="team_standings",
                join_keys={"HOME_TEAM_ID": "TEAM_ID"},
                join_type="left",
                description="Add home team standings to game scores",
                example_use_case="Game context with team records",
            )
        )

        self._relationships.append(
            JoinRelationship(
                from_endpoint="team_game_log",
                to_endpoint="team_advanced_stats",
                join_keys={"TEAM_ID": "TEAM_ID", "SEASON": "SEASON"},
                join_type="left",
                description="Enrich game logs with team season averages",
                example_use_case="Compare game performance to season averages",
            )
        )

    def _add_join_examples(self):
        """Add complete join examples."""
        self._join_examples.append(
            JoinExample(
                name="Player Performance with Team Context",
                description="Get player stats enriched with team standings and efficiency metrics",
                steps=[
                    {
                        "action": "fetch",
                        "endpoint": "player_career_stats",
                        "params": {"player_name": "LeBron James", "season": "2023-24"},
                    },
                    {
                        "action": "fetch",
                        "endpoint": "team_standings",
                        "params": {"season": "2023-24"},
                    },
                    {
                        "action": "fetch",
                        "endpoint": "team_advanced_stats",
                        "params": {"team_name": "Lakers", "season": "2023-24"},
                    },
                    {
                        "action": "join",
                        "tables": [0, 1],
                        "on": {"TEAM_ID": "TEAM_ID"},
                        "how": "left",
                    },
                    {
                        "action": "join",
                        "tables": ["previous", 2],
                        "on": {"TEAM_ID": "TEAM_ID"},
                        "how": "left",
                    },
                ],
                expected_output="Player stats with team record, rank, and efficiency metrics",
            )
        )

        self._join_examples.append(
            JoinExample(
                name="League Leaders with Efficiency Metrics",
                description="Top scorers enriched with advanced efficiency stats",
                steps=[
                    {
                        "action": "fetch",
                        "endpoint": "league_leaders",
                        "params": {
                            "stat_category": "PTS",
                            "season": "2023-24",
                            "limit": 20,
                        },
                    },
                    {
                        "action": "fetch",
                        "endpoint": "player_advanced_stats",
                        "params": {"season": "2023-24"},
                    },
                    {
                        "action": "join",
                        "tables": [0, 1],
                        "on": {"PLAYER_ID": "PLAYER_ID"},
                        "how": "inner",
                    },
                ],
                expected_output="Top scorers with TS%, Usage%, PIE, and ratings",
            )
        )

        self._join_examples.append(
            JoinExample(
                name="Game Results with Team Season Context",
                description="Team game log enriched with season standings and advanced stats",
                steps=[
                    {
                        "action": "fetch",
                        "endpoint": "team_game_log",
                        "params": {
                            "team": "Lakers",
                            "season": "2023-24",
                            "date_from": "2024-01-01",
                            "date_to": "2024-01-31",
                        },
                    },
                    {
                        "action": "fetch",
                        "endpoint": "team_standings",
                        "params": {"season": "2023-24"},
                    },
                    {
                        "action": "fetch",
                        "endpoint": "team_advanced_stats",
                        "params": {"team_name": "Lakers", "season": "2023-24"},
                    },
                    {
                        "action": "join",
                        "tables": [0, 1],
                        "on": {"TEAM_ID": "TEAM_ID"},
                        "how": "left",
                    },
                    {
                        "action": "join",
                        "tables": ["previous", 2],
                        "on": {"TEAM_ID": "TEAM_ID"},
                        "how": "left",
                    },
                ],
                expected_output="Game-by-game results with team record and season efficiency metrics",
            )
        )

    def get_endpoint(self, name: str) -> Optional[EndpointMetadata]:
        """Get metadata for a specific endpoint."""
        return self._endpoints.get(name)

    def list_endpoints(
        self, category: Optional[EndpointCategory] = None
    ) -> List[EndpointMetadata]:
        """
        List all available endpoints, optionally filtered by category.

        Args:
            category: Optional category filter

        Returns:
            List of endpoint metadata objects
        """
        endpoints = list(self._endpoints.values())
        if category:
            endpoints = [e for e in endpoints if e.category == category]
        return endpoints

    def get_relationships(
        self, endpoint: Optional[str] = None
    ) -> List[JoinRelationship]:
        """
        Get join relationships, optionally filtered by endpoint.

        Args:
            endpoint: Optional endpoint name to filter by

        Returns:
            List of join relationships
        """
        if endpoint:
            return [
                r
                for r in self._relationships
                if r.from_endpoint == endpoint or r.to_endpoint == endpoint
            ]
        return self._relationships

    def get_join_examples(self) -> List[JoinExample]:
        """Get all join examples."""
        return self._join_examples

    def to_dict(self) -> Dict[str, Any]:
        """Convert entire catalog to dictionary format."""
        return {
            "endpoints": {
                name: endpoint.model_dump()
                for name, endpoint in self._endpoints.items()
            },
            "relationships": [r.model_dump() for r in self._relationships],
            "join_examples": [e.model_dump() for e in self._join_examples],
            "summary": {
                "total_endpoints": len(self._endpoints),
                "categories": list(set(e.category for e in self._endpoints.values())),
                "total_relationships": len(self._relationships),
                "total_examples": len(self._join_examples),
            },
        }

    # Phase 2: Catalog Helper Methods for Query Capabilities
    def get_endpoints_supporting_all_players(self) -> List[EndpointMetadata]:
        """Get endpoints that support ALL_ACTIVE/ALL players queries."""
        return [
            ep
            for ep in self._endpoints.values()
            if ep.scope_capability and ep.scope_capability.supports_all_players
        ]

    def get_endpoints_supporting_season_ranges(self) -> List[EndpointMetadata]:
        """Get endpoints that support season range expansion."""
        return [
            ep
            for ep in self._endpoints.values()
            if ep.range_capability and ep.range_capability.supports_season_range
        ]

    def get_endpoints_supporting_date_ranges(self) -> List[EndpointMetadata]:
        """Get endpoints that support date range filtering."""
        return [
            ep
            for ep in self._endpoints.values()
            if ep.range_capability and ep.range_capability.supports_date_range
        ]

    def get_filterable_columns(self, endpoint: str) -> Dict[str, FilterCapability]:
        """Get filterable columns for an endpoint."""
        ep = self.get_endpoint(endpoint)
        return ep.filterable_columns if ep else {}

    def get_pushable_filters(self, endpoint: str) -> List[str]:
        """Get list of columns that support API-level filter pushdown."""
        columns = self.get_filterable_columns(endpoint)
        return [col for col, cap in columns.items() if cap.pushable]

    def estimate_query_cost(
        self, endpoint: str, scope: Optional[Dict] = None
    ) -> int:
        """
        Estimate relative cost of a query.

        Base cost from endpoint.rate_cost multiplied by scope expansion factor:
        - ALL_ACTIVE: 450x
        - ALL: 4000x
        - Multi-entity: Nx

        Args:
            endpoint: Endpoint name
            scope: Scope dictionary (e.g., {"player": "ALL_ACTIVE"})

        Returns:
            Estimated relative cost (1 = simple query, 1350 = ALL_ACTIVE moderate endpoint)
        """
        ep = self.get_endpoint(endpoint)
        if not ep:
            return 1

        base_cost = ep.rate_cost

        # Check scope expansion
        if scope:
            player_scope = scope.get("player")
            team_scope = scope.get("team")

            if player_scope == "ALL_ACTIVE":
                return base_cost * 450
            elif player_scope == "ALL":
                return base_cost * 4000
            elif isinstance(player_scope, list):
                return base_cost * len(player_scope)

            if team_scope == "ALL":
                return base_cost * 30
            elif isinstance(team_scope, list):
                return base_cost * len(team_scope)

        return base_cost


# Global catalog instance
_catalog = None


def get_catalog() -> DataCatalog:
    """
    Get the global data catalog instance (singleton pattern).

    Returns:
        DataCatalog instance
    """
    global _catalog
    if _catalog is None:
        _catalog = DataCatalog()
    return _catalog
