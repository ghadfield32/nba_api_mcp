"""
Parameter aliases and normalization for NBA API MCP.

Provides mapping from friendly/intuitive parameter names to NBA API parameter names,
and normalization of parameter values.

Key Features:
- Friendly names (Regular → Regular Season)
- Enum validation (only valid values accepted)
- Bi-directional mapping (forward and reverse)
- Type-safe (enums prevent typos)

Design Principles:
- User-friendly: accept "Regular" instead of "Regular Season"
- API-compatible: map to exact NBA API values
- Extensible: easy to add new aliases
"""

from typing import Any, Dict, Optional
from enum import Enum


class SeasonType(str, Enum):
    """Season type enum with aliases"""

    REGULAR = "Regular Season"
    PLAYOFFS = "Playoffs"
    PLAY_IN = "PlayIn"
    PRESEASON = "Pre Season"
    ALL_STAR = "All Star"


class PerMode(str, Enum):
    """Per mode enum with aliases"""

    PER_GAME = "PerGame"
    TOTALS = "Totals"
    PER_36 = "Per36Minutes"
    PER_100 = "Per100Possessions"
    PER_100_PLAYS = "Per100Plays"
    PER_48 = "Per48Minutes"
    PER_40 = "Per40Minutes"
    MIN_PER = "MinutesPer"


class MeasureType(str, Enum):
    """Measure type enum for advanced stats"""

    BASE = "Base"
    ADVANCED = "Advanced"
    MISC = "Misc"
    FOUR_FACTORS = "Four Factors"
    SCORING = "Scoring"
    OPPONENT = "Opponent"
    USAGE = "Usage"
    DEFENSE = "Defense"


class PaceAdjust(str, Enum):
    """Pace adjustment enum"""

    YES = "Y"
    NO = "N"


class PlusMinus(str, Enum):
    """Plus/minus enum"""

    YES = "Y"
    NO = "N"


class Rank(str, Enum):
    """Rank enum"""

    YES = "Y"
    NO = "N"


class Location(str, Enum):
    """Game location enum"""

    HOME = "Home"
    ROAD = "Road"
    ALL = ""


class Outcome(str, Enum):
    """Game outcome enum"""

    WIN = "W"
    LOSS = "L"
    ALL = ""


class SeasonSegment(str, Enum):
    """Season segment enum"""

    FULL_SEASON = ""
    PRE_ALL_STAR = "Pre All-Star"
    POST_ALL_STAR = "Post All-Star"


# Parameter aliases mapping
# Maps friendly names to NBA API parameter values
PARAM_ALIASES: Dict[str, Dict[str, str]] = {
    "season_type": {
        "Regular": "Regular Season",
        "Playoffs": "Playoffs",
        "PlayIn": "PlayIn",
        "Preseason": "Pre Season",
        "AllStar": "All Star",
        # Also accept direct values
        "Regular Season": "Regular Season",
        "Pre Season": "Pre Season",
        "All Star": "All Star",
    },
    "per_mode": {
        "PerGame": "PerGame",
        "Totals": "Totals",
        "Per36": "Per36Minutes",
        "Per100": "Per100Possessions",
        "Per100Plays": "Per100Plays",
        "Per48": "Per48Minutes",
        "Per40": "Per40Minutes",
        "MinutesPer": "MinutesPer",
        # Also accept full names
        "Per36Minutes": "Per36Minutes",
        "Per100Possessions": "Per100Possessions",
    },
    "measure_type": {
        "Base": "Base",
        "Advanced": "Advanced",
        "Misc": "Misc",
        "FourFactors": "Four Factors",
        "Scoring": "Scoring",
        "Opponent": "Opponent",
        "Usage": "Usage",
        "Defense": "Defense",
        # Also accept full names
        "Four Factors": "Four Factors",
    },
    "pace_adjust": {
        "Y": "Y",
        "N": "N",
        "Yes": "Y",
        "No": "N",
        "yes": "Y",
        "no": "N",
        "true": "Y",
        "false": "N",
        True: "Y",
        False: "N",
    },
    "plus_minus": {
        "Y": "Y",
        "N": "N",
        "Yes": "Y",
        "No": "N",
        "yes": "Y",
        "no": "N",
        "true": "Y",
        "false": "N",
        True: "Y",
        False: "N",
    },
    "rank": {
        "Y": "Y",
        "N": "N",
        "Yes": "Y",
        "No": "N",
        "yes": "Y",
        "no": "N",
        "true": "Y",
        "false": "N",
        True: "Y",
        False: "N",
    },
    "location": {
        "Home": "Home",
        "Road": "Road",
        "All": "",
        "": "",
    },
    "outcome": {
        "W": "W",
        "L": "L",
        "Win": "W",
        "Loss": "L",
        "win": "W",
        "loss": "L",
        "All": "",
        "": "",
    },
    "season_segment": {
        "Full": "",
        "PreAllStar": "Pre All-Star",
        "PostAllStar": "Post All-Star",
        "Pre All-Star": "Pre All-Star",
        "Post All-Star": "Post All-Star",
        "": "",
    },
}


