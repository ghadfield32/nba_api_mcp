"""
NBA MCP Command Line Interface.

Provides convenient command-line access to NBA MCP features including:
- Server management (start/stop)
- Data fetching and exploration
- Catalog browsing
- Batch operations
- Development tools

Usage:
    nba-mcp serve                    # Start MCP server
    nba-mcp catalog                  # List all endpoints
    nba-mcp fetch player_career_stats --params player_name="LeBron James"
    nba-mcp batch '[{"endpoint":"league_leaders","params":{"stat_category":"PTS"}}]'

For detailed help on any command:
    nba-mcp <command> --help
"""

import asyncio
import json
import sys
from typing import List, Optional

import typer
from rich.console import Console
from rich.table import Table

# Import will be done after __name__ == "__main__" check to avoid circular imports
# from nba_api_mcp.nba_server import main as serve_main
# from nba_api_mcp.data.unified_fetch import batch_fetch, unified_fetch
# from nba_api_mcp.data.catalog import get_catalog

# Create Typer app
app = typer.Typer(
    name="nba-mcp",
    help="NBA MCP Server - NBA data via Model Context Protocol",
    add_completion=False,
    no_args_is_help=True,
    rich_markup_mode="rich",
)

# Rich console for beautiful output
console = Console()


# ============================================================================
# SERVER COMMAND
# ============================================================================


@app.command(
    help="""
    Start the NBA MCP server.

    The server runs in the specified mode and transport:
    - [bold]claude[/bold]: Optimized for Claude Desktop (stdio transport)
    - [bold]local[/bold]: Local development mode

    Examples:
        nba-mcp serve --mode claude
        nba-mcp serve --mode local --port 8005
        nba-mcp serve --transport sse
    """
)
def serve(
    mode: str = typer.Option(
        "claude",
        "--mode",
        "-m",
        help="Server mode: 'claude' or 'local'",
    ),
    transport: Optional[str] = typer.Option(
        None,
        "--transport",
        "-t",
        help="Transport protocol: 'stdio', 'sse', or 'websocket'",
    ),
    host: Optional[str] = typer.Option(
        None,
        "--host",
        "-h",
        help="Host address (default: 127.0.0.1)",
    ),
    port: Optional[int] = typer.Option(
        None,
        "--port",
        "-p",
        help="Port number (default: from config)",
    ),
):
    """Start the NBA MCP server."""
    # Import here to avoid circular imports
    from nba_api_mcp.nba_server import main as serve_main

    # Build sys.argv for the existing server main function
    args = ["nba_server", "--mode", mode]

    if transport:
        args.extend(["--transport", transport])
    if host:
        args.extend(["--host", host])
    if port:
        args.extend(["--port", str(port)])

    # Replace sys.argv and call the server
    old_argv = sys.argv
    try:
        sys.argv = args
        serve_main()
    finally:
        sys.argv = old_argv


# ============================================================================
# CATALOG COMMANDS
# ============================================================================


@app.command(
    help="""
    Browse the NBA MCP data catalog.

    Lists available endpoints with their metadata, parameters, and capabilities.

    Examples:
        nba-mcp catalog                          # List all endpoints
        nba-mcp catalog player_career_stats      # Show specific endpoint
        nba-mcp catalog --json                   # Output as JSON
        nba-mcp catalog --category player_stats  # Filter by category
    """
)
def catalog(
    endpoint: Optional[str] = typer.Argument(
        None,
        help="Specific endpoint name to inspect",
    ),
    json_out: bool = typer.Option(
        False,
        "--json",
        help="Output as JSON",
    ),
    category: Optional[str] = typer.Option(
        None,
        "--category",
        "-c",
        help="Filter by category",
    ),
    search: Optional[str] = typer.Option(
        None,
        "--search",
        "-s",
        help="Search endpoints by keyword",
    ),
):
    """Browse the data catalog."""
    from nba_api_mcp.data.catalog import get_catalog

    catalog_instance = get_catalog()

    # Show specific endpoint
    if endpoint:
        try:
            meta = catalog_instance.get_endpoint(endpoint)
            if json_out:
                console.print_json(data=meta.model_dump())
            else:
                _display_endpoint_details(meta)
        except KeyError:
            console.print(f"[red]Endpoint '{endpoint}' not found[/red]")
            typer.Exit(1)
        return

    # Get all endpoints
    endpoints = catalog_instance.list_endpoints()

    # Apply filters
    if category:
        endpoints = [e for e in endpoints if e.category == category]

    if search:
        search_lower = search.lower()
        endpoints = [
            e
            for e in endpoints
            if search_lower in e.name.lower()
            or search_lower in e.description.lower()
        ]

    # Output
    if json_out:
        console.print_json(
            data={"endpoints": [e.name for e in endpoints], "count": len(endpoints)}
        )
    else:
        _display_catalog_table(endpoints)


