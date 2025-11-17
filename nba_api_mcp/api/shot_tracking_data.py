"""
Shot Tracking Data Aggregation

Fetches and processes aggregated tracking data from NBA API including:
- Defender distance ranges (Very Tight, Tight, Open, Wide Open)
- Shot clock ranges
- Dribble ranges
- Touch time ranges

Note: NBA API provides AGGREGATED tracking data, not shot-by-shot defender coords.

Reference: SESSION_138_SHOT_LEVEL_XFG_PLAN.md
Author: Session 138
Date: 2025-11-12
"""

import logging
from typing import Dict, List, Optional, Tuple

import pandas as pd
from nba_api.stats.endpoints import PlayerDashPtShots

from .entity_resolver import resolve_entity
from .errors import EntityNotFoundError, NBAApiError, retry_with_backoff
from .tools.nba_api_utils import normalize_season

logger = logging.getLogger(__name__)


# ============================================================================
# CONSTANTS
# ============================================================================

DEFENDER_DISTANCE_RANGES = {
    'very_tight': '0-2 Feet - Very Tight',
    'tight': '2-4 Feet - Tight',
    'open': '4-6 Feet - Open',
    'wide_open': '6+ Feet - Wide Open'
}

SHOT_CLOCK_RANGES = [
    '24-22', '22-18 Very Early', '18-15 Early', '15-7 Average',
    '7-4 Late', '4-0 Very Late', 'ShotClock Off'
]

DRIBBLE_RANGES = ['0 Dribbles', '1 Dribble', '2 Dribbles', '3-6 Dribbles', '7+ Dribbles']

TOUCH_TIME_RANGES = ['Touch < 2 Seconds', 'Touch 2-6 Seconds', 'Touch 6+ Seconds']


# ============================================================================
# DATA FETCHING
# ============================================================================

@retry_with_backoff(max_retries=3)
def fetch_player_tracking_data(
    player_id: int,
    team_id: int,
    season: str,
    season_type: str = "Regular Season"
) -> Dict[str, pd.DataFrame]:
    """
    Fetch aggregated tracking data for a player.

    Uses PlayerDashPtShots endpoint which provides 7 datasets:
    0. Overall shot stats
    1. Shot area (restricted, paint, mid-range, etc.)
    2. Shot clock range
    3. Dribble range
    4. Closest defender distance (2pt)
    5. Closest defender distance (3pt)
    6. Touch time range

    Args:
        player_id: NBA player ID
        team_id: NBA team ID
        season: Season in YYYY-YY format (e.g., "2023-24")
        season_type: "Regular Season" or "Playoffs"

    Returns:
        Dictionary with keys:
        - 'overall': Overall shot stats
        - 'shot_area': By shot area
        - 'shot_clock': By shot clock range
        - 'dribbles': By dribble count
        - 'defender_2pt': By defender distance (2pt shots)
        - 'defender_3pt': By defender distance (3pt shots)
        - 'touch_time': By touch time

    Raises:
        NBAApiError: If API call fails
    """
    try:
        logger.info(
            f"Fetching tracking data: player_id={player_id}, team_id={team_id}, "
            f"season={season}, season_type={season_type}"
        )

        # Fetch from NBA API
        tracking_data = PlayerDashPtShots(
            player_id=player_id,
            team_id=team_id,
            season=season,
            season_type_all_star=season_type,
            per_mode_simple='PerGame',  # PerGame or Totals
            last_n_games=0,
            league_id='00',
            month=0,
            opponent_team_id=0,
            period=0,
            date_from_nullable='',
            date_to_nullable='',
            game_segment_nullable='',
            location_nullable=''
        )

        # Get all 7 datasets
        dfs = tracking_data.get_data_frames()

        if len(dfs) < 7:
            logger.warning(
                f"Expected 7 datasets, got {len(dfs)}. Some tracking data may be missing."
            )

        # Map datasets to descriptive names
        dataset_map = {
            'overall': dfs[0] if len(dfs) > 0 else pd.DataFrame(),
            'shot_area': dfs[1] if len(dfs) > 1 else pd.DataFrame(),
            'shot_clock': dfs[2] if len(dfs) > 2 else pd.DataFrame(),
            'dribbles': dfs[3] if len(dfs) > 3 else pd.DataFrame(),
            'defender_2pt': dfs[4] if len(dfs) > 4 else pd.DataFrame(),
            'defender_3pt': dfs[5] if len(dfs) > 5 else pd.DataFrame(),
            'touch_time': dfs[6] if len(dfs) > 6 else pd.DataFrame()
        }

        logger.info(
            f"Fetched tracking data with {sum(len(df) for df in dataset_map.values())} total rows"
        )

        return dataset_map

    except Exception as e:
        logger.error(f"Error fetching tracking data: {e}")
        raise NBAApiError(
            message=f"Failed to fetch tracking data: {str(e)}",
            status_code=getattr(e, 'status_code', None),
            endpoint='PlayerDashPtShots'
        )


