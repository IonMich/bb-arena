"""BuzzerBeater Arena Optimizer - Ticket pricing optimization for basketball teams."""

__version__ = "0.1.0"
__author__ = "Arena Optimizer Team"
__description__ = "Optimize ticket pricing in BuzzerBeater to maximize arena revenue"

from .api.client import BuzzerBeaterAPI

__all__ = ["BuzzerBeaterAPI"]
