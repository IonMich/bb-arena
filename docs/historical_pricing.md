# Historical Arena Pricing Data Collection

This module provides functionality to collect historical arena pricing data from BuzzerBeater team arena pages. Unlike the API which only provides current pricing snapshots, these web pages contain:

1. **Last 10 official home game attendances** - with the pricing that was active during each game
2. **Historical ticket price changes** - a log of all price modifications over time

## Features

- **Respectful collection**: Configurable delays between requests to avoid overwhelming servers
- **Robust parsing**: Handles various HTML structures and data formats
- **Game matching**: Automatically matches collected games with stored database records
- **Comprehensive logging**: Detailed logging for monitoring and debugging
- **Batch processing**: Support for collecting data from multiple teams
- **Error handling**: Graceful handling of network issues and parsing errors

## Usage

### Command Line Script

The easiest way to collect historical pricing data is using the command-line script:

```bash
# Collect data for a single team
python scripts/collect_historical_pricing.py --team-id 12345

# Collect data for multiple teams
python scripts/collect_historical_pricing.py --team-ids 12345 67890 11111

# Use custom settings
python scripts/collect_historical_pricing.py --team-id 12345 --delay 2.0 --verbose
```

### Programmatic Usage

```python
from bb_arena_optimizer.collecting import HistoricalPricingService, TeamArenaCollector
from bb_arena_optimizer.storage.database import DatabaseManager

# Initialize services
db_manager = DatabaseManager("bb_arena_data.db")
pricing_service = HistoricalPricingService(db_manager)

# Collect data for a single team
result = pricing_service.collect_and_update_team_pricing("12345")

# Or use the collector directly
with TeamArenaCollector(request_delay=1.5) as collector:
    collection_result = collector.collect_team_arena_data("12345")
    if collection_result.success:
        print(f"Found {collection_result.last_10_games_found} games")
        print(f"Found {collection_result.price_changes_found} price changes")
```

### Integration with Existing Workflow

This functionality complements the existing API-based data collection:

1. **Use API for current data**: Continue using the BuzzerBeater API for real-time arena and pricing snapshots
2. **Use collection for historical context**: Use this collector to backfill pricing data for existing games
3. **Combine for comprehensive analysis**: The database now contains both attendance and the actual prices charged

## Enhanced Collection Features

The collector now supports enhanced collection that includes friendly games and other matches not shown on the arena webpage:

### Standard Collection

- Collects from the team's arena webpage
- Shows "Last 10 official games" only  
- Excludes friendly games and some tournament games

### Enhanced Collection Mode

- Collects from arena webpage PLUS database queries
- Finds additional home games (friendlies) within pricing periods
- Provides comprehensive coverage of all applicable games

```python
# Enhanced collection includes friendlies
with TeamArenaCollector() as collector:
    result = collector.collect_team_arena_data_enhanced(team_id, db_manager)
    
print(f"Official games: {result.last_10_games_found}")
print(f"Additional games (friendlies): {result.additional_games_found}")
```

## Configuration

### Request Delays

The collector includes configurable delays between requests to be respectful to the BuzzerBeater servers:

- **Single team**: Default 1.0 second delay
- **Multiple teams**: Default 1.5 second delay (recommended to increase for large batches)

### Database Integration

The collected data automatically updates existing game records in the database:

- Matches games by date (with 1-day tolerance for timezone issues)
- Updates pricing fields: `bleachers_price`, `lower_tier_price`, `courtside_price`, `luxury_boxes_price`
- Sets `updated_at` timestamp when records are modified
- Logs all updates for audit purposes

## Data Structure

### Game Pricing Data

Each collected game contains:

```python
@dataclass
class GamePricingData:
    game_id: Optional[str] = None
    date: Optional[datetime] = None
    opponent: Optional[str] = None
    attendance: Optional[int] = None
    bleachers_price: Optional[int] = None
    lower_tier_price: Optional[int] = None
    courtside_price: Optional[int] = None
    luxury_boxes_price: Optional[int] = None
    is_price_change: bool = False
    price_change_note: Optional[str] = None
    is_additional_game: bool = False  # True if found in database but not on arena webpage
```

### Results

Collection results include comprehensive statistics:

```python
{
    "success": True,
    "team_id": "12345",
    "collection_result": {
        "last_10_games_found": 8,
        "price_changes_found": 3
    },
    "update_result": {
        "games_updated": 6,
        "games_not_found": 2,
        "price_changes_processed": 3
    }
}
```

## Error Handling

The collector handles various error conditions gracefully:

- **Network errors**: Timeouts, connection issues, HTTP errors
- **Parsing errors**: Malformed HTML, missing data, unexpected formats
- **Data matching errors**: Games that can't be matched with database records
- **Database errors**: Connection issues, constraint violations

All errors are logged with appropriate detail levels and don't stop processing of other teams.

## Limitations

1. **Public pages only**: Only works with publicly accessible team arena pages (no login required)
2. **HTML structure dependent**: May need updates if BuzzerBeater changes their page structure
3. **Rate limiting**: Includes delays to be respectful, so large batches take time
4. **Historical scope**: Limited to what's displayed on the arena pages (typically last 10 games)

## Best Practices

1. **Start small**: Test with a few teams before running large batches
2. **Monitor logs**: Watch for parsing errors or blocked requests
3. **Respect rate limits**: Don't reduce delays too much
4. **Regular updates**: Run periodically to capture new games and price changes
5. **Backup data**: Ensure database backups before large collection runs

## Development

### Testing

Run the test suite to verify functionality:

```bash
python scripts/test_pricing_collector.py
```

### Extending

The collector is designed to be extensible:

- Add new parsing patterns in `_find_games_section()` and `_find_price_changes_section()`
- Customize data extraction in `_parse_games_section()` and `_parse_price_changes_section()`
- Extend game matching logic in `_find_matching_stored_game()`

### Dependencies

- `requests`: HTTP client for collection of web page information
- `beautifulsoup4`: HTML parsing
- `lxml`: Fast XML/HTML parser (backend for BeautifulSoup)

All dependencies are already included in the project's requirements.
