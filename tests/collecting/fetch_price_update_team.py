#!/usr/bin/env python3
"""
Fetch team arena page to see price update rows.
Usage: python fetch_price_update_team.py <team_id>
"""

import sys
import time
from pathlib import Path
import requests
from bs4 import BeautifulSoup


def main():
    if len(sys.argv) != 2:
        print("Usage: python fetch_price_update_team.py <team_id>")
        print("Example: python fetch_price_update_team.py 142773")
        sys.exit(1)
    
    team_id = sys.argv[1]
    
    # Get the current script directory and build path relative to it
    script_dir = Path(__file__).parent
    output_file = script_dir / "fixtures" / f"team_{team_id}_with_price_updates.html"
    
    print(f"Script directory: {script_dir}")
    print(f"Output file will be: {output_file.absolute()}")
    
    # Use the same URL pattern as the collector
    url = f"https://www.buzzerbeater.com/team/{team_id}/arena.aspx"
    
    # Create a session with realistic headers
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    })
    
    print(f"Fetching arena page for team {team_id} (with price updates)...")
    print(f"URL: {url}")
    
    try:
        # Be respectful to the server
        time.sleep(1)
        
        response = session.get(url, timeout=30)
        response.raise_for_status()
        
        print(f"Successfully fetched {len(response.content)} bytes")
        
        # Parse with BeautifulSoup to pretty-print and validate
        soup = BeautifulSoup(response.content, 'html.parser')
        html_content = str(soup)
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"Saved HTML to: {output_path}")
        
        # Also extract just the attendance table to analyze
        table = soup.find('table', id='cphContent_seatingStats')
        if table and hasattr(table, 'find_all'):
            # Create table-only filename by replacing the suffix properly
            table_file = output_path.with_name(output_path.stem + '_table_only.html')
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
                cells = row.find_all('td')
                if len(cells) >= 2:
                    date_text = cells[0].get_text().strip()
                    opponent_text = cells[1].get_text().strip()
                    attendance_text = cells[6].get_text().strip() if len(cells) > 6 else "N/A"
                    print(f"Row {i}: {date_text} | {opponent_text} | Attendance: {attendance_text}")
        
        print("Done!")
        
    except requests.RequestException as e:
        print(f"Error fetching arena page: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")


if __name__ == "__main__":
    main()
