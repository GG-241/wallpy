#!/usr/bin/env python3
"""
wallpy screensaver — Cross-platform generative art screensaver.

Monitors system idle time and displays animated art when the computer
is inactive. Exits on any keyboard or mouse input.

Requirements: Python 3.7+, tkinter (stdlib)
  Linux X11 : xprintidle  (apt install xprintidle / dnf install xprintidle)
  Linux Wayland: dbus-send (usually pre-installed)
  macOS  : nothing extra (uses ioreg)
  Windows: nothing extra (uses ctypes)

Usage:
    python screensaver.py                     # monitor, random art after 5 min
    python screensaver.py --idle-time 60      # trigger after 60 s
    python screensaver.py --mode textwaterfall  # always use text waterfall
    python screensaver.py --preview           # launch art instantly (no wait)
    python screensaver.py --list-modes        # show available art modes
"""

import sys
import re
import json
import math
import time
import random
import colorsys
import platform
import subprocess
import argparse
import tkinter as tk
from pathlib import Path
from typing import List, Optional, Tuple


# ─────────────────────────────────────────────────────────────────────────────
# IDLE-TIME DETECTION  (Windows / macOS / Linux X11 & Wayland)
# ─────────────────────────────────────────────────────────────────────────────

def get_idle_seconds() -> float:
    """Return how many seconds the system input has been idle."""
    system = platform.system()
    try:
        if system == "Windows":
            import ctypes
            class _LASTINPUTINFO(ctypes.Structure):
                _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_ulong)]
            lii = _LASTINPUTINFO()
            lii.cbSize = ctypes.sizeof(_LASTINPUTINFO)
            ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii))   # type: ignore[attr-defined]
            ms = ctypes.windll.kernel32.GetTickCount() - lii.dwTime    # type: ignore[attr-defined]
            return ms / 1000.0

        elif system == "Darwin":
            out = subprocess.check_output(["ioreg", "-c", "IOHIDSystem"], text=True)
            for line in out.splitlines():
                if "HIDIdleTime" in line:
                    ns = int(line.split("=")[-1].strip())
                    return ns / 1_000_000_000.0

        else:  # Linux / BSD
            # ── X11 via xprintidle ──────────────────────────────────────────
            try:
                ms = subprocess.check_output(
                    ["xprintidle"], text=True, stderr=subprocess.DEVNULL
                ).strip()
                return int(ms) / 1000.0
            except (FileNotFoundError, subprocess.CalledProcessError, ValueError):
                pass
            # ── Wayland via dbus ────────────────────────────────────────────
            try:
                out = subprocess.check_output([
                    "dbus-send", "--print-reply",
                    "--dest=org.freedesktop.ScreenSaver",
                    "/org/freedesktop/ScreenSaver",
                    "org.freedesktop.ScreenSaver.GetSessionIdleTime",
                ], text=True, stderr=subprocess.DEVNULL)
                ms = int(out.split()[-1])
                return ms / 1000.0
            except Exception:
                pass
    except Exception:
        pass
    return 0.0


# ─────────────────────────────────────────────────────────────────────────────
# BASE ART CLASS
# ─────────────────────────────────────────────────────────────────────────────

class ArtMode:
    """Base class for all art modes."""
    name: str = ""
    description: str = ""

    def __init__(self, canvas: tk.Canvas, width: int, height: int,
                 config: Optional[dict] = None):
        self.canvas = canvas
        self.width = width
        self.height = height
        self.config = config or {}

    def setup(self) -> None:
        """Called once before animation starts."""

    def tick(self) -> None:
        """Called every frame to advance and redraw the animation."""


# ─────────────────────────────────────────────────────────────────────────────
# ART MODE 1 — MATRIX RAIN
# ─────────────────────────────────────────────────────────────────────────────

class TextWaterfall(ArtMode):
    name = "textwaterfall"
    description = "Green falling Katakana characters"

    _CHARS = (
        "アイウエオカキクケコサシスセソタチツテトナニヌネノ"
        "ハヒフヘホマミムメモヤユヨラリルレロワヲン"
        "0123456789ABCDEF"
    )

    def setup(self) -> None:
        self.canvas.configure(bg="black")
        self.col_w = 16
        self.row_h = 14
        self.trail = 22
        self.ncols = self.width // self.col_w + 1
        self._max_row = self.height // self.row_h + self.trail + 2
        # Pre-compute trail colours once
        self._colors = ["#ffffff"] + [
            f"#00{max(0, 210 - t * (210 // self.trail)):02x}00"
            for t in range(1, self.trail)
        ]
        # head position (in rows) for each column
        self.heads = [random.randint(-self.trail, 0) for _ in range(self.ncols)]
        # pre-create text objects: [col][trail_index]
        self.items: List[List[int]] = []
        for c in range(self.ncols):
            col = []
            x = c * self.col_w + self.col_w // 2
            for _ in range(self.trail):
                item = self.canvas.create_text(
                    x, -20, text="", font=("Courier", 12, "bold"), fill="black"
                )
                col.append(item)
            self.items.append(col)

    def tick(self) -> None:
        max_row = self._max_row
        colors = self._colors
        H = self.height
        row_h = self.row_h
        for c in range(self.ncols):
            self.heads[c] += 1
            if self.heads[c] > max_row:
                self.heads[c] = random.randint(-self.trail, 0)

            head = self.heads[c]
            x = c * self.col_w + self.col_w // 2
            for t, item in enumerate(self.items[c]):
                y = (head - t) * row_h
                if 0 <= y <= H + row_h:
                    self.canvas.itemconfigure(item, text=random.choice(self._CHARS), fill=colors[t])
                    self.canvas.coords(item, x, y)
                else:
                    self.canvas.itemconfigure(item, text="")


