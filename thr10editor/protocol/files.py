"""Файловые форматы THR: .YDL (библиотека официального эдитора), .syx, одиночный 265-байтный.

См. docs/PROTOCOL.md, раздел 8.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from . import constants as C
from .patch import decode_name
from .sysex import PatchDump, decode, encode_patch_dump, split_sysex_stream


class FileFormatError(ValueError):
    pass


@dataclass(frozen=True)
class RawPatch:
    name: str
    patch: bytes  # 256 байт


def _is_empty(patch: bytes) -> bool:
    return not any(patch[: C.PATCH_PARAM_BASE]) and not any(patch[C.PATCH_PARAM_BASE:-1])


# ---- .YDL ------------------------------------------------------------------

def read_ydl(data: bytes, *, skip_empty: bool = True) -> list[RawPatch]:
    """Прочитать библиотеку .YDL. S2, S3 — CONFIRMED_MULTI."""
    if not data.startswith(C.YDL_MAGIC):
        raise FileFormatError("это не файл .YDL (нет сигнатуры DTAB01d)")
    out: list[RawPatch] = []
    pos = C.YDL_HEADER_SIZE
    while pos + C.PATCH_SIZE <= len(data):
        patch = bytes(data[pos: pos + C.PATCH_SIZE])
        pos += C.YDL_RECORD_SIZE
        if skip_empty and _is_empty(patch):
            continue
        out.append(RawPatch(decode_name(patch), patch))
    return out


def write_ydl(patches: Iterable[bytes], *, pad_to: int | None = C.YDL_DEFAULT_COUNT) -> bytes:
    """Записать .YDL. DERIVED: неизвестные байты — нули (как в реальном файле S3).

    pad_to — дополнить пустыми пресетами до этого количества (в библиотеке
    официального эдитора их 100). None — без дополнения.
    """
    items = [bytes(p) for p in patches]
    for p in items:
        if len(p) != C.PATCH_SIZE:
            raise FileFormatError("пресет должен быть 256 байт")
    if pad_to is not None:
        if len(items) > pad_to:
            raise FileFormatError(f"в .YDL помещается не больше {pad_to} пресетов")
        items += [bytes(C.PATCH_SIZE)] * (pad_to - len(items))
    out = bytearray(C.YDL_MAGIC)
    out += bytes(C.YDL_HEADER_SIZE - len(C.YDL_MAGIC))
    for p in items:
        out += p
        out += bytes(C.YDL_RECORD_TRAILER)
    return bytes(out)


# ---- .syx ------------------------------------------------------------------

def read_syx(data: bytes) -> list[RawPatch]:
    """Все дампы пресетов из потока SysEx (.syx). Неверная сумма — ошибка."""
    out: list[RawPatch] = []
    for msg in split_sysex_stream(data):
        m = decode(msg)
        if isinstance(m, PatchDump):
            if not m.checksum_ok:
                raise FileFormatError("в .syx есть дамп с неверной контрольной суммой")
            out.append(RawPatch(decode_name(m.patch), m.patch))
    if not out:
        raise FileFormatError("в файле нет дампов пресетов THR")
    return out


def write_syx(patches: Iterable[bytes]) -> bytes:
    return b"".join(encode_patch_dump(p) for p in patches)


# ---- одиночный 265-байтный файл (S1) ---------------------------------------

def read_single(data: bytes) -> list[RawPatch]:
    if len(data) != C.SINGLE_FILE_SIZE or not data.startswith(C.SINGLE_FILE_MAGIC):
        raise FileFormatError("не одиночный файл пресета THR (265 байт, «DTA…»)")
    patch = bytes(data[C.SINGLE_FILE_OFFSET:])
    return [RawPatch(decode_name(patch), patch)]


# ---- автоопределение -------------------------------------------------------

def read_any(data: bytes) -> tuple[str, list[RawPatch]]:
    """Определить формат и прочитать. Возвращает (формат, пресеты)."""
    if data.startswith(C.YDL_MAGIC):
        return "ydl", read_ydl(data)
    if len(data) == C.SINGLE_FILE_SIZE and data.startswith(C.SINGLE_FILE_MAGIC):
        return "single", read_single(data)
    if C.SYSEX_START in data:
        return "syx", read_syx(data)
    raise FileFormatError("неизвестный формат файла")
