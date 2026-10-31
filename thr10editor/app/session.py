"""Сессия редактора: связывает модель состояния и транспорт (без Qt).

* Изменения из интерфейса уходят на комбик (с ограничением частоты).
* Изменения с комбика (ручки, кнопки ячеек, ответ на запрос) применяются
  к модели с пометкой Origin.DEVICE и обратно не отправляются.
* Неподтверждённые параметры на реальный комбик не отправляются.
* Отслеживает состояние связи по heartbeat и ответам.
"""

from __future__ import annotations

import logging
import time
from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Callable

from ..model.state import Changes, Origin, ToneState
from ..protocol.params import (
    PARAMS,
    SYSTEM_SETTINGS,
    TYPE_KEYS,
    ParamDef,
    ProtocolOverrides,
    keys_affected_by_type,
)
from ..protocol.patch import DecodedPatch, decode_patch, encode_patch
from ..protocol.sysex import (
    DumpRequest,
    Heartbeat,
    ParamChange,
    PatchDump,
    SystemCommand,
    UnsafeMessageError,
    decode,
    encode_dump_request,
    encode_param,
    encode_patch_dump,
    encode_system,
    hexstr,
)
from ..transport.base import Transport, TransportError
from ..transport.sender import RateLimitedSender

log = logging.getLogger(__name__)


class LinkStatus(str, Enum):
    OFFLINE = "offline"  # транспорт не выбран
    CONNECTING = "connecting"  # порт открыт, ждём ответа
    CONNECTED = "connected"  # комбик отвечает
    NO_RESPONSE = "no_response"  # порт открыт, но ответа нет
    ERROR = "error"  # ошибка транспорта


@dataclass(frozen=True)
class LogEntry:
    time: float
    direction: str  # "in" | "out" | "info" | "warn" | "error"
    text: str
    raw: str = ""


