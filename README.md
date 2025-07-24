# BuzzerBeater Arena Optimizer

A Python application for collecting, storing, and analyzing BuzzerBeater basketball game data including attendance, pricing, and revenue optimization.

## Quick Start

1. **Configure Environment Variables**:

   ```bash
   cp .env.example .env
   # Edit .env with your BuzzerBeater credentials:
   # BB_USERNAME=your_username
   # BB_SECURITY_CODE=your_security_code
   ```

## Usage

### Frontend (Web Interface)

1. **Install Dependencies**:

   ```bash
   uv sync
   ```

2. **Start Python Server**:

   ```bash
   uv run run_server.py
   ```

3. **Start Frontend**:

   ```bash
   cd frontend
   npm install
   npm run dev
   ```

### Bulk Collection Script

1. **Install Dependencies**:

   ```bash
   uv sync --dev
   ```

2. **Run Collection Script**:

   ```bash
   uv run python scripts/test_collection.py
   ```

## Development Testing

```bash
# Run tests
uv run pytest
```

## Development

```bash
# Type checking
uv run mypy src/

# Linting
uv run ruff check src/
```
