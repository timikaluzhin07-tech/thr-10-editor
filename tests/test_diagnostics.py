import os
import struct
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import parse_capture as pc  # noqa: E402
import thr_probe as probe  # noqa: E402

from thr10editor.protocol.params import default_values  # noqa: E402
from thr10editor.protocol.patch import encode_patch  # noqa: E402
from thr10editor.protocol.sysex import (  # noqa: E402
    encode_dump_request,
    encode_param,
    encode_patch_dump,
    encode_system,
)
from thr10editor.transport.demo import DemoAmp, DemoTransport  # noqa: E402


class FakeTime:
    def __init__(self):
        self.t = 0.0

    def clock(self):
        return self.t

    def sleep(self, dt):
        self.t += dt


def make(amp_cls=DemoAmp):
    ft = FakeTime()
    amp = amp_cls(clock=ft.clock)
    t = DemoTransport(amp=amp)
    t.open()
    return ft, amp, t


def run(t, ft, tmp_path, **kw):
    path = tmp_path / "probe.log"
    with open(path, "w", encoding="utf-8") as f:
        rc = probe.run_probe(t, probe.Log(f, echo=False), clock=ft.clock, sleep=ft.sleep, **kw)
    return rc, path.read_text(encoding="utf-8")


# ---- thr_probe ------------------------------------------------------------------

def test_probe_changes_and_restores_master(tmp_path):
    ft, amp, t = make()
    original = amp.values["amp.master"]
    rc, log = run(t, ft, tmp_path)
    assert rc == probe.EXIT_OK, log
    assert amp.values["amp.master"] == original
    assert "OK: комбик принял amp.master" in log
    assert "модель: THR10" in log
    sent = [m for m in amp.received]
    # только запросы состояния и изменения Master — больше ничего
    allowed = {encode_dump_request(), encode_param("amp.master", original),
               encode_param("amp.master", min(100, original + 5)),
               encode_param("amp.master", original - 5)}
    assert set(sent) <= allowed


def test_probe_no_change_mode(tmp_path):
    ft, amp, t = make()
    rc, log = run(t, ft, tmp_path, change=False)
    assert rc == probe.EXIT_OK
    assert all(m == encode_dump_request() for m in amp.received)
    assert "delay.time" in log  # полный список параметров в логе


def test_probe_no_response(tmp_path):
    ft, amp, t = make()
    amp.powered = False
    rc, log = run(t, ft, tmp_path)
    assert rc == probe.EXIT_NO_RESPONSE
    assert "не прислал дамп" in log


class StubbornAmp(DemoAmp):
    """Комбик, который игнорирует изменения параметров."""

    def receive(self, msg):
        if msg[3] == 0x10:
            self.received.append(msg)
            return
        super().receive(msg)


def test_probe_mismatch_still_restores(tmp_path):
    ft, amp, t = make(StubbornAmp)
    rc, log = run(t, ft, tmp_path)
    assert rc == probe.EXIT_MISMATCH
    assert "Возвращаю amp.master" in log


def test_probe_cli_demo(tmp_path):
    rc = probe.main(["--demo", "--no-change", "--log", str(tmp_path / "x.log")])
    assert rc == 0
    assert "Текущее состояние" in (tmp_path / "x.log").read_text(encoding="utf-8")


# ---- parse_capture: синтетический pcapng с USBPcap ------------------------------------

def usb_midi(msg: bytes, cable: int = 0) -> bytes:
    out = bytearray()
    i = 0
    while i < len(msg):
        chunk = msg[i:i + 3]
        rest = len(msg) - i
        if rest > 3 or (rest == 3 and chunk[-1] != 0xF7):
            cin = 0x4
        else:
            cin = {1: 0x5, 2: 0x6, 3: 0x7}[len(chunk)]
        out += bytes([(cable << 4) | cin]) + chunk + bytes(3 - len(chunk))
        i += 3
    return bytes(out)


def usbpcap(payload: bytes, endpoint: int, device: int = 5) -> bytes:
    hdr = struct.pack("<HQIHBHHBBI", 27, 1, 0, 9, 0 if endpoint < 0x80 else 1, 1, device,
                      endpoint, 3, len(payload))
    return hdr + payload