# ============================================================================
# PRESSURE PROFILE
# ============================================================================

def calculate_pressure_profile(
    defender_2pt_df: pd.DataFrame,
    defender_3pt_df: pd.DataFrame
) -> Dict[str, Dict[str, float]]:
    """
    Calculate player's pressure profile from defender distance data.

    Shows how a player performs under different defensive pressure levels.

    Args:
        defender_2pt_df: Defender distance data for 2pt shots
        defender_3pt_df: Defender distance data for 3pt shots

    Returns:
        Dictionary with structure:
        {
            'very_tight': {'fga_freq': 0.15, 'fg_pct': 0.42, 'fga': 5.2},
            'tight': {'fga_freq': 0.30, 'fg_pct': 0.48, 'fga': 7.8},
            'open': {'fga_freq': 0.35, 'fg_pct': 0.52, 'fga': 9.1},
            'wide_open': {'fga_freq': 0.20, 'fg_pct': 0.58, 'fga': 5.2}
        }
    """
    # Combine 2pt and 3pt defender data
    combined_df = pd.concat([defender_2pt_df, defender_3pt_df], ignore_index=True)

    if combined_df.empty:
        logger.warning("No defender distance data available for pressure profile")
        return {}

    # Check for required columns
    if 'CLOSE_DEF_DIST_RANGE' not in combined_df.columns:
        logger.error("CLOSE_DEF_DIST_RANGE column not found in tracking data")
        return {}

    profile = {}

    # Calculate metrics for each defender distance range
    for key, range_name in DEFENDER_DISTANCE_RANGES.items():
        range_data = combined_df[combined_df['CLOSE_DEF_DIST_RANGE'] == range_name]

        if range_data.empty:
            continue

        # Sum across all rows for this range (2pt and 3pt)
        fga = range_data['FGA'].sum() if 'FGA' in range_data.columns else 0
        fgm = range_data['FGM'].sum() if 'FGM' in range_data.columns else 0
        fg_pct = fgm / fga if fga > 0 else 0.0

        # FGA frequency
        total_fga = combined_df['FGA'].sum() if 'FGA' in combined_df.columns else 1
        fga_freq = fga / total_fga if total_fga > 0 else 0.0

        profile[key] = {
            'fga': round(float(fga), 1),
            'fga_freq': round(fga_freq, 3),
            'fg_pct': round(fg_pct, 3),
            'fgm': round(float(fgm), 1),
            'efg_pct': round(
                range_data['EFG_PCT'].mean() if 'EFG_PCT' in range_data.columns else fg_pct,
                3
            )
        }

    return profile


def calculate_pressure_index(pressure_profile: Dict[str, Dict[str, float]]) -> float:
    """
    Calculate pressure index: weighted average of shot difficulty.

    Higher pressure index = takes more contested shots.

    Args:
        pressure_profile: Output from calculate_pressure_profile()

    Returns:
        Pressure index [0, 1] where:
        - 0 = all wide open shots
        - 1 = all very tight shots
    """
    if not pressure_profile:
        return 0.5  # Default to medium pressure

    # Difficulty weights for each range
    difficulty_weights = {
        'very_tight': 1.0,
        'tight': 0.67,
        'open': 0.33,
        'wide_open': 0.0
    }

    # Weighted average
    total_freq = sum(
        profile['fga_freq']
        for profile in pressure_profile.values()
    )

    if total_freq == 0:
        return 0.5

    pressure_index = sum(
        profile['fga_freq'] * difficulty_weights.get(key, 0.5)
        for key, profile in pressure_profile.items()
    ) / total_freq

    return round(pressure_index, 3)


def calculate_contest_tolerance(pressure_profile: Dict[str, Dict[str, float]]) -> float:
    """
    Calculate contest tolerance: how much FG% drops under pressure.

    Lower value = more affected by defense (less tolerant).
    Higher value = maintains FG% under pressure (more tolerant).

    Args:
        pressure_profile: Output from calculate_pressure_profile()

    Returns:
        Contest tolerance: (FG% tight - FG% open) * -1
        Positive = FG% drops with pressure (expected)
        Negative = FG% improves with pressure (rare, possible small samples)
    """
    if not pressure_profile:
        return 0.0

    # Get tight and open FG%
    tight_fg_pct = pressure_profile.get('tight', {}).get('fg_pct', 0)
    open_fg_pct = pressure_profile.get('open', {}).get('fg_pct', 0)

    # Negative value = FG% drops (less tolerant)
    # Positive value = FG% improves (more tolerant, unusual)
    tolerance = (tight_fg_pct - open_fg_pct) * -1

    return round(tolerance, 3)


