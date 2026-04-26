"""
FilterSpec Adapter for NBA API MCP.

Provides compatibility layer between basketball_mcp_core's unified FilterSpec
and nba_api_mcp's dict-based filter format.

This adapter enables:
1. Using FilterSpec from basketball_mcp_core when available
2. Converting FilterSpec to nba_api_mcp's native dict format
3. Maintaining backward compatibility with existing code

Usage:
    from nba_api_mcp.data.filter_adapter import (
        FilterSpecAdapter,
        convert_filterspec_to_dict,
        create_filter_from_params,
    )

    # Convert FilterSpec to dict format
    filter_dict = convert_filterspec_to_dict(filter_spec)

    # Create filter from raw params
    filter_dict = create_filter_from_params(
        season="2024-25",
        min_minutes=10,
        season_type="Playoffs"
    )
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)

# Try to import FilterSpec from basketball_mcp_core
try:
    from basketball_mcp_core.filters.spec import FilterSpec, DateSpan

    FILTERSPEC_AVAILABLE = True
    logger.info("basketball_mcp_core FilterSpec available")
except ImportError:
    FILTERSPEC_AVAILABLE = False
    FilterSpec = None
    DateSpan = None
    logger.debug("basketball_mcp_core not installed - using native dict filters")


# Mapping from FilterSpec fields to nba_api_mcp filter format
FILTERSPEC_TO_NBA_MAPPING = {
    # Season & timing
    "season": ("SEASON", "=="),
    "season_type": ("SEASON_TYPE", "=="),

    # Team filters
    "team": ("TEAM_NAME", "IN"),
    "team_ids": ("TEAM_ID", "IN"),
    "opponent": ("OPPONENT", "IN"),
    "opponent_ids": ("OPPONENT_ID", "IN"),

    # Player filters
    "player": ("PLAYER_NAME", "IN"),
    "player_ids": ("PLAYER_ID", "IN"),

    # Game filters
    "game_ids": ("GAME_ID", "IN"),
    "home_away": ("LOCATION", "=="),

    # Statistical filters
    "min_minutes": ("MIN", ">="),
    "last_n_games": ("LAST_N_GAMES", "=="),

    # NBA-specific (from basketball_mcp_core)
    "clutch_time": ("CLUTCH_TIME", "=="),
    "ahead_behind": ("AHEAD_BEHIND", "=="),
    "point_diff": ("POINT_DIFF", ">="),
    "stat_category": ("STAT_CATEGORY", "=="),

    # Per mode
    "per_mode": ("PER_MODE", "=="),
}

# Fields that map to date range filters
DATE_RANGE_FIELDS = {"date"}


class FilterSpecAdapter:
    """
    Adapter to convert between FilterSpec and nba_api_mcp dict format.

    Example:
        >>> adapter = FilterSpecAdapter()
        >>>
        >>> # From FilterSpec (if available)
        >>> if FILTERSPEC_AVAILABLE:
        ...     spec = FilterSpec(season="2024-25", min_minutes=10)
        ...     filter_dict = adapter.to_dict(spec)
        >>>
        >>> # From raw params
        >>> filter_dict = adapter.from_params(season="2024-25", min_minutes=10)
    """

    def __init__(self):
        """Initialize adapter with field mappings."""
        self.field_mapping = FILTERSPEC_TO_NBA_MAPPING.copy()

    def to_dict(
        self,
        spec: Any,  # FilterSpec when available
    ) -> Dict[str, List[Any]]:
        """
        Convert FilterSpec to nba_api_mcp dict format.

        Args:
            spec: FilterSpec instance from basketball_mcp_core

        Returns:
            Dict in format: {"COLUMN": ["operator", value]}

        Example:
            >>> spec = FilterSpec(season="2024-25", min_minutes=10)
            >>> adapter.to_dict(spec)
            {"SEASON": ["==", "2024-25"], "MIN": [">=", 10]}
        """
        if not FILTERSPEC_AVAILABLE or spec is None:
            return {}

        result: Dict[str, List[Any]] = {}

        # Convert each FilterSpec field
        for field_name, (column, operator) in self.field_mapping.items():
            value = getattr(spec, field_name, None)

            if value is not None:
                # Handle list values (IN operator)
                if isinstance(value, list) and operator == "IN":
                    if value:  # Only add non-empty lists
                        result[column] = ["IN", value]
                else:
                    result[column] = [operator, value]

        # Handle date range (special case)
        if spec.date is not None:
            if spec.date.start:
                result["GAME_DATE_FROM"] = [">=", spec.date.start.isoformat()]
            if spec.date.end:
                result["GAME_DATE_TO"] = ["<=", spec.date.end.isoformat()]

        # Handle quarter filter
        if spec.quarter:
            result["PERIOD"] = ["IN", spec.quarter]

        # Handle game minute filters
        if spec.min_game_minute is not None:
            result["GAME_MINUTE"] = [">=", spec.min_game_minute]
        if spec.max_game_minute is not None:
            result["GAME_MINUTE_MAX"] = ["<=", spec.max_game_minute]

        return result

    def from_params(self, **kwargs) -> Dict[str, List[Any]]:
        """
        Create filter dict from keyword arguments.

        This provides a convenient way to create filters without
        requiring FilterSpec to be available.

        Args:
            **kwargs: Filter parameters (same names as FilterSpec fields)

        Returns:
            Dict in format: {"COLUMN": ["operator", value]}

        Example:
            >>> adapter.from_params(season="2024-25", min_minutes=10)
            {"SEASON": ["==", "2024-25"], "MIN": [">=", 10]}
        """
        result: Dict[str, List[Any]] = {}

        for field_name, value in kwargs.items():
            if value is None:
                continue

            # Check if field has a mapping
            if field_name in self.field_mapping:
                column, operator = self.field_mapping[field_name]

                # Handle list values
                if isinstance(value, list) and operator == "IN":
                    if value:
                        result[column] = ["IN", value]
                else:
                    result[column] = [operator, value]

            # Handle date range
            elif field_name == "date_from":
                result["GAME_DATE_FROM"] = [">=", value]
            elif field_name == "date_to":
                result["GAME_DATE_TO"] = ["<=", value]

            # Handle other filters as equality
            else:
                # Try to map column name directly (uppercase)
                column = field_name.upper()
                result[column] = ["==", value]

        return result

    def to_api_params(
        self,
        spec: Any,  # FilterSpec when available
    ) -> Dict[str, Any]:
        """
        Convert FilterSpec to NBA API parameters.

        Unlike to_dict(), this returns parameters suitable for direct
        use with NBA API endpoints (no operator wrapping).

        Args:
            spec: FilterSpec instance

        Returns:
            Dict of API parameters

        Example:
            >>> spec = FilterSpec(season="2024-25", season_type="Playoffs")
            >>> adapter.to_api_params(spec)
            {"season": "2024-25", "season_type_nullable": "Playoffs"}
        """
        if not FILTERSPEC_AVAILABLE or spec is None:
            return {}

        result: Dict[str, Any] = {}

        # Direct mappings to NBA API parameters
        if spec.season:
            result["season"] = spec.season
        if spec.season_type:
            result["season_type_nullable"] = spec.season_type
        if spec.per_mode:
            result["per_mode_detailed"] = spec.per_mode

        # Team/player filters
        if spec.team_ids:
            result["team_id_nullable"] = spec.team_ids[0] if len(spec.team_ids) == 1 else None
        if spec.player_ids:
            result["player_id_nullable"] = spec.player_ids[0] if len(spec.player_ids) == 1 else None

        # Date range
        if spec.date:
            if spec.date.start:
                result["date_from_nullable"] = spec.date.start.strftime("%m/%d/%Y")
            if spec.date.end:
                result["date_to_nullable"] = spec.date.end.strftime("%m/%d/%Y")

        # Last N games
        if spec.last_n_games:
            result["last_n_games"] = spec.last_n_games

        # NBA-specific fields (from basketball_mcp_core)
        if hasattr(spec, "clutch_time") and spec.clutch_time:
            result["clutch_time_nullable"] = spec.clutch_time
        if hasattr(spec, "ahead_behind") and spec.ahead_behind:
            result["ahead_behind_nullable"] = spec.ahead_behind
        if hasattr(spec, "point_diff") and spec.point_diff is not None:
            result["point_diff_nullable"] = spec.point_diff

        return result


# Module-level convenience functions
_adapter = None


def get_adapter() -> FilterSpecAdapter:
    """Get singleton adapter instance."""
    global _adapter
    if _adapter is None:
        _adapter = FilterSpecAdapter()
    return _adapter


def convert_filterspec_to_dict(spec: Any) -> Dict[str, List[Any]]:
    """
    Convert FilterSpec to nba_api_mcp dict format.

    Args:
        spec: FilterSpec instance from basketball_mcp_core

    Returns:
        Dict in format: {"COLUMN": ["operator", value]}
    """
    return get_adapter().to_dict(spec)


def convert_filterspec_to_api_params(spec: Any) -> Dict[str, Any]:
    """
    Convert FilterSpec to NBA API parameters.

    Args:
        spec: FilterSpec instance

    Returns:
        Dict of API parameters
    """
    return get_adapter().to_api_params(spec)


def create_filter_from_params(**kwargs) -> Dict[str, List[Any]]:
    """
    Create filter dict from keyword arguments.

    Args:
        **kwargs: Filter parameters

    Returns:
        Dict in format: {"COLUMN": ["operator", value]}
    """
    return get_adapter().from_params(**kwargs)


def is_filterspec_available() -> bool:
    """Check if FilterSpec from basketball_mcp_core is available."""
    return FILTERSPEC_AVAILABLE
