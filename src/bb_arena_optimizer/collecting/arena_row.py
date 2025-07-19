"""
Arena Pricing Pipeline - Arena Row Parsing and Data Objects

This module provides classes for parsing individual rows from BuzzerBeater arena
attendance tables and creating structured data objects for both game 
and price change records.

Key Components:
- GameEvent: Structured data for game records
- PriceChange: Structured data for ticket price updates
- ArenaRowParser: Service for parsing table rows into data objects
- TestArenaRowParsing: Comprehensive test suite
"""

import pytest
from pathlib import Path
from bs4 import BeautifulSoup, Tag
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Union
import re


@dataclass
class GameEvent:
    """Represents a game record from the arena table."""
    
    # Row metadata
    row_index: int  # Original position in table (0-based, excluding header)
    
    # Game identification
    game_id: str  # Extracted from match link href (mandatory)
    date_raw: str  # Original date string from HTML in the timezone of the HTTP request origin
    
    @classmethod
    def from_table_row(cls, row: Tag, row_index: int) -> 'GameEvent':
        """Create GameEvent object from a table row."""
        cells = row.find_all('td')
        if len(cells) < 8:
            raise ValueError(f"Game row must have 8 cells, got {len(cells)}")
        
        # Extract game ID from date link
        game_id = None
        if isinstance(cells[0], Tag):
            date_link = cells[0].find('a')
            if isinstance(date_link, Tag) and date_link.get('href'):
                href = date_link.get('href')
                if href and isinstance(href, str):
                    match = re.search(r'/match/(\d+)/', href)
                    if match:
                        game_id = match.group(1)
        
        if game_id is None:
            raise ValueError("Game ID is mandatory but could not be extracted")
        
        # Get date string
        date_raw = cells[0].get_text().strip()
        
        return cls(
            row_index=row_index,
            game_id=game_id,
            date_raw=date_raw
        )


@dataclass
class PriceChange:
    """Represents a ticket price update record from the arena table."""
    
    # Row metadata
    row_index: int  # Original position in table (0-based, excluding header)
    
    # Price change identification
    date_raw: str  # Original date string from HTML in the timezone of the HTTP request origin

    # New ticket prices by seating section
    bleachers_price: Optional[int]  # Price in game currency
    lower_tier_price: Optional[int]
    courtside_price: Optional[int]
    luxury_boxes_price: Optional[int]
    
    @classmethod
    def from_table_row(cls, row: Tag, row_index: int) -> 'PriceChange':
        """Create PriceChange object from a table row."""
        cells = row.find_all('td')
        if len(cells) < 8:
            raise ValueError(f"Price change row must have 8 cells, got {len(cells)}")
        
        # Get date string
        date_raw = cells[0].get_text().strip()
        
        # Parse price values (these are in the attendance columns for price updates)
        def safe_int(text: str) -> Optional[int]:
            try:
                return int(text.strip())
            except (ValueError, AttributeError):
                return None
        
        bleachers_price = safe_int(cells[2].get_text())
        lower_tier_price = safe_int(cells[3].get_text())
        courtside_price = safe_int(cells[4].get_text())
        luxury_boxes_price = safe_int(cells[5].get_text())
        
        return cls(
            row_index=row_index,
            date_raw=date_raw,
            bleachers_price=bleachers_price,
            lower_tier_price=lower_tier_price,
            courtside_price=courtside_price,
            luxury_boxes_price=luxury_boxes_price
        )


class ArenaRowParser:
    """Service for parsing attendance table rows into structured objects."""
    
    @staticmethod
    def is_price_change_row(row: Tag) -> bool:
        """
        Determine if a table row represents a price change.
        
        Args:
            row: BeautifulSoup table row Tag
            
        Returns:
            True if this is a price change row
        """
        cells = row.find_all('td')
        if len(cells) < 2:
            return False
        
        # Check if opponent cell contains "Ticket Price Update"
        opponent_text = cells[1].get_text().strip()
        if 'Ticket Price Update' in opponent_text:
            return True
        
        # Alternative check: total attendance is -1
        if len(cells) >= 7:
            attendance_text = cells[6].get_text().strip()
            if attendance_text == '-1':
                return True
        
        return False
    
    @staticmethod
    def parse_data_rows(table: Tag) -> List[Union[GameEvent, PriceChange]]:
        """
        Parse all data rows from attendance table into structured objects.
        
        Args:
            table: BeautifulSoup table Tag
            
        Returns:
            List of GameEvent and PriceChange objects in table order
        """
        all_rows = table.find_all('tr')
        parsed_objects: List[Union[GameEvent, PriceChange]] = []
        row_index = 0
        
        for row in all_rows:
            if isinstance(row, Tag):
                # Skip header row
                row_class = row.get('class')
                if row_class and 'tableHeader' in str(row_class):
                    continue
                
                try:
                    if ArenaRowParser.is_price_change_row(row):
                        price_change = PriceChange.from_table_row(row, row_index)
                        parsed_objects.append(price_change)
                    else:
                        game_event = GameEvent.from_table_row(row, row_index)
                        parsed_objects.append(game_event)

                    row_index += 1
                    
                except Exception as e:
                    # Log error but continue processing other rows
                    print(f"Warning: Failed to parse row {row_index}: {e}")
                    row_index += 1
                    continue
        
        return parsed_objects
