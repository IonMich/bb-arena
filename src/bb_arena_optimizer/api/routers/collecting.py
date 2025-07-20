"""API router for collecting arena data and updating pricing."""

import logging
from typing import Dict
import requests
from bs4 import BeautifulSoup
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ...storage.database import DatabaseManager
from ...collecting.arena_table_parser import ArenaTableIsolator
from ...collecting.arena_row import ArenaRowParser
from ...collecting.price_period import build_price_periods_from_data
from ...utils.datetime_utils import get_bb_timezone_from_html

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/collecting",
    tags=["collecting"]
)

class ArenaUpdateRequest(BaseModel):
    team_id: int

class ArenaUpdateResponse(BaseModel):
    message: str
    team_id: int
    periods_created: int
    games_updated: int

@router.post("/update-pricing-from-arena", response_model=ArenaUpdateResponse)
async def update_pricing_from_arena_webpage(request: ArenaUpdateRequest) -> ArenaUpdateResponse:
    """
    Fetch arena webpage for a team, create price periods, and update game pricing.
    
    Args:
        request: Contains team_id for the team to update
        
    Returns:
        Summary of the update operation
    """
    try:
        logger.info(f"🔄 Starting arena pricing update for team {request.team_id}")
        
        # Initialize database manager
        db_manager = DatabaseManager("bb_arena_data.db")
        
        # Fetch arena webpage
        logger.info(f"📥 Fetching arena webpage for team {request.team_id}")
        html_content = _fetch_arena_webpage(request.team_id)
        
        # Parse the arena table
        logger.info("🔍 Parsing arena table from HTML")
        arena_table = ArenaTableIsolator.find_attendance_table(html_content)
        
        if not arena_table:
            raise HTTPException(status_code=404, detail="Arena table not found on webpage")
        
        # Parse arena rows
        arena_rows = ArenaRowParser.parse_data_rows(arena_table)
        
        if not arena_rows:
            raise HTTPException(status_code=404, detail="No arena data found in table")
        
        logger.info(f"📊 Found {len(arena_rows)} arena rows")
        
        # Detect timezone from HTML
        timezone_str = get_bb_timezone_from_html(html_content)
        logger.info(f"🌍 Detected timezone: {timezone_str}")
        
        # Create price periods
        logger.info("🏗️ Creating price periods from arena data")
        periods = build_price_periods_from_data(
            arena_rows, 
            db_manager, 
            str(request.team_id), 
            timezone_str
        )
        
        logger.info(f"✅ Created {len(periods)} price periods")
        
        # Update game pricing for each period
        total_games_updated = 0
        for period in periods:
            update_results = period.update_game_pricing()
            games_updated = sum(1 for success in update_results.values() if success)
            total_games_updated += games_updated
            logger.info(f"💰 Updated pricing for {games_updated} games in period {period.period_id} "
                       f"({period.safe_start.date()} - {period.safe_end.date()})")
        
        logger.info(f"🎉 Arena pricing update completed for team {request.team_id}. "
                   f"Created {len(periods)} periods, updated {total_games_updated} games")
        
        return ArenaUpdateResponse(
            message="Arena pricing updated successfully",
            team_id=request.team_id,
            periods_created=len(periods),
            games_updated=total_games_updated
        )
        
    except requests.RequestException as e:
        logger.error(f"❌ Failed to fetch arena webpage for team {request.team_id}: {e}")
        raise HTTPException(status_code=503, detail=f"Failed to fetch arena webpage: {str(e)}")
    
    except Exception as e:
        logger.error(f"❌ Error updating arena pricing for team {request.team_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


def _fetch_arena_webpage(team_id: int) -> str:
    """
    Fetch the arena webpage HTML for a given team.
    
    Args:
        team_id: The BuzzerBeater team ID
        
    Returns:
        HTML content of the arena page
        
    Raises:
        requests.RequestException: If the request fails
    """
    url = f"https://www.buzzerbeater.com/team/{team_id}/arena.aspx"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    logger.debug(f"🌐 Making request to {url}")
    
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    
    logger.debug(f"✅ Successfully fetched arena webpage (status: {response.status_code})")
    
    return response.text

# CLI functionality
def fetch_and_save_arena_html(team_id: int, output_dir: str | None = None) -> None:
    """
    CLI function to fetch arena HTML and save to fixtures directory.
    
    Args:
        team_id: The BuzzerBeater team ID
        output_dir: Optional output directory (defaults to tests/collecting/fixtures)
    """
    import sys
    import time
    from pathlib import Path
    from bs4 import Tag
    
    if output_dir is None:
        # Default to tests/collecting/fixtures relative to project root
        current_file = Path(__file__)
        project_root = current_file.parent.parent.parent.parent.parent  # Go up to bb-arena root
        output_path = project_root / "tests" / "collecting" / "fixtures"
    else:
        output_path = Path(output_dir)
    
    output_file = output_path / f"team_{team_id}_arenapage.html"
    
    print(f"Fetching arena page for team {team_id}...")
    print(f"Output directory: {output_path}")
    print(f"Output file will be: {output_file.absolute()}")
    
    try:
        # Be respectful to the server
        time.sleep(1)
        
        # Fetch the HTML
        html_content = _fetch_arena_webpage(team_id)
        
        print(f"Successfully fetched {len(html_content)} characters")
        
        # Parse with BeautifulSoup to pretty-print and validate
        soup = BeautifulSoup(html_content, 'html.parser')
        pretty_html = str(soup)
        
        # Ensure output directory exists
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Save the full HTML
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(pretty_html)
        
        print(f"Saved HTML to: {output_file}")
        
        # Also extract just the attendance table for analysis
        table = soup.find('table', id='cphContent_seatingStats')
        if table and isinstance(table, Tag):
            table_file = output_file.with_name(output_file.stem + '_table_only.html')
            with open(table_file, 'w', encoding='utf-8') as f:
                f.write(str(table))
            print(f"Saved attendance table to: {table_file}")
            
            # Analyze the table structure
            rows = table.find_all('tr')
            print(f"\nTable analysis:")
            print(f"Total rows: {len(rows)}")
            
            for i, row in enumerate(rows):
                if i == 0:  # Header
                    continue
                if isinstance(row, Tag):
                    cells = row.find_all('td')
                    if len(cells) >= 2:
                        date_text = cells[0].get_text().strip()
                        opponent_text = cells[1].get_text().strip()
                        attendance_text = cells[6].get_text().strip() if len(cells) > 6 else "N/A"
                        print(f"Row {i}: {date_text} | {opponent_text} | Attendance: {attendance_text}")
        else:
            print("⚠️  No attendance table found in HTML")
        
        print("✅ Done!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


def main():
    """CLI entry point for fetching arena HTML."""
    import sys
    
    if len(sys.argv) not in [2, 3]:
        print("Usage: python -m bb_arena_optimizer.api.routers.collecting <team_id> [output_dir]")
        print("Example: python -m bb_arena_optimizer.api.routers.collecting 142773")
        print("Example: python -m bb_arena_optimizer.api.routers.collecting 142773 /path/to/output")
        sys.exit(1)
    
    team_id = int(sys.argv[1])
    output_dir = sys.argv[2] if len(sys.argv) == 3 else None
    
    fetch_and_save_arena_html(team_id, output_dir)


if __name__ == "__main__":
    main()