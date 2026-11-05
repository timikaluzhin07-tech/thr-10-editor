"""Пресет THR10: 256 байт ↔ имя + логические значения параметров.

Раскладка (S1 convert_data.py, S3 patches.h):
    0..63    имя ASCII, дополняется нулями
    64..127  неизвестно (пишем нули)
    128+AA   значение параметра с адресом AA (1 байт или VH VL)
    255      при отправке обязан быть 0
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from . import constants as C
from .params import PARAMS, Kind, ParamDef, normalize_values

_TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e", "ж": "zh",
    "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o",
    "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "h", "ц": "ts",
    "ч": "ch", "ш": "sh", "щ": "sch", "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu",
    "я": "ya",
}


def sanitize_name(name: str) -> str:
    """Имя для комбика: ASCII 0x20–0x7E, кириллица транслитерируется, ≤ 64 символов."""
    out = []
    for ch in name:
        low = ch.lower()
        if low in _TRANSLIT:
            t = _TRANSLIT[low]
            out.append(t.capitalize() if ch != low and t else t)
        elif 0x20 <= ord(ch) <= 0x7E:
            out.append(ch)
        else:
            out.append("?")
    return "".join(out)[: C.PATCH_NAME_SIZE]


def _write(buf: bytearray, p: ParamDef, value: int) -> None:
    raw = p.to_raw(value)
    pos = C.PATCH_PARAM_BASE + p.address
    if p.width == 2:
        buf[pos] = (raw >> 7) & 0x7F
        buf[pos + 1] = raw & 0x7F
    else:
        buf[pos] = raw & 0x7F


def _read_raw(patch: bytes, p: ParamDef) -> int:
    pos = C.PATCH_PARAM_BASE + p.address
    if p.width == 2:
        return ((patch[pos] & 0x7F) << 7) | (patch[pos + 1] & 0x7F)
    return patch[pos]


def encode_patch(name: str, values: Mapping[str, int]) -> bytes:
    """Логические значения → 256 байт. Пишутся только параметры активных типов."""
    full = normalize_values(values)
    buf = bytearray(C.PATCH_SIZE)
    raw_name = sanitize_name(name).encode("ascii")
    buf[: len(raw_name)] = raw_name
    for p in PARAMS.values():
        if p.is_active(full):
            _write(buf, p, full[p.key])
    buf[-1] = 0
    return bytes(buf)


@dataclass
class DecodedPatch:
    name: str
    values: dict[str, int]
    warnings: list[str] = field(default_factory=list)


def decode_name(patch: bytes) -> str:
    raw = patch[: C.PATCH_NAME_SIZE].split(b"\x00", 1)[0]
    return "".join(chr(b) for b in raw if 0x20 <= b <= 0x7E)


def decode_patch(patch: bytes, base: Mapping[str, int] | None = None) -> DecodedPatch:
    """256 байт → имя и значения.

    Параметры неактивных типов эффектов в дампе не хранятся — для них
    берутся значения из base (или значения по умолчанию).
    """
    if len(patch) != C.PATCH_SIZE:
        raise ValueError(f"пресет должен быть {C.PATCH_SIZE} байт, а не {len(patch)}")
    values = normalize_values(base)
    warnings: list[str] = []

    def read(p: ParamDef) -> None:
        raw = _read_raw(patch, p)
        if p.kind is not Kind.SWITCH and not p.minimum <= raw <= p.maximum:
            warnings.append(f"{p.key}: значение {raw} вне {p.minimum}..{p.maximum}, ограничено")
        values[p.key] = p.from_raw(raw)

    independent = [p for p in PARAMS.values() if p.depends_on is None]
    for p in independent:
        read(p)
    for p in PARAMS.values():
        if p.depends_on is not None and p.is_active(values):
            read(p)
    return DecodedPatch(decode_name(patch), values, warnings)
