"""Инструменты звука: A/B, сет-лист, тап-темп, рандомайзер, морфинг, LFO.

Чистая логика без Qt и без транспорта: всё, что меняет звук, возвращает
словарь значений, а применяет его контроллер (через ToneState).
"""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field
from typing import Callable, Mapping

from ..protocol.params import DELAY_TIME_UNIT_MS, PARAMS, TYPE_KEYS, Kind, normalize_values
from .preset import new_id
from .taper import from_position, to_position

# ============================================================================
# A/B
# ============================================================================


@dataclass
class ABSlot:
    name: str
    values: dict[str, int]


class ABCompare:
    """Два слота звука. Текущий звук редактора — живое содержимое активного слота."""

    def __init__(self) -> None:
        self.active = "A"
        self.slots: dict[str, ABSlot | None] = {"A": None, "B": None}

    @property
    def other(self) -> str:
        return "B" if self.active == "A" else "A"

    def switch(self, name: str, values: Mapping[str, int]) -> ABSlot:
        """Сохранить текущее в активный слот и вернуть содержимое другого.

        Если другой слот пуст, он начинается с копии текущего звука.
        """
        self.slots[self.active] = ABSlot(name, dict(values))
        other = self.slots[self.other] or ABSlot(name, dict(values))
        self.slots[self.other] = other
        self.active = self.other
        return ABSlot(other.name, dict(other.values))

    def copy_to_other(self, name: str, values: Mapping[str, int]) -> None:
        self.slots[self.other] = ABSlot(name, dict(values))

    def peek_other(self) -> ABSlot | None:
        s = self.slots[self.other]
        return ABSlot(s.name, dict(s.values)) if s else None


# ============================================================================
# Сет-лист
# ============================================================================


class SetlistPlayer:
    """Навигация по упорядоченному списку (без зацикливания по умолчанию)."""

    def __init__(self, items: list[str] | None = None, *, wrap: bool = False):
        self.items = list(items or [])
        self.index = 0
        self.wrap = wrap

    @property
    def current(self) -> str | None:
        return self.items[self.index] if 0 <= self.index < len(self.items) else None

    def goto(self, index: int) -> str | None:
        if not self.items:
            return None
        if self.wrap:
            index %= len(self.items)
        index = max(0, min(len(self.items) - 1, index))
        self.index = index
        return self.current

    def next(self) -> str | None:
        return self.goto(self.index + 1)

    def prev(self) -> str | None:
        return self.goto(self.index - 1)

    def peek(self, offset: int) -> str | None:
        i = self.index + offset
        if self.wrap and self.items:
            i %= len(self.items)
        return self.items[i] if 0 <= i < len(self.items) else None


# ============================================================================
# Тап-темп
# ============================================================================

SUBDIVISIONS: dict[str, float] = {
    "1/2": 2.0,
    "1/4.": 1.5,
    "1/4": 1.0,
    "1/4T": 2 / 3,
    "1/8.": 0.75,
    "1/8": 0.5,
    "1/8T": 1 / 3,
    "1/16": 0.25,
}


class TapTempo:
    """Тап-темп: среднее последних интервалов; пауза дольше timeout — сброс."""

    def __init__(self, *, timeout: float = 2.0, max_taps: int = 5,
                 clock: Callable[[], float] = time.monotonic):
        self.timeout = timeout
        self.max_taps = max_taps
        self.clock = clock
        self._taps: list[float] = []

    def tap(self, t: float | None = None) -> float | None:
        """Зарегистрировать удар. Возвращает интервал в мс (или None на первом ударе)."""
        t = self.clock() if t is None else t
        if self._taps and t - self._taps[-1] > self.timeout:
            self._taps.clear()
        self._taps.append(t)
        self._taps = self._taps[-self.max_taps:]
        return self.interval_ms

    @property
    def interval_ms(self) -> float | None:
        if len(self._taps) < 2:
            return None
        intervals = [b - a for a, b in zip(self._taps, self._taps[1:])]
        return 1000.0 * sum(intervals) / len(intervals)

    @property
    def bpm(self) -> float | None:
        ms = self.interval_ms
        return 60000.0 / ms if ms else None

    @property
    def taps(self) -> int:
        return len(self._taps)

    def reset(self) -> None:
        self._taps.clear()


def delay_value_for(interval_ms: float, subdivision: str = "1/4") -> tuple[int, bool]:
    """Значение Delay Time для интервала четверти и доли. (значение, ограничено ли)."""
    p = PARAMS["delay.time"]
    ms = interval_ms * SUBDIVISIONS.get(subdivision, 1.0)
    raw = round(ms / DELAY_TIME_UNIT_MS)
    clamped = p.clamp(raw)
    return clamped, clamped != raw


# ============================================================================
# Рандомайзер
# ============================================================================