# ─────────────────────────────────────────────────────────────────────────────
# ART MODE 1b — MATRIX CONTINUOUS  (word-rain from a text file)
# ─────────────────────────────────────────────────────────────────────────────

class MatrixContinuous(ArtMode):
    name = "matrix_continuous"
    description = "Matrix rain using words loaded from a text file"

    _FALLBACK = [
        "MATRIX", "CODE", "DATA", "FLOW", "RAIN", "GRID", "NODE", "LOOP",
        "CORE", "SYNC", "BYTE", "HASH", "LINK", "WIRE", "ZERO", "ONE",
        "SIGNAL", "PULSE", "WAVE", "STREAM", "VOID", "HEAP", "STACK",
    ]

    def setup(self) -> None:
        self.canvas.configure(bg="black")

        # ── Load words ──────────────────────────────────────────────────────
        words_file = self.config.get("words_file")
        words: List[str] = []
        if words_file:
            try:
                with open(words_file, "r", encoding="utf-8", errors="replace") as fh:
                    words = fh.read().split()
            except OSError as exc:
                print(f"[wallpy] Warning: cannot read '{words_file}': {exc}")
        # Truncate very long tokens; fall back to built-in list if file is empty
        self._words = [w[:14] for w in words] if words else self._FALLBACK.copy()

        # ── Column geometry — sized to fit the longest word ──────────────────
        max_chars  = min(max(len(w) for w in self._words), 14)
        self.font_size = 11
        # Courier 11 bold: ~7 px per char is a good cross-platform estimate
        self.col_w  = max_chars * 7 + 10
        self.row_h  = 17
        self.trail  = 18
        self.ncols  = self.width // self.col_w + 1
        self._max_row = self.height // self.row_h + self.trail + 2

        # Pre-compute trail colours
        self._colors = ["#ffffff"] + [
            f"#00{max(0, 200 - t * (200 // self.trail)):02x}00"
            for t in range(1, self.trail)
        ]

        self.heads = [random.randint(-self.trail, 0) for _ in range(self.ncols)]

        # Pre-create text items
        font = ("Courier", self.font_size, "bold")
        self.items: List[List[int]] = []
        for c in range(self.ncols):
            col = []
            x = c * self.col_w + self.col_w // 2
            for _ in range(self.trail):
                col.append(self.canvas.create_text(
                    x, -20, text="", font=font, fill="black"
                ))
            self.items.append(col)

        # Shuffled word pool — cycles through every word before reshuffling
        self._pool = self._words.copy()
        random.shuffle(self._pool)
        self._pool_idx = 0

    def _next_word(self) -> str:
        word = self._pool[self._pool_idx]
        self._pool_idx += 1
        if self._pool_idx >= len(self._pool):
            random.shuffle(self._pool)
            self._pool_idx = 0
        return word

    def tick(self) -> None:
        max_row = self._max_row
        colors  = self._colors
        H, row_h = self.height, self.row_h

        for c in range(self.ncols):
            self.heads[c] += 1
            if self.heads[c] > max_row:
                self.heads[c] = random.randint(-self.trail, 0)

            head = self.heads[c]
            x    = c * self.col_w + self.col_w // 2
            for t, item in enumerate(self.items[c]):
                y = (head - t) * row_h
                if 0 <= y <= H + row_h:
                    self.canvas.itemconfigure(item,
                        text=self._next_word(), fill=colors[t])
                    self.canvas.coords(item, x, y)
                else:
                    self.canvas.itemconfigure(item, text="")


# ─────────────────────────────────────────────────────────────────────────────
# ART MODE 2 — STARFIELD WARP
# ─────────────────────────────────────────────────────────────────────────────

class Starfield(ArtMode):
    name = "stars"
    description = "Hyperspace star-warp effect"

    N = 350

    def setup(self) -> None:
        self.canvas.configure(bg="black")
        self.cx = self.width / 2
        self.cy = self.height / 2
        # Each star: [nx, ny, z, speed]  nx/ny in [-1,1]
        self.stars = [self._new_star(initial=True) for _ in range(self.N)]
        self.ovals = [
            self.canvas.create_oval(-2, -2, 2, 2, fill="white", outline="")
            for _ in range(self.N)
        ]

    def _new_star(self, initial: bool = False):
        z = random.uniform(0.05, 1.0) if initial else 1.0
        return [
            random.uniform(-1, 1),
            random.uniform(-1, 1),
            z,
            random.uniform(0.006, 0.022),
        ]

    def tick(self) -> None:
        for i, s in enumerate(self.stars):
            s[2] -= s[3]
            if s[2] <= 0.01:
                self.stars[i] = self._new_star()
                s = self.stars[i]
            z = s[2]
            px = self.cx + s[0] * self.cx / z
            py = self.cy + s[1] * self.cy / z
            sz = max(1, int(3.5 * (1 - z)))
            b = int(255 * (1 - z))
            b = max(40, b)
            color = f"#{b:02x}{b:02x}{b:02x}"
            self.canvas.coords(self.ovals[i], px - sz, py - sz, px + sz, py + sz)
            self.canvas.itemconfigure(self.ovals[i], fill=color)


# ─────────────────────────────────────────────────────────────────────────────
# ART MODE 3 — BOUNCING SHAPES
# ─────────────────────────────────────────────────────────────────────────────

