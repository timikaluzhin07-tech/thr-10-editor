"""QObject-обёртки параметров и блоков эффектов для QML."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from PySide6.QtCore import Property, QObject, Signal, Slot

from ..protocol.constants import Status
from ..protocol.params import GROUPS_BY_KEY, PARAMS, Kind, ParamDef, params_in_group

if TYPE_CHECKING:  # pragma: no cover
    from .backend import Backend

# Параметры с логарифмической шкалой ручки (частоты и времена).
LOG_TAPER = {"delay.time", "delay.highcut", "delay.lowcut", "reverb.time", "reverb.pre",
             "reverb.lowcut", "reverb.highcut"}


def to_position(p: ParamDef, value: int) -> float:
    """Значение → положение ручки 0..1 (с учётом шкалы)."""
    if p.span == 0:
        return 0.0
    if p.key in LOG_TAPER and p.minimum > 0:
        return math.log(value / p.minimum) / math.log(p.maximum / p.minimum)
    return (value - p.minimum) / p.span


def from_position(p: ParamDef, x: float) -> int:
    x = max(0.0, min(1.0, x))
    if p.key in LOG_TAPER and p.minimum > 0:
        return p.clamp(p.minimum * (p.maximum / p.minimum) ** x)
    return p.clamp(p.minimum + x * p.span)


class ParamItem(QObject):
    changed = Signal()
    activeChanged = Signal()
    flagsChanged = Signal()

    def __init__(self, backend: "Backend", pdef: ParamDef):
        super().__init__(backend)
        self._b = backend
        self._p = pdef
        self._value = pdef.default
        self._active = True
        self._locked = False
        self._automated = False

    # ---- синхронизация из бэкенда ------------------------------------------------
    def sync(self, value: int) -> None:
        if value != self._value:
            self._value = value
            self.changed.emit()

    def sync_active(self, active: bool) -> None:
        if active != self._active:
            self._active = active
            self.activeChanged.emit()

    def sync_flags(self, locked: bool, automated: bool) -> None:
        if (locked, automated) != (self._locked, self._automated):
            self._locked, self._automated = locked, automated
            self.flagsChanged.emit()

    # ---- константы ----------------------------------------------------------------
    @Property(str, constant=True)
    def key(self) -> str:
        return self._p.key

    @Property(str, constant=True)
    def label(self) -> str:
        return self._p.label

    @Property(str, constant=True)
    def kind(self) -> str:
        return self._p.kind.value

    @Property(str, constant=True)
    def group(self) -> str:
        return self._p.group

    @Property(int, constant=True)
    def minimum(self) -> int:
        return self._p.minimum

    @Property(int, constant=True)
    def maximum(self) -> int:
        return self._p.maximum

    @Property(int, constant=True)
    def defaultValue(self) -> int:  # noqa: N802
        return self._p.default

    @Property(float, constant=True)
    def defaultPosition(self) -> float:  # noqa: N802
        return to_position(self._p, self._p.default)

    @Property("QStringList", constant=True)
    def options(self) -> list[str]:
        return list(self._p.options)

    @Property(str, constant=True)
    def hint(self) -> str:
        parts = [self._p.hint] if self._p.hint else []
        if self._p.display_status is Status.DERIVED:
            parts.append("Единицы отображения — вывод, требует проверки на железе")
        parts.append(f"Адрес 0x{self._p.address:02X}, источник {self._p.source}")
        return ". ".join(parts)

    @Property(bool, constant=True)
    def displayDerived(self) -> bool:  # noqa: N802
        return self._p.display_status is Status.DERIVED

    @Property(int, constant=True)
    def coarseStep(self) -> int:  # noqa: N802
        return max(1, round(self._p.span / 100))

    @Property(int, constant=True)
    def fineStep(self) -> int:  # noqa: N802
        return max(1, round(self._p.span / 1000))

    @Property(bool, constant=True)
    def logTaper(self) -> bool:  # noqa: N802
        return self._p.key in LOG_TAPER

    # ---- изменяемые ------------------------------------------------------------------
    @Property(int, notify=changed)
    def value(self) -> int:
        return self._value

    @Property(str, notify=changed)
    def text(self) -> str:
        return self._p.format(self._value)

    @Property(float, notify=changed)
    def position(self) -> float:
        return to_position(self._p, self._value)

    @Property(bool, notify=activeChanged)
    def active(self) -> bool:
        return self._active

    @Property(bool, notify=flagsChanged)
    def locked(self) -> bool:
        return self._locked

    @Property(bool, notify=flagsChanged)
    def automated(self) -> bool:
        return self._automated

    @Property(bool, notify=changed)
    def confirmed(self) -> bool:
        return self._b.is_confirmed(self._p.key)

    # ---- действия ----------------------------------------------------------------------
    @Slot(int)
    def setValue(self, v: int) -> None:  # noqa: N802
        self._b.set_param(self._p.key, int(v))

    @Slot(float)
    def setPosition(self, x: float) -> None:  # noqa: N802
        self._b.set_param(self._p.key, from_position(self._p, x))

    @Slot(str, result=bool)
    def setFromText(self, text: str) -> bool:  # noqa: N802
        v = self._p.parse(text)
        if v is None:
            return False
        self._b.set_param(self._p.key, v)
        return True

    @Slot(int)
    def step(self, steps: int) -> None:
        self._b.set_param(self._p.key, self._value + int(steps))

    @Slot()
    def reset(self) -> None:
        self._b.begin_gesture(self._p.key)
        self._b.set_param(self._p.key, self._p.default)
        self._b.end_gesture()

    @Slot()
    def beginGesture(self) -> None:  # noqa: N802
        self._b.begin_gesture(self._p.key)

    @Slot()
    def endGesture(self) -> None:  # noqa: N802
        self._b.end_gesture()

    @Slot()
    def toggleLock(self) -> None:  # noqa: N802
        self._b.toggle_lock(self._p.key)

    @Slot(int, result=str)
    def format(self, v: int) -> str:
        return self._p.format(v)

    @Slot(float, result=str)
    def formatPosition(self, x: float) -> str:  # noqa: N802
        return self._p.format(from_position(self._p, x))


class GroupItem(QObject):
    changed = Signal()

    def __init__(self, backend: "Backend", key: str):
        super().__init__(backend)
        self._b = backend
        self._g = GROUPS_BY_KEY[key]
        self._enabled = True
        self._type = 0
        self._keys: list[str] = []

    def sync(self, values: dict[str, int]) -> None:
        g = self._g
        enabled = bool(values[g.switch_key]) if g.switch_key else True
        type_index = values[g.type_key] if g.type_key else 0
        keys = [p.key for p in params_in_group(g.key)
                if p.key not in (g.switch_key, g.type_key) and p.is_active(values)
                and p.key not in ("amp.model", "amp.cab")]
        if (enabled, type_index, keys) != (self._enabled, self._type, self._keys):
            self._enabled, self._type, self._keys = enabled, type_index, keys
            self.changed.emit()

    @Property(str, constant=True)
    def key(self) -> str:
        return self._g.key

    @Property(str, constant=True)
    def title(self) -> str:
        return self._g.title

    @Property(str, constant=True)
    def accent(self) -> str:
        return self._g.accent

    @Property(bool, constant=True)
    def hasSwitch(self) -> bool:  # noqa: N802
        return self._g.switch_key is not None

    @Property(str, constant=True)
    def switchKey(self) -> str:  # noqa: N802
        return self._g.switch_key or ""

    @Property(str, constant=True)
    def typeKey(self) -> str:  # noqa: N802
        return self._g.type_key or ""

    @Property("QStringList", constant=True)
    def typeOptions(self) -> list[str]:  # noqa: N802
        return list(PARAMS[self._g.type_key].options) if self._g.type_key else []

    @Property(bool, notify=changed)
    def enabled(self) -> bool:
        return self._enabled

    @Property(int, notify=changed)
    def typeIndex(self) -> int:  # noqa: N802
        return self._type

    @Property("QStringList", notify=changed)
    def activeKeys(self) -> list[str]:  # noqa: N802
        return list(self._keys)

    @Property("QStringList", notify=changed)
    def knobKeys(self) -> list[str]:  # noqa: N802
        return [k for k in self._keys if PARAMS[k].kind is Kind.RANGE]

    @Property("QStringList", notify=changed)
    def choiceKeys(self) -> list[str]:  # noqa: N802
        return [k for k in self._keys if PARAMS[k].kind is Kind.CHOICE]

    @Slot(bool)
    def setEnabled(self, on: bool) -> None:  # noqa: N802
        if self._g.switch_key:
            self._b.begin_gesture(self._g.switch_key)
            self._b.set_param(self._g.switch_key, 1 if on else 0)
            self._b.end_gesture()

    @Slot(int)
    def setType(self, index: int) -> None:  # noqa: N802
        if self._g.type_key:
            self._b.begin_gesture(self._g.type_key)
            self._b.set_param(self._g.type_key, index)
            self._b.end_gesture()
