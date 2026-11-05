"""Таблица параметров THR10: адреса, диапазоны, подписи, статусы.

Адреса и диапазоны — источник S1 (SysExTones), адреса и минимумы
дополнительно подтверждены реальными байтами S3 (THR_Footswitch).
Значения по умолчанию — выбор редактора (это не часть протокола).
См. docs/PROTOCOL.md, раздел 7.

Значения в модели «логические»:
  * RANGE  — сырое значение протокола (то, что уходит в VH/VL);
  * CHOICE — индекс варианта;
  * SWITCH — 1 = включено, 0 = выключено (в протоколе 00 = вкл, 7F = выкл).
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable, Mapping

from .constants import Status

# Единица Delay Time в миллисекундах на 1 шаг значения. DERIVED, см.
# docs/PROTOCOL.md («Единицы Time — вывод»). Проверяется на железе.
DELAY_TIME_UNIT_MS = 0.1


class Kind(str, Enum):
    RANGE = "range"
    CHOICE = "choice"
    SWITCH = "switch"


class Display(str, Enum):
    PLAIN = "plain"  # число как есть
    PERCENT = "percent"  # 0–100
    DELAY_MS = "delay_ms"  # значение × DELAY_TIME_UNIT_MS, мс
    TENTH_MS = "tenth_ms"  # ×0,1 мс
    TENTH_S = "tenth_s"  # ×0,1 с
    TENTH = "tenth"  # ×0,1 (коэффициент)
    HZ_HIGHCUT = "hz_highcut"  # Гц, максимум = Thru
    HZ_LOWCUT = "hz_lowcut"  # Гц, минимум = Thru
    CHOICE = "choice"
    SWITCH = "switch"


AMP_MODELS = ("Clean", "Crunch", "Lead", "Brit Hi", "Modern", "Bass", "Aco", "Flat")
CABINETS = ("US 4x12", "US 2x12", "Brit 4x12", "Brit 2x12", "1x12", "4x10", "None")
COMP_TYPES = ("Stomp", "Rack")
COMP_RATIOS = ("1:1", "1:4", "1:8", "1:12", "1:20", "1:∞")
COMP_KNEES = ("Soft", "Medium", "Hard")
MOD_TYPES = ("Chorus", "Flanger", "Tremolo", "Phaser")
REVERB_TYPES = ("Hall", "Room", "Plate", "Spring")


@dataclass(frozen=True)
class ParamDef:
    key: str
    label: str
    group: str
    address: int
    kind: Kind
    minimum: int
    maximum: int
    default: int
    width: int = 1  # байт в дампе: 1 или 2 (14 бит)
    options: tuple[str, ...] = ()
    display: Display = Display.PLAIN
    depends_on: str | None = None  # ключ параметра-типа
    depends_values: tuple[int, ...] = ()
    status: Status = Status.CONFIRMED  # статус байтов (адрес/диапазон)
    display_status: Status = Status.CONFIRMED  # статус единиц отображения
    source: str = "S1"
    hint: str = ""

    # ---- значения -------------------------------------------------------
    def clamp(self, value: float | int) -> int:
        v = int(round(value))
        if v < self.minimum:
            return self.minimum
        if v > self.maximum:
            return self.maximum
        return v

    def is_active(self, values: Mapping[str, int]) -> bool:
        """Активен ли параметр при текущем типе эффекта."""
        if self.depends_on is None:
            return True
        return values.get(self.depends_on, PARAMS[self.depends_on].default) in self.depends_values

    @property
    def is_continuous(self) -> bool:
        return self.kind is Kind.RANGE

    @property
    def is_type_selector(self) -> bool:
        return self.key in TYPE_KEYS

    @property
    def span(self) -> int:
        return self.maximum - self.minimum

    def normalized(self, value: int) -> float:
        return 0.0 if self.span == 0 else (value - self.minimum) / self.span

    def from_normalized(self, x: float) -> int:
        return self.clamp(self.minimum + x * self.span)

    # ---- протокол -------------------------------------------------------
    def to_raw(self, value: int) -> int:
        """Логическое значение → значение протокола."""
        if self.kind is Kind.SWITCH:
            return 0x00 if value else 0x7F
        return self.clamp(value)

    def from_raw(self, raw: int) -> int:
        """Значение протокола → логическое (с ограничением диапазона)."""
        if self.kind is Kind.SWITCH:
            return 0 if raw else 1
        return self.clamp(raw)

    # ---- отображение ----------------------------------------------------
    def format(self, value: int) -> str:
        v = self.clamp(value)
        d = self.display
        if d is Display.SWITCH:
            return "Вкл" if v else "Выкл"
        if d is Display.CHOICE:
            return self.options[v] if 0 <= v < len(self.options) else str(v)
        if d is Display.DELAY_MS:
            return _fmt_ms(v * DELAY_TIME_UNIT_MS)
        if d is Display.TENTH_MS:
            return _fmt_ms(v / 10)
        if d is Display.TENTH_S:
            return f"{v / 10:.1f} с"
        if d is Display.TENTH:
            return f"{v / 10:.1f}"
        if d is Display.HZ_HIGHCUT and v == self.maximum:
            return "Thru"
        if d is Display.HZ_LOWCUT and v == self.minimum:
            return "Thru"
        if d in (Display.HZ_HIGHCUT, Display.HZ_LOWCUT):
            if v >= 1000:
                return f"{v / 1000:.2f}".rstrip("0").rstrip(".") + " кГц"
            return f"{v} Гц"
        return str(v)

    def parse(self, text: str) -> int | None:
        """Текст из поля ввода (в единицах отображения) → значение.

        Возвращает None, если текст не распознан.
        """
        t = text.strip().lower().replace(",", ".")
        if not t:
            return None
        d = self.display
        if d is Display.SWITCH:
            if t in ("1", "on", "вкл", "да", "true"):
                return 1
            if t in ("0", "off", "выкл", "нет", "false"):
                return 0
            return None
        if d is Display.CHOICE:
            for i, name in enumerate(self.options):
                if name.lower() == t:
                    return i
            num = _number(t)
            return None if num is None else self.clamp(num)
        if d in (Display.HZ_HIGHCUT, Display.HZ_LOWCUT):
            if t in ("thru", "off", "выкл"):
                return self.maximum if d is Display.HZ_HIGHCUT else self.minimum
            mult = 1000.0 if re.search(r"(k|к)", t) else 1.0
            num = _number(t)
            return None if num is None else self.clamp(num * mult)
        num = _number(t)
        if num is None:
            return None
        if d is Display.DELAY_MS:
            return self.clamp(num / DELAY_TIME_UNIT_MS)
        if d in (Display.TENTH_MS, Display.TENTH_S, Display.TENTH):
            return self.clamp(num * 10)
        return self.clamp(num)


def _fmt_ms(ms: float) -> str:
    if ms >= 100:
        return f"{ms:.0f} мс"
    return f"{ms:.1f} мс"


def _number(text: str) -> float | None:
    m = re.search(r"-?\d+(?:\.\d+)?", text)
    if not m:
        return None
    try:
        value = float(m.group(0))
    except ValueError:  # pragma: no cover - регулярка гарантирует формат
        return None
    return value if math.isfinite(value) else None


# --------------------------------------------------------------------------
# Таблица
# --------------------------------------------------------------------------

def _range(key, label, group, address, lo, hi, default, *, width=1,
           display=Display.PERCENT, depends=None, values=(), status=Status.CONFIRMED,
           display_status=Status.CONFIRMED, source="S1", hint=""):
    return ParamDef(key, label, group, address, Kind.RANGE, lo, hi, default, width,
                    (), display, depends, tuple(values), status, display_status, source, hint)


def _choice(key, label, group, address, options, default, *, depends=None, values=(),
            status=Status.CONFIRMED, display_status=Status.CONFIRMED, source="S1", hint=""):
    return ParamDef(key, label, group, address, Kind.CHOICE, 0, len(options) - 1, default, 1,
                    tuple(options), Display.CHOICE, depends, tuple(values), status,
                    display_status, source, hint)


def _switch(key, group, address, default):
    return ParamDef(key, "Вкл", group, address, Kind.SWITCH, 0, 1, default, 1, (),
                    Display.SWITCH, None, (), Status.CONFIRMED_MULTI, Status.CONFIRMED,
                    "S1, S3")


_D = Status.DERIVED
_M = Status.CONFIRMED_MULTI

_PARAM_LIST: list[ParamDef] = [
    # Усилитель
    _choice("amp.model", "Amp", "amp", 0x00, AMP_MODELS, 0, status=_M, source="S1, S3"),
    _range("amp.gain", "Gain", "amp", 0x01, 0, 100, 50,
           hint="В модели Aco работает как микс микрофона (S1)"),
    _range("amp.master", "Master", "amp", 0x02, 0, 100, 50),
    _range("amp.bass", "Bass", "amp", 0x03, 0, 100, 50),
    _range("amp.middle", "Middle", "amp", 0x04, 0, 100, 50),
    _range("amp.treble", "Treble", "amp", 0x05, 0, 100, 50),
    _choice("amp.cab", "Cab", "amp", 0x06, CABINETS, 1, status=_M, source="S1, S3"),
    # Компрессор
    _switch("comp.on", "comp", 0x1F, 0),
    _choice("comp.type", "Тип", "comp", 0x10, COMP_TYPES, 0),
    _range("comp.stomp.sustain", "Sustain", "comp", 0x11, 0, 100, 50,
           depends="comp.type", values=(0,)),
    _range("comp.stomp.output", "Output", "comp", 0x12, 0, 100, 50,
           depends="comp.type", values=(0,)),
    _range("comp.rack.threshold", "Threshold", "comp", 0x11, 0, 600, 300, width=2,
           display=Display.PLAIN, depends="comp.type", values=(1,)),
    _range("comp.rack.attack", "Attack", "comp", 0x13, 0, 100, 50,
           depends="comp.type", values=(1,)),
    _range("comp.rack.release", "Release", "comp", 0x14, 0, 100, 50,
           depends="comp.type", values=(1,)),
    _choice("comp.rack.ratio", "Ratio", "comp", 0x15, COMP_RATIOS, 1,
            depends="comp.type", values=(1,), display_status=_D,
            hint="Подписи из S1, сверить с официальным эдитором"),
    _choice("comp.rack.knee", "Knee", "comp", 0x16, COMP_KNEES, 1,
            depends="comp.type", values=(1,)),
    _range("comp.rack.output", "Output", "comp", 0x17, 0, 600, 300, width=2,
           display=Display.PLAIN, depends="comp.type", values=(1,)),
    # Модуляция
    _switch("mod.on", "mod", 0x2F, 0),
    _choice("mod.type", "Тип", "mod", 0x20, MOD_TYPES, 0),
    _range("mod.chorus.speed", "Speed", "mod", 0x21, 0, 100, 50, depends="mod.type", values=(0,)),
    _range("mod.chorus.depth", "Depth", "mod", 0x22, 0, 100, 50, depends="mod.type", values=(0,)),
    _range("mod.chorus.mix", "Mix", "mod", 0x23, 0, 100, 50, depends="mod.type", values=(0,)),
    _range("mod.flanger.speed", "Speed", "mod", 0x21, 0, 100, 50, depends="mod.type", values=(1,)),
    _range("mod.flanger.manual", "Manual", "mod", 0x22, 0, 100, 50, depends="mod.type", values=(1,)),
    _range("mod.flanger.depth", "Depth", "mod", 0x23, 0, 100, 50, depends="mod.type", values=(1,)),
    _range("mod.flanger.feedback", "Feedback", "mod", 0x24, 0, 100, 50,
           depends="mod.type", values=(1,)),
    _range("mod.flanger.spread", "Spread", "mod", 0x25, 0, 100, 50, depends="mod.type", values=(1,)),
    _range("mod.tremolo.freq", "Freq", "mod", 0x21, 0, 100, 50, depends="mod.type", values=(2,)),
    _range("mod.tremolo.depth", "Depth", "mod", 0x22, 0, 100, 50, depends="mod.type", values=(2,)),
    _range("mod.phaser.speed", "Speed", "mod", 0x21, 0, 100, 50, depends="mod.type", values=(3,)),
    _range("mod.phaser.manual", "Manual", "mod", 0x22, 0, 100, 50, depends="mod.type", values=(3,)),
    _range("mod.phaser.depth", "Depth", "mod", 0x23, 0, 100, 50, depends="mod.type", values=(3,)),
    _range("mod.phaser.feedback", "Feedback", "mod", 0x24, 0, 100, 50,
           depends="mod.type", values=(3,)),
    # Дилей
    _switch("delay.on", "delay", 0x3F, 0),
    _range("delay.time", "Time", "delay", 0x31, 1, 9999, 3500, width=2,
           display=Display.DELAY_MS, status=_M, display_status=_D, source="S1, S3",
           hint="Единица 0,1 мс — вывод, проверяется на железе"),
    _range("delay.feedback", "Feedback", "delay", 0x33, 0, 100, 30),
    _range("delay.highcut", "High Cut", "delay", 0x34, 1000, 16001, 16001, width=2,
           display=Display.HZ_HIGHCUT, status=_M, display_status=_D, source="S1, S3"),
    _range("delay.lowcut", "Low Cut", "delay", 0x36, 21, 8000, 21, width=2,
           display=Display.HZ_LOWCUT, status=_M, display_status=_D, source="S1, S3"),
    _range("delay.level", "Level", "delay", 0x38, 0, 100, 30),
    # Реверб
    _switch("reverb.on", "reverb", 0x4F, 1),
    _choice("reverb.type", "Тип", "reverb", 0x40, REVERB_TYPES, 0),
    _range("reverb.time", "Time", "reverb", 0x41, 3, 200, 25, width=2, display=Display.TENTH_S,
           depends="reverb.type", values=(0, 1, 2), status=_M, display_status=_D,
           source="S1, S3"),
    _range("reverb.pre", "Pre", "reverb", 0x43, 1, 2000, 200, width=2, display=Display.TENTH_MS,
           depends="reverb.type", values=(0, 1, 2), status=_M, display_status=_D,
           source="S1, S3"),
    _range("reverb.lowcut", "Low Cut", "reverb", 0x45, 21, 8000, 21, width=2,
           display=Display.HZ_LOWCUT, depends="reverb.type", values=(0, 1, 2), status=_M,
           display_status=_D, source="S1, S3"),
    _range("reverb.highcut", "High Cut", "reverb", 0x47, 1000, 16001, 16001, width=2,
           display=Display.HZ_HIGHCUT, depends="reverb.type", values=(0, 1, 2), status=_M,
           display_status=_D, source="S1, S3"),
    _range("reverb.highratio", "High Ratio", "reverb", 0x49, 1, 10, 8, display=Display.TENTH,
           depends="reverb.type", values=(0, 1, 2), status=_M, display_status=_D,
           source="S1, S3"),
    _range("reverb.lowratio", "Low Ratio", "reverb", 0x4A, 1, 14, 10, display=Display.TENTH,
           depends="reverb.type", values=(0, 1, 2), status=_M, display_status=_D,
           source="S1, S3"),
    _range("reverb.level", "Level", "reverb", 0x4B, 0, 100, 30,
           depends="reverb.type", values=(0, 1, 2)),
    _range("reverb.spring.reverb", "Reverb", "reverb", 0x41, 0, 100, 50,
           depends="reverb.type", values=(3,)),
    _range("reverb.spring.filter", "Filter", "reverb", 0x42, 0, 100, 50,
           depends="reverb.type", values=(3,)),
    # Гейт
    _switch("gate.on", "gate", 0x5F, 0),
    _range("gate.threshold", "Threshold", "gate", 0x51, 0, 100, 50),
    _range("gate.release", "Release", "gate", 0x52, 0, 100, 50),
]

PARAMS: dict[str, ParamDef] = {p.key: p for p in _PARAM_LIST}
PARAM_KEYS: tuple[str, ...] = tuple(PARAMS)
TYPE_KEYS: frozenset[str] = frozenset({"comp.type", "mod.type", "reverb.type"})
SWITCH_KEYS: tuple[str, ...] = tuple(p.key for p in _PARAM_LIST if p.kind is Kind.SWITCH)
CONTINUOUS_KEYS: tuple[str, ...] = tuple(p.key for p in _PARAM_LIST if p.kind is Kind.RANGE)


@dataclass(frozen=True)
class Group:
    key: str
    title: str
    switch_key: str | None
    type_key: str | None
    accent: str  # имя токена цвета группы


GROUPS: tuple[Group, ...] = (
    Group("amp", "Усилитель", None, None, "groupAmp"),
    Group("comp", "Компрессор", "comp.on", "comp.type", "groupComp"),
    Group("mod", "Модуляция", "mod.on", "mod.type", "groupMod"),
    Group("delay", "Дилей", "delay.on", None, "groupDelay"),
    Group("reverb", "Реверб", "reverb.on", "reverb.type", "groupReverb"),
    Group("gate", "Гейт", "gate.on", None, "groupGate"),
)
GROUPS_BY_KEY = {g.key: g for g in GROUPS}


@dataclass(frozen=True)
class SystemDef:
    """Настройки устройства вне пресета (lamp/wide). Источник S1, UNCONFIRMED."""

    key: str
    label: str
    default: bool
    status: Status = Status.UNCONFIRMED
    source: str = "S1"


SYSTEM_SETTINGS: dict[str, SystemDef] = {
    "system.lamp": SystemDef("system.lamp", "Подсветка (Lamp)", True),
    "system.wide": SystemDef("system.wide", "Широкое стерео (Wide)", False),
}


def default_values() -> dict[str, int]:
    return {k: p.default for k, p in PARAMS.items()}


def params_in_group(group: str) -> list[ParamDef]:
    return [p for p in _PARAM_LIST if p.group == group]


def active_keys(values: Mapping[str, int]) -> list[str]:
    return [k for k, p in PARAMS.items() if p.is_active(values)]


def resolve_address(address: int, values: Mapping[str, int]) -> ParamDef | None:
    """Найти параметр по адресу с учётом текущих типов эффектов."""
    for p in _PARAM_LIST:
        if p.address == address and p.is_active(values):
            return p
    return None


def normalize_values(values: Mapping[str, int] | None) -> dict[str, int]:
    """Полный набор значений: недостающие — по умолчанию, лишние ключи отбрасываются."""
    out = default_values()
    if values:
        for k, v in values.items():
            p = PARAMS.get(k)
            if p is not None:
                try:
                    out[k] = p.clamp(v)
                except (TypeError, ValueError):
                    pass
    return out


def keys_affected_by_type(type_key: str) -> list[str]:
    return [p.key for p in _PARAM_LIST if p.depends_on == type_key]


def iter_params(keys: Iterable[str] | None = None) -> Iterable[ParamDef]:
    if keys is None:
        yield from _PARAM_LIST
    else:
        for k in keys:
            yield PARAMS[k]


@dataclass
class ProtocolOverrides:
    """Пользовательские подтверждения (protocol_overrides.json).

    Ключи из списка confirmed считаются подтверждёнными перехватом
    и разрешаются к отправке.
    """

    confirmed: set[str] = field(default_factory=set)

    def is_sendable_param(self, p: ParamDef) -> bool:
        return p.status.sendable or p.key in self.confirmed

    def is_sendable_system(self, s: SystemDef) -> bool:
        return s.status.sendable or s.key in self.confirmed

    @classmethod
    def from_json(cls, data: object) -> "ProtocolOverrides":
        if isinstance(data, dict) and isinstance(data.get("confirmed"), list):
            return cls({str(x) for x in data["confirmed"]})
        return cls()