class BouncingShapes(ArtMode):
    name = "shapes"
    description = "Colourful geometric shapes bouncing around"

    N = 28
    PALETTE = [
        "#e63946", "#457b9d", "#a8dadc", "#f4a261", "#2a9d8f",
        "#e9c46a", "#264653", "#8338ec", "#ff006e", "#3a86ff",
        "#06d6a0", "#ffd166", "#ef476f", "#118ab2",
    ]

    def setup(self) -> None:
        self.canvas.configure(bg="#080810")
        self.data: List[List] = []
        self.items: List[int] = []
        for _ in range(self.N):
            r = random.randint(14, 55)
            x = random.uniform(r + 1, self.width - r - 1)
            y = random.uniform(r + 1, self.height - r - 1)
            speed = random.uniform(1.5, 4.0)
            angle = random.uniform(0, 2 * math.pi)
            vx = speed * math.cos(angle)
            vy = speed * math.sin(angle)
            color = random.choice(self.PALETTE)
            kind = random.choice(["oval", "rect", "tri", "hex"])
            item = self._make_item(kind, x, y, r, color)
            self.data.append([x, y, vx, vy, r, kind])
            self.items.append(item)

    def _tri_pts(self, x, y, r):
        a = math.pi / 2
        return [
            x + r * math.cos(a + 0 * 2*math.pi/3),
            y - r * math.sin(a + 0 * 2*math.pi/3),
            x + r * math.cos(a + 1 * 2*math.pi/3),
            y - r * math.sin(a + 1 * 2*math.pi/3),
            x + r * math.cos(a + 2 * 2*math.pi/3),
            y - r * math.sin(a + 2 * 2*math.pi/3),
        ]

    def _hex_pts(self, x, y, r):
        pts = []
        for k in range(6):
            a = k * math.pi / 3
            pts += [x + r * math.cos(a), y + r * math.sin(a)]
        return pts

    def _make_item(self, kind, x, y, r, color) -> int:
        if kind == "oval":
            return self.canvas.create_oval(x-r, y-r, x+r, y+r, fill=color, outline="")
        elif kind == "rect":
            return self.canvas.create_rectangle(x-r, y-r, x+r, y+r, fill=color, outline="")
        elif kind == "tri":
            return self.canvas.create_polygon(self._tri_pts(x, y, r), fill=color, outline="")
        else:
            return self.canvas.create_polygon(self._hex_pts(x, y, r), fill=color, outline="")

    def tick(self) -> None:
        for d, item in zip(self.data, self.items):
            x, y, vx, vy, r, kind = d
            x += vx;  y += vy
            if x - r <= 0 or x + r >= self.width:
                vx = -vx;  x += vx * 2
            if y - r <= 0 or y + r >= self.height:
                vy = -vy;  y += vy * 2
            d[0], d[1], d[2], d[3] = x, y, vx, vy
            if kind == "oval":
                self.canvas.coords(item, x-r, y-r, x+r, y+r)
            elif kind == "rect":
                self.canvas.coords(item, x-r, y-r, x+r, y+r)
            elif kind == "tri":
                self.canvas.coords(item, *self._tri_pts(x, y, r))
            else:
                self.canvas.coords(item, *self._hex_pts(x, y, r))


# ─────────────────────────────────────────────────────────────────────────────
# ART MODE 4 — LISSAJOUS CURVES
# ─────────────────────────────────────────────────────────────────────────────

class Lissajous(ArtMode):
    name = "lissajous"
    description = "Evolving Lissajous parametric curves"

    N_PTS = 600

    def setup(self) -> None:
        self.canvas.configure(bg="black")
        self.delta = 0.0
        self.a = random.choice([1, 2, 3, 4, 5])
        self.b = random.choice([1, 2, 3, 4, 5])
        self.hue = random.random()
        # Pre-build flat coordinate list
        coords = [0.0] * (self.N_PTS * 2 + 2)
        self.curve = self.canvas.create_line(*coords, fill="white", width=2, smooth=True)

    @staticmethod
    def _hsv(h, s=0.85, v=1.0) -> str:
        r, g, b = colorsys.hsv_to_rgb(h % 1.0, s, v)
        return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"

    def tick(self) -> None:
        self.delta += 0.006
        self.hue  += 0.0015
        cx, cy = self.width / 2, self.height / 2
        rx, ry = cx * 0.88, cy * 0.88
        pts: List[float] = []
        for i in range(self.N_PTS + 1):
            t = 2 * math.pi * i / self.N_PTS
            pts.append(cx + rx * math.sin(self.a * t + self.delta))
            pts.append(cy + ry * math.sin(self.b * t))
        self.canvas.coords(self.curve, pts)
        self.canvas.itemconfigure(self.curve, fill=self._hsv(self.hue))
        # Randomly mutate frequency ratio
        if random.random() < 0.0015:
            self.a = random.choice([1, 2, 3, 4, 5])
            self.b = random.choice([1, 2, 3, 4, 5])


# ─────────────────────────────────────────────────────────────────────────────
# ART MODE 5 — GAME OF LIFE
# ─────────────────────────────────────────────────────────────────────────────

