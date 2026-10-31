#!/usr/bin/env python3
"""Разбор перехвата трафика между официальным THR Editor и комбиком.

Понимает:
  * .pcapng / .pcap из Wireshark + USBPcap (тип канала USBPcap, 249);
  * .syx — сырые SysEx-сообщения;
  * текстовые hex-дампы (например, скопированные из журнала MIDI-монитора).

Из USB-пакетов собираются SysEx-сообщения (формат USB-MIDI: 4-байтовые
пакеты с кодом CIN; если он не подходит — поиск F0…F7 в «сыром» потоке),
затем каждое расшифровывается слоем протокола редактора. Всё, что редактор
не знает, помечается «НЕИЗВЕСТНО» — это то, что нужно прислать разработчику.

Примеры:
    python tools/parse_capture.py capture.pcapng
    python tools/parse_capture.py capture.pcapng --only-unknown
    python tools/parse_capture.py capture.pcapng --json report.json
    python tools/parse_capture.py dump.syx
"""

from __future__ import annotations

import argparse
import json
import os
import re
import struct
import sys
from dataclasses import asdict, dataclass, field
from typing import Iterator

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from thr10editor.protocol import constants as C  # noqa: E402
from thr10editor.protocol.params import default_values  # noqa: E402
from thr10editor.protocol.patch import decode_patch  # noqa: E402
from thr10editor.protocol.sysex import (  # noqa: E402
    DumpRequest,
    Heartbeat,
    ParamChange,
    PatchDump,
    SystemCommand,
    decode,
    hexstr,
    split_sysex_stream,
)

LINKTYPE_USBPCAP = 249


def _safe_console() -> None:
    """Не падать на кириллице, если консоль/конвейер в однобайтной кодировке."""
    for stream in (sys.stdout, sys.stderr):
        if stream is not None and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(errors="replace")
            except (ValueError, OSError):
                pass


_safe_console()
USBPCAP_HEADER = struct.Struct("<HQIHBHHBBI")  # 27 байт

TO_DEVICE = "ПК → комбик"
FROM_DEVICE = "комбик → ПК"


@dataclass
class UsbPacket:
    time: float
    bus: int
    device: int
    endpoint: int
    transfer: int
    data: bytes

    @property
    def direction(self) -> str:
        return FROM_DEVICE if self.endpoint & 0x80 else TO_DEVICE


@dataclass
class Message:
    time: float
    direction: str
    raw: bytes
    kind: str = ""
    text: str = ""
    known: bool = True
    details: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# pcap / pcapng
# ---------------------------------------------------------------------------

def _iter_pcapng(data: bytes) -> Iterator[tuple[int, float, bytes]]:
    """(тип канала, время, пакет) из pcapng."""
    pos = 0
    endian = "<"
    links: list[tuple[int, float]] = []  # (linktype, делитель времени)
    while pos + 12 <= len(data):
        btype = struct.unpack_from(endian + "I", data, pos)[0]
        if btype == 0x0A0D0D0A:  # Section Header Block
            bom = data[pos + 8: pos + 12]
            endian = "<" if bom == b"\x4d\x3c\x2b\x1a" else ">"
            links = []
        blen = struct.unpack_from(endian + "I", data, pos + 4)[0]
        if blen < 12 or pos + blen > len(data):
            break
        body = data[pos + 8: pos + blen - 4]
        if btype == 0x00000001:  # Interface Description Block
            linktype = struct.unpack_from(endian + "H", body, 0)[0]
            resol = 1e6
            opos = 8
            while opos + 4 <= len(body):
                code, olen = struct.unpack_from(endian + "HH", body, opos)
                if code == 0:
                    break
                if code == 9 and olen >= 1:  # if_tsresol
                    v = body[opos + 4]
                    resol = 2 ** (v & 0x7F) if v & 0x80 else 10 ** v
                opos += 4 + ((olen + 3) & ~3)
            links.append((linktype, resol))
        elif btype == 0x00000006:  # Enhanced Packet Block
            iface, ts_hi, ts_lo, caplen = struct.unpack_from(endian + "IIII", body, 0)
            pkt = body[20: 20 + caplen]
            lt, resol = links[iface] if iface < len(links) else (0, 1e6)
            yield lt, ((ts_hi << 32) | ts_lo) / resol, pkt
        elif btype == 0x00000003:  # Simple Packet Block
            lt, _ = links[0] if links else (0, 1e6)
            yield lt, 0.0, body[4:]
        pos += blen


