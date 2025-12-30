#!/bin/bash

# Frontend Code Quality Check Script
# Runs formatting checks and linting for the frontend codebase

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================"
echo "Frontend Code Quality Checks"
echo "========================================"
echo ""

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
    echo ""
fi

# Run formatting check
echo "1. Checking code formatting with Prettier..."
echo "----------------------------------------"
if npm run format:check; then
    echo "✓ All files are properly formatted"
else
    echo ""
    echo "✗ Some files need formatting. Run 'npm run format' to fix."
    exit 1
fi
echo ""

# Run linting
echo "2. Running ESLint..."
echo "----------------------------------------"
if npm run lint; then
    echo "✓ No linting errors found"
else
    echo ""
    echo "✗ Linting errors found. Run 'npm run lint:fix' to auto-fix what's possible."
    exit 1
fi
echo ""

echo "========================================"
echo "All quality checks passed!"
echo "========================================"
