"""Байтовые константы протокола THR10 (первое поколение).

Каждая константа помечена источником и статусом, подробности —
docs/PROTOCOL.md. Источники:

    S1  github.com/SysExTones/sysex_tones (THR/CONSTANTS.py, THR10/CONSTANTS.py)
    S2  gist.github.com/MathisRosenhauer/25921bf9f584fb64ca124dee5c287180 (thrpatch)
    S3  github.com/MathisRosenhauer/THR_Footswitch (send_patch, patches.h)
    S4  форум yamahamusicians.com, «A bit about sysex (restored)», перехват amidi
"""

from __future__ import annotations

from enum import Enum


class Status(str, Enum):
    """Статус подтверждённости команды/параметра."""

    CONFIRMED_MULTI = "confirmed_multi"  # несколько источников / реальные байты
    CONFIRMED = "confirmed"  # один источник, работавший на железе
    DERIVED = "derived"  # вывод; влияет только на отображение
    UNCONFIRMED = "unconfirmed"  # не отправляется на комбик

    @property
    def sendable(self) -> bool:
        return self in (Status.CONFIRMED, Status.CONFIRMED_MULTI)


SYSEX_START = 0xF0
SYSEX_END = 0xF7

# Производитель Yamaha + байт 7D. S1, S2, S3.
YAMAHA_ID = 0x43
THR_DEVICE_BYTE = 0x7D
THR_PREFIX = bytes([SYSEX_START, YAMAHA_ID, THR_DEVICE_BYTE])

# Байт «тип сообщения» после F0 43 7D.
TYPE_DUMP = 0x00  # S1, S2, S3 — CONFIRMED_MULTI
TYPE_PARAM = 0x10  # S1 — CONFIRMED
TYPE_REQUEST = 0x20  # S1 — CONFIRMED
TYPE_SYSTEM = 0x30  # S1 — UNCONFIRMED (не отправляется)
TYPE_HEARTBEAT = 0x60  # S1, S4 — CONFIRMED_MULTI

# Изменение параметра: F0 43 7D 10 41 30 01 AA VH VL F7. S1.
PARAM_PREFIX = THR_PREFIX + bytes([TYPE_PARAM, 0x41, 0x30, 0x01])
PARAM_MESSAGE_LENGTH = len(PARAM_PREFIX) + 3 + 1  # = 11

# "DTA1AllP" — метка блока «весь пресет». S1, S2, S3.
MAGIC_ALLP = b"DTA1AllP"
# Дамп: F0 43 7D 00 02 0C "DTA1AllP" 00 00 7F 7F <256> CS F7. S1, S2, S3.
DUMP_DATA_SIZE = 0x10C  # 268 = 12 + 256, S2
DUMP_HEADER = THR_PREFIX + bytes([TYPE_DUMP, DUMP_DATA_SIZE >> 7, DUMP_DATA_SIZE & 0x7F])
DUMP_MAGIC = MAGIC_ALLP + bytes([0x00, 0x00, 0x7F, 0x7F])
DUMP_PATCH_OFFSET = len(DUMP_HEADER) + len(DUMP_MAGIC)  # 18, S1 THR_DUMP_OFFSET
DUMP_MESSAGE_LENGTH = len(DUMP_HEADER) + DUMP_DATA_SIZE + 2  # 276, S1 THR_DUMP_SIZE

# Запрос текущего состояния: F0 43 7D 20 "DTA1AllP" F7. S1 — CONFIRMED.
REQUEST_CURRENT = THR_PREFIX + bytes([TYPE_REQUEST]) + MAGIC_ALLP + bytes([SYSEX_END])

# Heartbeat: F0 43 7D 60 44 54 41 MM F7. S1, S4.
HEARTBEAT_PREFIX = THR_PREFIX + bytes([TYPE_HEARTBEAT]) + b"DTA"
HEARTBEAT_LENGTH = len(HEARTBEAT_PREFIX) + 2

MODEL_CODES: dict[int, str] = {
    0x30: "THR5",
    0x31: "THR10",
    0x32: "THR10X",
    0x33: "THR10C",
    0x34: "THR5A",
}

# Системные команды (S1) — UNCONFIRMED, отправка заблокирована SafetyGate.
SYSTEM_PREFIX = THR_PREFIX + bytes([TYPE_SYSTEM, 0x41, 0x30])
SYSTEM_COMMANDS: dict[str, dict[bool, bytes]] = {
    "system.wide": {True: bytes([0x00, 0x00]), False: bytes([0x00, 0x01])},
    "system.lamp": {True: bytes([0x01, 0x00]), False: bytes([0x01, 0x01])},
}
SYSTEM_STATUS = Status.UNCONFIRMED

# Пресет: 256 байт. Имя — 64 байта с начала (S1), параметры — с 128 (S1, S3).
PATCH_SIZE = 256
PATCH_NAME_SIZE = 64
PATCH_PARAM_BASE = 128

# Включение блока: 00 = вкл, 7F = выкл. S1, S3.
SWITCH_ON_RAW = 0x00
SWITCH_OFF_RAW = 0x7F

# Файл библиотеки официального эдитора .YDL. S2, S3.
YDL_MAGIC = b"DTAB01d"
YDL_HEADER_SIZE = 13
YDL_RECORD_TRAILER = 5
YDL_RECORD_SIZE = PATCH_SIZE + YDL_RECORD_TRAILER  # 261
YDL_DEFAULT_COUNT = 100  # S3: «-n 100 (all patches)»

# Одиночный файл 265 байт (S1, detect_midi_dump) — DERIVED.
SINGLE_FILE_SIZE = 265
SINGLE_FILE_OFFSET = 9
SINGLE_FILE_MAGIC = b"DTA"
