"""
Data management package for NBA MCP.

This package provides dataset management, joins, and data catalog functionality.

Modules:
    - catalog: Endpoint metadata and data dictionary
    - dataset_manager: Dataset lifecycle management
    - fetch: Raw data retrieval from NBA API
    - joins: DuckDB-powered SQL joins
    - introspection: Endpoint capability discovery
    - pagination: Large dataset chunking and fetching
    - limits: Dataset size limit configuration
"""

from nba_api_mcp.data.catalog import DataCatalog, EndpointMetadata, JoinRelationship
from nba_api_mcp.data.dataset_manager import (
    DatasetHandle,
    DatasetManager,
    ProvenanceInfo,
    get_dataset_manager,
    get_manager,
)
from nba_api_mcp.data.fetch import fetch_endpoint
from nba_api_mcp.data.introspection import (
    EndpointCapabilities,
    EndpointIntrospector,
    get_introspector,
)
from nba_api_mcp.data.joins import join_tables, validate_join_columns
from nba_api_mcp.data.limits import (
    FetchLimits,
    SizeCheckResult,
    get_limits,
    reset_limits,
)
from nba_api_mcp.data.pagination import ChunkInfo, DatasetPaginator, get_paginator

__all__ = [
    # Catalog
    "DataCatalog",
    "EndpointMetadata",
    "JoinRelationship",
    # Dataset Management
    "DatasetManager",
    "DatasetHandle",
    "ProvenanceInfo",
    "get_manager",
    "get_dataset_manager",
    # Operations
    "fetch_endpoint",
    "join_tables",
    "validate_join_columns",
    # Introspection
    "EndpointIntrospector",
    "EndpointCapabilities",
    "get_introspector",
    # Pagination
    "DatasetPaginator",
    "ChunkInfo",
    "get_paginator",
    # Limits
    "FetchLimits",
    "SizeCheckResult",
    "get_limits",
    "reset_limits",
]
