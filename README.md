# NBA MCP Server

A production-ready MCP (Model Context Protocol) server that provides comprehensive NBA data access through a standardized API interface. Built on top of the official NBA API with advanced features including caching, rate limiting, metrics collection, and a powerful unified data fetching system.

```
┌─────────────────────────────────────────────────────────────────┐
│                        NBA MCP Server                           │
│                                                                 │
│  Claude Desktop  ←→  MCP Protocol  ←→  Unified Fetch System    │
│  VS Code/Cursor  ←→  FastMCP      ←→  NBA API Client           │
│  Custom Client   ←→  HTTP/Stdio   ←→  Redis Cache + Filters   │
│                                                                 │
│  📊 50+ Endpoints  │  🔍 Fuzzy Matching  │  ⚡ Sub-ms Cache    │
│  🎯 Smart Filters  │  🔗 Batch Queries   │  📈 Metrics/Tracing │
└─────────────────────────────────────────────────────────────────┘
```

## Table of Contents

- [Features](#features)
- [Quick Start](#quick-start)
- [Unified Data Fetching System](#-unified-data-fetching-system)
  - [Basic Usage](#basic-usage)
  - [Advanced Filtering](#advanced-filtering)
  - [Batch Fetching](#batch-fetching-parallel-execution)
  - [Available Endpoints](#available-endpoints)
- [Configuration & Setup](#-configuration--setup)
- [Using the NBA MCP Tool](#-using-the-nba-mcp-tool)
  - [In Claude Desktop](#in-claude-desktop)
  - [Available MCP Tools](#available-mcp-tools)
  - [Example Conversations](#example-conversations)
- [Development](#development)
- [Monitoring & Observability](#monitoring--observability)
- [Quick Reference](#-quick-reference)

## Features

- **🎯 Unified Data Fetching**: Single `unified_fetch()` function to access any NBA dataset with flexible filtering and granularity control
- **⚡ Real-time & Historical Data**: Live scores, game stats, player/team information, and historical records
- **📊 Advanced Analytics**: Team and player advanced statistics, era-adjusted comparisons, shot charts
- **💬 Natural Language Queries**: Ask questions in plain English (e.g., "Who leads the NBA in assists?")
- **🎮 Game Context**: Rich pre-game analysis with standings, form, head-to-head, and narrative synthesis
- **🚀 Production Infrastructure**: Redis caching, rate limiting, Prometheus metrics, OpenTelemetry tracing
- **🔍 Entity Resolution**: Fuzzy matching for player and team names with confidence scoring
- **🛡️ Robust Error Handling**: Retry logic, circuit breakers, graceful degradation
- **🔗 Batch Operations**: Fetch multiple datasets in parallel for maximum efficiency

## Quick Start

### ⚡ Try in 30 Seconds

```bash
# Install via pipx (recommended) or pip
pipx install nba-mcp
# OR: pip install nba-mcp

# Start the server
nba-mcp serve --mode claude

# In another terminal, try fetching data
nba-mcp fetch league_leaders --params stat_category=PTS season=2024-25 --filter "PTS >= 25"

# Browse available endpoints
nba-mcp catalog

# Show configuration
nba-mcp config
```

### 🐳 Docker Quick Start

```bash
# Clone and start with docker-compose
git clone https://github.com/ghadfield32/nba_mcp.git
cd nba_mcp
docker-compose up -d

# The server is now running with Redis caching at http://localhost:8000
```

### Prerequisites

- Python 3.10 or higher
- Git
- (Optional) Redis for caching
- (Optional) Ollama for local LLM usage
- (Optional) Docker for containerized deployment

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/ghadfield32/nba_mcp.git
cd nba_mcp
```

2. **Create and activate a virtual environment**
```bash
# Using UV (recommended)
pip install uv
uv venv nbavenv

# Activate on Windows
.\nbavenv\Scripts\activate

# Activate on Unix/MacOS
source nbavenv/bin/activate
```

3. **Install dependencies**
```bash
# Using uv (resolves deps from pyproject.toml / uv.lock)
uv sync --extra dev

# Or use pip directly (editable install with dev extras)
pip install -e ".[dev]"
```

4. **Configure environment (optional)**
```bash
# Copy example env file and customize
cp .env.example .env
# Edit .env with your preferred settings
```

### Running the Server

**New CLI (Recommended)**
```bash
# Start server with CLI
nba-mcp serve --mode claude

# Or with custom port
nba-mcp serve --mode local --port 8005
```

**Traditional Method**
```bash
# Claude Desktop Mode (Port 8000)
python -m nba_mcp.nba_server --mode claude

# Local LLM Mode (Port 8001)
python -m nba_mcp.nba_server --mode local
```

**Docker Deployment**
```bash
# Basic deployment with Redis
docker-compose up -d

# With monitoring (Prometheus + Grafana)
docker-compose --profile monitoring up -d
```

The server will start and display available tools and configuration.

---

## 🎯 Unified Data Fetching System

The heart of this MCP server is the **`unified_fetch()`** function - a powerful, flexible API for retrieving any NBA dataset with advanced filtering and granularity control.

### Why Use unified_fetch?

Instead of memorizing dozens of different API endpoints and their specific parameters, you can use a single function to access all NBA data:

- ✅ **Single Interface**: One function for all endpoints
- ✅ **Flexible Filtering**: Apply filters using simple syntax
- ✅ **Entity Resolution**: Use player/team names instead of IDs
- ✅ **Auto-Caching**: Intelligent caching for performance
- ✅ **Batch Operations**: Fetch multiple datasets in parallel
- ✅ **Type-Safe**: Full type hints and validation

### Basic Usage

```python
from nba_api_mcp.data.unified_fetch import unified_fetch
import asyncio

# Simple fetch - get player career stats
async def get_lebron_stats():
    result = await unified_fetch(
        endpoint="player_career_stats",
        params={"player_name": "LeBron James"}
    )

    print(f"Fetched {result.data.num_rows} rows")
    print(f"Execution time: {result.execution_time_ms:.2f}ms")
    print(f"From cache: {result.from_cache}")

    # Access the data as PyArrow Table
    data = result.data

    # Or convert to tuple format
    data, provenance = result.to_tuple()

asyncio.run(get_lebron_stats())
```

### Advanced Filtering

Apply filters to any dataset using a simple, intuitive syntax:

```python
# Filter team game log for wins with 110+ points
result = await unified_fetch(
    endpoint="team_game_log",
    params={"team": "Lakers", "season": "2023-24"},
    filters={
        "WL": ["==", "W"],           # Only wins
        "PTS": [">=", 110],          # Scored 110+ points
        "FG_PCT": [">", 0.5]         # Shooting over 50%
    }
)

# Use IN operator for multiple values
result = await unified_fetch(
    endpoint="team_standings",
    params={"season": "2023-24"},
    filters={
        "team_abbreviation": ["IN", ["LAL", "GSW", "BOS"]]
    }
)

# Use BETWEEN for ranges
result = await unified_fetch(
    endpoint="player_game_logs",
    params={"player_name": "Stephen Curry", "season": "2023-24"},
    filters={
        "PTS": ["BETWEEN", [25, 40]],  # Scored between 25-40 points
        "FG3M": [">=", 5]               # Made 5+ threes
    }
)
```

#### Supported Filter Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `==` or `=` | Equal to | `{"WL": ["==", "W"]}` |
| `!=` | Not equal to | `{"conference": ["!=", "East"]}` |
| `>` | Greater than | `{"PTS": [">", 20]}` |
| `>=` | Greater than or equal | `{"PTS": [">=", 20]}` |
| `<` | Less than | `{"TOV": ["<", 3]}` |
| `<=` | Less than or equal | `{"TOV": ["<=", 3]}` |
| `IN` | Value in list | `{"TEAM": ["IN", ["LAL", "GSW"]]}` |
| `BETWEEN` | Between two values | `{"PTS": ["BETWEEN", [20, 30]]}` |
| `LIKE` | Pattern matching | `{"PLAYER_NAME": ["LIKE", "%James%"]}` |

### Batch Fetching (Parallel Execution)

Fetch multiple datasets simultaneously for maximum efficiency:

```python
from nba_api_mcp.data.unified_fetch import batch_fetch

# Fetch multiple datasets in parallel
results = await batch_fetch([
    {
        "endpoint": "player_career_stats",
        "params": {"player_name": "LeBron James"}
    },
    {
        "endpoint": "player_career_stats",
        "params": {"player_name": "Stephen Curry"}
    },
    {
        "endpoint": "team_standings",
        "params": {"season": "2023-24"}
    },
    {
        "endpoint": "league_leaders",
        "params": {"stat_category": "PTS"},
        "filters": {"PTS": [">=", 25]}
    }
])

# Process results
for i, result in enumerate(results):
    print(f"Query {i+1}: {result.data.num_rows} rows in {result.execution_time_ms:.2f}ms")
```

### Available Endpoints

Here are the most commonly used endpoints:

#### 🏀 Player Statistics
- `player_career_stats` - Career statistics across all seasons
- `player_game_logs` - Game-by-game stats for a player
- `player_advanced_stats` - Advanced metrics (TS%, Usage%, PER, etc.)

#### 🏆 Team Statistics
- `team_standings` - Conference and division standings
- `team_game_log` - Team game history
- `team_advanced_stats` - Team efficiency metrics

#### 📈 League Data
- `league_leaders` - League leaders in any statistical category
- `league_game_log` - All games across the league

#### 🎯 Game Data
- `live_scoreboard` - Live scores and game status
- `play_by_play` - Detailed play-by-play data
- `box_score` - Traditional box score stats

#### 📊 Advanced Analytics
- `shot_chart` - Shot location data with hexagonal binning
- `player_tracking` - Player tracking and hustle stats

For a complete list of endpoints, see the [Data Catalog](nba_api_mcp/data/catalog.py).

### Parameter Reference

Common parameters across endpoints:

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `player_name` | string | Player name (fuzzy match) | `"LeBron James"` |
| `team` or `team_name` | string | Team name or abbreviation | `"Lakers"` or `"LAL"` |
| `season` | string | NBA season | `"2023-24"` |
| `date_from` | string | Start date | `"2024-01-01"` |
| `date_to` | string | End date | `"2024-03-01"` |
| `stat_category` | string | Statistical category | `"PTS"`, `"AST"`, `"REB"` |
| `per_mode` | string | Stat calculation mode | `"PerGame"`, `"Totals"` |

### Working with Results

The `UnifiedFetchResult` object provides rich metadata:

```python
result = await unified_fetch(
    endpoint="player_career_stats",
    params={"player_name": "LeBron James"}
)

# Access the data (PyArrow Table)
data = result.data
print(f"Rows: {data.num_rows}")
print(f"Columns: {data.num_columns}")

# Performance metrics
print(f"Execution time: {result.execution_time_ms:.2f}ms")
print(f"From cache: {result.from_cache}")

# Provenance tracking
print(f"Source endpoints: {result.provenance.source_endpoints}")
print(f"Operations: {result.provenance.operations}")
print(f"Parameters: {result.provenance.parameters}")

# Warnings and transformations
if result.warnings:
    print(f"Warnings: {result.warnings}")
if result.transformations:
    print(f"Transformations: {result.transformations}")

# Convert to pandas DataFrame
df = data.to_pandas()

# Or get as tuple for backward compatibility
data, provenance = result.to_tuple()
```

### Filter Pushdown Optimization

The system automatically optimizes queries by pushing filters down to the API level when possible:

```python
# This filter will be pushed to the API level (faster)
result = await unified_fetch(
    endpoint="player_game_logs",
    params={"player_name": "Stephen Curry"},
    filters={
        "date_from": [">=", "2024-01-01"],  # ✅ Pushed to API
        "date_to": ["<=", "2024-03-01"]     # ✅ Pushed to API
    }
)

# These filters are applied post-fetch using DuckDB (still fast)
result = await unified_fetch(
    endpoint="player_game_logs",
    params={"player_name": "Stephen Curry"},
    filters={
        "PTS": [">=", 30],              # Applied post-fetch
        "FG3M": [">=", 5],              # Applied post-fetch
        "PLUS_MINUS": [">", 10]         # Applied post-fetch
    }
)
```

Check the transformation log to see which filters were pushed:
```python
print(result.transformations)
# Output: ['Pushed 2 filter(s) to API: [\'date_from\', \'date_to\']']
```

### Cache Control

Control caching behavior per request:

```python
# Use cache (default)
result = await unified_fetch(
    endpoint="player_career_stats",
    params={"player_name": "LeBron James"},
    use_cache=True
)

# Disable cache for this request
result = await unified_fetch(
    endpoint="live_scoreboard",
    params={"target_date": "2024-03-15"},
    use_cache=False
)

# Force refresh even if cached
result = await unified_fetch(
    endpoint="team_standings",
    params={"season": "2023-24"},
    force_refresh=True
)
```

---

## 🔧 Configuration & Setup

### Setting Up the NBA MCP Tool

The NBA MCP server can be used with Claude Desktop, VS Code with Claude Code, Cursor, or any MCP-compatible client.

#### Option 1: Claude Desktop (Recommended for Chat)

1. **Locate your Claude Desktop config file:**
   - **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
   - **MacOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`

2. **Add the NBA MCP server configuration:**

   ```json
   {
     "mcpServers": {
       "nba": {
         "command": "python",
         "args": ["-m", "nba_api_mcp.nba_server", "--mode", "claude"],
         "env": {
           "PYTHONPATH": "C:\\path\\to\\nba_api_mcp"
         }
       }
     }
   }
   ```

   **Important**: Replace `C:\\path\\to\\nba_api_mcp` with the actual path to your installation.

3. **Restart Claude Desktop**

4. **Verify the connection:**
   - Open Claude Desktop
   - Look for the 🔌 MCP icon in the bottom right
   - The NBA server should appear in the list of connected servers

#### Option 2: VS Code with Claude Code

1. **Locate your MCP configuration file:**
   - **Windows**: `%APPDATA%\Code\User\mcp.json`
   - **macOS/Linux**: `~/.config/Code/User/mcp.json`

2. **Add the NBA MCP server:**

   ```json
   {
     "mcpServers": {
       "nba": {
         "command": "python",
         "args": ["-m", "nba_api_mcp.nba_server", "--mode", "local"],
         "env": {
           "PYTHONPATH": "C:\\path\\to\\nba_api_mcp"
         }
       }
     }
   }
   ```

3. **Restart VS Code**

#### Option 3: Cursor IDE

1. **Locate your Cursor MCP configuration file:**
   - **Windows**: `%APPDATA%\Cursor\User\mcp.json`
   - **macOS/Linux**: `~/.config/Cursor/User/mcp.json`

2. **Add the same configuration as VS Code**

3. **Restart Cursor**

#### Option 4: Remote Server Mode (HTTP)

For advanced setups or remote access:

1. **Start the server manually:**
   ```bash
   python -m nba_api_mcp.nba_server --mode local
   ```

2. **Configure your MCP client to connect via HTTP:**
   ```json
   {
     "mcpServers": {
       "nba": {
         "url": "http://localhost:8000"
       }
     }
   }
   ```

### Environment Variables

Configure optional features through environment variables:

```bash
# Server configuration
export NBA_MCP_PORT=8000
export NBA_MCP_LOG_LEVEL=INFO

# Redis caching (optional)
export REDIS_HOST=localhost
export REDIS_PORT=6379
export REDIS_DB=0
export ENABLE_REDIS_CACHE=true

# Rate limiting
export NBA_MCP_DAILY_QUOTA=10000
export NBA_MCP_SIMPLE_RATE_LIMIT=60
export NBA_MCP_COMPLEX_RATE_LIMIT=30

# Observability (optional)
export ENABLE_METRICS=true
export ENABLE_TRACING=false
export OTLP_ENDPOINT=http://localhost:4317
```

---

## 🎮 Using the NBA MCP Tool

Once configured, you can interact with the NBA MCP server through your MCP client (Claude Desktop, VS Code, etc.). The server provides a comprehensive set of tools for querying NBA data.

### In Claude Desktop

Simply ask Claude natural language questions about NBA data:

```
You: "What are the current NBA standings for the Western Conference?"

Claude: [Uses get_team_standings tool to fetch data]
Here are the current Western Conference standings...
```

```
You: "Show me LeBron James' stats from last season"

Claude: [Uses get_player_career_information tool]
LeBron James' 2023-24 season statistics:
- Games: 71
- PPG: 25.7
- RPG: 7.3
- APG: 8.3
...
```

### Available MCP Tools

The server exposes these tools through the MCP protocol:

#### 📊 Game Information

**`get_live_scores`**
- Get current or historical game scores
- Parameters: `target_date` (optional, defaults to today)
- Example: "Show me the scores from yesterday"

**`play_by_play`**
- Detailed play-by-play data for a specific game
- Parameters: `game_id`
- Example: "Get the play-by-play for game 0022300515"

**`get_game_context`**
- Rich pre-game analysis with standings, form, head-to-head
- Parameters: `team1_name`, `team2_name`, `season`
- Example: "Give me context for the Lakers vs Warriors game"

#### 🏀 Player Statistics

**`get_player_career_information`**
- Comprehensive career statistics for a player
- Parameters: `player_name`, `seasons` (optional)
- Example: "Get LeBron James' career stats"

**`get_player_advanced_stats`**
- Advanced metrics (TS%, Usage%, eFG%, PER, etc.)
- Parameters: `player_name`, `season`
- Example: "What's Stephen Curry's true shooting percentage?"

**`compare_players`**
- Head-to-head comparison of two players
- Parameters: `player1_name`, `player2_name`, `stat_categories`
- Example: "Compare Giannis and Embiid in points and rebounds"

**`compare_players_era_adjusted`**
- Cross-era comparisons with statistical adjustments
- Parameters: `player1_name`, `player2_name`
- Example: "Compare Michael Jordan and LeBron James across eras"

#### 🏆 Team Statistics

**`get_team_standings`**
- Conference and division standings
- Parameters: `season`, `conference` (optional)
- Example: "What are the Eastern Conference standings?"

**`get_team_advanced_stats`**
- Team efficiency metrics
- Parameters: `team_name`, `season`
- Example: "Show me the Celtics' advanced stats"

**`get_date_range_game_log_or_team_game_log`**
- Team game history within a date range
- Parameters: `team_name`, `season`, `date_from`, `date_to`
- Example: "Get Lakers games from January to March"

#### 📈 League Data

**`get_league_leaders_info`**
- League leaders in any statistical category
- Parameters: `stat_category`, `per_mode`, `season`
- Example: "Who leads the league in assists?"

#### 🎯 Shot Charts

**`get_shot_chart`**
- Shot location data with hexagonal binning
- Parameters: `player_or_team_name`, `season`, `granularity`
- Example: "Show me Stephen Curry's shot chart"

#### 💬 Natural Language Queries

**`answer_nba_question`**
- Ask questions in plain English
- Parameters: `question`
- The tool will automatically:
  - Parse your question
  - Determine which data to fetch
  - Execute the appropriate queries
  - Synthesize a natural language response

**Supported question types:**
- "Who leads the NBA in assists this season?"
- "Compare LeBron James and Michael Jordan career stats"
- "What are the Lakers standings?"
- "Show me Stephen Curry's shooting stats"
- "Who scored the most points last night?"

#### 🔍 Entity Resolution

**`resolve_nba_entity`**
- Fuzzy matching for player and team names
- Parameters: `entity_name`, `entity_type` (player/team)
- Automatically handles:
  - Typos and misspellings
  - Partial names
  - Common nicknames
  - Team abbreviations

### Example Conversations

#### Getting Live Scores

```
You: What games are on today?

Claude: [Calls get_live_scores()]
Today's NBA games:
1. Lakers vs Warriors (7:30 PM PT) - Live: GSW 98, LAL 95 (Q3)
2. Celtics vs Heat (7:00 PM ET) - Final: BOS 112, MIA 103
3. Nuggets vs Suns (8:00 PM MT) - Upcoming
```

#### Player Analysis

```
You: Show me Giannis Antetokounmpo's stats this season

Claude: [Calls get_player_career_information(player_name="Giannis Antetokounmpo", seasons=["2024-25"])]
Giannis Antetokounmpo 2024-25 Season:
- Games Played: 45
- PPG: 30.8
- RPG: 11.2
- APG: 6.1
- FG%: 61.2%
- Advanced: 65.3 TS%, 34.2 USG%, 28.5 PER
```

#### Team Standings

```
You: What are the current Western Conference standings?

Claude: [Calls get_team_standings(season="2024-25", conference="West")]
Western Conference Standings:
1. Thunder (35-8) - 81.4%
2. Nuggets (32-11) - 74.4%
3. Grizzlies (31-12) - 72.1%
...
```

#### Comparative Analysis

```
You: Compare Luka Doncic and Shai Gilgeous-Alexander this season

Claude: [Calls compare_players(player1_name="Luka Doncic", player2_name="Shai Gilgeous-Alexander", stat_categories=["PTS", "AST", "REB"])]

Luka Doncic vs Shai Gilgeous-Alexander (2024-25):

Points per game:
- Luka: 28.9
- SGA: 30.3 ✓

Assists per game:
- Luka: 8.2 ✓
- SGA: 5.6

Rebounds per game:
- Luka: 8.3 ✓
- SGA: 5.7
```

### Tips for Best Results

1. **Be Specific**: Include season years, player full names when possible
2. **Use Natural Language**: The tools support fuzzy matching - "Lebron" works just as well as "LeBron James"
3. **Combine Tools**: Ask complex questions that require multiple data sources
4. **Check Availability**: Use the MCP tools menu to see all available functions

### Programmatic Usage

You can also use the tools programmatically through the MCP protocol:

```python
from nba_api_mcp.nba_server import mcp

# Example: Call a tool directly
result = await mcp.call_tool(
    "get_player_career_information",
    {
        "player_name": "LeBron James",
        "seasons": ["2023-24"]
    }
)
```

---

### Working with Local LLMs (Ollama)

1. **Pull an Ollama model**
```bash
ollama pull llama3.2:3b
```

2. **Start the NBA MCP server in local mode**
```bash
python -m nba_mcp.nba_server --mode local
```

3. **Run the example agent**
```bash
python examples/langgraph_ollama_agent_w_tools.py --mode local
```

4. **Interact with the agent**
```
Enter a question:
> who leads the nba in assists this season?

AIMessage: Let me check the league leaders for assists this season.
ToolMessage: [League leaders data for assists...]
AIMessage: Based on the data, Tyrese Haliburton leads the NBA in assists...
```

## Development

### Running Tests

```bash
# Run all tests
pytest tests/

# Run specific test categories
pytest tests/test_api_client.py
pytest tests/api/test_live_scores.py
pytest tests/api/test_player_stats.py

# Run integration tests
pytest tests/integration/

# Run with coverage
pytest --cov=nba_mcp --cov-report=html tests/
```

### Validation Script

Run the comprehensive validation suite:

```bash
python run_validation.py
```

This runs 23 core tests covering:
- Entity resolution
- Live data fetching
- Player and team statistics
- Advanced analytics
- Comparisons
- Shot charts
- Natural language queries

### Code Quality

```bash
# Format code
black nba_api_mcp/
isort nba_api_mcp/

# Type checking
mypy nba_api_mcp/

# Linting
flake8 nba_api_mcp/
```

## Monitoring & Observability

### Metrics Endpoint

When metrics are enabled, access Prometheus metrics at:

```
http://localhost:8000/metrics
```

Includes 14 metric types:
- Request counts and durations
- Error rates by type
- Cache hit/miss rates
- Rate limit usage
- Tool execution times

### Grafana Dashboard

A pre-built Grafana dashboard is available in `grafana/`:

```bash
# Start Grafana (with Docker)
cd grafana
docker-compose up -d

# Access at http://localhost:3000
# Default credentials: admin/admin
```

## Performance

- **Cache Performance**: 410x speedup with Redis (820ms → 2ms for cached responses)
- **Parallel Execution**: Game context composition uses 4x parallel API calls
- **Rate Limits**:
  - Simple tools: 60 requests/minute
  - Complex tools: 30 requests/minute
  - Multi-API tools: 20 requests/minute
  - Global quota: 10,000 requests/day

## Troubleshooting

### Common Issues

**1. Module Not Found Errors**
```bash
# Ensure PYTHONPATH is set correctly
export PYTHONPATH=/path/to/nba_mcp

# Or reinstall in development mode
pip install -e .
```

**2. API Rate Limiting**
```bash
# Check rate limit status in logs
# Reduce request frequency
# Wait for quota reset (daily)
```

**3. Redis Connection Issues**
```bash
# Verify Redis is running
redis-cli ping

# Or disable Redis caching
export ENABLE_REDIS_CACHE=false
```

**4. NBA API Errors**
```python
# The NBA API can be flaky
# The server includes automatic retries with exponential backoff
# Check logs for specific error details
```

### Debug Mode

Enable detailed logging:

```bash
export NBA_MCP_LOG_LEVEL=DEBUG
python -m nba_mcp.nba_server --mode claude
```

### Verify Installation

```bash
# Check Python version
python --version  # Should be 3.10+

# Verify dependencies
pip list | grep nba_api
pip list | grep fastmcp

# Test API connectivity
python -c "from nba_api.stats.static import players; print(len(players.get_players()))"
```

## Architecture

```
NBA MCP Server
├── nba_server.py           # Main FastMCP server
├── api/                    # Core API layer
│   ├── client.py           # NBA API client
│   ├── advanced_stats.py   # Advanced statistics
│   ├── entity_resolver.py  # Fuzzy entity matching
│   ├── shot_charts.py      # Shot chart data
│   ├── game_context.py     # Multi-source composition
│   ├── era_adjusted.py     # Cross-era adjustments
│   └── tools/              # API utilities
├── nlq/                    # Natural language processing
│   ├── parser.py           # Query parsing
│   ├── planner.py          # Query planning
│   ├── executor.py         # Parallel execution
│   └── synthesizer.py      # Response formatting
├── cache/                  # Redis caching layer
├── rate_limit/             # Token bucket rate limiting
├── observability/          # Metrics and tracing
└── schemas/                # Pydantic models and schemas
```

## API Response Format

All tools return a standardized response envelope:

```json
{
  "status": "success",
  "data": { ... },
  "metadata": {
    "version": "v1",
    "schema_version": "2025-01",
    "timestamp": "2024-03-15T10:30:00Z",
    "source": "nba_api",
    "cached": true,
    "cache_ttl": 3600
  },
  "errors": []
}
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Make your changes
4. Run tests (`pytest tests/`)
5. Format code (`black nba_api_mcp/ && isort nba_api_mcp/`)
6. Commit your changes (`git commit -m "Add your feature"`)
7. Push to the branch (`git push origin feature/your-feature`)
8. Open a Pull Request

## License

MIT License - See LICENSE file for details

## Acknowledgments

- Built on [nba_api](https://github.com/swar/nba_api) by Swar Patel
- Powered by [FastMCP](https://github.com/fastmcp/fastmcp) framework
- NBA data provided by [NBA.com](https://www.nba.com/)

---

## 📚 Quick Reference

### Common Commands

```bash
# Install dependencies
uv sync --extra dev
# or
pip install -e ".[dev]"

# Start server for Claude Desktop
python -m nba_api_mcp.nba_server --mode claude

# Start server for local LLMs
python -m nba_api_mcp.nba_server --mode local

# Run tests
pytest tests/

# Run validation
python run_validation.py

# Format code
black nba_api_mcp/ && isort nba_api_mcp/
```

### Unified Fetch Cheat Sheet

```python
from nba_api_mcp.data.unified_fetch import unified_fetch, batch_fetch

# Basic fetch
result = await unified_fetch("player_career_stats", {"player_name": "LeBron James"})

# With filters
result = await unified_fetch(
    "team_game_log",
    {"team": "Lakers", "season": "2023-24"},
    filters={"WL": ["==", "W"], "PTS": [">=", 110]}
)

# Batch fetch
results = await batch_fetch([
    {"endpoint": "player_career_stats", "params": {"player_name": "LeBron"}},
    {"endpoint": "team_standings", "params": {"season": "2023-24"}},
])

# Cache control
result = await unified_fetch(..., use_cache=False)  # Disable cache
result = await unified_fetch(..., force_refresh=True)  # Force refresh
```

### Filter Operators Quick Reference

```python
# Equality
{"WL": ["==", "W"]}               # Equal to
{"conference": ["!=", "East"]}    # Not equal to

# Comparison
{"PTS": [">", 20]}                # Greater than
{"PTS": [">=", 20]}               # Greater than or equal
{"TOV": ["<", 3]}                 # Less than
{"TOV": ["<=", 3]}                # Less than or equal

# Lists and Patterns
{"TEAM": ["IN", ["LAL", "GSW"]]}  # In list
{"PTS": ["BETWEEN", [20, 30]]}    # Between values
{"PLAYER_NAME": ["LIKE", "%James%"]}  # Pattern match
```

### Most Common Endpoints

```python
# Player Data
"player_career_stats"       # Career statistics
"player_game_logs"          # Game-by-game logs
"player_advanced_stats"     # Advanced metrics

# Team Data
"team_standings"            # Standings
"team_game_log"            # Game history
"team_advanced_stats"      # Team efficiency

# League Data
"league_leaders"           # League leaders
"league_game_log"          # All games

# Game Data
"live_scoreboard"          # Live scores
"play_by_play"             # Play-by-play
"box_score"                # Box scores
```

### Configuration Files

```bash
# Claude Desktop Config
Windows: %APPDATA%\Claude\claude_desktop_config.json
macOS:   ~/Library/Application Support/Claude/claude_desktop_config.json

# VS Code / Cursor MCP Config
Windows: %APPDATA%\Code\User\mcp.json
         %APPDATA%\Cursor\User\mcp.json
macOS:   ~/.config/Code/User/mcp.json
         ~/.config/Cursor/User/mcp.json
```

### Environment Variables

```bash
# Essential
NBA_MCP_PORT=8000
NBA_MCP_LOG_LEVEL=INFO

# Redis Cache
REDIS_HOST=localhost
REDIS_PORT=6379
ENABLE_REDIS_CACHE=true

# Rate Limits
NBA_MCP_DAILY_QUOTA=10000
NBA_MCP_SIMPLE_RATE_LIMIT=60
NBA_MCP_COMPLEX_RATE_LIMIT=30

# Observability
ENABLE_METRICS=true
ENABLE_TRACING=false
```

### Troubleshooting Quick Fixes

```bash
# Module not found
export PYTHONPATH=/path/to/nba_api_mcp
pip install -e .

# Redis connection issues
redis-cli ping  # Check if Redis is running
export ENABLE_REDIS_CACHE=false  # Or disable Redis

# Check Python version
python --version  # Must be 3.10+

# Verify installation
python -c "from nba_api.stats.static import players; print(len(players.get_players()))"
```

---

## Support

For issues, questions, or feature requests:
- Open an issue on GitHub
- Check existing documentation in the repository
- Review the troubleshooting section above
- Consult the [Quick Reference](#-quick-reference) for common tasks
 
 
