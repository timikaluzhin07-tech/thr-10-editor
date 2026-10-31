#!/usr/bin/env python3
"""Нарисовать иконку приложения (PNG + многоразмерный ICO) средствами Qt.

    python tools/make_icon.py

Результат: thr10editor/ui/assets/icon.png и icon.ico. Цвета — из токенов
(тёмная тема): графитовый фон, янтарная дуга ручки.
"""

from __future__ import annotations

import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QPointF, QRectF, Qt  # noqa: E402
from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter, QPen  # noqa: E402

from thr10editor.ui.theme import load_tokens  # noqa: E402

OUT = os.path.join(ROOT, "thr10editor", "ui", "assets")


def draw(size: int) -> QImage:
    c = load_tokens()["themes"]["dark"]
    img = QImage(size, size, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    s = size / 256
    # подложка
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(c["surface"]))
    p.drawRoundedRect(QRectF(8 * s, 8 * s, 240 * s, 240 * s), 56 * s, 56 * s)
    # дорожка и дуга ручки
    rect = QRectF(48 * s, 48 * s, 160 * s, 160 * s)
    pen = QPen(QColor(c["knobTrack"]), 22 * s)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    p.drawArc(rect, -45 * 16, 270 * 16)
    pen.setColor(QColor(c["accent"]))
    p.setPen(pen)
    p.drawArc(rect, 225 * 16, -200 * 16)
    # лицевая часть и указатель
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(c["knobFace"]))
    p.drawEllipse(QPointF(128 * s, 128 * s), 52 * s, 52 * s)
    pen = QPen(QColor(c["text"]), 14 * s)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    p.translate(128 * s, 128 * s)
    p.rotate(-135 + 270 * (200 / 270))
    p.drawLine(QPointF(0, -18 * s), QPointF(0, -40 * s))
    p.end()
    return img


def png_bytes(img: QImage) -> bytes:
    ba = QByteArray()
    buf = QBuffer(ba)
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    img.save(buf, "PNG")
    return bytes(ba.data())


def write_ico(path: str, sizes: list[int]) -> None:
    images = [png_bytes(draw(sz)) for sz in sizes]
    header = struct.pack("<HHH", 0, 1, len(images))
    offset = 6 + 16 * len(images)
    entries = b""
    for sz, data in zip(sizes, images):
        dim = 0 if sz >= 256 else sz
        entries += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(data), offset)
        offset += len(data)
    with open(path, "wb") as f:
        f.write(header + entries + b"".join(images))


def main() -> int:
    QGuiApplication.instance() or QGuiApplication([])
    os.makedirs(OUT, exist_ok=True)
    draw(512).save(os.path.join(OUT, "icon.png"))
    write_ico(os.path.join(OUT, "icon.ico"), [16, 24, 32, 48, 64, 128, 256])
    print("иконка:", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
