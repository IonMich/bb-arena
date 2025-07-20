#!/usr/bin/env python3
"""
Test script to verify country sorting by user count.
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

def test_country_sorting():
    """Test get_countries and sorting by user count."""
    
    # Get credentials from environment
    username = os.getenv('BB_USERNAME')
    security_code = os.getenv('BB_SECURITY_CODE')
    
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
        
        print("\n🌍 Testing country data retrieval and sorting")
        print("=" * 60)
        
        # Get all countries
        countries = api.get_countries()
        
        if not countries:
            print("❌ No countries found")
            return
        
        print(f"✅ Found {len(countries)} countries")
        
        # Sort by user count (descending)
        sorted_countries = sorted(countries, key=lambda c: c.get("users", 0), reverse=True)
        
        print(f"\n📊 Top 20 countries by user count:")
        print("-" * 50)
        print(f"{'Rank':<4} {'ID':<4} {'Users':<8} {'Name':<25} {'Divisions'}")
        print("-" * 50)
        
        expected_top_5 = ["Utopia", "Italy", "Spain", "USA", "France"]
        actual_top_5 = []
        
        for i, country in enumerate(sorted_countries[:20]):
            rank = i + 1
            country_id = country.get("id", "N/A")
            name = country.get("name", "Unknown")
            users = country.get("users", 0)
            divisions = country.get("divisions", 0)
            
            # Collect actual top 5 for comparison
            if rank <= 5:
                actual_top_5.append(name)
            
            print(f"{rank:<4} {country_id:<4} {users:<8} {name:<25} {divisions}")
        
        # Check if our expectation matches reality
        print(f"\n🎯 Expected top 5: {expected_top_5}")
        print(f"🎯 Actual top 5:   {actual_top_5}")
        
        # Calculate match score
        matches = sum(1 for expected, actual in zip(expected_top_5, actual_top_5) 
                     if expected.lower() in actual.lower() or actual.lower() in expected.lower())
        
        print(f"\n📈 Match score: {matches}/5 countries in expected positions")
        
        if matches >= 4:
            print("✅ Country sorting appears to work correctly!")
        elif matches >= 2:
            print("⚠️  Partial match - country data may have changed or names differ")
        else:
            print("❌ Unexpected country ranking - check implementation")
        
        # Show some statistics
        total_users = sum(c.get("users", 0) for c in countries)
        avg_users = total_users / len(countries) if countries else 0
        
        print(f"\n📊 Country statistics:")
        print(f"   - Total countries: {len(countries)}")
        print(f"   - Total users: {total_users:,}")
        print(f"   - Average users per country: {avg_users:.1f}")
        print(f"   - Top country users: {sorted_countries[0].get('users', 0):,}")
        print(f"   - Bottom country users: {sorted_countries[-1].get('users', 0)}")
        
        # Test the collect_top_countries_data function logic
        print(f"\n🔧 Testing mass collector logic:")
        top_5_for_collection = [c["id"] for c in sorted_countries[:5]]
        print(f"   - Top 5 country IDs for collection: {top_5_for_collection}")
        
        # Verify these countries have reasonable data
        for i, country in enumerate(sorted_countries[:5]):
            country_id = country["id"]
            name = country["name"]
            users = country.get("users", 0)
            divisions = country.get("divisions", 0)
            
            print(f"   - {name} (ID: {country_id}): {users:,} users, {divisions} divisions")
            
            if users < 100:
                print(f"     ⚠️  Warning: Low user count for top country")
            if divisions == 0:
                print(f"     ⚠️  Warning: No divisions data")
        
        print(f"\n🎉 Country sorting test completed!")
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    
    finally:
        api.logout()
        print("👋 Logged out")

if __name__ == "__main__":
    test_country_sorting()