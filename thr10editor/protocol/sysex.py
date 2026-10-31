"""Кодирование и декодирование SysEx THR10 + защитный фильтр отправки.

Модуль не зависит от UI и транспорта. Все сообщения — полные байты
от F0 до F7 включительно.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Union

from . import constants as C
from .params import PARAMS, SYSTEM_SETTINGS, Kind, ParamDef, ProtocolOverrides, resolve_address


class ProtocolError(ValueError):
    """Неверное или неизвестное сообщение."""


class UnsafeMessageError(ProtocolError):
    """Попытка отправить на комбик сообщение, не разрешённое SafetyGate."""


# --------------------------------------------------------------------------
# Вспомогательные функции
# --------------------------------------------------------------------------

def checksum(data: Iterable[int]) -> int:
    """Контрольная сумма Yamaha: (-Σ data) & 0x7F. S1, S2, S3."""
    return (-sum(data)) & 0x7F


def split14(value: int) -> tuple[int, int]:
    """14-битное значение → (VH, VL) по 7 бит."""
    if not 0 <= value <= 0x3FFF:
        raise ProtocolError(f"значение {value} не помещается в 14 бит")
    return (value >> 7) & 0x7F, value & 0x7F


def join14(hi: int, lo: int) -> int:
    return ((hi & 0x7F) << 7) | (lo & 0x7F)


def hexstr(data: bytes | Iterable[int]) -> str:
    return " ".join(f"{b:02X}" for b in bytes(data))


def split_sysex_stream(data: bytes | Iterable[int]) -> list[bytes]:
    """Выделить из потока байт отдельные SysEx-сообщения F0…F7.

    Незавершённые сообщения и байты вне SysEx отбрасываются;
    новое F0 внутри сообщения начинает новое сообщение.
    """
    out: list[bytes] = []
    buf: bytearray | None = None
    for b in bytes(data):
        if b == C.SYSEX_START:
            buf = bytearray([b])
        elif buf is not None:
            if b >= 0x80 and b != C.SYSEX_END:
                if b >= 0xF8:  # real-time байты могут вклиниваться — пропускаем
                    continue
                buf = None
                continue
            buf.append(b)
            if b == C.SYSEX_END:
                out.append(bytes(buf))
                buf = None
    return out


# --------------------------------------------------------------------------
# Сообщения
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class ParamChange:
    address: int
    value: int  # 14-битное сырое значение

    def resolve(self, values: Mapping[str, int]) -> ParamDef | None:
        return resolve_address(self.address, values)


@dataclass(frozen=True)
class PatchDump:
    patch: bytes  # 256 байт
    checksum_ok: bool


@dataclass(frozen=True)
class Heartbeat:
    model_code: int

    @property
    def model(self) -> str:
        return C.MODEL_CODES.get(self.model_code, f"неизвестная (0x{self.model_code:02X})")


@dataclass(frozen=True)
class DumpRequest:
    pass


@dataclass(frozen=True)
class SystemCommand:
    payload: bytes


@dataclass(frozen=True)
class Unknown:
    raw: bytes
    reason: str = ""


Message = Union[ParamChange, PatchDump, Heartbeat, DumpRequest, SystemCommand, Unknown]


def encode_param_change(address: int, value: int) -> bytes:
    """F0 43 7D 10 41 30 01 AA VH VL F7. Источник S1."""
    if not 0 <= address <= 0x7F:
        raise ProtocolError(f"адрес 0x{address:X} вне 0..7F")
    hi, lo = split14(value)
    return C.PARAM_PREFIX + bytes([address, hi, lo, C.SYSEX_END])


def encode_param(param: ParamDef | str, value: int) -> bytes:
    """Изменение параметра по его описанию (логическое значение)."""
    p = PARAMS[param] if isinstance(param, str) else param
    return encode_param_change(p.address, p.to_raw(value))


def encode_dump_request() -> bytes:
    """Запрос текущего состояния. Источник S1."""
    return C.REQUEST_CURRENT


def encode_patch_dump(patch: bytes) -> bytes:
    """Дамп пресета для отправки в текущее состояние комбика. S1, S2, S3.

    Последний байт пресета обнуляется (S2, S3).
    """
    if len(patch) != C.PATCH_SIZE:
        raise ProtocolError(f"пресет должен быть {C.PATCH_SIZE} байт, а не {len(patch)}")
    body = bytearray(patch)
    body[-1] = 0
    if any(b > 0x7F for b in body):
        raise ProtocolError("в пресете есть байты > 0x7F")
    data = C.DUMP_MAGIC + bytes(body)
    return C.DUMP_HEADER + data + bytes([checksum(data), C.SYSEX_END])


def encode_system(key: str, on: bool) -> bytes:
    """Системная команда lamp/wide. UNCONFIRMED: SafetyGate не пропустит без подтверждения."""
    return C.SYSTEM_PREFIX + C.SYSTEM_COMMANDS[key][bool(on)] + bytes([C.SYSEX_END])


def decode(msg: bytes) -> Message:
    """Разобрать одно SysEx-сообщение."""
    msg = bytes(msg)
    if len(msg) < 5 or msg[0] != C.SYSEX_START or msg[-1] != C.SYSEX_END:
        return Unknown(msg, "не SysEx")
    if not msg.startswith(C.THR_PREFIX):
        return Unknown(msg, "не THR (нет F0 43 7D)")
    kind = msg[3]
    if kind == C.TYPE_PARAM:
        if len(msg) == C.PARAM_MESSAGE_LENGTH and msg.startswith(C.PARAM_PREFIX):
            return ParamChange(msg[7], join14(msg[8], msg[9]))
        return Unknown(msg, "изменение параметра неизвестной длины")
    if kind == C.TYPE_DUMP:
        if len(msg) == C.DUMP_MESSAGE_LENGTH and msg.startswith(C.DUMP_HEADER):
            data = msg[len(C.DUMP_HEADER):-2]
            if data[: len(C.DUMP_MAGIC)] != C.DUMP_MAGIC:
                return Unknown(msg, "дамп с неизвестной меткой")
            ok = checksum(data) == msg[-2]
            return PatchDump(bytes(data[len(C.DUMP_MAGIC):]), ok)
        return Unknown(msg, "дамп неизвестной длины")
    if kind == C.TYPE_HEARTBEAT:
        if len(msg) == C.HEARTBEAT_LENGTH and msg.startswith(C.HEARTBEAT_PREFIX):
            return Heartbeat(msg[-2])
        return Unknown(msg, "heartbeat неизвестного формата")
    if kind == C.TYPE_REQUEST:
        if msg == C.REQUEST_CURRENT:
            return DumpRequest()
        return Unknown(msg, "запрос неизвестного формата")
    if kind == C.TYPE_SYSTEM:
        if msg.startswith(C.SYSTEM_PREFIX):
            return SystemCommand(msg[len(C.SYSTEM_PREFIX):-1])
        return Unknown(msg, "системное сообщение неизвестного формата")
    return Unknown(msg, f"неизвестный тип 0x{kind:02X}")


# --------------------------------------------------------------------------
# Защитный фильтр
# --------------------------------------------------------------------------

class SafetyGate:
    """Пропускает на комбик только разрешённые сообщения.

    Разрешено:
      * изменение параметра с известным адресом, подтверждённым статусом
        (или подтверждённым пользователем в protocol_overrides.json) и
        значением в диапазоне;
      * запрос текущего состояния;
      * дамп пресета правильной структуры с верной контрольной суммой;
      * системные команды — только если пользователь их подтвердил.

    Всё остальное (в т.ч. любые неизвестные типы, прошивка, сброс)
    отклоняется с UnsafeMessageError.
    """

    def __init__(self, overrides: ProtocolOverrides | None = None):
        self.overrides = overrides or ProtocolOverrides()

    def check(self, msg: bytes) -> Message:
        decoded = decode(msg)
        if isinstance(decoded, ParamChange):
            candidates = [p for p in PARAMS.values() if p.address == decoded.address]
            if not candidates:
                raise UnsafeMessageError(f"неизвестный адрес параметра 0x{decoded.address:02X}")
            allowed = [p for p in candidates if self.overrides.is_sendable_param(p)]
            if not allowed:
                raise UnsafeMessageError(
                    f"параметр 0x{decoded.address:02X} не подтверждён — отправка запрещена")
            if not any(_raw_in_range(p, decoded.value) for p in allowed):
                raise UnsafeMessageError(
                    f"значение {decoded.value} вне диапазона параметра 0x{decoded.address:02X}")
            return decoded
        if isinstance(decoded, DumpRequest):
            return decoded
        if isinstance(decoded, PatchDump):
            if not decoded.checksum_ok:
                raise UnsafeMessageError("дамп с неверной контрольной суммой")
            if decoded.patch[-1] != 0:
                raise UnsafeMessageError("последний байт пресета должен быть 0")
            return decoded
        if isinstance(decoded, SystemCommand):
            for key, variants in C.SYSTEM_COMMANDS.items():
                if decoded.payload in variants.values():
                    if self.overrides.is_sendable_system(SYSTEM_SETTINGS[key]):
                        return decoded
                    raise UnsafeMessageError(
                        f"{key}: команда не подтверждена — отправка запрещена")
            raise UnsafeMessageError("неизвестная системная команда")
        if isinstance(decoded, Heartbeat):
            raise UnsafeMessageError("heartbeat отправляет только комбик")
        raise UnsafeMessageError(f"неизвестное сообщение: {decoded.reason}")

    def is_allowed(self, msg: bytes) -> bool:
        try:
            self.check(msg)
        except UnsafeMessageError:
            return False
        return True


def _raw_in_range(p: ParamDef, raw: int) -> bool:
    if p.kind is Kind.SWITCH:
        return raw in (C.SWITCH_ON_RAW, C.SWITCH_OFF_RAW)
    return p.minimum <= raw <= p.maximum