# Reverse mappings (for display purposes)
PARAM_REVERSE_ALIASES: Dict[str, Dict[str, str]] = {
    "season_type": {
        "Regular Season": "Regular",
        "Pre Season": "Preseason",
        "All Star": "AllStar",
    },
    "per_mode": {
        "Per36Minutes": "Per36",
        "Per100Possessions": "Per100",
    },
    "measure_type": {
        "Four Factors": "FourFactors",
    },
}


def normalize_param(param_name: str, value: Any) -> Any:
    """
    Normalize parameter value using aliases.

    Args:
        param_name: Parameter name (e.g., "season_type")
        value: Parameter value (e.g., "Regular" or "Regular Season")

    Returns:
        Normalized value for NBA API (e.g., "Regular Season")

    Examples:
        # Season type
        normalize_param("season_type", "Regular")
        # Returns: "Regular Season"

        # Per mode
        normalize_param("per_mode", "Per36")
        # Returns: "Per36Minutes"

        # Boolean to Y/N
        normalize_param("pace_adjust", True)
        # Returns: "Y"

        # Unknown parameter (pass through)
        normalize_param("unknown_param", "value")
        # Returns: "value"
    """
    if param_name in PARAM_ALIASES:
        alias_map = PARAM_ALIASES[param_name]
        return alias_map.get(value, value)

    return value


def denormalize_param(param_name: str, value: Any) -> Any:
    """
    Convert NBA API value to friendly display value.

    Args:
        param_name: Parameter name (e.g., "season_type")
        value: NBA API value (e.g., "Regular Season")

    Returns:
        Friendly display value (e.g., "Regular")

    Examples:
        # Season type
        denormalize_param("season_type", "Regular Season")
        # Returns: "Regular"

        # Per mode
        denormalize_param("per_mode", "Per36Minutes")
        # Returns: "Per36"
    """
    if param_name in PARAM_REVERSE_ALIASES:
        reverse_map = PARAM_REVERSE_ALIASES[param_name]
        return reverse_map.get(value, value)

    return value


def normalize_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize all parameters in a dictionary.

    Args:
        params: Dictionary of parameters

    Returns:
        Normalized parameters dictionary

    Examples:
        params = {
            "season_type": "Regular",
            "per_mode": "Per36",
            "pace_adjust": True
        }

        normalized = normalize_params(params)
        # Returns: {
        #     "season_type": "Regular Season",
        #     "per_mode": "Per36Minutes",
        #     "pace_adjust": "Y"
        # }
    """
    return {
        param_name: normalize_param(param_name, value)
        for param_name, value in params.items()
    }


def get_valid_values(param_name: str) -> Optional[list]:
    """
    Get valid values for a parameter.

    Args:
        param_name: Parameter name

    Returns:
        List of valid values, or None if parameter unknown

    Examples:
        # Get valid season types
        values = get_valid_values("season_type")
        # Returns: ["Regular Season", "Playoffs", "PlayIn", "Pre Season", "All Star"]

        # Get valid per modes
        values = get_valid_values("per_mode")
        # Returns: ["PerGame", "Totals", "Per36Minutes", ...]
    """
    if param_name == "season_type":
        return [e.value for e in SeasonType]
    elif param_name == "per_mode":
        return [e.value for e in PerMode]
    elif param_name == "measure_type":
        return [e.value for e in MeasureType]
    elif param_name == "location":
        return [e.value for e in Location]
    elif param_name == "outcome":
        return [e.value for e in Outcome]
    elif param_name == "season_segment":
        return [e.value for e in SeasonSegment]

    return None


def validate_param(param_name: str, value: Any) -> bool:
    """
    Validate that a parameter value is valid.

    Args:
        param_name: Parameter name
        value: Parameter value to validate

    Returns:
        True if valid, False otherwise

    Examples:
        # Valid season type
        validate_param("season_type", "Regular")
        # Returns: True

        # Invalid season type
        validate_param("season_type", "InvalidType")
        # Returns: False

        # Unknown parameter (always valid)
        validate_param("unknown_param", "any_value")
        # Returns: True
    """
    if param_name not in PARAM_ALIASES:
        # Unknown parameter, assume valid
        return True

    alias_map = PARAM_ALIASES[param_name]
    return value in alias_map


# Common parameter defaults
DEFAULT_PARAMS: Dict[str, Any] = {
    "season_type": "Regular Season",
    "per_mode": "PerGame",
    "measure_type": "Base",
    "pace_adjust": "N",
    "plus_minus": "N",
    "rank": "N",
    "location": "",
    "outcome": "",
    "season_segment": "",
}


def apply_defaults(params: Dict[str, Any], defaults: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Apply default values to parameters.

    Args:
        params: Parameters dictionary
        defaults: Custom defaults (optional, uses DEFAULT_PARAMS if not provided)

    Returns:
        Parameters with defaults applied

    Examples:
        params = {"season": "2023-24"}

        params_with_defaults = apply_defaults(params)
        # Returns: {
        #     "season": "2023-24",
        #     "season_type": "Regular Season",
        #     "per_mode": "PerGame",
        #     ...
        # }
    """
    defaults_to_use = defaults if defaults is not None else DEFAULT_PARAMS

    result = defaults_to_use.copy()
    result.update(params)

    return result
