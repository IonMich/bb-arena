# BuzzerBeater Arena Optimizer

A Python application for collecting, storing, and analyzing BuzzerBeater basketball game data including attendance, pricing, and revenue optimization.

## Features

- **API Integration**: Robust data collection from BuzzerBeater API with error handling
- **SQLite Storage**: Persistent storage of arena, pricing, and game data
- **Data Validation**: Game ID verification to ensure data integrity
- **Historical Analysis**: Track attendance patterns and revenue trends
- **Type Safety**: Full mypy compliance with strict type checking

## Quick Start

1. **Install Dependencies**:

   ```bash
   uv sync
   ```

2. **Configure Environment**:

   ```bash
   cp .env.example .env
   # Edit .env with your BuzzerBeater credentials:
   # BB_USERNAME=your_username
   # BB_SECURITY_CODE=your_security_code
   ```

3. **Collect Data**:

   ```bash
   uv run python -m bb_arena_optimizer.examples.data_collection_demo
   ```

4. **Inspect Database**:

   ```bash
   uv run python -m bb_arena_optimizer.examples.inspect_database
   ```

## Project Structure

```text
bb-arena/
├── src/bb_arena_optimizer/     # Main package
│   ├── api/                    # BuzzerBeater API client
│   ├── models/                 # Data models (Arena, Game, etc.)
│   ├── storage/               # Database and data collection
│   ├── examples/              # Usage examples and demos
│   └── utils/                 # Logging and utilities
├── tests/                     # Test files
└── bb_arena_data.db          # SQLite database (created after first run)
```

## Available Examples

- **`data_collection_demo.py`** - Collect and store current data snapshot
- **`inspect_database.py`** - View database contents and statistics  
- **`basic_analysis.py`** - Analyze stored data and trends
- **`complete_workflow.py`** - Full data collection and analysis workflow

## API Integration

The system uses the BuzzerBeater API with verified endpoints:

- `arena.aspx` - Arena configuration and seat pricing
- `schedule.aspx` - Team schedule and game information  
- `boxscore.aspx` - Game attendance and revenue data (with `matchid` parameter)
- `team.aspx` - Team information and details

## Data Integrity

The system includes robust data validation:

- Game ID verification to prevent storing incorrect data
- Date-based filtering to only collect completed games
- Fallback data detection and exclusion
- SQLite constraints and indexing for data consistency

## Development

```bash
# Install development dependencies
uv sync --dev

# Run tests
uv run pytest

# Type checking (strict mode)
uv run mypy src/

# Linting
uv run ruff check src/
```

## License

MIT License