class GameOfLife(ArtMode):
    name = "life"
    description = "Conway's Game of Life with age-based colours"

    CELL = 12          # larger cells = fewer iterations per frame
    _LOGIC_EVERY = 3   # run cell logic every N display frames (~10 Hz at 30 fps)

    def setup(self) -> None:
        self.canvas.configure(bg="black")
        self.cols = self.width  // self.CELL
        self.rows = self.height // self.CELL
        self.grid = self._random_grid(0.30)
        self.age: List[List[int]] = [[0] * self.cols for _ in range(self.rows)]
        self.rects = {}   # flat key (r*cols+c) -> canvas item id
        self.tick_count = 0
        # Pre-compute colour LUT for ages 0-59
        self._color_lut = [self._cell_color(a) for a in range(60)]

    def _random_grid(self, density: float):
        return [
            [random.random() < density for _ in range(self.cols)]
            for _ in range(self.rows)
        ]

    @staticmethod
    def _cell_color(age: int) -> str:
        if age <= 3:
            return f"#80ff80"
        elif age <= 12:
            t = (age - 3) / 9
            r = int(128 - 80 * t)
            g = int(255 - 155 * t)
            b = int(128 + 80 * t)
            return f"#{r:02x}{g:02x}{b:02x}"
        else:
            t = min(1.0, (age - 12) / 25)
            b = int(208 + 47 * t)
            rg = int(48 - 30 * t)
            return f"#{rg:02x}{rg:02x}{b:02x}"

    def tick(self) -> None:
        self.tick_count += 1
        # Throttle: only run logic every _LOGIC_EVERY display frames
        if self.tick_count % self._LOGIC_EVERY != 0:
            return

        cols, rows = self.cols, self.rows
        old = self.grid
        new_grid = [[False] * cols for _ in range(rows)]

        for r in range(rows):
            rm1 = (r - 1) % rows
            rp1 = (r + 1) % rows
            for c in range(cols):
                n = (
                    old[rm1][(c-1) % cols] + old[rm1][c] + old[rm1][(c+1) % cols] +
                    old[r ][(c-1) % cols]                 + old[r ][(c+1) % cols] +
                    old[rp1][(c-1) % cols] + old[rp1][c] + old[rp1][(c+1) % cols]
                )
                alive = old[r][c]
                new_grid[r][c] = (n == 3) or (alive and n == 2)
                if new_grid[r][c]:
                    self.age[r][c] = (self.age[r][c] + 1) if alive else 1
                else:
                    self.age[r][c] = 0

        # Sync canvas — only touch changed cells
        C = self.CELL
        lut = self._color_lut
        canvas = self.canvas
        rects = self.rects
        for r in range(rows):
            for c in range(cols):
                was, is_ = old[r][c], new_grid[r][c]
                key = r * cols + c
                if is_:
                    age = self.age[r][c]
                    if was != is_ or age % 4 == 0:
                        color = lut[min(age, 59)]
                        if key in rects:
                            canvas.itemconfigure(rects[key], fill=color)
                        else:
                            x1, y1 = c * C, r * C
                            rects[key] = canvas.create_rectangle(
                                x1, y1, x1 + C - 1, y1 + C - 1,
                                fill=color, outline=""
                            )
                elif was and key in rects:
                    canvas.delete(rects.pop(key))

        self.grid = new_grid

        # Re-seed if population collapses
        if self.tick_count % 250 == 0:
            live = sum(sum(row) for row in self.grid)
            if live < cols * rows * 0.04:
                self.grid = self._random_grid(0.28)


# ─────────────────────────────────────────────────────────────────────────────
# ART MODE 6 — PARTICLE WEB
# ─────────────────────────────────────────────────────────────────────────────

class ParticleWeb(ArtMode):
    name = "web"
    description = "Particles connected by glowing lines when near each other"

    N = 55
    LINK_DIST = 115

    def setup(self) -> None:
        self.canvas.configure(bg="#04040e")
        self._ld2 = self.LINK_DIST * self.LINK_DIST
        self.particles = [
            [
                random.uniform(0, self.width),
                random.uniform(0, self.height),
                random.uniform(-1.4, 1.4) or 0.6,
                random.uniform(-1.4, 1.4) or 0.6,
            ]
            for _ in range(self.N)
        ]
        # Create line pool first so dots are drawn on top
        max_lines = self.N * (self.N - 1) // 2
        self.line_pool = [
            self.canvas.create_line(0, 0, 1, 1, fill="", width=1)
            for _ in range(max_lines)
        ]
        self.dots = [
            self.canvas.create_oval(-3, -3, 3, 3, fill="#7799ff", outline="")
            for _ in range(self.N)
        ]
        self._active_lines = 0

    def tick(self) -> None:
        W, H = self.width, self.height
        ld2 = self._ld2
        particles = self.particles
        canvas = self.canvas

        # Move
        for p in particles:
            p[0] = (p[0] + p[2]) % W
            p[1] = (p[1] + p[3]) % H

        # Update dots
        for i, p in enumerate(particles):
            canvas.coords(self.dots[i], p[0]-3, p[1]-3, p[0]+3, p[1]+3)

        # Hide previously active lines
        for k in range(self._active_lines):
            canvas.itemconfigure(self.line_pool[k], fill="")

        # Draw connections using pool — no sqrt, alpha from d²
        pool_idx = 0
        N = self.N
        for i in range(N):
            px, py = particles[i][0], particles[i][1]
            for j in range(i + 1, N):
                dx = px - particles[j][0]
                dy = py - particles[j][1]
                d2 = dx * dx + dy * dy
                if d2 < ld2:
                    alpha = int(180 * (1 - d2 / ld2))
                    color = f"#{alpha:02x}{alpha:02x}{min(255, alpha + 60):02x}"
                    canvas.coords(
                        self.line_pool[pool_idx],
                        px, py, particles[j][0], particles[j][1],
                    )
                    canvas.itemconfigure(self.line_pool[pool_idx], fill=color)
                    pool_idx += 1

        self._active_lines = pool_idx


# ─────────────────────────────────────────────────────────────────────────────
# REGISTRY
# ─────────────────────────────────────────────────────────────────────────────

MODES = {
    cls.name: cls
    for cls in [
        TextWaterfall, MatrixContinuous, Starfield, BouncingShapes,
        Lissajous, GameOfLife, ParticleWeb,
    ]
}


# ─────────────────────────────────────────────────────────────────────────────
# MONITOR DETECTION  (x, y, width, height per display)
# ─────────────────────────────────────────────────────────────────────────────

