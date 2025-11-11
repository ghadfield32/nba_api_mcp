"""
Enhanced catalog metadata for NBA MCP endpoints.

Provides detailed field information including:
- Field types (int, float, string, date, bool)
- Nullable flags
- Pushdown capability (can filter be pushed to API)
- Primary keys and sort columns
- Sample values and descriptions

This metadata enables:
- Better query planning
- Automatic type coercion
- Filter pushdown optimization
- Schema validation
- API documentation generation

Usage:
    from nba_api_mcp.data.catalog_meta import get_endpoint_meta, get_field_info

    # Get full metadata for endpoint
    meta = get_endpoint_meta("player_game_logs")

    # Get specific field info
    field = get_field_info("player_game_logs", "PTS")
    print(f"Type: {field['type']}, Pushdown: {field['pushdown']}")
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class FieldType(str, Enum):
    """Field data types."""

    INTEGER = "int"
    FLOAT = "float"
    STRING = "string"
    DATE = "date"
    DATETIME = "datetime"
    BOOLEAN = "bool"
    ARRAY = "array"
    OBJECT = "object"


class FieldMetadata(BaseModel):
    """
    Metadata for a single field in an endpoint.

    Provides comprehensive information about field characteristics
    for type coercion, validation, and optimization.
    """

    name: str = Field(description="Field name")
    type: FieldType = Field(description="Data type")
    nullable: bool = Field(default=False, description="Can be NULL")
    pushdown: bool = Field(
        default=False, description="Can filter be pushed to NBA API"
    )
    description: Optional[str] = Field(default=None, description="Field description")
    example: Optional[Any] = Field(default=None, description="Example value")
    min_value: Optional[float] = Field(default=None, description="Minimum value")
    max_value: Optional[float] = Field(default=None, description="Maximum value")
    enum_values: Optional[List[str]] = Field(
        default=None, description="Valid enum values"
    )


class EndpointMetadataEnhanced(BaseModel):
    """
    Enhanced metadata for an endpoint.

    Extends base EndpointMetadata with detailed field information.
    """

    endpoint: str = Field(description="Endpoint name")
    fields: Dict[str, FieldMetadata] = Field(
        description="Field metadata by field name"
    )
    pushdown_params: List[str] = Field(
        default_factory=list, description="Parameters that support pushdown filtering"
    )
    primary_key: List[str] = Field(
        default_factory=list, description="Primary key fields"
    )
    sort_columns: List[str] = Field(
        default_factory=list, description="Recommended sort columns"
    )
    foreign_keys: Dict[str, str] = Field(
        default_factory=dict, description="Foreign key relationships (field -> endpoint)"
    )


# ============================================================================
# CATALOG METADATA DEFINITIONS
# ============================================================================

CATALOG_META: Dict[str, EndpointMetadataEnhanced] = {
    # ========================================================================
    # Player Endpoints
    # ========================================================================
    "player_game_logs": EndpointMetadataEnhanced(
        endpoint="player_game_logs",
        fields={
            "SEASON_ID": FieldMetadata(
                name="SEASON_ID",
                type=FieldType.STRING,
                pushdown=True,
                description="Season identifier (e.g., '2023-24')",
                example="2023-24",
            ),
            "PLAYER_ID": FieldMetadata(
                name="PLAYER_ID",
                type=FieldType.INTEGER,
                pushdown=True,
                description="Unique player identifier",
                example=2544,
            ),
            "PLAYER_NAME": FieldMetadata(
                name="PLAYER_NAME",
                type=FieldType.STRING,
                description="Player full name",
                example="LeBron James",
            ),
            "GAME_ID": FieldMetadata(
                name="GAME_ID",
                type=FieldType.STRING,
                description="Unique game identifier",
                example="0022300123",
            ),
            "GAME_DATE": FieldMetadata(
                name="GAME_DATE",
                type=FieldType.DATE,
                pushdown=True,
                description="Game date (YYYY-MM-DD)",
                example="2024-01-15",
            ),
            "MATCHUP": FieldMetadata(
                name="MATCHUP",
                type=FieldType.STRING,
                description="Game matchup (e.g., 'LAL vs. GSW')",
                example="LAL vs. GSW",
            ),
            "WL": FieldMetadata(
                name="WL",
                type=FieldType.STRING,
                description="Win/Loss indicator",
                enum_values=["W", "L"],
            ),
            "MIN": FieldMetadata(
                name="MIN",
                type=FieldType.INTEGER,
                nullable=True,
                description="Minutes played",
                min_value=0,
                max_value=60,
            ),
            "PTS": FieldMetadata(
                name="PTS",
                type=FieldType.INTEGER,
                description="Points scored",
                min_value=0,
            ),
            "FGM": FieldMetadata(
                name="FGM",
                type=FieldType.INTEGER,
                description="Field goals made",
                min_value=0,
            ),
            "FGA": FieldMetadata(
                name="FGA",
                type=FieldType.INTEGER,
                description="Field goals attempted",
                min_value=0,
            ),
            "FG_PCT": FieldMetadata(
                name="FG_PCT",
                type=FieldType.FLOAT,
                nullable=True,
                description="Field goal percentage",
                min_value=0.0,
                max_value=1.0,
            ),
            "FG3M": FieldMetadata(
                name="FG3M",
                type=FieldType.INTEGER,
                description="Three-pointers made",
                min_value=0,
            ),
            "FG3A": FieldMetadata(
                name="FG3A",
                type=FieldType.INTEGER,
                description="Three-pointers attempted",
                min_value=0,
            ),
            "FG3_PCT": FieldMetadata(
                name="FG3_PCT",
                type=FieldType.FLOAT,
                nullable=True,
                description="Three-point percentage",
                min_value=0.0,
                max_value=1.0,
            ),
            "FTM": FieldMetadata(
                name="FTM",
                type=FieldType.INTEGER,
                description="Free throws made",
                min_value=0,
            ),
            "FTA": FieldMetadata(
                name="FTA",
                type=FieldType.INTEGER,
                description="Free throws attempted",
                min_value=0,
            ),
            "FT_PCT": FieldMetadata(
                name="FT_PCT",
                type=FieldType.FLOAT,
                nullable=True,
                description="Free throw percentage",
                min_value=0.0,
                max_value=1.0,
            ),
            "OREB": FieldMetadata(
                name="OREB",
                type=FieldType.INTEGER,
                description="Offensive rebounds",
                min_value=0,
            ),
            "DREB": FieldMetadata(
                name="DREB",
                type=FieldType.INTEGER,
                description="Defensive rebounds",
                min_value=0,
            ),
            "REB": FieldMetadata(
                name="REB",
                type=FieldType.INTEGER,
                description="Total rebounds",
                min_value=0,
            ),
            "AST": FieldMetadata(
                name="AST",
                type=FieldType.INTEGER,
                description="Assists",
                min_value=0,
            ),
            "STL": FieldMetadata(
                name="STL",
                type=FieldType.INTEGER,
                description="Steals",
                min_value=0,
            ),
            "BLK": FieldMetadata(
                name="BLK",
                type=FieldType.INTEGER,
                description="Blocks",
                min_value=0,
            ),
            "TOV": FieldMetadata(
                name="TOV",
                type=FieldType.INTEGER,
                description="Turnovers",
                min_value=0,
            ),
            "PF": FieldMetadata(
                name="PF",
                type=FieldType.INTEGER,
                description="Personal fouls",
                min_value=0,
            ),
            "PLUS_MINUS": FieldMetadata(
                name="PLUS_MINUS",
                type=FieldType.INTEGER,
                nullable=True,
                description="Plus/minus rating",
            ),
        },
        pushdown_params=["date_from", "date_to", "season", "player_id"],
        primary_key=["PLAYER_ID", "GAME_ID"],
        sort_columns=["GAME_DATE", "PTS"],
        foreign_keys={"PLAYER_ID": "player_info", "GAME_ID": "game_info"},
    ),
    # ========================================================================
    # Team Endpoints
    # ========================================================================
    "team_standings": EndpointMetadataEnhanced(
        endpoint="team_standings",
        fields={
            "TEAM_ID": FieldMetadata(
                name="TEAM_ID",
                type=FieldType.INTEGER,
                description="Unique team identifier",
                example=1610612747,
            ),
            "TEAM": FieldMetadata(
                name="TEAM",
                type=FieldType.STRING,
                description="Team name",
                example="Los Angeles Lakers",
            ),
            "TEAM_CITY": FieldMetadata(
                name="TEAM_CITY",
                type=FieldType.STRING,
                description="Team city",
                example="Los Angeles",
            ),
            "CONFERENCE": FieldMetadata(
                name="CONFERENCE",
                type=FieldType.STRING,
                description="Conference (East/West)",
                enum_values=["East", "West"],
            ),
            "W": FieldMetadata(
                name="W",
                type=FieldType.INTEGER,
                description="Wins",
                min_value=0,
                max_value=82,
            ),
            "L": FieldMetadata(
                name="L",
                type=FieldType.INTEGER,
                description="Losses",
                min_value=0,
                max_value=82,
            ),
            "W_PCT": FieldMetadata(
                name="W_PCT",
                type=FieldType.FLOAT,
                description="Win percentage",
                min_value=0.0,
                max_value=1.0,
            ),
            "GB": FieldMetadata(
                name="GB",
                type=FieldType.FLOAT,
                nullable=True,
                description="Games behind leader",
                min_value=0.0,
            ),
            "HOME_RECORD": FieldMetadata(
                name="HOME_RECORD",
                type=FieldType.STRING,
                description="Home record (W-L)",
                example="20-10",
            ),
            "ROAD_RECORD": FieldMetadata(
                name="ROAD_RECORD",
                type=FieldType.STRING,
                description="Road record (W-L)",
                example="15-15",
            ),
        },
        pushdown_params=["season", "season_type"],
        primary_key=["TEAM_ID"],
        sort_columns=["W_PCT", "W"],
        foreign_keys={"TEAM_ID": "team_info"},
    ),
    # ========================================================================
    # League Endpoints
    # ========================================================================
    "league_leaders": EndpointMetadataEnhanced(
        endpoint="league_leaders",
        fields={
            "PLAYER_ID": FieldMetadata(
                name="PLAYER_ID",
                type=FieldType.INTEGER,
                description="Unique player identifier",
                example=2544,
            ),
            "RANK": FieldMetadata(
                name="RANK",
                type=FieldType.INTEGER,
                description="Rank in category",
                min_value=1,
            ),
            "PLAYER": FieldMetadata(
                name="PLAYER",
                type=FieldType.STRING,
                description="Player name",
                example="LeBron James",
            ),
            "TEAM": FieldMetadata(
                name="TEAM",
                type=FieldType.STRING,
                description="Team abbreviation",
                example="LAL",
            ),
            "GP": FieldMetadata(
                name="GP",
                type=FieldType.INTEGER,
                description="Games played",
                min_value=0,
                max_value=82,
            ),
            "MIN": FieldMetadata(
                name="MIN",
                type=FieldType.FLOAT,
                description="Minutes per game",
                min_value=0.0,
                max_value=48.0,
            ),
            # Stats vary by category - most common ones
            "PTS": FieldMetadata(
                name="PTS",
                type=FieldType.FLOAT,
                description="Points per game",
                min_value=0.0,
            ),
            "REB": FieldMetadata(
                name="REB",
                type=FieldType.FLOAT,
                nullable=True,
                description="Rebounds per game",
                min_value=0.0,
            ),
            "AST": FieldMetadata(
                name="AST",
                type=FieldType.FLOAT,
                nullable=True,
                description="Assists per game",
                min_value=0.0,
            ),
        },
        pushdown_params=["season", "stat_category", "per_mode", "season_type"],
        primary_key=["PLAYER_ID"],
        sort_columns=["RANK", "PTS"],
        foreign_keys={"PLAYER_ID": "player_info"},
    ),
}


# ============================================================================
# PUBLIC API
# ============================================================================


def get_endpoint_meta(endpoint: str) -> Optional[EndpointMetadataEnhanced]:
    """
    Get enhanced metadata for endpoint.

    Args:
        endpoint: Endpoint name

    Returns:
        EndpointMetadataEnhanced or None if not found

    Example:
        meta = get_endpoint_meta("player_game_logs")
        print(f"Primary key: {meta.primary_key}")
        print(f"Pushdown params: {meta.pushdown_params}")
    """
    return CATALOG_META.get(endpoint)


def get_field_info(endpoint: str, field: str) -> Optional[Dict[str, Any]]:
    """
    Get metadata for specific field.

    Args:
        endpoint: Endpoint name
        field: Field name

    Returns:
        Field metadata dict or None if not found

    Example:
        field_meta = get_field_info("player_game_logs", "PTS")
        print(f"Type: {field_meta['type']}")
        print(f"Can pushdown: {field_meta['pushdown']}")
    """
    meta = CATALOG_META.get(endpoint)
    if not meta:
        return None

    field_meta = meta.fields.get(field)
    return field_meta.model_dump() if field_meta else None


def get_pushdown_fields(endpoint: str) -> List[str]:
    """
    Get list of fields that support pushdown filtering.

    Args:
        endpoint: Endpoint name

    Returns:
        List of field names that support pushdown

    Example:
        pushdown_fields = get_pushdown_fields("player_game_logs")
        # Returns: ["SEASON_ID", "PLAYER_ID", "GAME_DATE"]
    """
    meta = CATALOG_META.get(endpoint)
    if not meta:
        return []

    return [
        field_name
        for field_name, field_meta in meta.fields.items()
        if field_meta.pushdown
    ]


def get_field_types(endpoint: str) -> Dict[str, str]:
    """
    Get field name to type mapping.

    Args:
        endpoint: Endpoint name

    Returns:
        Dict mapping field names to type strings

    Example:
        types = get_field_types("player_game_logs")
        # Returns: {"PTS": "int", "FG_PCT": "float", ...}
    """
    meta = CATALOG_META.get(endpoint)
    if not meta:
        return {}

    return {field_name: field_meta.type.value for field_name, field_meta in meta.fields.items()}


def list_endpoints() -> List[str]:
    """
    Get list of all endpoints with enhanced metadata.

    Returns:
        List of endpoint names

    Example:
        endpoints = list_endpoints()
        # Returns: ["player_game_logs", "team_standings", "league_leaders"]
    """
    return list(CATALOG_META.keys())


# Export public API
__all__ = [
    "FieldType",
    "FieldMetadata",
    "EndpointMetadataEnhanced",
    "get_endpoint_meta",
    "get_field_info",
    "get_pushdown_fields",
    "get_field_types",
    "list_endpoints",
    "CATALOG_META",
]