def _display_catalog_table(endpoints):
    """Display endpoints in a formatted table."""
    table = Table(title="NBA MCP Data Catalog", show_header=True, header_style="bold")
    table.add_column("Endpoint", style="cyan", no_wrap=True)
    table.add_column("Category", style="magenta")
    table.add_column("Description", style="white")

    for ep in endpoints:
        table.add_row(
            ep.name,
            ep.category.value if hasattr(ep.category, "value") else str(ep.category),
            ep.description[:60] + "..." if len(ep.description) > 60 else ep.description,
        )

    console.print(table)
    console.print(f"\n[green]Total endpoints: {len(endpoints)}[/green]")
    console.print("\n[dim]Use 'nba-mcp catalog <endpoint>' for details[/dim]")


def _display_endpoint_details(meta):
    """Display detailed endpoint information."""
    console.print(f"\n[bold cyan]{meta.display_name}[/bold cyan]")
    console.print(f"[dim]{meta.name}[/dim]\n")

    console.print(f"[bold]Description:[/bold] {meta.description}\n")

    # Parameters
    if meta.parameters:
        console.print("[bold]Parameters:[/bold]")
        for param in meta.parameters:
            required = "[red]*[/red]" if param.required else ""
            console.print(
                f"  {required} [cyan]{param.name}[/cyan] ({param.type}): {param.description}"
            )
            if param.default is not None:
                console.print(f"    Default: {param.default}")
            if param.example is not None:
                console.print(f"    Example: {param.example}")
        console.print()

    # Sample params
    if meta.sample_params:
        console.print("[bold]Sample usage:[/bold]")
        console.print(f"  {json.dumps(meta.sample_params, indent=2)}\n")

    # Output columns
    if meta.output_columns:
        console.print(f"[bold]Output columns:[/bold] {len(meta.output_columns)} columns")
        console.print(f"  {', '.join(meta.output_columns[:10])}")
        if len(meta.output_columns) > 10:
            console.print(f"  ... and {len(meta.output_columns) - 10} more\n")


# ============================================================================
# FETCH COMMAND
# ============================================================================


