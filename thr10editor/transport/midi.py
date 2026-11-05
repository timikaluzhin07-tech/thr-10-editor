"""Реальный MIDI через mido + python-rtmidi.

Каждое исходящее сообщение проходит SafetyGate: на комбик уходят только
изменения подтверждённых параметров, запрос состояния и корректный дамп.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from ..protocol import constants as C
from ..protocol.params import ProtocolOverrides
from ..protocol.sysex import SafetyGate, UnsafeMessageError
from .base import Transport, TransportError

log = logging.getLogger(__name__)

# Подстроки имени порта, по которым ищется комбик (без учёта регистра).
THR_PORT_PATTERNS = ("thr10", "thr5", "thr")


def _mido() -> Any:
    try:
        import mido  # noqa: WPS433 — импорт по требованию: без MIDI работает демо
    except ImportError as e:  # pragma: no cover - зависит от окружения
        raise TransportError(f"библиотека mido не установлена: {e}") from e
    try:
        mido.set_backend("mido.backends.rtmidi", load=True)
    except Exception as e:  # pragma: no cover - зависит от окружения
        raise TransportError(f"MIDI-драйвер (python-rtmidi) недоступен: {e}") from e
    return mido


@dataclass(frozen=True)
class PortPair:
    input: str
    output: str

    @property
    def label(self) -> str:
        return self.input if self.input == self.output else f"{self.input} / {self.output}"


def list_ports() -> tuple[list[str], list[str]]:
    mido = _mido()
    try:
        return list(mido.get_input_names()), list(mido.get_output_names())
    except Exception as e:  # pragma: no cover - драйвер
        raise TransportError(f"не удалось получить список MIDI-портов: {e}") from e


def _score(name: str) -> int:
    low = name.lower()
    for i, pat in enumerate(THR_PORT_PATTERNS):
        if pat in low:
            return len(THR_PORT_PATTERNS) - i
    return 0


def _base(name: str) -> str:
    """Имя порта без номера, который добавляет rtmidi (например «THR10 0» → «thr10»)."""
    parts = name.strip().rsplit(" ", 1)
    if len(parts) == 2 and parts[1].isdigit():
        return parts[0].lower()
    return name.strip().lower()


def find_thr_ports(inputs: list[str], outputs: list[str]) -> PortPair | None:
    """Найти пару портов THR. Предпочитает вход и выход с одинаковым именем."""
    ins = sorted((n for n in inputs if _score(n)), key=_score, reverse=True)
    outs = sorted((n for n in outputs if _score(n)), key=_score, reverse=True)
    if not ins or not outs:
        return None
    for i in ins:
        for o in outs:
            if _base(i) == _base(o):
                return PortPair(i, o)
    return PortPair(ins[0], outs[0])


def all_port_pairs(inputs: list[str], outputs: list[str]) -> list[PortPair]:
    """Все разумные пары вход/выход (одноимённые) для ручного выбора."""
    pairs = [PortPair(i, o) for i in inputs for o in outputs if _base(i) == _base(o)]
    return pairs or [PortPair(i, o) for i in inputs for o in outputs]


class MidiTransport(Transport):
    kind = "midi"
    accepts_unconfirmed = False

    def __init__(self, ports: PortPair, overrides: ProtocolOverrides | None = None):
        self.ports = ports
        self.gate = SafetyGate(overrides)
        self._in: Any = None
        self._out: Any = None

    @property
    def name(self) -> str:
        return self.ports.label

    @property
    def is_open(self) -> bool:
        return self._in is not None and self._out is not None

    def open(self) -> None:
        mido = _mido()
        try:
            self._in = mido.open_input(self.ports.input)
            self._out = mido.open_output(self.ports.output)
        except Exception as e:
            self.close()
            raise TransportError(
                f"не удалось открыть MIDI-порт «{self.ports.label}»: {e}. "
                "Проверьте, что комбик включён, подключён по USB и порт не занят "
                "другой программой (например, официальным THR Editor).") from e
        log.info("MIDI открыт: in=%s out=%s", self.ports.input, self.ports.output)

    def close(self) -> None:
        for port in (self._in, self._out):
            if port is not None:
                try:
                    port.close()
                except Exception:  # pragma: no cover - драйвер
                    log.exception("ошибка при закрытии порта")
        self._in = self._out = None

    def send(self, msg: bytes) -> None:
        if not self.is_open:
            raise TransportError("MIDI-порт не открыт")
        try:
            self.gate.check(msg)  # последний защитный рубеж
        except UnsafeMessageError:
            log.error("SafetyGate заблокировал сообщение: %s", msg.hex(" "))
            raise
        mido = _mido()
        try:
            self._out.send(mido.Message("sysex", data=list(msg[1:-1])))
        except Exception as e:
            raise TransportError(f"ошибка отправки в MIDI-порт: {e}") from e

    def poll(self) -> list[bytes]:
        if self._in is None:
            return []
        out: list[bytes] = []
        try:
            for m in self._in.iter_pending():
                if m.type == "sysex":
                    out.append(bytes([C.SYSEX_START, *m.data, C.SYSEX_END]))
        except Exception as e:
            raise TransportError(f"ошибка чтения MIDI-порта: {e}") from e
        return out
