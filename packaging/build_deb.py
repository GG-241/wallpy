#!/usr/bin/env python3
"""
Build a wallpy .deb package using only Python stdlib.
Works on macOS and Linux — no dpkg-deb required.
"""
import io
import os
import tarfile
import time
from pathlib import Path

VERSION = "1.0.0"
ROOT = Path(__file__).resolve().parent.parent


def _ar_write(f, name, data: bytes):
    """Write one member into an open ar archive file."""
    name_field  = name.encode().ljust(16)[:16]
    mtime_field = str(int(time.time())).encode().ljust(12)[:12]
    uid_field   = b"0     "
    gid_field   = b"0     "
    mode_field  = b"100644  "
    size_field  = str(len(data)).encode().ljust(10)[:10]
    magic       = b"`\n"
    header = name_field + mtime_field + uid_field + gid_field + mode_field + size_field + magic
    assert len(header) == 60
    f.write(header)
    f.write(data)
    if len(data) % 2:
        f.write(b"\n")


def _make_tar_gz(members: list) -> bytes:
    """Return a gzipped tar archive. members = [(arcname, bytes, mode)]"""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz", compresslevel=9) as tf:
        for arcname, data, mode in members:
            ti = tarfile.TarInfo(name=arcname)
            ti.size = len(data)
            ti.mode = mode
            ti.mtime = int(time.time())
            tf.addfile(ti, io.BytesIO(data))
    return buf.getvalue()


def build_deb():
    dist_dir = ROOT / "dist"
    dist_dir.mkdir(exist_ok=True)
    deb_path = dist_dir / f"wallpy_{VERSION}_all.deb"

    screensaver_bytes = (ROOT / "screensaver.py").read_bytes()

    launcher = b"#!/bin/sh\nexec python3 /usr/lib/wallpy/screensaver.py \"$@\"\n"

    desktop = (
        b"[Desktop Entry]\n"
        b"Version=1.0\n"
        b"Type=Application\n"
        b"Name=wallpy\n"
        b"Comment=Generative art screensaver\n"
        b"Exec=wallpy --preview\n"
        b"Icon=utilities-terminal\n"
        b"Terminal=false\n"
        b"Categories=Utility;\n"
    )

    control = f"""\
Package: wallpy
Version: {VERSION}
Section: utils
Priority: optional
Architecture: all
Depends: python3 (>= 3.7), python3-tk
Maintainer: wallpy <noreply@example.com>
Description: Cross-platform generative art screensaver
 Monitors system idle time and displays animated art when the
 computer is inactive. Supports 7 art modes and multi-monitor.
""".encode()

    control_tar = _make_tar_gz([
        ("./control", control, 0o644),
    ])

    data_tar = _make_tar_gz([
        ("./usr/lib/wallpy/screensaver.py", screensaver_bytes, 0o644),
        ("./usr/bin/wallpy",                launcher,          0o755),
        ("./usr/share/applications/wallpy.desktop", desktop,  0o644),
    ])

    with open(deb_path, "wb") as f:
        f.write(b"!<arch>\n")
        _ar_write(f, "debian-binary",  b"2.0\n")
        _ar_write(f, "control.tar.gz", control_tar)
        _ar_write(f, "data.tar.gz",    data_tar)

    size_kb = deb_path.stat().st_size // 1024
    print(f"DEB: {deb_path}  ({size_kb} KB)")


if __name__ == "__main__":
    build_deb()
