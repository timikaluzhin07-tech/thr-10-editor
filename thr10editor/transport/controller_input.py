"""MIDI-контроллер / ножная педаль для сет-листа.

Слушает отдельный входной MIDI-порт (не порт комбика). Поддерживаются
Control Change, Program Change и ноты; привязка «следующий/предыдущий»
задаётся обучением (learn) — нажмите педаль, и событие запомнится.
USB/Bluetooth-педали, которые притворяются клавиатурой (PageUp/PageDown,
стрелки), работают через горячие клавиши режима «сцена» без настройки.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from .base import TransportError

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class ControlEvent:
    kind: str  # "cc" | "pc" | "note"
    channel: int  # 0..15
    number: int
    value: int = 127

    @property
    def label(self) -> str:
        ch = self.channel + 1
        if self.kind == "cc":
            return f"CC {self.number} (канал {ch})"
        if self.kind == "pc":
            return f"Program Change {self.number + 1} (канал {ch})"
        return f"Нота {self.number} (канал {ch})"


@dataclass(frozen=True)
class Binding:
    kind: str
    channel: int | None
    number: int | None  # None для pc — любая программа

    def matches(self, e: ControlEvent) -> bool:
        if e.kind != self.kind:
            return False
        if self.channel is not None and e.channel != self.channel:
            return False
        if self.number is not None and e.number != self.number:
            return False
        if e.kind in ("cc", "note"):
            return e.value >= 64 if e.kind == "cc" else e.value > 0
        return True

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "channel": self.channel, "number": self.number}

    @classmethod
    def from_dict(cls, d: Any) -> "Binding | None":
        if not isinstance(d, dict) or d.get("kind") not in ("cc", "pc", "note"):
            return None
        return cls(d["kind"], d.get("channel"), d.get("number"))

    @classmethod
    def from_event(cls, e: ControlEvent) -> "Binding":
        return cls(e.kind, e.channel, e.number)

    @property
    def label(self) -> str:
        return ControlEvent(self.kind, self.channel or 0, self.number or 0).label


def from_mido(msg: Any) -> ControlEvent | None:
    t = getattr(msg, "type", "")
    if t == "control_change":
        return ControlEvent("cc", msg.channel, msg.control, msg.value)
    if t == "program_change":
        return ControlEvent("pc", msg.channel, msg.program, 127)
    if t == "note_on":
        return ControlEvent("note", msg.channel, msg.note, msg.velocity)
    return None


class ControllerMapper:
    """Превращает события в действия: "next", "prev" или ("goto", n)."""

    def __init__(self, next_binding: Binding | None = None, prev_binding: Binding | None = None,
                 *, pc_selects: bool = False):
        self.next = next_binding
        self.prev = prev_binding
        self.pc_selects = pc_selects
        self.learning: str | None = None  # "next" | "prev"
        self._held: set[tuple[str, int, int]] = set()

    def learn(self, which: str) -> None:
        """Начать ожидание события для «next»/«prev». Повторный вызов для того же —
        отмена (прежняя привязка не меняется)."""
        self.learning = None if self.learning == which else which

    def cancel_learn(self) -> None:
        self.learning = None

    def handle(self, e: ControlEvent) -> tuple[str, Any] | None:
        # Педаль CC шлёт 127 при нажатии и 0 при отпускании — реагируем на фронт.
        ident = (e.kind, e.channel, e.number)
        if e.kind in ("cc", "note"):
            pressed = e.value >= 64 if e.kind == "cc" else e.value > 0
            if not pressed:
                self._held.discard(ident)
                return None
            if ident in self._held:
                return None
            self._held.add(ident)
        if self.learning:
            which, self.learning = self.learning, None
            b = Binding.from_event(e)
            if which == "next":
                self.next = b
            else:
                self.prev = b
            return ("learned", (which, b))
        if self.next and self.next.matches(e):
            return ("next", None)
        if self.prev and self.prev.matches(e):
            return ("prev", None)
        if self.pc_selects and e.kind == "pc":
            return ("goto", e.number)
        return None


class ControllerInput:
    """Входной MIDI-порт контроллера (mido). Только чтение."""

    def __init__(self, port_name: str):
        self.port_name = port_name
        self._port: Any = None

    def open(self) -> None:
        from .midi import _mido

        mido = _mido()
        try:
            self._port = mido.open_input(self.port_name)
        except Exception as e:
            raise TransportError(f"не удалось открыть порт контроллера «{self.port_name}»: {e}") from e

    def close(self) -> None:
        if self._port is not None:
            try:
                self._port.close()
            except Exception:  # pragma: no cover
                log.exception("ошибка закрытия порта контроллера")
        self._port = None

    @property
    def is_open(self) -> bool:
        return self._port is not None

    def poll(self) -> list[ControlEvent]:
        if self._port is None:
            return []
        out = []
        try:
            for m in self._port.iter_pending():
                e = from_mido(m)
                if e is not None:
                    out.append(e)
        except Exception as e:
            raise TransportError(f"ошибка чтения порта контроллера: {e}") from e
        return out
