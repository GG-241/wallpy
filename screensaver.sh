#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# wallpy screensaver launcher  (Linux / macOS / WSL)
#
# Usage:
#   ./screensaver.sh [options]
#
# Options are passed through to screensaver.py:
#   -i, --idle-time SECONDS   Idle time before activating  (default: 300)
#   -m, --mode MODE           Art mode: matrix|stars|shapes|lissajous|life|web
#   -f, --fps  FPS            Frames per second            (default: 30)
#   -p, --preview             Launch immediately (no idle wait)
#       --list-modes          Show available art modes
#
# Examples:
#   ./screensaver.sh                       # random art after 5 min
#   ./screensaver.sh -i 60 -m matrix       # matrix rain after 60 s
#   ./screensaver.sh --preview -m stars    # preview starfield now
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY_SCRIPT="$SCRIPT_DIR/screensaver.py"

# ── Colour helpers ────────────────────────────────────────────────────────────
RED='\033[0;31m'; YELLOW='\033[1;33m'; GREEN='\033[0;32m'; NC='\033[0m'
info()  { echo -e "${GREEN}[wallpy]${NC} $*"; }
warn()  { echo -e "${YELLOW}[wallpy] WARNING:${NC} $*"; }
error() { echo -e "${RED}[wallpy] ERROR:${NC} $*" >&2; }

# ── Locate Python 3.7+ ────────────────────────────────────────────────────────
find_python() {
    for cmd in python3 python python3.12 python3.11 python3.10 python3.9 python3.8 python3.7; do
        if command -v "$cmd" &>/dev/null; then
            ver=$("$cmd" -c "import sys; print(sys.version_info >= (3,7))" 2>/dev/null)
            if [[ "$ver" == "True" ]]; then
                echo "$cmd"; return 0
            fi
        fi
    done
    return 1
}

PYTHON=$(find_python) || {
    error "Python 3.7 or newer is required but was not found."
    echo "  Install with:  sudo apt install python3   # Debian/Ubuntu"
    echo "                 brew install python         # macOS"
    exit 1
}

# ── Check tkinter ─────────────────────────────────────────────────────────────
if ! "$PYTHON" -c "import tkinter" 2>/dev/null; then
    error "tkinter is not available in $PYTHON."
    echo ""
    echo "  On Debian / Ubuntu:"
    echo "    sudo apt install python3-tk"
    echo ""
    echo "  On Fedora / RHEL:"
    echo "    sudo dnf install python3-tkinter"
    echo ""
    echo "  On macOS (Homebrew Python):"
    echo "    brew install python-tk"
    echo ""
    echo "  On Arch Linux:"
    echo "    sudo pacman -S tk"
    exit 1
fi

# ── Linux-specific: warn about idle-detection back-ends ───────────────────────
OS="$(uname -s)"
if [[ "$OS" == "Linux" ]]; then
    # Determine display server
    SESSION="${XDG_SESSION_TYPE:-}"
    if [[ "$SESSION" == "x11" ]] || [[ -n "${DISPLAY:-}" && "$SESSION" != "wayland" ]]; then
        if ! command -v xprintidle &>/dev/null; then
            warn "xprintidle not found — idle detection may not work on X11."
            echo "       Install with:  sudo apt install xprintidle"
            echo "                      sudo dnf install xprintidle"
            echo "       Or use --preview to run without idle detection."
        fi
    elif [[ "$SESSION" == "wayland" ]]; then
        if ! command -v dbus-send &>/dev/null; then
            warn "dbus-send not found — idle detection may not work on Wayland."
            echo "       Install with:  sudo apt install dbus"
            echo "       Or use --preview to run without idle detection."
        fi
    fi
fi

# ── Run ───────────────────────────────────────────────────────────────────────
info "Using $PYTHON"
exec "$PYTHON" "$PY_SCRIPT" "$@"
