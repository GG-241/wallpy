# wallpy

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Open Source](https://img.shields.io/badge/open%20source-yes-brightgreen.svg)](https://github.com/GG-241/wallpy)

A lightweight, cross-platform screensaver that displays randomly generated animated art when your computer has been idle for a set amount of time. Built to use minimal CPU and RAM — it is designed to be left running in the background permanently.

On multi-monitor setups, wallpy covers every screen simultaneously, with each display running its own independently animated art mode.

wallpy is **open source** under the [MIT License](LICENSE). Contributions, bug reports, and custom art modes are welcome — see [Contributing](#contributing) below.

---

## What it does

wallpy monitors system idle time and launches a fullscreen animation on every connected monitor when no input has been detected for a configurable duration. It exits instantly on any key press or mouse movement, returning you to your work.

Each run randomly picks one of seven generative art modes:

| Mode | Description |
|---|---|
| `textwaterfall` | Falling Katakana characters in cascading green columns |
| `matrix_continuous` | Same waterfall effect using words loaded from a text file |
| `stars` | Hyperspace warp starfield |
| `shapes` | Colourful bouncing geometric shapes |
| `lissajous` | Evolving parametric Lissajous curves |
| `life` | Conway's Game of Life with age-based colour |
| `web` | Particles connected by glowing lines when near each other |

An optional date/time overlay can be shown on top of any mode.

---

## Technical requirements

| Requirement | Details |
|---|---|
| **Python** | 3.7 or newer |
| **tkinter** | Included with most Python installs (see below) |
| **Linux X11** | `xprintidle` for idle detection |
| **Linux Wayland** | `dbus-send` (usually pre-installed) |
| **macOS** | Nothing extra — uses `ioreg` and `AppKit` for monitor detection |
| **Windows** | Nothing extra — uses `ctypes` |

---

## Install dependencies

### Python

- **Linux (Debian/Ubuntu):** `sudo apt install python3`
- **Linux (Fedora):** `sudo dnf install python3`
- **macOS:** `brew install python` or download from [python.org](https://www.python.org/downloads/)
- **Windows:** Download from [python.org](https://www.python.org/downloads/) — tick **"Add Python to PATH"** during install

### tkinter

tkinter ships with Python on Windows and macOS. On Linux it may need a separate install:

```bash
# Debian / Ubuntu
sudo apt install python3-tk

# Fedora / RHEL
sudo dnf install python3-tkinter

# Arch Linux
sudo pacman -S tk

# macOS (Homebrew Python)
brew install python-tk
```

### Idle detection (Linux only)

**X11:**
```bash
sudo apt install xprintidle      # Debian / Ubuntu
sudo dnf install xprintidle      # Fedora
```

**Wayland:** `dbus-send` is typically pre-installed. If not:
```bash
sudo apt install dbus
```

---

## Usage

```bash
# Linux / macOS — make the launcher executable once
chmod +x screensaver.sh

# Monitor and trigger after 5 minutes of idle (default)
./screensaver.sh

# Trigger after 60 seconds
./screensaver.sh --idle-time 60

# Always use a specific art mode
./screensaver.sh --mode textwaterfall

# Word-rain from a text file (cycles through all words in random order)
./screensaver.sh --mode matrix_continuous --words-file ~/my-words.txt

# Show a live clock overlay on top of any mode
./screensaver.sh --time
./screensaver.sh --date
./screensaver.sh --time --date

# Combine flags freely
./screensaver.sh --mode life --time --date --idle-time 120

# Set a custom frame rate (default: 30)
./screensaver.sh --fps 24

# Windows
screensaver.bat --idle-time 120 --time --date
```

You can also call the Python script directly on any platform:

```bash
python3 screensaver.py --idle-time 300 --mode stars --time
```

**Exit the screensaver:** press any key, move the mouse, or click.

---

## Multi-monitor support

wallpy automatically detects all connected monitors and opens a separate fullscreen window on each one. Each screen gets its own independently animated art instance. Dismissing the screensaver on any screen (key press, mouse movement, or click) closes all windows at once.

Monitor detection uses:
- **Linux:** `xrandr`
- **macOS:** `AppKit.NSScreen`
- **Windows:** `EnumDisplayMonitors` via `ctypes`

If detection fails, wallpy falls back to a single fullscreen window.

---

## Date and time overlay

The `--time` and `--date` flags add a live overlay to the bottom-right corner of every screen, on top of whichever art mode is running.

```bash
./screensaver.sh --preview --mode stars --time --date
```

- `--time` shows the current time in `HH:MM:SS` format, updated every second
- `--date` shows the current date as `Weekday,  DD Month YYYY`
- Both can be active at the same time

---

## Test that it works

**1. Verify Python and tkinter are installed:**
```bash
python3 -c "import tkinter; print('tkinter OK')"
```

**2. Preview an art mode immediately (no idle wait):**
```bash
./screensaver.sh --preview
./screensaver.sh --preview --mode textwaterfall
./screensaver.sh --preview --mode matrix_continuous --words-file ~/my-words.txt
./screensaver.sh --preview --mode life --time --date
```

**3. Test idle detection with a short timeout:**
```bash
./screensaver.sh --idle-time 5
# Stop moving the mouse — screensaver should appear within 5 seconds
```

**4. List all available modes:**
```bash
./screensaver.sh --list-modes
```

---

## Support

If you find wallpy useful, you can buy me a coffee:

[![Buy Me a Coffee](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://buymeacoffee.com/imgg)

<a href="https://buymeacoffee.com/imgg"><img src="assets/qr-buymeacoffee.png" width="160" alt="QR code — buymeacoffee.com/imgg"></a>

---

## Options

| Flag | Short | Default | Description |
|---|---|---|---|
| `--idle-time` | `-i` | `300` | Seconds of idle before activating |
| `--mode` | `-m` | random | Art mode to display |
| `--fps` | `-f` | `30` | Target frames per second (5–60) |
| `--words-file` | `-w` | — | Text file of words for `matrix_continuous` |
| `--time` | — | off | Overlay current time on all modes |
| `--date` | — | off | Overlay current date on all modes |
| `--preview` | `-p` | — | Launch immediately, skip idle check |
| `--list-modes` | — | — | Print available modes and exit |

---

## Modding — adding a custom art mode

All animation logic lives in `screensaver.py`. Every art mode is a class that inherits from `ArtMode` and implements two methods.

### ArtMode API

```python
class ArtMode:
    description: str          # shown by --list-modes

    def setup(self, canvas: tk.Canvas, width: int,
              height: int, config: dict) -> None:
        """Called once. Create all canvas items here — do NOT create
        items inside tick(). Store item IDs on self for reuse."""

    def tick(self) -> None:
        """Called every frame. Move/recolour existing canvas items.
        Never call canvas.create_*() here — only canvas.coords(),
        canvas.itemconfig(), etc."""
```

`config` is a dict that may contain:
- `show_time` / `show_date` — bool, whether the clock overlay is active
- `words_file` — str path, only relevant to text-based modes

### Step-by-step: writing a new mode

**1. Subclass `ArtMode`**

```python
class Pulse(ArtMode):
    description = "Expanding concentric rings"

    def setup(self, canvas, width, height, config):
        self.canvas = canvas
        self.cx, self.cy = width // 2, height // 2
        self.rings = [
            canvas.create_oval(0, 0, 0, 0, outline="#00ff88", width=2)
            for _ in range(6)
        ]
        self.phase = 0

    def tick(self):
        self.phase = (self.phase + 2) % 360
        for i, ring in enumerate(self.rings):
            offset = (self.phase + i * 60) % 360
            r = int(50 + 200 * (offset / 360))
            self.canvas.coords(ring,
                self.cx - r, self.cy - r,
                self.cx + r, self.cy + r)
            alpha = int(255 * (1 - offset / 360))
            colour = f"#{alpha:02x}ff{alpha:02x}"
            self.canvas.itemconfig(ring, outline=colour)
```

**2. Register the mode**

Find the `MODES` dict near the bottom of `screensaver.py` and add your class:

```python
MODES = {
    "textwaterfall":    TextWaterfall,
    "matrix_continuous": MatrixContinuous,
    "stars":            Starfield,
    "shapes":           BouncingShapes,
    "lissajous":        Lissajous,
    "life":             GameOfLife,
    "web":              ParticleWeb,
    "pulse":            Pulse,          # ← your new mode
}
```

**3. Test it**

```bash
python3 screensaver.py --preview --mode pulse
```

### Tips

- `setup()` is the **only** place to call `canvas.create_*()`. Pre-allocate every item you will ever need.
- `tick()` should only call `canvas.coords()`, `canvas.itemconfig()`, or similar — never create or delete items.
- Keep `tick()` fast. At 30 FPS you have ~33 ms per frame across all monitors.
- Use `colorsys.hsv_to_rgb()` (already imported) for smooth colour cycling.
- The `config` dict is passed to both `setup()` and is accessible as `self.config` if you store it.

---

## Contributing

1. Fork the repository on GitHub: [github.com/GG-241/wallpy](https://github.com/GG-241/wallpy)
2. Create a branch: `git checkout -b my-new-mode`
3. Make your changes and test them with `--preview`
4. Open a pull request with a short description and a screenshot or GIF of your mode

All contributions are welcome: new art modes, bug fixes, platform improvements, or documentation.

---

## License

MIT — see [LICENSE](LICENSE) for the full text.
