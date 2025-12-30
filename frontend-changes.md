# Frontend Changes: Dark/Light Theme Toggle

## Overview
Added a dark/light theme toggle button to the Course Materials Assistant UI with smooth transitions, CSS custom properties for theme switching, and persistent user preferences.

## Files Modified

### `frontend/index.html`
- Added a theme toggle button with sun and moon SVG icons
- Button is placed at the top of the body, outside the main container for fixed positioning
- Includes `type="button"`, `aria-label`, and `title` attributes for accessibility

### `frontend/style.css`

#### Toggle Button Styles
- **`.theme-toggle`**: Fixed positioning in top-right corner (1rem from edges), circular button (44px), uses existing design system colors
- **Icon transitions**: Smooth rotation and fade animations (0.3s ease) when switching between sun/moon icons
- **Responsive styles**: Smaller button (40px) on mobile devices

#### Light Theme CSS Variables
Complete light theme color palette via `[data-theme="light"]` selector:
- **`--background: #f8fafc`**: Light background color
- **`--surface: #ffffff`**: White surface for cards/panels
- **`--surface-hover: #f1f5f9`**: Subtle hover state
- **`--text-primary: #1e293b`**: Dark text for good contrast
- **`--text-secondary: #64748b`**: Muted secondary text
- **`--border-color: #e2e8f0`**: Light borders
- **`--user-message: #2563eb`**: Maintains primary blue for user messages
- **`--assistant-message: #f1f5f9`**: Light gray for assistant messages
- **`--shadow`**: Lighter shadow for light theme
- **`--focus-ring`**: Adjusted opacity for visibility on light backgrounds

#### Light Theme Overrides
- Scrollbar track/thumb colors adjusted for light backgrounds
- Code block backgrounds use subtle gray (`rgba(0, 0, 0, 0.06)`)

#### Smooth Theme Transitions
Added transition rules for all major UI elements:
- `body`, `.container`, `.sidebar`, `.chat-main`, `.chat-container`
- `.chat-messages`, `.message-content`, `.chat-input-container`
- `#chatInput`, `#sendButton`, `.new-chat-button`
- `.stat-item`, `.suggested-item`, `.course-title-item`
- `.stats-header`, `.suggested-header`, `.sources-collapsible`, `.source-item`

All elements transition `background-color`, `color`, `border-color`, and `box-shadow` over 0.3s ease.

### `frontend/script.js`

#### Theme Management Functions
- **`initializeTheme()`**: Loads saved theme from localStorage on page load (defaults to dark)
- **`toggleTheme()`**: Switches between dark/light themes, saves preference to localStorage
- **`updateThemeToggleLabel()`**: Updates aria-label and title for screen reader accessibility
- Added theme toggle event listener in `setupEventListeners()`

## Implementation Details

### CSS Custom Properties Approach
- All colors defined as CSS variables in `:root` (dark theme default)
- Light theme overrides via `[data-theme="light"]` selector on `<html>` element
- Theme switching is instantaneous - just changing one attribute updates all colors
- Maintains visual hierarchy and design language across both themes

### Data Attribute Usage
- Theme state stored on `document.documentElement` (the `<html>` element)
- Uses `data-theme="light"` attribute for light theme
- Dark theme is default (no attribute needed)

### Accessibility Standards
- Contrast ratios maintained: dark text (#1e293b) on light backgrounds (#f8fafc)
- Focus states visible in both themes via `--focus-ring` variable
- Full keyboard navigation support
- Dynamic aria-label updates ("Switch to light theme" / "Switch to dark theme")

## Features Summary

| Feature | Implementation |
|---------|---------------|
| Toggle Button | Fixed position, top-right, circular with sun/moon icons |
| Theme Storage | localStorage persists user preference |
| Smooth Transitions | 0.3s ease on all color properties |
| Accessibility | aria-label, keyboard nav, focus ring, good contrast |
| CSS Architecture | CSS custom properties with data-attribute switching |
| Responsive | Smaller button on mobile (40px vs 44px) |

---

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
