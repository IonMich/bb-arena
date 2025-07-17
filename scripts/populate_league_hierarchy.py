#!/usr/bin/env python3
"""
Script to populate the league_hierarchy table with complete league data from BuzzerBeater API.
This creates a comprehensive lookup table for all leagues across all countries and levels.
"""

import os
import sys
import sqlite3
from pathlib import Path

# Add the src directory to the Python path
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

from bb_arena_optimizer.api.client import BuzzerBeaterAPI


def main():
    """Populate league hierarchy table with complete league data."""
    # Database path
    db_path = project_root / "bb_arena_data.db"
    
    # Get API credentials from environment
    username = os.getenv("BB_USERNAME")
    security_code = os.getenv("BB_SECURITY_CODE")
    
    if not username or not security_code:
        print("Error: BB_USERNAME and BB_SECURITY_CODE environment variables must be set")
        return False
    
    # Initialize API client
    api = BuzzerBeaterAPI(username, security_code)
    
    # Login to the API
    if not api.login():
        print("Error: Failed to authenticate with BuzzerBeater API")
        return False
    
    try:
        print("Connecting to database...")
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Clear existing data to ensure fresh start
            cursor.execute("DELETE FROM league_hierarchy")
            print("Cleared existing league hierarchy data")
            
            print("Fetching countries...")
            countries = api.get_countries()
            if not countries:
                print("Error: Could not fetch countries data")
                return False
            
            print(f"Found {len(countries)} countries")
            total_leagues = 0
            
            for country in countries:
                country_id = country.get("id")
                country_name = country.get("name")
                
                if not country_id or not country_name:
                    print(f"Skipping country with missing data: {country}")
                    continue
                
                print(f"Processing {country_name} (ID: {country_id})...")
                
                # Get all leagues for this country
                leagues = api.get_leagues(country_id)
                if not leagues:
                    print(f"  No leagues found for {country_name}")
                    continue
                
                country_league_count = 0
                for league in leagues:
                    league_id = league.get("id")
                    league_name = league.get("name")
                    league_level = league.get("level")
                    
                    if not all([league_id, league_name, league_level]):
                        print(f"  Skipping league with missing data: {league}")
                        continue
                    
                    # Insert into database
                    cursor.execute("""
                        INSERT OR REPLACE INTO league_hierarchy 
                        (country_id, country_name, league_id, league_name, league_level)
                        VALUES (?, ?, ?, ?, ?)
                    """, (country_id, country_name, league_id, league_name, league_level))
                    
                    country_league_count += 1
                
                print(f"  Added {country_league_count} leagues for {country_name}")
                total_leagues += country_league_count
            
            # Commit all changes
            conn.commit()
            
            # Verify results
            cursor.execute("SELECT COUNT(*) FROM league_hierarchy")
            db_count = cursor.fetchone()[0]
            
            print(f"\nSuccess! Populated league hierarchy with {total_leagues} leagues")
            print(f"Database now contains {db_count} league entries")
            
            # Show some statistics
            cursor.execute("SELECT COUNT(DISTINCT country_id) FROM league_hierarchy")
            countries_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT league_level, COUNT(*) FROM league_hierarchy GROUP BY league_level ORDER BY league_level")
            level_stats = cursor.fetchall()
            
            print(f"Countries represented: {countries_count}")
            print("Leagues by level:")
            for level, count in level_stats:
                print(f"  Level {level}: {count} leagues")
            
            return True
            
    except Exception as e:
        print(f"Error: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