def pcapng(packets: list[tuple[float, bytes]]) -> bytes:
    def block(btype, body):
        pad = (-len(body)) % 4
        total = 12 + len(body) + pad
        return struct.pack("<II", btype, total) + body + b"\0" * pad + struct.pack("<I", total)

    out = block(0x0A0D0D0A, struct.pack("<IHHq", 0x1A2B3C4D, 1, 0, -1))
    out += block(0x1, struct.pack("<HHI", 249, 0, 65535))
    for t, pkt in packets:
        ts = int(t * 1e6)
        body = struct.pack("<IIIII", 0, ts >> 32, ts & 0xFFFFFFFF, len(pkt), len(pkt)) + pkt
        out += block(0x6, body)
    return out


def sample_messages():
    dump = encode_patch_dump(encode_patch("Cap", dict(default_values(), **{"delay.time": 5000})))
    return [
        (0.0, 0x02, encode_param("delay.time", 5000)),  # ПК → комбик (OUT)
        (0.1, 0x81, bytes.fromhex("F0437D60445441 31F7".replace(" ", ""))),  # heartbeat
        (0.2, 0x02, encode_dump_request()),
        (0.3, 0x81, dump),
        (0.4, 0x02, bytes.fromhex("F0437D7E0102F7")),  # неизвестная команда
        (0.5, 0x02, encode_system("system.lamp", False)),
    ]


def test_parse_pcapng_usb_midi(tmp_path):
    pkts = []
    for t, ep, msg in sample_messages():
        data = usb_midi(msg)
        # дамп разрезан на несколько USB-пакетов по 64 байта
        for i in range(0, len(data), 64):
            pkts.append((t + i * 1e-6, usbpcap(data[i:i + 64], ep)))
    path = tmp_path / "cap.pcapng"
    path.write_bytes(pcapng(pkts))
    msgs = pc.analyze(pc.load_messages(str(path)))
    kinds = [m.kind for m in msgs]
    assert kinds == ["param", "heartbeat", "request", "dump", "unknown", "system"]
    assert msgs[0].direction == pc.TO_DEVICE and msgs[3].direction == pc.FROM_DEVICE
    assert msgs[0].text.startswith("delay.time = 5000") and "500 мс" in msgs[0].text
    assert msgs[3].details["values"]["delay.time"] == 5000
    assert [m.known for m in msgs] == [True, True, True, True, False, False]


def test_parse_pcapng_raw_stream_fallback(tmp_path):
    pkts = [(t, usbpcap(msg, ep)) for t, ep, msg in sample_messages()]
    path = tmp_path / "raw.pcapng"
    path.write_bytes(pcapng(pkts))
    msgs = pc.analyze(pc.load_messages(str(path)))
    assert len(msgs) == 6


def test_parse_legacy_pcap(tmp_path):
    out = struct.pack("<IHHiIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 249)
    for t, ep, msg in sample_messages()[:2]:
        pkt = usbpcap(usb_midi(msg), ep)
        out += struct.pack("<IIII", int(t), int((t % 1) * 1e6), len(pkt), len(pkt)) + pkt
    path = tmp_path / "cap.pcap"
    path.write_bytes(out)
    assert [m.kind for m in pc.analyze(pc.load_messages(str(path)))] == ["param", "heartbeat"]


def test_parse_syx_and_text(tmp_path):
    syx = tmp_path / "a.syx"
    syx.write_bytes(encode_param("amp.gain", 7) + encode_dump_request())
    assert [m.kind for m in pc.analyze(pc.load_messages(str(syx)))] == ["param", "request"]
    txt = tmp_path / "a.txt"
    txt.write_text("12:00:01  F0 43 7D 10 41 30 01 02 00 05 F7\n")
    msgs = pc.analyze(pc.load_messages(str(txt)))
    assert msgs[0].text.startswith("amp.master = 5")


def test_parse_main_report(tmp_path, capsys):
    syx = tmp_path / "a.syx"
    syx.write_bytes(encode_param("amp.gain", 7) + bytes.fromhex("F0437D7E00F7"))
    out_json = tmp_path / "r.json"
    assert pc.main([str(syx), "--json", str(out_json)]) == 0
    text = capsys.readouterr().out
    assert "НЕИЗВЕСТНО" in text and "Неизвестных/неподтверждённых сообщений: 1" in text
    assert out_json.exists()


def test_parse_nothing_found(tmp_path):
    p = tmp_path / "empty.txt"
    p.write_text("hello")
    assert pc.main([str(p)]) == 2