def _monitors_linux() -> List[Tuple[int, int, int, int]]:
    out = subprocess.check_output(
        ["xrandr", "--query"], text=True, stderr=subprocess.DEVNULL
    )
    result = []
    for line in out.splitlines():
        if " connected" in line:
            m = re.search(r'(\d+)x(\d+)\+(\d+)\+(\d+)', line)
            if m:
                w, h, x, y = map(int, m.groups())
                result.append((x, y, w, h))
    return result


def _monitors_macos() -> List[Tuple[int, int, int, int]]:
    try:
        from AppKit import NSScreen  # type: ignore[import]
        primary_h = int(NSScreen.mainScreen().frame().size.height)
        result = []
        for screen in NSScreen.screens():
            f = screen.frame()
            x = int(f.origin.x)
            # AppKit uses bottom-left origin; flip to top-left for tkinter
            y = primary_h - int(f.origin.y) - int(f.size.height)
            result.append((x, y, int(f.size.width), int(f.size.height)))
        return result
    except ImportError:
        return []


def _monitors_windows() -> List[Tuple[int, int, int, int]]:
    import ctypes
    import ctypes.wintypes
    monitors: List[Tuple[int, int, int, int]] = []

    def _cb(hMon, hdcMon, lpRect, dwData):
        r = lpRect.contents
        monitors.append((r.left, r.top, r.right - r.left, r.bottom - r.top))
        return True

    MEPFN = ctypes.WINFUNCTYPE(
        ctypes.c_bool, ctypes.c_ulong, ctypes.c_ulong,
        ctypes.POINTER(ctypes.wintypes.RECT), ctypes.c_double,
    )
    ctypes.windll.user32.EnumDisplayMonitors(None, None, MEPFN(_cb), 0)  # type: ignore[attr-defined]
    return monitors


def get_monitors() -> List[Tuple[int, int, int, int]]:
    """Return (x, y, w, h) for every connected monitor, sorted left-to-right."""
    system = platform.system()
    try:
        if system == "Windows":
            monitors = _monitors_windows()
        elif system == "Darwin":
            monitors = _monitors_macos()
        else:
            monitors = _monitors_linux()
        if monitors:
            return sorted(monitors, key=lambda m: (m[0], m[1]))
    except Exception:
        pass
    return []   # caller falls back to single-screen


# ─────────────────────────────────────────────────────────────────────────────
# CLOCK OVERLAY
# ─────────────────────────────────────────────────────────────────────────────

def _add_clock_overlay(
    root: tk.Tk,
    canvas: tk.Canvas,
    width: int,
    height: int,
    show_time: bool,
    show_date: bool,
    running: List[bool],
) -> None:
    """Draw a live time/date in the bottom-right corner of canvas."""
    from datetime import datetime

    if not show_time and not show_date:
        return

    pad = 22
    items: List[tuple] = []

    if show_date:
        item = canvas.create_text(
            width - pad, height - pad,
            text="", anchor="se",
            font=("Courier", 20),
            fill="#00aa55",
        )
        items.append(("date", item))

    if show_time:
        # sits above the date line if both are shown
        y_off = 32 if show_date else 0
        item = canvas.create_text(
            width - pad, height - pad - y_off,
            text="", anchor="se",
            font=("Courier", 38, "bold"),
            fill="#00ff88",
        )
        items.append(("time", item))

    def _update() -> None:
        if not running[0]:
            return
        now = datetime.now()
        try:
            for kind, itm in items:
                if kind == "time":
                    canvas.itemconfigure(itm, text=now.strftime("%H:%M:%S"))
                else:
                    canvas.itemconfigure(itm, text=now.strftime("%A,  %d %B %Y"))
                canvas.tag_raise(itm)
        except tk.TclError:
            return
        root.after(1000, _update)

    root.after(0, _update)


# ─────────────────────────────────────────────────────────────────────────────
# SCREENSAVER WINDOW
# ─────────────────────────────────────────────────────────────────────────────