@app.command(
    help="""
    Fetch data from a single endpoint.

    Examples:
        nba-mcp fetch player_career_stats --params player_name="LeBron James"
        nba-mcp fetch team_standings --params season="2023-24"
        nba-mcp fetch league_leaders --params stat_category="PTS" --filters "PTS >= 30"
        nba-mcp fetch player_game_logs --params player_id=2544 --no-cache
    """
)
def fetch(
    endpoint: str = typer.Argument(..., help="Endpoint name to fetch"),
    params: List[str] = typer.Option(
        [],
        "--params",
        "-p",
        help="Parameters as key=value (repeatable)",
    ),
    filters: List[str] = typer.Option(
        [],
        "--filter",
        "-f",
        help="Filters as 'column op value' (repeatable)",
    ),
    no_cache: bool = typer.Option(
        False,
        "--no-cache",
        help="Disable cache for this request",
    ),
    force_refresh: bool = typer.Option(
        False,
        "--force-refresh",
        help="Force cache refresh",
    ),
    output_format: str = typer.Option(
        "summary",
        "--format",
        "-o",
        help="Output format: 'summary', 'json', 'table'",
    ),
    limit: Optional[int] = typer.Option(
        None,
        "--limit",
        "-l",
        help="Limit number of rows to display",
    ),
):
    """Fetch data from an endpoint."""
    from nba_api_mcp.data.unified_fetch import unified_fetch

    # Parse params
    parsed_params = {}
    for kv in params:
        if "=" not in kv:
            console.print(f"[red]Invalid param format: '{kv}'. Use key=value[/red]")
            raise typer.Exit(1)
        key, value = kv.split("=", 1)
        # Try to parse as JSON, fallback to string
        try:
            parsed_params[key] = json.loads(value)
        except Exception:
            parsed_params[key] = value

    # Parse filters
    parsed_filters = {}
    for filter_str in filters:
        parts = filter_str.split()
        if len(parts) < 3:
            console.print(
                f"[red]Invalid filter: '{filter_str}'. Use: COLUMN OPERATOR VALUE[/red]"
            )
            raise typer.Exit(1)

        col, op, *val_parts = parts
        val = " ".join(val_parts)

        # Try to parse value as JSON
        try:
            val = json.loads(val)
        except Exception:
            pass

        parsed_filters[col] = [op.upper(), val]

    # Run fetch
    async def run():
        try:
            result = await unified_fetch(
                endpoint=endpoint,
                params=parsed_params,
                filters=parsed_filters or None,
                use_cache=not no_cache,
                force_refresh=force_refresh,
            )

            # Output
            if output_format == "json":
                data_dict = result.data.to_pydict()
                if limit:
                    # Limit each column
                    data_dict = {k: v[:limit] for k, v in data_dict.items()}
                console.print_json(data=data_dict)

            elif output_format == "table":
                _display_data_table(result.data, limit=limit)

            else:  # summary
                _display_fetch_summary(result, limit=limit)

        except Exception as e:
            console.print(f"[red]Error:[/red] {str(e)}")
            if "--debug" in sys.argv:
                import traceback

                traceback.print_exc()
            raise typer.Exit(1)

    asyncio.run(run())


def _display_fetch_summary(result, limit=None):
    """Display fetch result summary."""
    console.print(f"\n[bold green]✓ Fetch successful[/bold green]\n")

    console.print(f"[bold]Rows:[/bold] {result.data.num_rows}")
    console.print(f"[bold]Columns:[/bold] {result.data.num_columns}")
    console.print(f"[bold]From cache:[/bold] {result.from_cache}")
    console.print(f"[bold]Execution time:[/bold] {result.execution_time_ms:.2f}ms")

    if result.warnings:
        console.print(f"\n[yellow]Warnings:[/yellow]")
        for warn in result.warnings:
            console.print(f"  - {warn}")

    if result.transformations:
        console.print(f"\n[dim]Transformations applied:[/dim]")
        for trans in result.transformations:
            console.print(f"  - {trans}")

    # Show sample data
    if result.data.num_rows > 0:
        console.print(f"\n[bold]Sample data:[/bold]")
        _display_data_table(result.data, limit=limit or 5)


def _display_data_table(data, limit=None):
    """Display PyArrow table as Rich table."""
    # Convert to pandas for easier display
    import pandas as pd

    df = data.to_pandas()

    if limit:
        df = df.head(limit)

    # Create Rich table
    table = Table(show_header=True, header_style="bold")

    for col in df.columns:
        table.add_column(str(col))

    for _, row in df.iterrows():
        table.add_row(*[str(val) for val in row])

    console.print(table)

    if data.num_rows > (limit or len(df)):
        console.print(
            f"\n[dim]Showing {len(df)} of {data.num_rows} rows. Use --limit to see more.[/dim]"
        )


# ============================================================================
# BATCH COMMAND
# ============================================================================


