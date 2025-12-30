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
