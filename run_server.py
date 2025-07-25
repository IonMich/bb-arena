#!/usr/bin/env python3
"""Simple script to start the FastAPI server."""

import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

if __name__ == "__main__":
    import uvicorn
    # Use the module string for reload to work properly
    uvicorn.run(
        "bb_arena_optimizer.api.server:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        reload_dirs=["src"]
    )