def _iter_pcap(data: bytes) -> Iterator[tuple[int, float, bytes]]:
    magic = data[:4]
    if magic in (b"\xd4\xc3\xb2\xa1", b"\x4d\x3c\xb2\xa1"):
        e = "<"
    else:
        e = ">"
    nano = magic in (b"\x4d\x3c\xb2\xa1", b"\xa1\xb2\x3c\x4d")
    linktype = struct.unpack_from(e + "I", data, 20)[0]
    pos = 24
    while pos + 16 <= len(data):
        sec, frac, incl, _orig = struct.unpack_from(e + "IIII", data, pos)
        pos += 16
        yield linktype, sec + frac / (1e9 if nano else 1e6), data[pos: pos + incl]
        pos += incl


def read_usb_packets(data: bytes) -> list[UsbPacket]:
    if data[:4] == b"\x0a\x0d\x0d\x0a":
        frames = _iter_pcapng(data)
    elif data[:4] in (b"\xd4\xc3\xb2\xa1", b"\xa1\xb2\xc3\xd4", b"\x4d\x3c\xb2\xa1", b"\xa1\xb2\x3c\x4d"):
        frames = _iter_pcap(data)
    else:
        raise ValueError("это не pcap/pcapng")
    out = []
    for linktype, t, pkt in frames:
        if linktype != LINKTYPE_USBPCAP or len(pkt) < USBPCAP_HEADER.size:
            continue
        hlen, _irp, _status, _func, _info, bus, dev, ep, transfer, dlen = USBPCAP_HEADER.unpack_from(pkt, 0)
        payload = pkt[hlen: hlen + dlen]
        if payload:
            out.append(UsbPacket(t, bus, dev, ep, transfer, bytes(payload)))
    return out


# ---------------------------------------------------------------------------
# USB-MIDI → SysEx
# ---------------------------------------------------------------------------

CIN_SIZES = {0x2: 2, 0x3: 3, 0x4: 3, 0x5: 1, 0x6: 2, 0x7: 3, 0x8: 3, 0x9: 3, 0xA: 3,
             0xB: 3, 0xC: 2, 0xD: 2, 0xE: 3, 0xF: 1}


def usb_midi_bytes(payload: bytes) -> bytes | None:
    """Распаковать 4-байтовые пакеты USB-MIDI в поток MIDI-байт; None, если не похоже."""
    if len(payload) % 4:
        return None
    out = bytearray()
    for i in range(0, len(payload), 4):
        cin = payload[i] & 0x0F
        if payload[i] == 0 and not any(payload[i + 1: i + 4]):
            continue  # заполнение
        size = CIN_SIZES.get(cin)
        if size is None:
            return None
        out += payload[i + 1: i + 1 + size]
    return bytes(out)


def extract_sysex(packets: list[UsbPacket]) -> list[tuple[float, str, bytes]]:
    """Собрать SysEx по направлениям/устройствам."""
    streams: dict[tuple, list[tuple[float, bytes]]] = {}
    for p in packets:
        if p.transfer not in (1, 3):  # interrupt / bulk
            continue
        key = (p.bus, p.device, p.endpoint)
        streams.setdefault(key, []).append((p.time, p.data))
    result: list[tuple[float, str, bytes]] = []
    for (bus, dev, ep), items in streams.items():
        direction = FROM_DEVICE if ep & 0x80 else TO_DEVICE
        for mode in ("usbmidi", "raw"):
            buf = bytearray()
            msgs: list[tuple[float, bytes]] = []
            start_t = None
            ok = True
            for t, data in items:
                chunk = usb_midi_bytes(data) if mode == "usbmidi" else data
                if chunk is None:
                    ok = False
                    break
                for b in chunk:
                    if b == C.SYSEX_START:
                        buf = bytearray([b])
                        start_t = t
                    elif buf:
                        if b >= 0xF8:
                            continue
                        if b >= 0x80 and b != C.SYSEX_END:
                            buf = bytearray()
                            continue
                        buf.append(b)
                        if b == C.SYSEX_END:
                            msgs.append((start_t or t, bytes(buf)))
                            buf = bytearray()
            if ok and any(m.startswith(C.THR_PREFIX) for _, m in msgs):
                result += [(t, direction, m) for t, m in msgs]
                break
    result.sort(key=lambda x: x[0])
    return result


# ---------------------------------------------------------------------------
# Расшифровка
# ---------------------------------------------------------------------------

