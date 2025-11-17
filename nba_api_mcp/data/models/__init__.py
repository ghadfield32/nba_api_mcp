"""
Query models for NBA API MCP.

This module provides structured query models for the NBA API MCP data fetching system.
Supports scope-based queries (ALL players, multi-entity), temporal ranges (season/date ranges),
and flexible filtering.
"""

from nba_api_mcp.data.models.query import (
    Query,
    QueryResult,
    Scope,
    Range,
    FilterExpression,
    ScopeCapability,
    RangeCapability,
    FilterCapability,
)

__all__ = [
    "Query",
    "QueryResult",
    "Scope",
    "Range",
    "FilterExpression",
    "ScopeCapability",
    "RangeCapability",
    "FilterCapability",
]
