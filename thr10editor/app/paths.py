"""Папка данных приложения (настройки, библиотека, журнал)."""

from __future__ import annotations

import os
import sys

from .. import APP_ID


def data_dir() -> str:
    """%APPDATA%\\THR10Editor на Windows; переопределяется THR10EDITOR_HOME."""
    override = os.environ.get("THR10EDITOR_HOME")
    if override:
        path = override
    elif sys.platform.startswith("win"):
        path = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), APP_ID)
    elif sys.platform == "darwin":
        path = os.path.expanduser(f"~/Library/Application Support/{APP_ID}")
    else:
        base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
        path = os.path.join(base, APP_ID)
    os.makedirs(path, exist_ok=True)
    return path
