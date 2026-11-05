#!/usr/bin/env python3
"""Сгенерировать thr10editor/ui/qml/Icons.js из набора иконок Lucide (ISC).

Иконки Lucide — штриховые (stroke 2, viewBox 24). Скрипт переводит элементы
SVG (path, line, circle, ellipse, rect, polyline, polygon) в одну строку пути
для QML PathSvg.

Использование (нужен распакованный npm-пакет lucide-static):
    python tools/build_icons.py path/to/lucide-static/icon-nodes.json
"""

from __future__ import annotations

import json
import os
import re
import sys

ICONS = {
    # имя в приложении: имя в Lucide
    "undo": "undo-2", "redo": "redo-2", "sun": "sun", "moon": "moon",
    "stage": "monitor-play", "keyboard": "keyboard", "folder": "folder",
    "folder-plus": "folder-plus", "star": "star", "search": "search", "plus": "plus",
    "trash": "trash", "import": "file-down", "export": "file-up", "lock": "lock",
    "unlock": "lock-open", "play": "play", "stop": "square", "chevron-left": "chevron-left",
    "chevron-right": "chevron-right", "chevron-down": "chevron-down",
    "chevron-up": "chevron-up", "settings": "settings", "plug": "plug-zap", "usb": "usb",
    "dice": "dices", "wave": "audio-waveform", "tap": "hand", "setlist": "list-music",
    "close": "x", "check": "check", "ab": "arrow-left-right", "menu": "menu",
    "copy": "copy", "edit": "pencil", "refresh": "refresh-cw", "power": "power",
    "info": "info", "warning": "triangle-alert", "save": "save", "send": "send",
    "panel-left": "panel-left", "panel-right": "panel-right", "tag": "tag",
    "guitar": "guitar", "sliders": "sliders-horizontal", "morph": "blend",
    "grip": "grip-vertical", "help": "circle-question-mark", "zoom-in": "zoom-in",
    "zoom-out": "zoom-out", "list": "list", "arrow-up": "arrow-up",
    "arrow-down": "arrow-down", "log": "terminal", "music": "list-music",
    "download": "download", "upload": "upload", "fullscreen": "maximize",
    "minimize": "minimize", "library": "library", "cpu": "cpu", "timer": "timer",
    "dot": "dot", "circle": "circle", "eye": "eye", "pause": "pause", "minus": "minus", "image": "image",
}


def _num(v: str | float) -> str:
    f = float(v)
    return str(int(f)) if f.is_integer() else f"{f:g}"


def _points(points: str) -> list[tuple[str, str]]:
    nums = points.replace(",", " ").split()
    return [(nums[i], nums[i + 1]) for i in range(0, len(nums) - 1, 2)]


_NUM = re.compile(r"[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?")


def absolutize_start(d: str) -> str:
    """Первый «m» в отдельном пути абсолютный (SVG), а при склейке путей — нет.

    «m19 12-7 7» → «M19 12l-7 7».
    """
    d = d.strip()
    if not d.startswith("m"):
        return d
    rest = d[1:]
    m1 = _NUM.search(rest)
    m2 = _NUM.search(rest, m1.end())
    tail = rest[m2.end():]
    stripped = tail.lstrip(" ,")
    if stripped and (stripped[0].isdigit() or stripped[0] in "-+."):
        tail = "l" + stripped
    return f"M{m1.group(0)} {m2.group(0)}{tail}"


def element_to_path(tag: str, a: dict[str, str]) -> str:
    if tag == "path":
        return absolutize_start(a["d"])
    if tag == "line":
        return f"M{_num(a['x1'])} {_num(a['y1'])}L{_num(a['x2'])} {_num(a['y2'])}"
    if tag in ("circle", "ellipse"):
        cx, cy = float(a["cx"]), float(a["cy"])
        rx = float(a.get("r", a.get("rx", 0)))
        ry = float(a.get("r", a.get("ry", rx)))
        return (f"M{_num(cx - rx)} {_num(cy)}A{_num(rx)} {_num(ry)} 0 1 0 {_num(cx + rx)} {_num(cy)}"
                f"A{_num(rx)} {_num(ry)} 0 1 0 {_num(cx - rx)} {_num(cy)}Z")
    if tag == "rect":
        x, y = float(a.get("x", 0)), float(a.get("y", 0))
        w, h = float(a["width"]), float(a["height"])
        rx = float(a.get("rx", a.get("ry", 0)))
        ry = float(a.get("ry", rx))
        if rx == 0:
            return f"M{_num(x)} {_num(y)}H{_num(x + w)}V{_num(y + h)}H{_num(x)}Z"
        return (f"M{_num(x + rx)} {_num(y)}H{_num(x + w - rx)}"
                f"A{_num(rx)} {_num(ry)} 0 0 1 {_num(x + w)} {_num(y + ry)}V{_num(y + h - ry)}"
                f"A{_num(rx)} {_num(ry)} 0 0 1 {_num(x + w - rx)} {_num(y + h)}H{_num(x + rx)}"
                f"A{_num(rx)} {_num(ry)} 0 0 1 {_num(x)} {_num(y + h - ry)}V{_num(y + ry)}"
                f"A{_num(rx)} {_num(ry)} 0 0 1 {_num(x + rx)} {_num(y)}Z")
    if tag in ("polyline", "polygon"):
        pts = _points(a["points"])
        d = "M" + "L".join(f"{_num(x)} {_num(y)}" for x, y in pts)
        return d + ("Z" if tag == "polygon" else "")
    raise ValueError(f"неподдерживаемый элемент {tag}")


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    with open(argv[1], encoding="utf-8") as f:
        nodes = json.load(f)
    out = {}
    for name, lucide in sorted(ICONS.items()):
        if lucide not in nodes:
            print(f"нет иконки {lucide}", file=sys.stderr)
            return 1
        out[name] = "".join(element_to_path(tag, attrs) for tag, attrs in nodes[lucide])
    target = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "thr10editor", "ui", "qml", "Icons.js")
    with open(target, "w", encoding="utf-8") as f:
        f.write("// Сгенерировано tools/build_icons.py из Lucide Icons (ISC License,\n")
        f.write("// Copyright (c) Lucide Icons and Contributors). Не редактировать вручную.\n")
        f.write(".pragma library\n\n")
        f.write("var paths = ")
        json.dump(out, f, ensure_ascii=False, indent=1)
        f.write(";\n")
    print(f"{len(out)} иконок → {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
