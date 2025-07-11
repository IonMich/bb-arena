#!/usr/bin/env python3
"""Quick script to check the contents of both arena_snapshots and price_snapshots tables."""

import sqlite3

def main():
    try:
        with sqlite3.connect('bb_arena_data.db') as conn:
            cursor = conn.cursor()
            
            # Get arena snapshots count
            cursor.execute('SELECT COUNT(*) FROM arena_snapshots')
            arena_count = cursor.fetchone()[0]
            
            # Get price snapshots count  
            cursor.execute('SELECT COUNT(*) FROM price_snapshots')
            price_count = cursor.fetchone()[0]
            
            # Get games count
            cursor.execute('SELECT COUNT(*) FROM games')
            games_count = cursor.fetchone()[0]
            
            # Get unique teams in each table
            cursor.execute('SELECT COUNT(DISTINCT team_id) FROM arena_snapshots WHERE team_id IS NOT NULL')
            arena_teams = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(DISTINCT team_id) FROM price_snapshots WHERE team_id IS NOT NULL')
            price_teams = cursor.fetchone()[0]
            
            # Get unique teams in games table
            cursor.execute('SELECT COUNT(DISTINCT home_team_id) FROM games WHERE home_team_id IS NOT NULL')
            games_home_teams = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(DISTINCT away_team_id) FROM games WHERE away_team_id IS NOT NULL') 
            games_away_teams = cursor.fetchone()[0]
            
            print("=== DATABASE CONTENTS ===")
            print(f"Arena snapshots: {arena_count} total records, {arena_teams} unique teams")
            print(f"Price snapshots: {price_count} total records, {price_teams} unique teams")
            print(f"Game records: {games_count} total records, {games_home_teams} home teams, {games_away_teams} away teams")
            
            # Show recent entries
            print("\n=== RECENT ARENA SNAPSHOTS ===")
            cursor.execute('SELECT team_id, arena_name, total_capacity, created_at FROM arena_snapshots ORDER BY created_at DESC LIMIT 5')
            for row in cursor.fetchall():
                print(f"Team {row[0]}: {row[1]} ({row[2]} capacity) - {row[3]}")
                
            print("\n=== RECENT PRICE SNAPSHOTS ===")
            cursor.execute('SELECT team_id, bleachers_price, lower_tier_price, courtside_price, luxury_boxes_price, created_at FROM price_snapshots ORDER BY created_at DESC LIMIT 5')
            for row in cursor.fetchall():
                print(f"Team {row[0]}: B:{row[1]} LT:{row[2]} C:{row[3]} LB:{row[4]} - {row[5]}")
                
            print("\n=== RECENT GAME RECORDS ===")
            cursor.execute('SELECT game_id, home_team_id, away_team_id, total_attendance, ticket_revenue, created_at, season, game_type, date FROM games ORDER BY created_at DESC LIMIT 5')
            for row in cursor.fetchall():
                attendance = f"{row[3]:,}" if row[3] else "No data"
                revenue = f"${row[4]:,}" if row[4] else "No data"
                season = f"S{row[6]}" if row[6] else "No season"
                game_type = row[7] if row[7] else "No type"
                game_date = row[8] if row[8] else "No date"
                print(f"Game {row[0]}: Home {row[1]} vs Away {row[2]} | {season} {game_type} | {game_date} | Att: {attendance} | Rev: {revenue}")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
