"""
Configuration management for NBA MCP using pydantic-settings.

Provides typed configuration with validation, .env file support, and
sensible defaults for all settings.

Features:
- Type-safe configuration with validation
- .env file support (auto-loaded)
- Environment variable overrides
- Sensible defaults for development
- Structured organization by feature area

Usage:
    from nba_api_mcp.config import settings

    # Access configuration
    port = settings.NBA_MCP_PORT
    redis_host = settings.REDIS_HOST

    # Configuration is immutable after initialization
    # To change settings, modify .env file or set environment variables
"""

from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    NBA MCP Server configuration.

    All settings can be configured via:
    1. .env file (highest priority for local development)
    2. Environment variables
    3. Default values (defined below)

    Settings are loaded in this order (later sources override earlier):
    1. Default values
    2. .env file
    3. Environment variables (highest priority)
    """

    # =========================================================================
    # Server Configuration
    # =========================================================================

    NBA_MCP_PORT: int = Field(
        default=8005,
        description="Port for the MCP server to listen on",
        validation_alias="NBA_MCP_PORT",
    )

    MCP_HOST: str = Field(
        default="127.0.0.1",
        description="Host address for the MCP server",
    )

    MCP_TRANSPORT: str = Field(
        default="stdio",
        description="Transport protocol: stdio, sse, or websocket",
    )

    NBA_MCP_LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL",
    )

    LOG_FORMAT: str = Field(
        default="text",
        description="Log format: 'text' for human-readable, 'json' for structured",
    )

    ENVIRONMENT: str = Field(
        default="development",
        description="Environment name: development, staging, production",
    )

    # =========================================================================
    # Redis Cache Configuration
    # =========================================================================

    ENABLE_REDIS_CACHE: bool = Field(
        default=False,
        description="Enable Redis caching (falls back to in-memory if disabled/unavailable)",
    )

    REDIS_HOST: str = Field(
        default="localhost",
        description="Redis server hostname",
    )

    REDIS_PORT: int = Field(
        default=6379,
        description="Redis server port",
    )

    REDIS_DB: int = Field(
        default=0,
        description="Redis database number",
    )

    REDIS_URL: Optional[str] = Field(
        default=None,
        description="Redis connection URL (overrides host/port/db if set)",
    )

    REDIS_CONNECT_TIMEOUT: float = Field(
        default=0.3,
        description="Redis connection timeout in seconds",
    )

    REDIS_MAX_CONNECTIONS: int = Field(
        default=50,
        description="Maximum Redis connection pool size",
    )

    # =========================================================================
    # Rate Limiting Configuration
    # =========================================================================

    NBA_MCP_DAILY_QUOTA: int = Field(
        default=10000,
        description="Daily request quota for NBA API calls",
    )

    NBA_MCP_SIMPLE_RATE_LIMIT: int = Field(
        default=60,
        description="Rate limit for simple tools (requests per minute)",
    )

    NBA_MCP_COMPLEX_RATE_LIMIT: int = Field(
        default=30,
        description="Rate limit for complex tools (requests per minute)",
    )

    # =========================================================================
    # Observability Configuration
    # =========================================================================

    ENABLE_METRICS: bool = Field(
        default=False,
        description="Enable Prometheus metrics collection",
    )

    ENABLE_TRACING: bool = Field(
        default=False,
        description="Enable OpenTelemetry distributed tracing",
    )

    OTLP_ENDPOINT: Optional[str] = Field(
        default=None,
        description="OpenTelemetry Protocol (OTLP) collector endpoint",
    )

    ENABLE_SCHEMA_VALIDATION: bool = Field(
        default=False,
        description="Enable strict schema validation for API responses",
    )

    # =========================================================================
    # LLM Integration Configuration
    # =========================================================================

    NBA_MCP_ENABLE_LLM_FALLBACK: bool = Field(
        default=True,
        description="Enable LLM fallback for natural language query parsing",
    )

    NBA_MCP_LLM_MODEL: str = Field(
        default="llama3.2:3b",
        description="Ollama model for query parsing (e.g., llama3.2:3b, phi-4, qwen2.5:7b)",
    )

    NBA_MCP_LLM_URL: str = Field(
        default="http://localhost:11434",
        description="Ollama server URL",
    )

    NBA_MCP_LLM_TIMEOUT: int = Field(
        default=5,
        description="LLM request timeout in seconds",
    )

    # =========================================================================
    # Data Storage Configuration
    # =========================================================================

    NBA_MCP_DATA_DIR: str = Field(
        default="mcp_data/",
        description="Directory for storing saved NBA data",
    )

    # =========================================================================
    # Concurrency Configuration
    # =========================================================================

    NBA_MCP_MAX_CONCURRENT_LIVE: int = Field(
        default=4,
        description="Max concurrent requests for live endpoints (scoreboard, play-by-play)",
    )

    NBA_MCP_MAX_CONCURRENT_STANDARD: int = Field(
        default=8,
        description="Max concurrent requests for standard endpoints",
    )

    NBA_MCP_MAX_CONCURRENT_HEAVY: int = Field(
        default=2,
        description="Max concurrent requests for heavy endpoints (shot charts, play-by-play)",
    )

    NBA_MCP_DUCKDB_THREADS: int = Field(
        default=4,
        description="Number of threads for DuckDB query processing",
    )

    # =========================================================================
    # Pydantic Settings Configuration
    # =========================================================================

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",  # Ignore extra fields from environment
    )


# Global settings instance - loaded once on import
settings = Settings()


# Helper function for runtime configuration changes (if needed)
def reload_settings() -> Settings:
    """
    Reload settings from environment and .env file.

    Use this if you need to reload configuration at runtime,
    though normally settings should be loaded once at startup.

    Returns:
        New Settings instance with current environment values
    """
    return Settings()


# Export settings as module-level variable for convenience
__all__ = ["settings", "reload_settings", "Settings"]
