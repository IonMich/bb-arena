# BuzzerBeater Arena Optimizer

A Python application for collecting, storing, and analyzing BuzzerBeater basketball game data including attendance, pricing, and revenue optimization.

## Quick Start

1. **Clone the Repository**:

   ```bash
   git clone https://github.com/IonMich/bb-arena.git
   cd bb-arena
   ```

2. [Install `uv`](https://docs.astral.sh/uv/getting-started/installation/#standalone-installer)

3. **Configure Environment Variables**:

   ```bash
   cp .env.example .env
   # Edit .env with your BuzzerBeater credentials:
   # BB_USERNAME=your_username
   # BB_SECURITY_CODE=your_security_code
   ```

## Usage

### Frontend (Web Interface)

1. **Start Python Server**:

   ```bash
   uv run run_server.py
   ```

2. **Start Frontend**:

   ```bash
   cd frontend
   npm install
   npm run dev
   ```

3. **Access the Web Interface**:

   Open your browser and go to `http://localhost:5173`.

### Bulk Collection Script

1. **Run Collection Script**:

   **Basic usage (default: USA level 1, seasons 68-69, all tasks):**

   ```bash
   uv run python scripts/data_collection.py
   ```

   **List available countries:**

   ```bash
   uv run python scripts/data_collection.py --list-countries
   ```

   **Custom countries and league levels:**

   ```bash
   # Multiple countries, include second division teams
   uv run python scripts/data_collection.py --countries 1 7 12 --max-league-level 2
   
   # Resume collection: skip initial tasks, only collect games
   uv run python scripts/data_collection.py --countries 1 --seasons 68 69 --tasks 5
   ```

   **Run specific tasks only:**

   ```bash
   # Only collect home games and pricing data
   uv run python scripts/data_collection.py --tasks 5 6
   
   # Only collect team info, arena, and history data
   uv run python scripts/data_collection.py --tasks 2 3 4
   ```

   Add the `--help` flag to see all available options and task descriptions.

### Data Analysis

   ![Comparison of Predicted vs Actual Attendance, Grouped by Seating Section](output/attendance_pred_actual.png)

## Development Testing

```bash
# Run tests
uv run pytest
```

## Development

```bash
# Type Checking
uv run ty check src/

# Linting
uv run ruff check src/
```
