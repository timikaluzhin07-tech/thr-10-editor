"""Настройки приложения в JSON (без Qt)."""

from __future__ import annotations

import copy
import json
import logging
import os
from typing import Any

from ..protocol.params import ProtocolOverrides

log = logging.getLogger(__name__)

DEFAULTS: dict[str, Any] = {
    "theme": "dark",
    "zoom": 1.0,
    "last_port": "",
    "auto_connect": True,
    "start_demo_if_no_device": True,
    "send_interval_ms": 20,
    "sidebar_visible": True,
    "tools_visible": True,
    "tap_subdivision": "1/4",
    "lfo_rate_limit_hz": 20,
    "midi_controller": {"port": "", "next": None, "prev": None},
    "randomizer": {"amount": 100, "locked": ["amp.master"], "bounds": {}},
    "morph": {"duration": 4.0, "curve": "smooth"},
    "window": {"width": 1360, "height": 860, "maximized": False},
}


def atomic_write_json(path: str, data: Any) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


class AppSettings:
    def __init__(self, path: str):
        self.path = path
        self.data: dict[str, Any] = copy.deepcopy(DEFAULTS)
        self.load()

    def load(self) -> None:
        if not os.path.exists(self.path):
            return
        try:
            with open(self.path, encoding="utf-8") as f:
                loaded = json.load(f)
        except (OSError, ValueError) as e:
            log.warning("настройки повреждены, используются значения по умолчанию: %s", e)
            return
        if isinstance(loaded, dict):
            for k, v in loaded.items():
                if k in DEFAULTS and isinstance(DEFAULTS[k], dict) and isinstance(v, dict):
                    merged = copy.deepcopy(DEFAULTS[k])
                    merged.update(v)
                    self.data[k] = merged
                else:
                    self.data[k] = v

    def save(self) -> None:
        try:
            atomic_write_json(self.path, self.data)
        except OSError as e:
            log.error("не удалось сохранить настройки: %s", e)

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set(self, key: str, value: Any, *, save: bool = True) -> None:
        self.data[key] = value
        if save:
            self.save()


def load_overrides(path: str) -> ProtocolOverrides:
    """protocol_overrides.json: {"confirmed": [...]}; файла нет — пусто."""
    if not os.path.exists(path):
        return ProtocolOverrides()
    try:
        with open(path, encoding="utf-8") as f:
            return ProtocolOverrides.from_json(json.load(f))
    except (OSError, ValueError) as e:
        log.error("protocol_overrides.json не прочитан: %s", e)
        return ProtocolOverrides()
