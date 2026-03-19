"""NBA MCP Server Package."""

# Pre-populate platform._uname_cache before importing nba_server (which pulls in
# prometheus_client -> platform_collector.py -> PlatformCollector() -> platform.system()).
# On Windows, platform.system() calls _wmi_query() which hangs when WMI is unresponsive.
# sys.getwindowsversion() is a fast C-level call that avoids WMI entirely.
import sys as _sys
if _sys.platform == "win32":
    import platform as _platform
    if _platform._uname_cache is None:
        import socket as _socket
        _v = _sys.getwindowsversion()
        _platform._uname_cache = _platform.uname_result(
            "Windows",
            _socket.gethostname(),
            "11",
            f"{_v.major}.{_v.minor}.{_v.build}",
            "AMD64",
        )

from nba_api_mcp.nba_server import main

__all__ = [
    "main",
    "get_live_scoreboard",
    "get_player_career_stats",
    "get_league_leaders",
    "get_league_game_log",
]

__version__ = "0.5.1"
