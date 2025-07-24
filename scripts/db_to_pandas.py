"""
Database to Pandas Converter for BB-Arena Project

This script provides utilities to convert database tables to pandas DataFrames
for statistical analysis of arena demand, pricing, and other attributes.
"""

import sqlite3
import pandas as pd
from pathlib import Path
from typing import Optional, Dict, Any, List
import sys

# Add the src directory to path for imports
sys.path.append(str(Path(__file__).parent.parent / "src"))

class DatabaseConverter:
    """Converts database tables to pandas DataFrames for analysis."""
    
    def __init__(self, db_path: str = "bb_arena_data.db"):
        """Initialize converter with database path."""
        self.db_path = Path(db_path)
        if not self.db_path.is_absolute():
            # Look for db in project root
            self.db_path = Path(__file__).parent.parent / db_path
    
    def get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        return sqlite3.connect(self.db_path)
    
    def table_to_df(self, table_name: str, query: Optional[str] = None, **kwargs) -> pd.DataFrame:
        """
        Convert a database table to pandas DataFrame.
        
        Args:
            table_name: Name of the table to convert
            query: Custom SQL query (optional, defaults to SELECT * FROM table_name)
            **kwargs: Additional arguments passed to pd.read_sql_query
        
        Returns:
            pandas DataFrame with the table data
        """
        if query is None:
            query = f"SELECT * FROM {table_name}"
        
        with self.get_connection() as conn:
            df = pd.read_sql_query(query, conn, **kwargs)
        
        return df
    
    def get_games_df(self, 
                     limit: Optional[int] = None,
                     season: Optional[int] = None,
                     game_type: Optional[str] = None,
                     team_id: Optional[int] = None) -> pd.DataFrame:
        """
        Get games data with optional filtering.
        
        Args:
            limit: Limit number of rows (None for all)
            season: Filter by season number
            game_type: Filter by game type (e.g., 'league.rs')
            team_id: Filter by team (home or away)
        
        Returns:
            pandas DataFrame with games data
        """
        query = "SELECT * FROM games"
        conditions = []
        
        if season is not None:
            conditions.append(f"season = {season}")
        if game_type is not None:
            conditions.append(f"game_type = '{game_type}'")
        if team_id is not None:
            conditions.append(f"(home_team_id = {team_id} OR away_team_id = {team_id})")
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY date DESC"
        
        if limit is not None:
            query += f" LIMIT {limit}"
        
        df = self.table_to_df("games", query)
        
        # Convert date column to datetime
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'], format='ISO8601')
        
        return df
    
    def get_arena_snapshots_df(self) -> pd.DataFrame:
        """Get arena snapshots data."""
        return self.table_to_df("arena_snapshots")
    
    def get_price_snapshots_df(self) -> pd.DataFrame:
        """Get price snapshots data."""
        df = self.table_to_df("price_snapshots")
        if 'created_at' in df.columns:
            df['created_at'] = pd.to_datetime(df['created_at'])
        return df
    
    def get_team_info_df(self) -> pd.DataFrame:
        """Get team information data."""
        df = self.table_to_df("team_info")
        if 'last_synced' in df.columns:
            df['last_synced'] = pd.to_datetime(df['last_synced'])
        return df
    
    def get_team_league_history_df(self) -> pd.DataFrame:
        """Get team league history data."""
        return self.table_to_df("team_league_history")
    
    def get_league_hierarchy_df(self) -> pd.DataFrame:
        """Get league hierarchy data."""
        return self.table_to_df("league_hierarchy")
    
    def get_seasons_df(self) -> pd.DataFrame:
        """Get seasons data."""
        df = self.table_to_df("seasons")
        for col in ['start_date', 'end_date']:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col])
        return df
    
    def get_team_ids_for_league(self, season: int, league_id: int) -> List[int]:
        """
        Get all team_ids for a given season and league_id.
        
        Args:
            season: Season number
            league_id: League ID to filter by
        
        Returns:
            List of team IDs in the specified league and season
        """
        if season == 69:
            # For current season (69), use team_info table
            query = """
            SELECT DISTINCT bb_team_id 
            FROM team_info 
            WHERE league_id = ?
            ORDER BY bb_team_id
            """
            params = (league_id,)
        else:
            # For past seasons, use team_league_history table
            query = """
            SELECT DISTINCT team_id 
            FROM team_league_history 
            WHERE season = ? AND league_id = ?
            ORDER BY team_id
            """
            params = (season, league_id)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            result = cursor.fetchall()
        
        return [int(row[0]) for row in result]
    
    def get_league_regular_season_games(self, season: int, league_id: int) -> pd.DataFrame:
        """
        Get all regular season games for a specific league and season, sorted by date.
        
        Args:
            season: Season number
            league_id: League ID to filter by
            
        Returns:
            DataFrame with regular season games sorted by start date
        """
        team_ids = self.get_team_ids_for_league(season, league_id)
        if not team_ids:
            return pd.DataFrame()
        
        # Create placeholders for the IN clause
        placeholders = ','.join(['?'] * len(team_ids))
        
        query = f"""
        SELECT * FROM games 
        WHERE season = ? 
        AND game_type IN ('league.rs', 'league.rs.tv')
        AND (home_team_id IN ({placeholders}) OR away_team_id IN ({placeholders}))
        ORDER BY date
        """
        
        params = [season] + team_ids + team_ids
        
        with self.get_connection() as conn:
            df = pd.read_sql_query(query, conn, params=params)
        
        # Convert date column to datetime
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'], format='ISO8601')
        
        return df
    
    def group_games_into_rounds(self, games_df: pd.DataFrame) -> List[Dict]:
        """
        Group games into rounds of 8 games each, validating time proximity.
        
        Args:
            games_df: DataFrame of games sorted by date
            
        Returns:
            List of round dictionaries with round_number, games, median_time, and validation info
        """
        rounds = []
        
        for i in range(0, len(games_df), 8):
            round_games = games_df.iloc[i:i+8].copy()
            round_number = i // 8 + 1
            
            if len(round_games) == 0:
                break
                
            # Calculate median start time
            median_time = round_games['date'].median()
            
            # Validate all games are within 15 minutes of median
            time_diffs = abs((round_games['date'] - median_time).dt.total_seconds() / 60)
            max_diff = time_diffs.max()
            valid_round = max_diff <= 15
            
            round_info = {
                'round_number': round_number,
                'games': round_games,
                'median_time': median_time,
                'game_count': len(round_games),
                'max_time_diff_minutes': max_diff,
                'valid_round': valid_round
            }
            
            if not valid_round:

                raise ValueError(
                    f"Round {round_number} has games with time differences exceeding 15 minutes: "
                    f"max_diff={max_diff:.1f} minutes"
                )
            
            rounds.append(round_info)
            
        return rounds
    
    def calculate_standings_before_round(self, season: int, league_id: int, round_number: int) -> pd.DataFrame:
        """
        Calculate team standings before a specific round.
        
        Args:
            season: Season number
            league_id: League ID
            round_number: Round number (1-based)
            
        Returns:
            DataFrame with team standings (wins, losses, win_pct, points_for, points_against, point_diff)
        """
        # Get all regular season games for the league
        games_df = self.get_league_regular_season_games(season, league_id)
        
        if games_df.empty:
            return pd.DataFrame()
            
        # Group into rounds
        rounds = self.group_games_into_rounds(games_df)
        
        # Get all teams in the league
        team_ids = self.get_team_ids_for_league(season, league_id)
        
        # Initialize standings
        standings = {team_id: {'wins': 0, 'losses': 0, 'points_for': 0, 'points_against': 0} for team_id in team_ids}
        
        # Process games from rounds before the specified round
        for round_info in rounds[:round_number-1]:  # rounds before the target round
            for _, game in round_info['games'].iterrows():
                home_team = game['home_team_id']
                away_team = game['away_team_id']
                home_score = game['score_home']
                away_score = game['score_away']
                
                # Skip games without valid scores
                if pd.isna(home_score) or pd.isna(away_score):
                    continue
                    
                try:
                    home_score = int(home_score)
                    away_score = int(away_score)
                except (ValueError, TypeError):
                    continue
                
                # Update points for both teams
                if home_team in standings:
                    standings[home_team]['points_for'] += home_score
                    standings[home_team]['points_against'] += away_score
                if away_team in standings:
                    standings[away_team]['points_for'] += away_score
                    standings[away_team]['points_against'] += home_score
                
                # Determine winner and update standings
                if home_score > away_score:
                    # Home team wins
                    if home_team in standings:
                        standings[home_team]['wins'] += 1
                    if away_team in standings:
                        standings[away_team]['losses'] += 1
                elif away_score > home_score:
                    # Away team wins
                    if away_team in standings:
                        standings[away_team]['wins'] += 1
                    if home_team in standings:
                        standings[home_team]['losses'] += 1
                # Note: ties are not counted as wins or losses
        
        # Convert to DataFrame
        standings_list = []
        for team_id, record in standings.items():
            total_games = record['wins'] + record['losses']
            win_pct = record['wins'] / total_games if total_games > 0 else 0.0
            point_diff = record['points_for'] - record['points_against']
            
            standings_list.append({
                'team_id': team_id,
                'wins': record['wins'],
                'losses': record['losses'],
                'games_played': total_games,
                'win_pct': win_pct,
                'points_for': record['points_for'],
                'points_against': record['points_against'],
                'point_diff': point_diff
            })
        
        standings_df = pd.DataFrame(standings_list)
        
        # Sort by win percentage (descending), then by point differential (descending), then by wins (descending)
        standings_df = standings_df.sort_values(['win_pct', 'point_diff', 'wins'], ascending=[False, False, False])
        standings_df = standings_df.reset_index(drop=True)
        standings_df['rank'] = standings_df.index + 1
        
        return standings_df
    
    def get_team_wins_before_round(self, team_id: int, season: int, league_id: int, round_number: int) -> int:
        """
        Get the number of wins for a specific team before a given round.
        
        Args:
            team_id: Team ID to get wins for
            season: Season number
            league_id: League ID
            round_number: Round number (1-based)
            
        Returns:
            Number of wins for the team before the specified round
        """
        standings = self.calculate_standings_before_round(season, league_id, round_number)
        
        if standings.empty:
            return 0
            
        team_row = standings[standings['team_id'] == team_id]
        
        if team_row.empty:
            return 0
            
        return int(team_row.iloc[0]['wins'])
    
    def league_round_of_game(self, game_id: str) -> int | None:
        """Get the league round for a BB game ID."""
        # Get game details
        with self.get_connection() as conn:
            game_df = pd.read_sql_query(
                "SELECT season, game_type, home_team_id FROM games WHERE game_id = ?", 
                conn, params=[game_id]
            )
        
        if game_df.empty:
            return None
            
        season = game_df.iloc[0]['season']
        game_type = game_df.iloc[0]['game_type']
        home_team_id = game_df.iloc[0]['home_team_id']
        
        if game_type not in ['league.rs', 'league.rs.tv']:
            return None
        
        # Find which league this team belongs to
        if season == 69:
            with self.get_connection() as conn:
                league_df = pd.read_sql_query(
                    "SELECT league_id FROM team_info WHERE bb_team_id = ?",
                    conn, params=[str(home_team_id)]
                )
                if league_df.empty:
                    return None
                league_id = int(league_df.iloc[0]['league_id'])
        else:
            with self.get_connection() as conn:
                league_df = pd.read_sql_query(
                    "SELECT league_id FROM team_league_history WHERE team_id = ? AND season = ?",
                    conn, params=[home_team_id, season]
                )
                if league_df.empty:
                    return None
                league_id = int(league_df.iloc[0]['league_id'])
        
        # Get all league games using game_ids only
        league_games = self.get_league_regular_season_games(season, league_id)
        if league_games.empty:
            return None
            
        rounds = self.group_games_into_rounds(league_games)
        
        # Find which round contains our game using game_id
        for round_info in rounds:
            round_games = round_info['games']
            if game_id in round_games['game_id'].values:
                return round_info['round_number']
        
        return None
    
    def get_all_tables(self) -> Dict[str, pd.DataFrame]:
        """Get all tables as a dictionary of DataFrames."""
        tables = {
            'games': self.get_games_df(),
            'arena_snapshots': self.get_arena_snapshots_df(),
            'price_snapshots': self.get_price_snapshots_df(),
            'team_info': self.get_team_info_df(),
            'team_league_history': self.get_team_league_history_df(),
            'league_hierarchy': self.get_league_hierarchy_df(),
            'seasons': self.get_seasons_df()
        }
        return tables
    
    def list_tables(self) -> List[str]:
        """List all tables in the database."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            return [row[0] for row in cursor.fetchall()]
    
    def get_table_info(self, table_name: str) -> pd.DataFrame:
        """Get column information for a table."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            return pd.DataFrame(columns, columns=['cid', 'name', 'type', 'notnull', 'dflt_value', 'pk'])


def main():
    """Example usage of the converter."""
    converter = DatabaseConverter()
    
    print("Available tables:", converter.list_tables())
    print("\n" + "="*50)
    
    # Get latest 10 games
    games_df = converter.get_games_df(limit=10)
    print(f"\nLatest 10 games shape: {games_df.shape}")
    print(f"Columns: {list(games_df.columns)}")
    print("\nSample data:")
    print(games_df[['game_id', 'date', 'total_attendance', 'ticket_revenue']].head())


if __name__ == "__main__":
    main()