@app.command(
    help="""
    Fetch multiple endpoints in parallel.

    Accepts a JSON array of fetch specifications.

    Examples:
        nba-mcp batch '[{"endpoint":"league_leaders","params":{"stat_category":"PTS"}}]'

        nba-mcp batch '[
            {"endpoint":"player_career_stats","params":{"player_name":"LeBron"}},
            {"endpoint":"team_standings","params":{"season":"2023-24"}}
        ]'
    """
)
def batch(
    specs: str = typer.Argument(
        ...,
        help="JSON array of fetch specifications",
    ),
    max_concurrent: int = typer.Option(
        5,
        "--concurrent",
        "-c",
        help="Maximum concurrent requests",
    ),
):
    """Execute multiple fetches in parallel."""
    from nba_api_mcp.data.unified_fetch import batch_fetch

    # Parse specs
    try:
        parsed_specs = json.loads(specs)
    except json.JSONDecodeError as e:
        console.print(f"[red]Invalid JSON:[/red] {e}")
        raise typer.Exit(1)

    if not isinstance(parsed_specs, list):
        console.print("[red]Specs must be a JSON array[/red]")
        raise typer.Exit(1)

    # Run batch fetch
    async def run():
        try:
            with console.status(
                f"[bold green]Fetching {len(parsed_specs)} endpoints..."
            ):
                results = await batch_fetch(parsed_specs, max_concurrent=max_concurrent)

            # Display results
            console.print(f"\n[bold green]✓ Batch fetch complete[/bold green]\n")

            table = Table(show_header=True, header_style="bold")
            table.add_column("#", style="dim")
            table.add_column("Endpoint", style="cyan")
            table.add_column("Rows", justify="right")
            table.add_column("Time (ms)", justify="right")
            table.add_column("Cache", justify="center")

            for i, result in enumerate(results, 1):
                cache_icon = "✓" if result.from_cache else "✗"
                table.add_row(
                    str(i),
                    parsed_specs[i - 1]["endpoint"],
                    str(result.data.num_rows),
                    f"{result.execution_time_ms:.2f}",
                    cache_icon,
                )

            console.print(table)

        except Exception as e:
            console.print(f"[red]Error:[/red] {str(e)}")
            if "--debug" in sys.argv:
                import traceback

                traceback.print_exc()
            raise typer.Exit(1)

    asyncio.run(run())


# ============================================================================
# CONFIG COMMAND
# ============================================================================


@app.command(
    help="""
    Show current configuration.

    Displays all configuration values from environment variables and .env file.
    """
)
def config(
    json_out: bool = typer.Option(
        False,
        "--json",
        help="Output as JSON",
    ),
):
    """Show current configuration."""
    from nba_api_mcp.config import settings

    config_dict = settings.model_dump()

    if json_out:
        console.print_json(data=config_dict)
    else:
        console.print("\n[bold]NBA MCP Configuration[/bold]\n")

        # Group by category
        categories = {
            "Server": ["NBA_MCP_PORT", "MCP_HOST", "MCP_TRANSPORT", "ENVIRONMENT"],
            "Logging": ["NBA_MCP_LOG_LEVEL", "LOG_FORMAT"],
            "Redis Cache": [
                "ENABLE_REDIS_CACHE",
                "REDIS_HOST",
                "REDIS_PORT",
                "REDIS_DB",
                "REDIS_URL",
            ],
            "Rate Limiting": [
                "NBA_MCP_DAILY_QUOTA",
                "NBA_MCP_SIMPLE_RATE_LIMIT",
                "NBA_MCP_COMPLEX_RATE_LIMIT",
            ],
            "Observability": ["ENABLE_METRICS", "ENABLE_TRACING", "OTLP_ENDPOINT"],
            "LLM": [
                "NBA_MCP_ENABLE_LLM_FALLBACK",
                "NBA_MCP_LLM_MODEL",
                "NBA_MCP_LLM_URL",
            ],
            "Concurrency": [
                "NBA_MCP_MAX_CONCURRENT_LIVE",
                "NBA_MCP_MAX_CONCURRENT_STANDARD",
                "NBA_MCP_MAX_CONCURRENT_HEAVY",
            ],
        }

        for category, keys in categories.items():
            console.print(f"[bold cyan]{category}:[/bold cyan]")
            for key in keys:
                if key in config_dict:
                    value = config_dict[key]
                    # Mask sensitive values
                    if "URL" in key and value and isinstance(value, str):
                        if "://" in value:
                            value = value.split("://")[0] + "://***"
                    console.print(f"  {key}: [green]{value}[/green]")
            console.print()


# ============================================================================
# VERSION COMMAND
# ============================================================================


@app.command(help="Show version information")
def version():
    """Show version information."""
    try:
        import importlib.metadata

        version = importlib.metadata.version("nba-mcp")
    except Exception:
        version = "unknown"

    console.print(f"\n[bold]NBA MCP[/bold] version [cyan]{version}[/cyan]")
    console.print("NBA data via Model Context Protocol\n")


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    app()