@dataclass
class RandomizerConfig:
    amount: float = 1.0  # 0..1: насколько далеко от текущего звука
    locked: set[str] = field(default_factory=lambda: {"amp.master"})
    bounds: dict[str, tuple[float, float]] = field(default_factory=dict)  # положения 0..1
    include_types: bool = False  # типы эффектов
    include_switches: bool = False  # вкл/выкл блоков
    include_amp: bool = False  # модель усилителя и кабинет

    def bounds_for(self, key: str) -> tuple[float, float]:
        lo, hi = self.bounds.get(key, (0.0, 1.0))
        lo, hi = max(0.0, min(1.0, lo)), max(0.0, min(1.0, hi))
        return (lo, hi) if lo <= hi else (hi, lo)


def randomize(values: Mapping[str, int], cfg: RandomizerConfig,
              rng: random.Random | None = None) -> dict[str, int]:
    """Новые значения. Заблокированные параметры не меняются; границы — в положениях ручки."""
    rng = rng or random.Random()
    current = normalize_values(values)
    out = dict(current)
    amount = max(0.0, min(1.0, cfg.amount))
    for key, p in PARAMS.items():
        if key in cfg.locked:
            continue
        if p.kind is Kind.RANGE:
            lo, hi = cfg.bounds_for(key)
            pos = to_position(p, current[key])
            target = rng.uniform(lo, hi)
            new_pos = max(lo, min(hi, pos + amount * (target - pos)))
            out[key] = from_position(p, new_pos)
        elif p.kind is Kind.SWITCH:
            if cfg.include_switches:
                out[key] = rng.randint(0, 1)
        elif p.kind is Kind.CHOICE:
            if key in TYPE_KEYS:
                if not cfg.include_types:
                    continue
            elif key in ("amp.model", "amp.cab"):
                if not cfg.include_amp:
                    continue
            out[key] = rng.randint(p.minimum, p.maximum)
    return out


# ============================================================================
# Морфинг
# ============================================================================

CURVES: dict[str, Callable[[float], float]] = {
    "linear": lambda t: t,
    "smooth": lambda t: t * t * (3 - 2 * t),
    "ease-in": lambda t: t * t,
    "ease-out": lambda t: 1 - (1 - t) * (1 - t),
}


def interpolate(a: Mapping[str, int], b: Mapping[str, int], t: float,
                curve: str = "linear") -> dict[str, int]:
    """Промежуточный звук. Непрерывные параметры — в положениях ручки; выбор и
    вкл/выкл переключаются на середине (t ≥ 0,5)."""
    t = max(0.0, min(1.0, t))
    k = CURVES.get(curve, CURVES["linear"])(t)
    a, b = normalize_values(a), normalize_values(b)
    out: dict[str, int] = {}
    for key, p in PARAMS.items():
        if p.kind is Kind.RANGE:
            pa, pb = to_position(p, a[key]), to_position(p, b[key])
            out[key] = from_position(p, pa + (pb - pa) * k)
        else:
            out[key] = b[key] if k >= 0.5 else a[key]
    return out


class Morph:
    def __init__(self, start: Mapping[str, int], end: Mapping[str, int], duration: float,
                 curve: str = "smooth", *, clock: Callable[[], float] = time.monotonic):
        self.start_values = normalize_values(start)
        self.end_values = normalize_values(end)
        self.duration = max(0.05, float(duration))
        self.curve = curve if curve in CURVES else "linear"
        self.clock = clock
        self.t0 = clock()

    def progress(self, now: float | None = None) -> float:
        now = self.clock() if now is None else now
        return max(0.0, min(1.0, (now - self.t0) / self.duration))

    def values(self, now: float | None = None) -> tuple[dict[str, int], bool]:
        x = self.progress(now)
        return interpolate(self.start_values, self.end_values, x, self.curve), x >= 1.0


# ============================================================================
# Автоматизация (LFO)
# ============================================================================

WAVEFORMS = ("sine", "triangle", "square", "saw_up", "saw_down", "random")
WAVEFORM_LABELS = {"sine": "Синус", "triangle": "Треугольник", "square": "Меандр",
                   "saw_up": "Пила ↑", "saw_down": "Пила ↓", "random": "Случайная"}


def wave(shape: str, phase: float, seed: int = 0) -> float:
    """Значение формы волны в точке phase (в периодах), диапазон −1..1."""
    x = phase % 1.0
    if shape == "sine":
        return math.sin(2 * math.pi * x)
    if shape == "triangle":
        return 4 * x - 1 if x < 0.5 else 3 - 4 * x
    if shape == "square":
        return 1.0 if x < 0.5 else -1.0
    if shape == "saw_up":
        return 2 * x - 1
    if shape == "saw_down":
        return 1 - 2 * x
    if shape == "random":  # sample & hold: новое значение на каждом периоде
        cycle = math.floor(phase)
        return random.Random(seed * 1_000_003 + cycle).uniform(-1, 1)
    raise ValueError(f"неизвестная форма {shape}")


