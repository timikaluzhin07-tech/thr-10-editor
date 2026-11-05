"""Дизайн-токены: загрузка tokens.json, контраст, масштабирование.

Чистый Python (без Qt) — чтобы токены можно было проверять тестами.
Qt-обёртка — thr10editor/ui/theme_provider.py.
"""

from __future__ import annotations

import json
import os
from typing import Any

TOKENS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tokens.json")


def load_tokens(path: str = TOKENS_PATH) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def parse_color(value: str) -> tuple[float, float, float, float]:
    """#RRGGBB или #AARRGGBB (формат Qt) → (r, g, b, a) в 0..1."""
    v = value.strip().lstrip("#")
    if len(v) == 6:
        a, rgb = 255, v
    elif len(v) == 8:
        a, rgb = int(v[:2], 16), v[2:]
    else:
        raise ValueError(f"неверный цвет: {value}")
    r, g, b = (int(rgb[i:i + 2], 16) for i in (0, 2, 4))
    return r / 255, g / 255, b / 255, a / 255


def _lin(c: float) -> float:
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def luminance(color: str) -> float:
    r, g, b, _ = parse_color(color)
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def contrast(fg: str, bg: str) -> float:
    """Контраст WCAG 2.x между двумя непрозрачными цветами."""
    l1, l2 = sorted((luminance(fg), luminance(bg)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


def auto_scale(width: float, height: float, tokens: dict[str, Any]) -> float:
    """Масштаб интерфейса по размеру окна, квантованный шагом step."""
    s = tokens["scale"]
    raw = min(width / s["baseWidth"], height / s["baseHeight"])
    raw = max(s["min"], min(s["max"], raw))
    step = s["step"]
    return round(round(raw / step) * step, 4)