class Screensaver:
    """One borderless window per monitor, each running its own art mode."""

    def __init__(self, mode: Optional[str], fps: int,
                 config: Optional[dict] = None):
        _frame_ms = max(1, 1000 // fps)
        cfg = config or {}

        # Invisible coordinator root — never shown, drives the event loop
        root = tk.Tk()
        root.withdraw()

        monitors = get_monitors()
        if not monitors:
            # Fallback: treat the whole virtual desktop as one screen
            monitors = [(0, 0, root.winfo_screenwidth(), root.winfo_screenheight())]

        _running = [True]
        _windows: List[tk.Toplevel] = []
        _arts:    List[ArtMode]    = []

        def _exit(_e=None):
            if not _running[0]:
                return
            _running[0] = False
            for win in _windows:
                try:
                    win.destroy()
                except Exception:
                    pass
            try:
                root.destroy()
            except Exception:
                pass

        show_time = cfg.get("show_time", False)
        show_date = cfg.get("show_date", False)

        for mx, my, mw, mh in monitors:
            chosen = mode or random.choice(list(MODES))

            win = tk.Toplevel(root)
            win.overrideredirect(True)          # no title-bar / decorations
            win.geometry(f"{mw}x{mh}+{mx}+{my}")
            win.configure(bg="black", cursor="none")
            win.attributes("-topmost", True)

            canvas = tk.Canvas(win, bg="black", highlightthickness=0,
                               width=mw, height=mh)
            canvas.pack(fill=tk.BOTH, expand=True)
            win.update_idletasks()

            for event in ("<KeyPress>", "<ButtonPress>"):
                win.bind(event, _exit)
            # Delay motion binding so window-placement events don't trigger exit
            win.after(500, lambda w=win: w.bind("<Motion>", _exit))

            art: ArtMode = MODES[chosen](canvas, mw, mh, config=cfg)
            art.setup()

            _add_clock_overlay(root, canvas, mw, mh,
                               show_time=show_time, show_date=show_date,
                               running=_running)

            _windows.append(win)
            _arts.append(art)

        # Give focus to the first window so key events are captured immediately
        if _windows:
            _windows[0].focus_force()

        _perf = time.perf_counter

        def _tick():
            if not _running[0]:
                return
            t0 = _perf()
            try:
                for art in _arts:
                    art.tick()
            except tk.TclError:
                return  # a window was destroyed between scheduling and firing
            elapsed_ms = int((_perf() - t0) * 1000)
            delay = max(1, _frame_ms - elapsed_ms)
            root.after(delay, _tick)

        root.after(0, _tick)
        root.mainloop()


# ─────────────────────────────────────────────────────────────────────────────
# IDLE MONITOR LOOP
# ─────────────────────────────────────────────────────────────────────────────

def monitor(idle_threshold: float, mode: Optional[str], fps: int,
            config: Optional[dict] = None) -> None:
    print(f"[wallpy] Monitoring — screensaver triggers after {idle_threshold:.0f}s idle.")
    print("[wallpy] Press Ctrl+C to stop.\n")
    screensaver_running = False
    while True:
        idle = get_idle_seconds()
        if idle >= idle_threshold:
            if not screensaver_running:
                print(f"[wallpy] {idle:.0f}s idle — launching screensaver…")
                screensaver_running = True
            Screensaver(mode, fps, config=config)
            print("[wallpy] Dismissed. Watching again…")
            screensaver_running = False
        else:
            time.sleep(2)


# ─────────────────────────────────────────────────────────────────────────────
# SETTINGS / CONTROL UI  (shown when launched as a .app bundle)
# ─────────────────────────────────────────────────────────────────────────────

class WallpyApp:
    """Settings window and monitoring controller for GUI / .app mode."""

    _CONFIG = Path.home() / ".wallpy" / "config.json"

    # ── colour palette ────────────────────────────────────────────────────────
    _BG     = "#111111"
    _TITLE  = "#00ff88"
    _LABEL  = "#66aaff"
    _VALUE  = "#ffffff"
    _CHK    = "#cc88ff"
    _STATUS = "#ffcc00"
    _SEP    = "#333333"
    _FONT   = "Courier"

    def __init__(self, args) -> None:
        self.root = tk.Tk()
        self.root.title("wallpy")
        self.root.resizable(False, False)
        self.root.configure(bg=self._BG)

        saved = self._load_config()

        self._monitoring   = False
        self._saver_active = False

        self.idle_var   = tk.DoubleVar(value=saved.get("idle_time",  args.idle_time))
        self.mode_var   = tk.StringVar(value=saved.get("mode",       args.mode or "random"))
        self.fps_var    = tk.IntVar(   value=saved.get("fps",        args.fps))
        self.time_var   = tk.BooleanVar(value=saved.get("show_time", getattr(args, "time", False)))
        self.date_var   = tk.BooleanVar(value=saved.get("show_date", args.date))
        self.status_var = tk.StringVar(value="● not monitoring")

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── helpers ───────────────────────────────────────────────────────────────

    def _lbl(self, parent, text, **kw):
        return tk.Label(parent, text=text, bg=self._BG, fg=self._LABEL,
                        font=(self._FONT, 10, "bold"), **kw)

    def _val_lbl(self, parent, **kw):
        return tk.Label(parent, bg=self._BG, fg=self._VALUE,
                        font=(self._FONT, 11), **kw)

    # ── persistence ───────────────────────────────────────────────────────────

    def _load_config(self) -> dict:
        try:
            return json.loads(self._CONFIG.read_text())
        except Exception:
            return {}

    def _save_config(self) -> None:
        try:
            self._CONFIG.parent.mkdir(parents=True, exist_ok=True)
            self._CONFIG.write_text(json.dumps({
                "idle_time": self.idle_var.get(),
                "mode":      self.mode_var.get(),
                "fps":       self.fps_var.get(),
                "show_time": self.time_var.get(),
                "show_date": self.date_var.get(),
            }, indent=2))
        except Exception:
            pass

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        BG  = self._BG
        F   = self._FONT
        PAD = 22

        outer = tk.Frame(self.root, bg=BG, padx=PAD, pady=PAD)
        outer.pack(fill=tk.BOTH, expand=True)

        # title
        tk.Label(outer, text="wallpy", bg=BG, fg=self._TITLE,
                 font=(F, 26, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 20))

        # art mode
        self._lbl(outer, "ART MODE").grid(row=1, column=0, sticky="w")
        om = tk.OptionMenu(outer, self.mode_var, "random", *MODES.keys())
        om.config(bg="#1a1a2e", fg=self._VALUE, font=(F, 11),
                  activebackground="#2a2a4e", activeforeground=self._VALUE,
                  highlightthickness=0, bd=0)
        om["menu"].config(bg="#1a1a2e", fg=self._VALUE, font=(F, 11),
                          activebackground="#2a2a4e", activeforeground=self._VALUE)
        om.grid(row=1, column=1, columnspan=2, sticky="ew", padx=(14, 0))

        # idle time
        self._lbl(outer, "IDLE TIME").grid(row=2, column=0, sticky="w", pady=(14, 0))
        idle_lbl = tk.StringVar()
        def _upd_idle(*_): idle_lbl.set(f"{int(self.idle_var.get())} s")
        self.idle_var.trace_add("write", _upd_idle); _upd_idle()
        tk.Scale(outer, variable=self.idle_var, from_=10, to=1800,
                 orient=tk.HORIZONTAL, showvalue=False, length=190,
                 bg=BG, fg=self._TITLE, troughcolor="#2a2a2a",
                 highlightthickness=0, bd=0).grid(
            row=2, column=1, sticky="ew", padx=(14, 0), pady=(14, 0))
        self._val_lbl(outer, textvariable=idle_lbl, width=6, anchor="w").grid(
            row=2, column=2, sticky="w", pady=(14, 0))

        # fps
        self._lbl(outer, "FPS").grid(row=3, column=0, sticky="w", pady=(8, 0))
        fps_lbl = tk.StringVar()
        def _upd_fps(*_): fps_lbl.set(str(self.fps_var.get()))
        self.fps_var.trace_add("write", _upd_fps); _upd_fps()
        tk.Scale(outer, variable=self.fps_var, from_=5, to=60,
                 orient=tk.HORIZONTAL, showvalue=False, length=190,
                 bg=BG, fg=self._TITLE, troughcolor="#2a2a2a",
                 highlightthickness=0, bd=0).grid(
            row=3, column=1, sticky="ew", padx=(14, 0), pady=(8, 0))
        self._val_lbl(outer, textvariable=fps_lbl, width=6, anchor="w").grid(
            row=3, column=2, sticky="w", pady=(8, 0))

        # overlay toggles
        self._lbl(outer, "OVERLAY").grid(row=4, column=0, sticky="w", pady=(12, 0))
        chk = tk.Frame(outer, bg=BG)
        chk.grid(row=4, column=1, columnspan=2, sticky="w",
                 padx=(14, 0), pady=(12, 0))
        ckw = dict(bg=BG, fg=self._CHK, selectcolor="#2a2a2a",
                   activebackground=BG, activeforeground=self._CHK,
                   font=(F, 11), bd=0, highlightthickness=0)
        tk.Checkbutton(chk, text="clock", variable=self.time_var, **ckw).pack(side=tk.LEFT)
        tk.Checkbutton(chk, text="date",  variable=self.date_var, **ckw).pack(
            side=tk.LEFT, padx=(16, 0))

        # divider + status
        tk.Frame(outer, height=1, bg=self._SEP).grid(
            row=5, column=0, columnspan=3, sticky="ew", pady=(18, 12))
        tk.Label(outer, textvariable=self.status_var, bg=BG, fg=self._STATUS,
                 font=(F, 11), anchor="w").grid(
            row=6, column=0, columnspan=3, sticky="w")
        tk.Frame(outer, height=1, bg=self._SEP).grid(
            row=7, column=0, columnspan=3, sticky="ew", pady=(12, 18))

        # buttons — use Label + binding instead of Button so macOS hit-testing
        # works regardless of custom bg/relief settings
        btns = tk.Frame(outer, bg=BG)
        btns.grid(row=8, column=0, columnspan=3, sticky="ew")

        def _make_lbl_btn(text_or_var, cmd, fg, bg_n, bg_a):
            kw = ({"textvariable": text_or_var}
                  if isinstance(text_or_var, tk.StringVar)
                  else {"text": text_or_var})
            lbl = tk.Label(btns, fg=fg, bg=bg_n, font=(F, 11, "bold"),
                           padx=14, pady=7, cursor="hand2", **kw)
            lbl.bind("<Enter>",           lambda e: lbl.config(bg=bg_a))
            lbl.bind("<Leave>",           lambda e: lbl.config(bg=bg_n))
            lbl.bind("<ButtonPress-1>",   lambda e: lbl.config(bg=bg_a))
            def _release(e, _c=cmd, _l=lbl, _bg=bg_n):
                _l.config(bg=_bg)
                _c()
            lbl.bind("<ButtonRelease-1>", _release)
            return lbl

        _make_lbl_btn("PREVIEW",       self._preview,        "#00ccff", "#003344", "#005566").pack(side=tk.LEFT)
        self._mon_text = tk.StringVar(value="START MONITORING")
        self._mon_btn  = _make_lbl_btn(self._mon_text, self._toggle_monitor, "#00ff88", "#002200", "#004400")
        self._mon_btn.pack(side=tk.LEFT, padx=(10, 0))
        _make_lbl_btn("QUIT",          self._quit,           "#ff6666", "#330000", "#550000").pack(side=tk.RIGHT)

        outer.columnconfigure(1, weight=1)

    # ── monitoring ────────────────────────────────────────────────────────────

    def _toggle_monitor(self) -> None:
        if self._monitoring:
            self._monitoring = False
            self.status_var.set("● not monitoring")
            self._mon_text.set("START MONITORING")
        else:
            self._save_config()
            self._monitoring = True
            self._mon_text.set("STOP MONITORING")
            self._poll_idle()

    def _poll_idle(self) -> None:
        if not self._monitoring:
            return
        idle      = get_idle_seconds()
        threshold = self.idle_var.get()
        self.status_var.set(f"◉ monitoring  —  idle {idle:.0f} s / {threshold:.0f} s")
        if idle >= threshold and not self._saver_active:
            self._saver_active = True
            self._open_screensaver(on_close=lambda: setattr(self, "_saver_active", False))
        self.root.after(2000, self._poll_idle)

    # ── screensaver ───────────────────────────────────────────────────────────

    def _preview(self) -> None:
        self._save_config()
        self._open_screensaver()

    def _open_screensaver(self, on_close=None) -> None:
        mode = self.mode_var.get()
        if mode == "random":
            mode = None
        fps      = max(5, min(60, self.fps_var.get()))
        cfg      = {"words_file": None,
                    "show_time":  self.time_var.get(),
                    "show_date":  self.date_var.get()}
        frame_ms = max(1, 1000 // fps)

        monitors = get_monitors()
        if not monitors:
            monitors = [(0, 0, self.root.winfo_screenwidth(),
                         self.root.winfo_screenheight())]

        _windows: List[tk.Toplevel] = []
        _arts:    List[ArtMode]    = []
        _running  = [True]

        def _exit(_e=None):
            if not _running[0]:
                return
            _running[0] = False
            for w in _windows:
                try:
                    w.destroy()
                except Exception:
                    pass
            if on_close:
                on_close()

        for mx, my, mw, mh in monitors:
            chosen = mode or random.choice(list(MODES))
            win = tk.Toplevel(self.root)
            win.overrideredirect(True)
            win.geometry(f"{mw}x{mh}+{mx}+{my}")
            win.configure(bg="black", cursor="none")
            win.attributes("-topmost", True)

            canvas = tk.Canvas(win, bg="black", highlightthickness=0,
                               width=mw, height=mh)
            canvas.pack(fill=tk.BOTH, expand=True)
            win.update_idletasks()

            for event in ("<KeyPress>", "<ButtonPress>"):
                win.bind(event, _exit)
            win.after(500, lambda w=win: w.bind("<Motion>", _exit))

            art: ArtMode = MODES[chosen](canvas, mw, mh, config=cfg)
            art.setup()

            _add_clock_overlay(self.root, canvas, mw, mh,
                               show_time=cfg["show_time"],
                               show_date=cfg["show_date"],
                               running=_running)
            _windows.append(win)
            _arts.append(art)

        if _windows:
            _windows[0].focus_force()

        _perf = time.perf_counter

        def _tick():
            if not _running[0]:
                return
            t0 = _perf()
            try:
                for art in _arts:
                    art.tick()
            except tk.TclError:
                return
            elapsed_ms = int((_perf() - t0) * 1000)
            self.root.after(max(1, frame_ms - elapsed_ms), _tick)

        self.root.after(0, _tick)

    # ── lifecycle ─────────────────────────────────────────────────────────────

    def _bring_to_front(self) -> None:
        """Force window to the front on macOS after PyInstaller bundle launch.

        PyInstaller bundles don't become the active app automatically, so the
        window appears but clicks register as 'activate app' rather than
        'click button'. Temporarily setting -topmost forces proper activation.
        """
        self.root.attributes("-topmost", True)
        self.root.update()
        self.root.lift()
        self.root.focus_force()
        self.root.after(400, lambda: self.root.attributes("-topmost", False))

    def _on_close(self) -> None:
        if self._monitoring:
            self.root.iconify()   # minimize to Dock; monitoring keeps running
        else:
            self._quit()

    def _quit(self) -> None:
        self._monitoring = False
        self.root.destroy()

    def run(self) -> None:
        if getattr(sys, "frozen", False) and platform.system() == "Darwin":
            self.root.after(150, self._bring_to_front)
        self.root.mainloop()


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    # Strip macOS -psn_* process serial number injected by the OS when launching
    # a .app bundle from Finder; argparse doesn't know this argument.
    argv = [a for a in sys.argv if not a.startswith("-psn_")]

    # When launched as a frozen .app bundle with no user arguments, open the
    # settings / control UI instead of silently waiting for idle time.
    _show_gui = getattr(sys, "frozen", False) and len(argv) == 1

    parser = argparse.ArgumentParser(
        prog="wallpy",
        description="wallpy — generative art screensaver",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="\n".join(
            f"  {name:12s} {cls.description}"
            for name, cls in MODES.items()
        ),
    )
    parser.add_argument(
        "--idle-time", "-i", type=float, default=300, metavar="SECONDS",
        help="Idle time in seconds before activating (default: 300)",
    )
    parser.add_argument(
        "--mode", "-m", choices=list(MODES), default=None,
        help="Art mode (default: random each run)",
    )
    parser.add_argument(
        "--fps", "-f", type=int, default=30,
        help="Target frames per second (default: 30, range 5–60)",
    )
    parser.add_argument(
        "--words-file", "-w", metavar="FILE",
        help="Text file of space-separated words for matrix_continuous mode",
    )
    parser.add_argument(
        "--date", action="store_true",
        help="Overlay the current date on all screensavers",
    )
    parser.add_argument(
        "--time", action="store_true",
        help="Overlay the current time on all screensavers",
    )
    parser.add_argument(
        "--preview", "-p", action="store_true",
        help="Launch screensaver immediately, skip idle check",
    )
    parser.add_argument(
        "--list-modes", action="store_true",
        help="Print available art modes and exit",
    )
    parser.add_argument(
        "--gui", action="store_true",
        help="Open the settings / control window",
    )
    args = parser.parse_args(argv[1:])

    if args.list_modes:
        print("Available art modes:")
        for name, cls in MODES.items():
            print(f"  {name:20s} {cls.description}")
        return

    args.fps = max(5, min(60, args.fps))

    # Warn if matrix_continuous is selected but no file given
    if args.mode == "matrix_continuous" and not args.words_file:
        print("[wallpy] Note: --words-file not set; using built-in fallback words.")

    config = {
        "words_file": args.words_file,
        "show_date":  args.date,
        "show_time":  getattr(args, "time"),   # "time" is a builtin; access via getattr
    }

    if args.preview:
        Screensaver(args.mode, args.fps, config=config)
    elif _show_gui or args.gui:
        WallpyApp(args).run()
    else:
        try:
            monitor(args.idle_time, args.mode, args.fps, config=config)
        except KeyboardInterrupt:
            print("\n[wallpy] Stopped.")


if __name__ == "__main__":
    main()
