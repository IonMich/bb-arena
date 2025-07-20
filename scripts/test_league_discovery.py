#!/usr/bin/env python3
"""
Test script to check league discovery for specific countries.
"""

import sys
import os
from typing import Any, Dict, List
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from bb_arena_optimizer.api.client import BuzzerBeaterAPI
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_league_discovery():
    """Test get_leagues for USA, Spain, and Greece."""
    
    # You'll need to replace these with your actual credentials
    # For testing, you can either:
    # 1. Set environment variables: BB_USERNAME and BB_SECURITY_CODE
    # 2. Or replace the None values below with your credentials
    
    username = os.getenv('BB_USERNAME') or None
    security_code = os.getenv('BB_SECURITY_CODE') or None
    
    if not username or not security_code:
        print("❌ Please set BB_USERNAME and BB_SECURITY_CODE environment variables")
        print("   Or edit this script to include your credentials")
        return
    
    api = BuzzerBeaterAPI(username, security_code)
    
    try:
        # Login
        if not api.login():
            print("❌ Failed to login to BuzzerBeater API")
            return
        
        print("✅ Successfully logged in to BuzzerBeater API")
        
        # Test countries
        test_countries = [
            (1, "USA"),
            (7, "Spain"), 
            (12, "Greece")  # Greece is typically country ID 9
        ]
        
        for country_id, country_name in test_countries:
            print(f"\n🔍 Testing league discovery for {country_name} (ID: {country_id})")
            print("=" * 60)
            
            try:
                leagues = api.get_leagues(country_id, max_level=3)
                
                if not leagues:
                    print(f"❌ No leagues found for {country_name}")
                    continue
                
                print(f"✅ Found {len(leagues)} leagues for {country_name}:")
                
                # Group by level
                by_level: Dict[int, List[Dict[str, Any]]] = {}
                for league in leagues:
                    level = league["level"]
                    if level not in by_level:
                        by_level[level] = []
                    by_level[level].append(league)
                
                # Display results
                for level in sorted(by_level.keys()):
                    level_leagues = by_level[level]
                    print(f"\n  📊 Level {level} ({len(level_leagues)} leagues):")
                    
                    for league in level_leagues[:5]:  # Show first 5 leagues per level
                        print(f"    - ID: {league['id']}, Name: {league['name']}")
                    
                    if len(level_leagues) > 5:
                        print(f"    ... and {len(level_leagues) - 5} more leagues")
                
                # Test getting standings for level 1 league
                level_1_leagues = by_level.get(1, [])
                if level_1_leagues:
                    test_league = level_1_leagues[0]
                    print(f"\n🏆 Testing standings for level 1 league: {test_league['name']}")
                    
                    standings = api.get_league_standings(test_league["id"])
                    if standings and "teams" in standings:
                        teams = standings["teams"]
                        print(f"  ✅ Found {len(teams)} teams in the league")
                        
                        # Show first few teams
                        for i, team in enumerate(teams[:3]):
                            print(f"    {i+1}. Team ID: {team['id']}, Name: {team['name']}")
                        
                        if len(teams) > 3:
                            print(f"    ... and {len(teams) - 3} more teams")
                    else:
                        print(f"  ❌ Could not get standings for league {test_league['id']}")
                
            except Exception as e:
                print(f"❌ Error testing {country_name}: {e}")
                continue
        
        print(f"\n🎉 League discovery test completed!")
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    
    finally:
        api.logout()
        print("👋 Logged out")

if __name__ == "__main__":
    test_league_discovery()