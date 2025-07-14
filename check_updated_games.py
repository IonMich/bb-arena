#!/usr/bin/env python3
"""Check the updated games in database after pricing update."""

from src.bb_arena_optimizer.storage.database import DatabaseManager

def main():
    print('Checking games for team 143440 after pricing update...')
    
    db_manager = DatabaseManager()
    
    # Get games for team 143440
    games = db_manager.get_games_for_team('143440', limit=10)
    
    print(f'\nFound {len(games)} games:')
    print('-' * 80)
    
    for i, game in enumerate(games):
        print(f'Game {i+1}:')
        print(f'  ID: {game.game_id}')
        print(f'  Date: {game.date}')
        print(f'  Home Team: {game.home_team_id}')
        print(f'  Away Team: {game.away_team_id}')
        print(f'  Attendance: Total={game.total_attendance}')
        if hasattr(game, 'bleachers_attendance'):
            print(f'    Bleachers: {game.bleachers_attendance}')
            print(f'    Lower Tier: {game.lower_tier_attendance}')
            print(f'    Courtside: {game.courtside_attendance}')
            print(f'    Luxury Boxes: {game.luxury_boxes_attendance}')
        
        # Check pricing fields
        pricing_fields = [
            ('Bleachers Price', getattr(game, 'bleachers_price', None)),
            ('Lower Tier Price', getattr(game, 'lower_tier_price', None)),
            ('Courtside Price', getattr(game, 'courtside_price', None)),
            ('Luxury Boxes Price', getattr(game, 'luxury_boxes_price', None))
        ]
        
        has_pricing = any(price is not None for _, price in pricing_fields)
        
        if has_pricing:
            print(f'  Pricing: ✅')
            for field_name, price in pricing_fields:
                if price is not None:
                    print(f'    {field_name}: ${price}')
                else:
                    print(f'    {field_name}: None')
        else:
            print(f'  Pricing: ❌ No pricing data found')
        
        print()

if __name__ == '__main__':
    main()