def analyze(messages: list[tuple[float, str, bytes]]) -> list[Message]:
    values = default_values()
    out: list[Message] = []
    for t, direction, raw in messages:
        m = decode(raw)
        msg = Message(t, direction, raw)
        if isinstance(m, ParamChange):
            p = m.resolve(values)
            msg.kind = "param"
            if p is None:
                msg.known = False
                msg.text = f"изменение параметра: НЕИЗВЕСТНЫЙ адрес 0x{m.address:02X} = {m.value}"
            else:
                values[p.key] = p.from_raw(m.value)
                msg.text = f"{p.key} = {m.value}  →  {p.format(values[p.key])}"
                msg.details = {"key": p.key, "address": m.address, "raw": m.value}
        elif isinstance(m, PatchDump):
            d = decode_patch(m.patch, base=values)
            values = d.values
            msg.kind = "dump"
            msg.text = f"дамп пресета «{d.name}» (сумма {'OK' if m.checksum_ok else 'НЕВЕРНА'})"
            msg.details = {"name": d.name, "values": d.values, "warnings": d.warnings}
        elif isinstance(m, Heartbeat):
            msg.kind = "heartbeat"
            msg.text = f"heartbeat {m.model}"
        elif isinstance(m, DumpRequest):
            msg.kind = "request"
            msg.text = "запрос текущего состояния"
        elif isinstance(m, SystemCommand):
            msg.kind = "system"
            msg.text = f"системная команда {hexstr(m.payload)} (lamp/wide по S1?)"
            msg.known = False  # не подтверждена — важно увидеть
        else:
            msg.kind = "unknown"
            msg.known = False
            msg.text = f"НЕИЗВЕСТНО: {m.reason}"
        out.append(msg)
    return out


def load_messages(path: str) -> list[tuple[float, str, bytes]]:
    with open(path, "rb") as f:
        data = f.read()
    if data[:4] in (b"\x0a\x0d\x0d\x0a", b"\xd4\xc3\xb2\xa1", b"\xa1\xb2\xc3\xd4",
                    b"\x4d\x3c\xb2\xa1", b"\xa1\xb2\x3c\x4d"):
        return extract_sysex(read_usb_packets(data))
    if C.SYSEX_START in data[:1] or data.startswith(C.THR_PREFIX):
        return [(0.0, "?", m) for m in split_sysex_stream(data)]
    text = data.decode("utf-8", errors="ignore")
    nums = bytes(int(x, 16) for x in re.findall(r"\b[0-9A-Fa-f]{2}\b", text))
    return [(0.0, "?", m) for m in split_sysex_stream(nums)]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", help=".pcapng / .pcap / .syx / текстовый hex-дамп")
    ap.add_argument("--only-unknown", action="store_true", help="показать только неизвестное")
    ap.add_argument("--no-heartbeat", action="store_true", help="скрыть heartbeat")
    ap.add_argument("--json", default="", help="сохранить отчёт в JSON")
    args = ap.parse_args(argv)

    try:
        raw_msgs = load_messages(args.file)
    except (OSError, ValueError) as e:
        print(f"Ошибка: {e}")
        return 1
    msgs = analyze(raw_msgs)
    if not msgs:
        print("SysEx THR не найден. Проверьте, что перехват шёл на том USB-хабе, где комбик,"
              " и что в это время официальный эдитор менял параметры.")
        return 2
    t0 = msgs[0].time
    for m in msgs:
        if args.only_unknown and m.known:
            continue
        if args.no_heartbeat and m.kind == "heartbeat":
            continue
        flag = "  " if m.known else "!!"
        print(f"{flag} {m.time - t0:9.3f}  {m.direction:12s}  {m.text}")
        if not m.known or m.kind not in ("heartbeat", "dump"):
            print(f"{'':27s}{hexstr(m.raw)}")
    kinds: dict[str, int] = {}
    for m in msgs:
        kinds[m.kind] = kinds.get(m.kind, 0) + 1
    unknown = [m for m in msgs if not m.known]
    print()
    print("Итог: " + ", ".join(f"{k}: {v}" for k, v in sorted(kinds.items())))
    seen_params = sorted({m.details["key"] for m in msgs if m.kind == "param" and m.details})
    if seen_params:
        print("Параметры, которые менялись: " + ", ".join(seen_params))
    print(f"Неизвестных/неподтверждённых сообщений: {len(unknown)}"
          + (" — пришлите этот отчёт разработчику" if unknown else ""))
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump([{**asdict(m), "raw": hexstr(m.raw)} for m in msgs], f, ensure_ascii=False, indent=1)
        print(f"JSON: {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
