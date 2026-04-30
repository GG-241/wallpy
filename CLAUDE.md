# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What is wallpy

A cross-platform Python screensaver that monitors system idle time and displays fullscreen animated art. No build step — pure Python stdlib with tkinter. Supports Windows, macOS, and Linux (X11 + Wayland).

## Running the app

```bash
# Linux/macOS (recommended)
./screensaver.sh --preview              # Launch immediately
./screensaver.sh --idle-time 60         # Custom idle threshold (seconds)
./screensaver.sh --mode stars           # Force a specific art mode
./screensaver.sh --list-modes           # Print all available modes

# Windows
screensaver.bat [same options]

# Direct Python (any platform)
python3 screensaver.py --preview
```

### Verifying dependencies

```bash
python3 -c "import tkinter; print('tkinter OK')"
# Linux X11 needs: xprintidle
# Linux Wayland needs: dbus-send (usually pre-installed)
# Windows/macOS: no extra tools needed
```

## Architecture

All code lives in `screensaver.py` (~1050 lines). Three concerns:

**1. Platform detection layer** — idle time and monitor geometry are platform-specific:
- `get_idle_seconds()`: ctypes (Windows), `ioreg` (macOS), `xprintidle`/`dbus-send` (Linux)
- `get_monitors()`: `ctypes.EnumDisplayMonitors` (Windows), `AppKit.NSScreen` (macOS, y-axis flipped), `xrandr` (Linux)

**2. Art mode system** — `ArtMode` is an abstract base class with `setup(canvas, w, h, config)` and `tick()`. All 7 modes inherit from it and are registered in the `MODES` dict. `setup()` pre-allocates canvas items once; `tick()` mutates them in place — never create/delete items during animation.

**3. `Screensaver` class** — creates one borderless fullscreen tkinter window per monitor, each with its own `ArtMode` instance. A single hidden root window drives the shared event loop. Frame timing is adaptive: measures actual render time and schedules the next frame as `frame_ms - elapsed_ms`.

### Art modes

| Key | Class | Visual |
|-----|-------|--------|
| `textwaterfall` | `TextWaterfall` | Matrix-style falling Katakana |
| `matrix_continuous` | `MatrixContinuous` | Falling text from a user words file |
| `stars` | `Starfield` | Hyperspace warp (350 stars) |
| `shapes` | `BouncingShapes` | Colliding geometric shapes |
| `lissajous` | `Lissajous` | Parametric curves with hue animation |
| `life` | `GameOfLife` | Conway's Life with age-based color; auto-reseeds |
| `web` | `ParticleWeb` | 55 particles connected by proximity lines |

### Config dict keys passed to art modes

- `words_file` — path to newline-separated word list (used by `matrix_continuous`)
- `show_time` — bool, enables clock overlay
- `show_date` — bool, enables date overlay

## Adding a new art mode

1. Subclass `ArtMode`, implement `setup()` and `tick()`
2. Add an entry to the `MODES` dict: `"key": {"class": MyClass, "description": "..."}`
3. Pre-allocate all canvas items in `setup()`; reuse them via `canvas.itemconfig()` / `canvas.coords()` in `tick()`
