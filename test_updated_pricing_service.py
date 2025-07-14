#!/usr/bin/env python3
"""Quick test of the updated pricing service logic."""

from src.bb_arena_optimizer.storage.database import DatabaseManager
from src.bb_arena_optimizer.collecting.pricing_service import HistoricalPricingService

def main():
    print('Testing updated pricing service with team 143440...')
    
    # Initialize the service
    db_manager = DatabaseManager()
    pricing_service = HistoricalPricingService(db_manager)
    
    # Test with the team that had issues
    result = pricing_service.collect_and_update_team_pricing('143440', collector_delay=0.5)
    
    print('\nResult:')
    for key, value in result.items():
        print(f'  {key}: {value}')
    
    if result.get('success') and 'update_result' in result:
        update_result = result['update_result']
        print(f'\nUpdate Summary:')
        print(f'  Games updated: {update_result.get("games_updated", 0)}')
        print(f'  Games not found: {update_result.get("games_not_found", 0)}')
        print(f'  Price changes processed: {update_result.get("price_changes_processed", 0)}')
        print(f'  Total collected games: {update_result.get("total_collected_games", 0)}')
        
        # Show success rate
        total_games = update_result.get("total_collected_games", 0)
        updated_games = update_result.get("games_updated", 0)
        if total_games > 0:
            success_rate = (updated_games / total_games) * 100
            print(f'  Success rate: {success_rate:.1f}% ({updated_games}/{total_games})')

if __name__ == '__main__':
    main()
