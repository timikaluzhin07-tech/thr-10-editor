"""Крошечный анимированный GIF (1×1, несколько кадров) без сторонних библиотек."""

import struct


def gif_bytes(frames: int = 2) -> bytes:
    out = b"GIF89a" + struct.pack("<HH", 1, 1) + b"\x80\x00\x00"  # 2 цвета в палитре
    out += b"\xff\x00\x00" + b"\x00\x00\xff"
    out += b"!\xff\x0bNETSCAPE2.0\x03\x01\x00\x00\x00"  # бесконечный повтор
    for i in range(frames):
        out += b"!\xf9\x04\x00\x0a\x00\x00\x00"  # задержка кадра 0,1 с
        out += b",\x00\x00\x00\x00\x01\x00\x01\x00\x00"
        # LZW (минимальный код 2): clear, индекс цвета, end
        out += b"\x02\x02" + (b"D" if i % 2 == 0 else b"L") + b"\x01\x00"
    return out + b";"


def write_gif(path, frames: int = 2):
    with open(path, "wb") as f:
        f.write(gif_bytes(frames))
    return path
