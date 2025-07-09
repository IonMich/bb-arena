#!/bin/bash

# Development tools runner for bb-arena-optimizer

echo "🔧 Running development tools for bb-arena-optimizer"
echo "=================================================="

echo "📋 Running tests..."
uv run pytest tests/ -v

echo ""
echo "🔍 Running mypy type checking..."
uv run mypy src/bb_arena_optimizer/ --show-error-codes

echo ""
echo "🧹 Running ruff linting..."
uv run ruff check src/ tests/

echo ""
echo "✨ Running ruff formatting check..."
uv run ruff format src/ tests/ --check

echo ""
echo "✅ Development tools complete!"