class EditorSession:
    HEARTBEAT_TIMEOUT = 2.5
    CONNECT_TIMEOUT = 3.0
    ECHO_WINDOW = 0.6
    BULK_DUMP_THRESHOLD = 8  # больше изменений разом → один дамп вместо пачки
    RESYNC_DELAY = 0.3
    RECONNECT_PERIOD = 3.0

    def __init__(self, state: ToneState | None = None, *,
                 overrides: ProtocolOverrides | None = None,
                 clock: Callable[[], float] = time.monotonic,
                 min_interval: float = 0.02):
        self.state = state or ToneState()
        self.overrides = overrides or ProtocolOverrides()
        self.clock = clock
        self.min_interval = min_interval
        self.transport: Transport | None = None
        self.sender: RateLimitedSender | None = None
        self.status = LinkStatus.OFFLINE
        self.status_text = "Комбик не подключён"
        self.device_model = ""
        self.got_state = False
        self.log: deque[LogEntry] = deque(maxlen=600)
        self.system = {k: d.default for k, d in SYSTEM_SETTINGS.items()}
        self.local_only: set[str] = set()
        self.reconnect_factory: Callable[[], Transport] | None = None

        self._opened_at = 0.0
        self._last_rx: float | None = None
        self._heartbeat_seen = False
        self._recent_sent: dict[int, list[tuple[float, int]]] = {}
        self._capture_slot: int | None = None
        self._resync_at: float | None = None
        self._next_reconnect: float | None = None

        self.on_status: list[Callable[[LinkStatus, str], None]] = []
        self.on_log: list[Callable[[LogEntry], None]] = []
        self.on_device_dump: list[Callable[[DecodedPatch], None]] = []
        self.on_slot_captured: list[Callable[[int, DecodedPatch], None]] = []

        self.state.subscribe(self._on_state_change)

    # ---- журнал и статус -----------------------------------------------------
    def _log(self, direction: str, text: str, raw: bytes | None = None) -> None:
        entry = LogEntry(self.clock(), direction, text, hexstr(raw) if raw else "")
        self.log.append(entry)
        level = {"error": logging.ERROR, "warn": logging.WARNING}.get(direction, logging.INFO)
        log.log(level, "%s %s %s", direction.upper(), text, entry.raw)
        for cb in list(self.on_log):
            cb(entry)

    def _set_status(self, status: LinkStatus, text: str) -> None:
        if status == self.status and text == self.status_text:
            return
        self.status, self.status_text = status, text
        self._log("info" if status in (LinkStatus.CONNECTED, LinkStatus.OFFLINE,
                                       LinkStatus.CONNECTING) else "warn", f"Связь: {text}")
        for cb in list(self.on_status):
            cb(status, text)

    @property
    def is_demo(self) -> bool:
        return self.transport is not None and self.transport.kind == "demo"

    # ---- подключение ---------------------------------------------------------
    def attach(self, transport: Transport) -> bool:
        """Открыть транспорт. False — не удалось (подробности в status_text)."""
        self.detach()
        try:
            transport.open()
        except TransportError as e:
            self._set_status(LinkStatus.ERROR, str(e))
            self._log("error", str(e))
            if self.reconnect_factory is not None:
                self._next_reconnect = self.clock() + self.RECONNECT_PERIOD
            return False
        self.transport = transport
        self.sender = RateLimitedSender(self._write, min_interval=self.min_interval,
                                        clock=self.clock)
        self._opened_at = self.clock()
        self._last_rx = None
        self._heartbeat_seen = False
        self.got_state = False
        self.device_model = ""
        self._next_reconnect = None
        self._set_status(LinkStatus.CONNECTING, f"Подключение: {transport.name}…")
        self.request_state()
        return True

    def detach(self) -> None:
        if self.transport is not None:
            try:
                if self.sender is not None and self.transport.is_open:
                    self.sender.flush()
            except (TransportError, UnsafeMessageError) as e:
                self._log("warn", f"не удалось дослать очередь: {e}")
            try:
                self.transport.close()
            except TransportError:
                pass
        self.transport = None
        self.sender = None
        self._capture_slot = None
        self._set_status(LinkStatus.OFFLINE, "Комбик не подключён")

    def _fail(self, error: Exception) -> None:
        name = self.transport.name if self.transport else ""
        self._log("error", f"{name}: {error}")
        if self.transport is not None:
            try:
                self.transport.close()
            except TransportError:
                pass
        self.transport = None
        self.sender = None
        self._set_status(LinkStatus.ERROR, f"Связь потеряна: {error}")
        if self.reconnect_factory is not None:
            self._next_reconnect = self.clock() + self.RECONNECT_PERIOD

    # ---- отправка ------------------------------------------------------------
    def _write(self, msg: bytes) -> None:
        assert self.transport is not None
        self.transport.send(msg)
        m = decode(msg)
        if isinstance(m, ParamChange):
            now = self.clock()
            lst = self._recent_sent.setdefault(m.address, [])
            lst.append((now, m.value))
            if len(lst) > 32:
                del lst[:-32]
            p = m.resolve(self.state.values)
            self._log("out", f"{p.key if p else hex(m.address)} = {m.value}", msg)
        elif isinstance(m, PatchDump):
            self._log("out", "дамп пресета", msg)
        elif isinstance(m, DumpRequest):
            self._log("out", "запрос состояния", msg)
        else:
            self._log("out", type(m).__name__, msg)

    def can_send_param(self, p: ParamDef) -> bool:
        if self.transport is None:
            return False
        return self.transport.accepts_unconfirmed or self.overrides.is_sendable_param(p)

    def is_param_confirmed(self, key: str) -> bool:
        return self.overrides.is_sendable_param(PARAMS[key])

    def _dump_allowed(self) -> bool:
        if self.transport is None:
            return False
        if self.transport.accepts_unconfirmed:
            return True
        return all(self.overrides.is_sendable_param(p) for p in PARAMS.values())

    def request_state(self) -> None:
        if self.sender is not None:
            self.sender.submit("request", encode_dump_request(), barrier=True)

    def push_full_state(self) -> None:
        """Отправить всё состояние одним дампом (в текущее состояние комбика)."""
        if self.sender is None:
            return
        if not self._dump_allowed():
            for p in PARAMS.values():
                if p.is_active(self.state.values):
                    self._submit_param(p, barrier=p.is_type_selector)
            return
        patch = encode_patch(self.state.name, self.state.values)
        self.sender.submit_dump(encode_patch_dump(patch))

    def _submit_param(self, p: ParamDef, *, barrier: bool = False) -> None:
        if self.sender is None:
            return
        if not self.can_send_param(p):
            if p.key not in self.local_only:
                self._log("warn", f"{p.key} не подтверждён — изменение только локально")
            self.local_only.add(p.key)
            return
        self.sender.submit(p.key, encode_param(p, self.state[p.key]), barrier=barrier)

    def _on_state_change(self, changes: Changes, origin: Origin) -> None:
        if origin is Origin.DEVICE or self.sender is None:
            return
        if origin is Origin.LOAD or (
                origin in (Origin.HISTORY, Origin.RANDOM)
                and len(changes) > self.BULK_DUMP_THRESHOLD):
            self.push_full_state()
            return
        values = self.state.values
        keys = sorted(changes, key=lambda k: 0 if k in TYPE_KEYS else 1)
        for key in keys:
            p = PARAMS[key]
            if p.is_type_selector:
                self._submit_param(p, barrier=True)
                for dk in keys_affected_by_type(key):
                    dp = PARAMS[dk]
                    if dp.is_active(values):
                        self._submit_param(dp)
            elif p.is_active(values):
                self._submit_param(p)

    def set_system(self, key: str, on: bool) -> bool:
        """Lamp/Wide. Возвращает True, если команда ушла на комбик."""
        self.system[key] = bool(on)
        d = SYSTEM_SETTINGS[key]
        if self.sender is None or self.transport is None:
            return False
        if not (self.transport.accepts_unconfirmed or self.overrides.is_sendable_system(d)):
            self._log("warn", f"{key}: команда не подтверждена — не отправлена")
            return False
        self.sender.submit(key, encode_system(key, on))
        return True

    # ---- ячейки ---------------------------------------------------------------
    def arm_slot_capture(self, index: int) -> None:
        """Следующий дамп с комбика записать как содержимое ячейки index (0–4)."""
        self._capture_slot = index
        self._log("info", f"Жду дамп ячейки {index + 1}: нажмите её кнопку на комбике")

    def cancel_slot_capture(self) -> None:
        self._capture_slot = None

    @property
    def capture_slot(self) -> int | None:
        return self._capture_slot

    # ---- приём ---------------------------------------------------------------
    def _is_echo(self, address: int, value: int, now: float) -> bool:
        lst = self._recent_sent.get(address)
        if not lst:
            return False
        lst[:] = [(t, v) for t, v in lst if now - t <= self.ECHO_WINDOW]
        for i, (_, v) in enumerate(lst):
            if v == value:
                del lst[: i + 1]
                return True
        return False

    def _mark_alive(self, now: float) -> None:
        self._last_rx = now
        if self.status is not LinkStatus.CONNECTED and self.transport is not None:
            model = f" ({self.device_model})" if self.device_model else ""
            prefix = "Демо" if self.is_demo else "Подключено"
            self._set_status(LinkStatus.CONNECTED, f"{prefix}: {self.transport.name}{model}")

    def handle_incoming(self, raw: bytes, now: float | None = None) -> None:
        now = self.clock() if now is None else now
        m = decode(raw)
        if isinstance(m, Heartbeat):
            first = not self._heartbeat_seen
            self._heartbeat_seen = True
            if m.model != self.device_model:
                self.device_model = m.model
                self._log("info", f"Модель: {m.model}" + (
                    "" if m.model == "THR10" else " — интерфейс рассчитан на THR10, "
                    "названия моделей усилителей могут отличаться"))
                if self.status is LinkStatus.CONNECTED and self.transport is not None:
                    prefix = "Демо" if self.is_demo else "Подключено"
                    self._set_status(LinkStatus.CONNECTED,
                                     f"{prefix}: {self.transport.name} ({m.model})")
            self._mark_alive(now)
            if first and not self.got_state:
                self.request_state()
            return
        if isinstance(m, PatchDump):
            if not m.checksum_ok:
                self._log("error", "дамп с неверной контрольной суммой — пропущен", raw)
                return
            self._mark_alive(now)
            d = decode_patch(m.patch, base=self.state.values)
            for w in d.warnings:
                self._log("warn", w)
            self.got_state = True
            self._log("in", f"дамп пресета «{d.name}»", raw)
            if self._capture_slot is not None:
                slot, self._capture_slot = self._capture_slot, None
                for cb in list(self.on_slot_captured):
                    cb(slot, d)
            self.state.replace(d.values, name=d.name, origin=Origin.DEVICE)
            for cb in list(self.on_device_dump):
                cb(d)
            return
        if isinstance(m, ParamChange):
            self._mark_alive(now)
            p = m.resolve(self.state.values)
            if p is None:
                self._log("warn", f"неизвестный адрес 0x{m.address:02X} = {m.value}", raw)
                return
            if self._is_echo(m.address, m.value, now):
                return
            self._log("in", f"{p.key} = {m.value} (ручка на комбике)", raw)
            self.state.set(p.key, p.from_raw(m.value), Origin.DEVICE)
            if p.is_type_selector or p.key == "amp.model":
                self._resync_at = now + self.RESYNC_DELAY
            return
        if isinstance(m, (DumpRequest, SystemCommand)):
            self._mark_alive(now)
            self._log("in", type(m).__name__, raw)
            return
        self._log("warn", f"нераспознанное сообщение: {m.reason}", raw)

    # ---- такт ------------------------------------------------------------------
    def tick(self, now: float | None = None) -> None:
        now = self.clock() if now is None else now
        if self.transport is None:
            if (self._next_reconnect is not None and now >= self._next_reconnect
                    and self.reconnect_factory is not None):
                self._next_reconnect = now + self.RECONNECT_PERIOD
                try:
                    transport = self.reconnect_factory()
                except TransportError as e:
                    self._set_status(LinkStatus.ERROR, f"Переподключение не удалось: {e}")
                    return
                self.attach(transport)
            return
        try:
            for raw in self.transport.poll():
                self.handle_incoming(raw, now)
        except TransportError as e:
            self._fail(e)
            return
        if self._resync_at is not None and now >= self._resync_at:
            self._resync_at = None
            self.request_state()
        if self.sender is not None:
            try:
                self.sender.pump(now)
            except UnsafeMessageError as e:
                self._log("error", f"SafetyGate: {e}")
            except TransportError as e:
                self._fail(e)
                return
        if self.status is LinkStatus.CONNECTED and self._last_rx is not None:
            if now - self._last_rx > self.HEARTBEAT_TIMEOUT:
                self._set_status(LinkStatus.NO_RESPONSE,
                                 "Комбик не отвечает — проверьте питание и USB-кабель")
        elif self.status is LinkStatus.CONNECTING and now - self._opened_at > self.CONNECT_TIMEOUT:
            self._set_status(LinkStatus.NO_RESPONSE,
                             "Порт открыт, но комбик не отвечает. Включите комбик "
                             "или выберите другой порт")