# ============================================================================
# SHOT CREATION METRICS
# ============================================================================

def calculate_shot_creation_profile(
    dribbles_df: pd.DataFrame,
    touch_time_df: pd.DataFrame
) -> Dict[str, float]:
    """
    Calculate shot creation profile from dribble and touch time data.

    Args:
        dribbles_df: Dribble range data
        touch_time_df: Touch time range data

    Returns:
        Dictionary with shot creation metrics:
        {
            'quick_release_pct': 0.45,  # % shots < 2s touch time
            'iso_scoring_pct': 0.12,    # % shots 7+ dribbles
            'spot_up_pct': 0.38,        # % shots 0 dribbles
            'avg_dribbles': 2.3,        # Avg dribbles per shot
            'avg_touch_time': 3.1       # Avg touch time (seconds)
        }
    """
    metrics = {}

    # Dribble-based metrics
    if not dribbles_df.empty and 'DRIBBLE_RANGE' in dribbles_df.columns:
        total_fga = dribbles_df['FGA'].sum() if 'FGA' in dribbles_df.columns else 0

        # Spot up (0 dribbles)
        spot_up = dribbles_df[dribbles_df['DRIBBLE_RANGE'] == '0 Dribbles']
        metrics['spot_up_pct'] = round(
            spot_up['FGA'].sum() / total_fga if total_fga > 0 else 0.0,
            3
        )

        # Iso scoring (7+ dribbles)
        iso = dribbles_df[dribbles_df['DRIBBLE_RANGE'] == '7+ Dribbles']
        metrics['iso_scoring_pct'] = round(
            iso['FGA'].sum() / total_fga if total_fga > 0 else 0.0,
            3
        )

        # Estimate average dribbles (weighted by FGA)
        dribble_midpoints = {
            '0 Dribbles': 0,
            '1 Dribble': 1,
            '2 Dribbles': 2,
            '3-6 Dribbles': 4.5,
            '7+ Dribbles': 9
        }
        avg_dribbles = sum(
            row['FGA'] * dribble_midpoints.get(row['DRIBBLE_RANGE'], 0)
            for _, row in dribbles_df.iterrows()
        ) / total_fga if total_fga > 0 else 0.0
        metrics['avg_dribbles'] = round(avg_dribbles, 1)

    # Touch time-based metrics
    if not touch_time_df.empty and 'TOUCH_TIME_RANGE' in touch_time_df.columns:
        total_fga = touch_time_df['FGA'].sum() if 'FGA' in touch_time_df.columns else 0

        # Quick release (< 2s)
        quick = touch_time_df[touch_time_df['TOUCH_TIME_RANGE'] == 'Touch < 2 Seconds']
        metrics['quick_release_pct'] = round(
            quick['FGA'].sum() / total_fga if total_fga > 0 else 0.0,
            3
        )

        # Estimate average touch time (weighted by FGA)
        touch_time_midpoints = {
            'Touch < 2 Seconds': 1.0,
            'Touch 2-6 Seconds': 4.0,
            'Touch 6+ Seconds': 8.0
        }
        avg_touch_time = sum(
            row['FGA'] * touch_time_midpoints.get(row['TOUCH_TIME_RANGE'], 0)
            for _, row in touch_time_df.iterrows()
        ) / total_fga if total_fga > 0 else 0.0
        metrics['avg_touch_time'] = round(avg_touch_time, 1)

    return metrics


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def get_player_tracking_metrics(
    player_name: str,
    season: str,
    season_type: str = "Regular Season"
) -> Dict[str, any]:
    """
    Get comprehensive tracking metrics for a player.

    Main entry point for shot tracking data analysis.

    Args:
        player_name: Player name (fuzzy matching supported)
        season: Season in YYYY-YY format (e.g., "2023-24")
        season_type: "Regular Season" or "Playoffs"

    Returns:
        Dictionary with structure:
        {
            'player': {'id': int, 'name': str, 'team_id': int},
            'season': str,
            'pressure_profile': {...},
            'pressure_index': float,
            'contest_tolerance': float,
            'shot_creation': {...},
            'raw_data': {
                'overall': DataFrame,
                'shot_area': DataFrame,
                ...
            }
        }

    Raises:
        EntityNotFoundError: If player not found
        NBAApiError: If API call fails

    Example:
        >>> metrics = get_player_tracking_metrics("Stephen Curry", "2023-24")
        >>> print(f"Pressure Index: {metrics['pressure_index']:.3f}")
        >>> print(f"Spot Up %: {metrics['shot_creation']['spot_up_pct']:.1%}")
    """
    # Normalize season
    normalized_seasons = normalize_season(season)
    season_str = normalized_seasons[0] if isinstance(normalized_seasons, list) else normalized_seasons

    # Resolve player
    entity = resolve_entity(query=player_name, entity_type='player')
    player_id = entity.entity_id
    player_full_name = entity.name

    # Get team ID (use most recent team)
    # Note: For simplicity, using 0 for all teams. In production, would fetch actual team_id
    team_id = 0  # 0 = all teams

    logger.info(
        f"Fetching tracking metrics for {player_full_name} (ID: {player_id}) - {season_str}"
    )

    # Fetch raw tracking data
    raw_data = fetch_player_tracking_data(
        player_id=player_id,
        team_id=team_id,
        season=season_str,
        season_type=season_type
    )

    # Calculate pressure profile
    pressure_profile = calculate_pressure_profile(
        raw_data['defender_2pt'],
        raw_data['defender_3pt']
    )

    # Calculate pressure metrics
    pressure_index = calculate_pressure_index(pressure_profile)
    contest_tolerance = calculate_contest_tolerance(pressure_profile)

    # Calculate shot creation profile
    shot_creation = calculate_shot_creation_profile(
        raw_data['dribbles'],
        raw_data['touch_time']
    )

    # Compile results
    result = {
        'player': {
            'id': player_id,
            'name': player_full_name,
            'team_id': team_id
        },
        'season': season_str,
        'season_type': season_type,
        'pressure_profile': pressure_profile,
        'pressure_index': pressure_index,
        'contest_tolerance': contest_tolerance,
        'shot_creation': shot_creation,
        'raw_data': raw_data
    }

    return result


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def format_tracking_report(metrics: Dict) -> str:
    """
    Format tracking metrics into readable report.

    Args:
        metrics: Output from get_player_tracking_metrics()

    Returns:
        Formatted string report
    """
    lines = [
        "=" * 80,
        f"SHOT TRACKING METRICS: {metrics['player']['name']}",
        f"Season: {metrics['season']} {metrics['season_type']}",
        "=" * 80,
        "",
        "PRESSURE PROFILE:",
    ]

    # Pressure profile
    for key, profile in metrics['pressure_profile'].items():
        lines.append(
            f"  {key.replace('_', ' ').title():15s}: "
            f"{profile['fga']:5.1f} FGA ({profile['fga_freq']:5.1%}), "
            f"FG% = {profile['fg_pct']:.1%}, "
            f"eFG% = {profile['efg_pct']:.1%}"
        )

    lines.extend([
        "",
        "PRESSURE METRICS:",
        f"  Pressure Index: {metrics['pressure_index']:.3f} "
        f"(0.0 = all open, 1.0 = all contested)",
        f"  Contest Tolerance: {metrics['contest_tolerance']:+.3f} "
        f"(negative = more affected by defense)",
        "",
        "SHOT CREATION:"
    ])

    # Shot creation
    creation = metrics['shot_creation']
    if creation:
        lines.extend([
            f"  Spot Up %: {creation.get('spot_up_pct', 0):.1%} (0 dribbles)",
            f"  Iso Scoring %: {creation.get('iso_scoring_pct', 0):.1%} (7+ dribbles)",
            f"  Quick Release %: {creation.get('quick_release_pct', 0):.1%} (<2s touch)",
            f"  Avg Dribbles: {creation.get('avg_dribbles', 0):.1f}",
            f"  Avg Touch Time: {creation.get('avg_touch_time', 0):.1f}s"
        ])

    lines.append("=" * 80)

    return "\n".join(lines)


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == '__main__':
    # Example: Fetch tracking metrics for Stephen Curry
    print("Fetching tracking metrics for Stephen Curry...")

    try:
        metrics = get_player_tracking_metrics(
            player_name="Stephen Curry",
            season="2023-24",
            season_type="Regular Season"
        )

        # Print formatted report
        print(format_tracking_report(metrics))

        # Access specific metrics
        print("\nPressure Index:", metrics['pressure_index'])
        print("Spot Up %:", metrics['shot_creation'].get('spot_up_pct', 0))

    except Exception as e:
        print(f"Error: {e}")
