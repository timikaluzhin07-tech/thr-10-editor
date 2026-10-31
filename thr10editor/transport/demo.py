"""Демо-режим: программная модель комбика THR10.

DemoAmp ведёт себя как комбик на уровне SysEx: принимает изменения
параметров и дампы, отвечает дампом на запрос, шлёт heartbeat, а по
командам симуляции «крутит ручки» и «нажимает кнопки ячеек» — так можно
проверить синхронизацию без железа. Все сообщения проходят через тот же
слой протокола, что и в реальном режиме.
"""

from __future__ import annotations

import time
from typing import Callable

from ..protocol import constants as C
from ..protocol.params import PARAMS, default_values, normalize_values
from ..protocol.patch import decode_patch, encode_patch
from ..protocol.sysex import (
    DumpRequest,
    ParamChange,
    PatchDump,
    SystemCommand,
    Unknown,
    decode,
    encode_param,
    encode_patch_dump,
)
from .base import Transport, TransportError

HEARTBEAT_PERIOD = 0.5  # S1: «about twice a second»


def _preset(name: str, **values: int) -> tuple[str, dict[str, int]]:
    v = default_values()
    v.update({k.replace("__", "."): x for k, x in values.items()})
    return name, normalize_values(v)


# Заводские ячейки для демо (значения из заводских пресетов S1 + наши эффекты).
DEMO_SLOTS: list[tuple[str, dict[str, int]]] = [
    _preset("PRESET1", amp__model=0, amp__gain=37, amp__master=100, amp__bass=78,
            amp__middle=59, amp__treble=66, amp__cab=1, reverb__on=1),
    _preset("PRESET2", amp__model=1, amp__gain=79, amp__master=44, amp__bass=55,
            amp__middle=73, amp__treble=62, amp__cab=3),
    _preset("PRESET3", amp__model=2, amp__gain=77, amp__master=89, amp__bass=38,
            amp__middle=81, amp__treble=84, amp__cab=2, delay__on=1),
    _preset("PRESET4", amp__model=3, amp__gain=45, amp__master=100, amp__bass=87,
            amp__middle=73, amp__treble=30, amp__cab=2, gate__on=1),
    _preset("PRESET5", amp__model=4, amp__gain=29, amp__master=76, amp__bass=67,
            amp__middle=82, amp__treble=61, amp__cab=0, gate__on=1),
]


class DemoAmp:
    """Симулятор комбика. Входящие байты — receive(), исходящие — outbox."""

    def __init__(self, model_code: int = 0x31, clock: Callable[[], float] = time.monotonic):
        self.model_code = model_code
        self._clock = clock
        name, values = DEMO_SLOTS[0]
        self.name = name
        self.values = dict(values)
        self.slots = [(n, dict(v)) for n, v in DEMO_SLOTS]
        self.system = {"system.lamp": True, "system.wide": False}
        self.outbox: list[bytes] = []
        self.received: list[bytes] = []
        self.powered = True
        self._last_heartbeat = -1e9

    # ---- приём ---------------------------------------------------------------
    def receive(self, msg: bytes) -> None:
        if not self.powered:
            return
        self.received.append(bytes(msg))
        m = decode(msg)
        if isinstance(m, ParamChange):
            p = m.resolve(self.values)
            if p is not None:
                self.values[p.key] = p.from_raw(m.value)
        elif isinstance(m, PatchDump):
            if m.checksum_ok:
                d = decode_patch(m.patch, base=self.values)
                self.name, self.values = d.name, d.values
        elif isinstance(m, DumpRequest):
            self.outbox.append(self.current_dump())
        elif isinstance(m, SystemCommand):
            for key, variants in C.SYSTEM_COMMANDS.items():
                for on, payload in variants.items():
                    if payload == m.payload:
                        self.system[key] = on
        elif isinstance(m, Unknown):
            raise TransportError(f"демо-комбик получил неизвестное сообщение: {m.reason}")

    def current_dump(self) -> bytes:
        return encode_patch_dump(encode_patch(self.name, self.values))

    # ---- симуляция действий на комбике ---------------------------------------
    def turn_knob(self, key: str, value: int) -> None:
        """Как будто ручку повернули на самом комбике."""
        p = PARAMS[key]
        if not p.is_active(self.values):
            return
        self.values[key] = p.clamp(value)
        self.outbox.append(encode_param(p, self.values[key]))

    def press_slot(self, index: int) -> None:
        """Как будто нажали кнопку ячейки 1–5 (index 0–4)."""
        name, values = self.slots[index]
        self.name, self.values = name, dict(values)
        self.outbox.append(self.current_dump())

    def store_slot(self, index: int) -> None:
        """Как будто удержали кнопку ячейки — сохранить текущее состояние."""
        self.slots[index] = (self.name, dict(self.values))

    def tick(self) -> None:
        if not self.powered:
            return
        now = self._clock()
        if now - self._last_heartbeat >= HEARTBEAT_PERIOD:
            self._last_heartbeat = now
            self.outbox.append(C.HEARTBEAT_PREFIX + bytes([self.model_code, C.SYSEX_END]))

    def take(self) -> list[bytes]:
        out, self.outbox = self.outbox, []
        return out


class DemoTransport(Transport):
    kind = "demo"
    accepts_unconfirmed = True

    def __init__(self, amp: DemoAmp | None = None, clock: Callable[[], float] = time.monotonic):
        self.amp = amp or DemoAmp(clock=clock)
        self._open = False

    @property
    def name(self) -> str:
        return "Демо-комбик"

    @property
    def is_open(self) -> bool:
        return self._open

    def open(self) -> None:
        self._open = True

    def close(self) -> None:
        self._open = False

    def send(self, msg: bytes) -> None:
        if not self._open:
            raise TransportError("демо-порт закрыт")
        self.amp.receive(msg)

    def poll(self) -> list[bytes]:
        if not self._open:
            return []
        self.amp.tick()
        return self.amp.take()
