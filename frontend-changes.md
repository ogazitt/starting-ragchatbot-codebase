# Frontend Code Quality Tools

This document describes the code quality tools added to the frontend development workflow.

## Overview

Added essential code quality tools for the frontend:
- **Prettier** for automatic code formatting (JavaScript, CSS, HTML)
- **ESLint** for JavaScript linting and best practices enforcement
- Development scripts for running quality checks

## Files Added

### Configuration Files

| File | Purpose |
|------|---------|
| `frontend/package.json` | NPM package configuration with dev dependencies and scripts |
| `frontend/.prettierrc` | Prettier formatting configuration |
| `frontend/.prettierignore` | Files/folders to exclude from Prettier |
| `frontend/eslint.config.js` | ESLint rules and configuration (flat config format) |
| `frontend/quality-check.sh` | Shell script to run all quality checks |

### Updated Files

| File | Changes |
|------|---------|
| `.gitignore` | Added `frontend/node_modules/` to ignore list |
| `frontend/script.js` | Formatted with Prettier, fixed ESLint warnings |
| `frontend/style.css` | Formatted with Prettier |
| `frontend/index.html` | Formatted with Prettier |

## Usage

### Installation

```bash
cd frontend
npm install
```

### Running Quality Checks

```bash
# Check formatting (no changes)
npm run format:check

# Fix formatting
npm run format

# Run linting
npm run lint

# Fix auto-fixable lint issues
npm run lint:fix

# Run all quality checks
npm run quality

# Fix all issues automatically
npm run quality:fix

# Or use the shell script
./quality-check.sh
```

## Configuration Details

### Prettier Configuration (`.prettierrc`)

```json
{
  "semi": true,
  "singleQuote": true,
  "tabWidth": 2,
  "useTabs": false,
  "trailingComma": "es5",
  "printWidth": 100,
  "bracketSpacing": true,
  "arrowParens": "always",
  "endOfLine": "lf",
  "htmlWhitespaceSensitivity": "css"
}
```

### ESLint Rules

The ESLint configuration includes:

- **Best Practices**: `eqeqeq`, `no-eval`, `curly`, `no-fallthrough`
- **Variables**: `no-unused-vars` (with underscore prefix exception), `no-use-before-define`, `no-shadow`
- **Modern JavaScript**: `prefer-const`, `no-var`, `object-shorthand`, `prefer-arrow-callback`, `prefer-template`
- **Error Prevention**: `no-console` (warn/error allowed), `no-debugger`, `no-duplicate-imports`
- **Prettier Integration**: Uses `eslint-config-prettier` to disable formatting rules that conflict with Prettier

### Global Variables

ESLint is configured to recognize:
- Browser globals (`window`, `document`, `fetch`, etc.)
- `marked` library (loaded from CDN)

## Dependencies

Development dependencies added:
- `eslint@^9.17.0` - JavaScript linter
- `eslint-config-prettier@^9.1.0` - Disables ESLint rules that conflict with Prettier
- `globals@^15.14.0` - Global variable definitions for ESLint
- `prettier@^3.4.2` - Code formatter

## Code Fixes Applied

The following issues were fixed in the existing code:

1. **script.js:73** - Changed `query: query` to `query` (object shorthand)
2. **script.js:157** - Renamed shadow variable `html` to `item` in filter callback
3. **script.js:225-230** - Removed debug `console.log` statements (only `console.warn`/`console.error` are allowed)