@dataclass
class Lfo:
    key: str
    waveform: str = "sine"
    rate_hz: float = 0.25  # медленная автоматизация: 0,01–5 Гц
    depth: float = 0.3  # доля хода ручки (размах ±depth/2)
    phase: float = 0.0  # сдвиг фазы в периодах
    enabled: bool = True
    id: str = field(default_factory=new_id)

    MIN_RATE = 0.01
    MAX_RATE = 5.0

    def clamp(self) -> None:
        self.rate_hz = max(self.MIN_RATE, min(self.MAX_RATE, float(self.rate_hz)))
        self.depth = max(0.0, min(1.0, float(self.depth)))
        if self.waveform not in WAVEFORMS:
            self.waveform = "sine"

    def to_dict(self) -> dict:
        return {"id": self.id, "key": self.key, "waveform": self.waveform,
                "rate_hz": self.rate_hz, "depth": self.depth, "phase": self.phase,
                "enabled": self.enabled}

    @classmethod
    def from_dict(cls, d: Mapping) -> "Lfo":
        lfo = cls(key=str(d["key"]), waveform=str(d.get("waveform", "sine")),
                  rate_hz=float(d.get("rate_hz", 0.25)), depth=float(d.get("depth", 0.3)),
                  phase=float(d.get("phase", 0.0)), enabled=bool(d.get("enabled", True)),
                  id=str(d.get("id") or new_id()))
        lfo.clamp()
        return lfo


class Automation:
    """Набор LFO. Модулирует параметры вокруг значения, которое было на старте.

    max_rate_hz ограничивает частоту обновления каждого параметра, чтобы не
    забивать MIDI-порт (сверх этого действует общий лимит отправки).
    """

    def __init__(self, *, max_rate_hz: float = 20.0, clock: Callable[[], float] = time.monotonic):
        self.lfos: list[Lfo] = []
        self.max_rate_hz = max_rate_hz
        self.clock = clock
        self.running = False
        self.t0 = 0.0
        self.base: dict[str, int] = {}
        self._last_emit: dict[str, float] = {}
        self._last_value: dict[str, int] = {}

    # ---- список LFO ---------------------------------------------------------------
    def add(self, key: str, **kw) -> Lfo:
        if PARAMS[key].kind is not Kind.RANGE:
            raise ValueError("LFO можно назначить только на ручку")
        self.remove_key(key)
        lfo = Lfo(key=key, **kw)
        lfo.clamp()
        self.lfos.append(lfo)
        if self.running:
            self.base.setdefault(key, PARAMS[key].default)
        return lfo

    def remove(self, lfo_id: str) -> Lfo | None:
        for i, l in enumerate(self.lfos):
            if l.id == lfo_id:
                return self.lfos.pop(i)
        return None

    def remove_key(self, key: str) -> None:
        self.lfos = [l for l in self.lfos if l.key != key]

    def get(self, lfo_id: str) -> Lfo | None:
        return next((l for l in self.lfos if l.id == lfo_id), None)

    def keys(self) -> set[str]:
        return {l.key for l in self.lfos}

    # ---- работа ---------------------------------------------------------------------
    def start(self, current: Mapping[str, int], now: float | None = None) -> None:
        self.t0 = self.clock() if now is None else now
        self.base = {l.key: int(current[l.key]) for l in self.lfos}
        self._last_emit.clear()
        self._last_value.clear()
        self.running = True

    def stop(self) -> dict[str, int]:
        """Остановить. Возвращает исходные значения, к которым надо вернуться."""
        self.running = False
        base, self.base = self.base, {}
        return base

    def rebase(self, key: str, value: int) -> None:
        """Пользователь сам покрутил ручку под LFO — новый центр модуляции."""
        if key in self.base:
            self.base[key] = value

    def value_at(self, lfo: Lfo, now: float) -> int:
        p = PARAMS[lfo.key]
        base_pos = to_position(p, self.base.get(lfo.key, p.default))
        phase = (now - self.t0) * lfo.rate_hz + lfo.phase
        seed = int(lfo.id[:8], 16) if all(c in "0123456789abcdef" for c in lfo.id[:8]) else 0
        pos = base_pos + 0.5 * lfo.depth * wave(lfo.waveform, phase, seed)
        return from_position(p, pos)

    def tick(self, now: float | None = None) -> dict[str, int]:
        if not self.running:
            return {}
        now = self.clock() if now is None else now
        min_dt = 1.0 / self.max_rate_hz if self.max_rate_hz > 0 else 0.0
        out: dict[str, int] = {}
        for lfo in self.lfos:
            if not lfo.enabled:
                continue
            last = self._last_emit.get(lfo.key)
            if last is not None and now - last < min_dt:
                continue
            v = self.value_at(lfo, now)
            if self._last_value.get(lfo.key) == v:
                continue
            self._last_emit[lfo.key] = now
            self._last_value[lfo.key] = v
            out[lfo.key] = v
        return out
