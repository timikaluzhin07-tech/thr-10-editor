import pytest

from thr10editor.protocol import constants as C
from thr10editor.protocol.params import PARAMS, ProtocolOverrides
from thr10editor.protocol.sysex import (
    DumpRequest,
    Heartbeat,
    ParamChange,
    PatchDump,
    ProtocolError,
    SafetyGate,
    SystemCommand,
    Unknown,
    UnsafeMessageError,
    checksum,
    decode,
    encode_dump_request,
    encode_param,
    encode_param_change,
    encode_patch_dump,
    encode_system,
    join14,
    split14,
    split_sysex_stream,
)


def h(s: str) -> bytes:
    return bytes.fromhex(s)


# ---- байты из источников ------------------------------------------------------

def test_param_change_bytes_gain_50():
    # S1: THR_COMMAND_PREFIX + [0x01, 0x00] + [50] + F7
    assert encode_param("amp.gain", 50) == h("F0 43 7D 10 41 30 01 01 00 32 F7")


def test_param_change_bytes_14bit_delay_time():
    # 5000 = 39*128 + 8 → 27 08
    assert encode_param("delay.time", 5000) == h("F0 43 7D 10 41 30 01 31 27 08 F7")


def test_switch_encoding_on_is_00_off_is_7f():
    assert encode_param("comp.on", 1) == h("F0 43 7D 10 41 30 01 1F 00 00 F7")
    assert encode_param("comp.on", 0) == h("F0 43 7D 10 41 30 01 1F 00 7F F7")
    assert encode_param("gate.on", 0) == h("F0 43 7D 10 41 30 01 5F 00 7F F7")


def test_type_selector_bytes():
    assert encode_param("reverb.type", 3) == h("F0 43 7D 10 41 30 01 40 00 03 F7")
    assert encode_param("amp.model", 7) == h("F0 43 7D 10 41 30 01 00 00 07 F7")


def test_request_bytes():
    assert encode_dump_request() == h("F0 43 7D 20 44 54 41 31 41 6C 6C 50 F7")


def test_dump_header_matches_s3_prefix():
    prefix_s3 = h("F0 43 7D 00 02 0C 44 54 41 31 41 6C 6C 50 00 00 7F 7F")
    msg = encode_patch_dump(bytes(256))
    assert msg[:18] == prefix_s3
    assert len(msg) == 276
    assert msg[-1] == 0xF7


def test_checksum_matches_s3_running_sum():
    # S3: cs начинается с 0x71 (сумма префикса), итог (~cs + 1) & 0x7F
    data = C.DUMP_MAGIC + bytes(256)
    assert sum(C.DUMP_MAGIC) & 0xFF == 0x71
    assert checksum(data) == (~0x71 + 1) & 0x7F


def test_dump_zeroes_last_patch_byte():
    patch = bytearray(256)
    patch[255] = 0x33
    msg = encode_patch_dump(bytes(patch))
    decoded = decode(msg)
    assert isinstance(decoded, PatchDump)
    assert decoded.checksum_ok
    assert decoded.patch[255] == 0


def test_dump_roundtrip():
    patch = bytes((i * 7) & 0x7F for i in range(255)) + b"\x00"
    decoded = decode(encode_patch_dump(patch))
    assert isinstance(decoded, PatchDump)
    assert decoded.patch == patch and decoded.checksum_ok


def test_dump_bad_checksum_detected():
    msg = bytearray(encode_patch_dump(bytes(256)))
    msg[-2] ^= 0x01
    decoded = decode(bytes(msg))
    assert isinstance(decoded, PatchDump) and not decoded.checksum_ok


def test_dump_rejects_wrong_size_and_high_bytes():
    with pytest.raises(ProtocolError):
        encode_patch_dump(bytes(255))
    with pytest.raises(ProtocolError):
        encode_patch_dump(bytes([0x80]) + bytes(255))


def test_heartbeat_s4_capture():
    m = decode(h("F0 43 7D 60 44 54 41 31 F7"))
    assert isinstance(m, Heartbeat)
    assert m.model == "THR10"


@pytest.mark.parametrize("code,name", [(0x30, "THR5"), (0x32, "THR10X"), (0x33, "THR10C"),
                                       (0x34, "THR5A")])
def test_heartbeat_models(code, name):
    m = decode(h("F0 43 7D 60 44 54 41") + bytes([code, 0xF7]))
    assert isinstance(m, Heartbeat) and m.model == name


def test_system_command_bytes_from_s1():
    assert encode_system("system.wide", True) == h("F0 43 7D 30 41 30 00 00 F7")
    assert encode_system("system.wide", False) == h("F0 43 7D 30 41 30 00 01 F7")
    assert encode_system("system.lamp", True) == h("F0 43 7D 30 41 30 01 00 F7")
    assert encode_system("system.lamp", False) == h("F0 43 7D 30 41 30 01 01 F7")
    assert isinstance(decode(encode_system("system.lamp", True)), SystemCommand)


# ---- кодек ---------------------------------------------------------------------

@pytest.mark.parametrize("value", [0, 1, 127, 128, 1000, 9999, 16001, 0x3FFF])
def test_split_join_14(value):
    hi, lo = split14(value)
    assert hi <= 0x7F and lo <= 0x7F
    assert join14(hi, lo) == value


def test_split14_out_of_range():
    with pytest.raises(ProtocolError):
        split14(0x4000)
    with pytest.raises(ProtocolError):
        split14(-1)


def test_param_change_bad_address():
    with pytest.raises(ProtocolError):
        encode_param_change(0x80, 1)


def test_decode_param_change():
    m = decode(h("F0 43 7D 10 41 30 01 47 07 68 F7"))
    assert m == ParamChange(0x47, 1000)
    assert m.resolve({"reverb.type": 0}).key == "reverb.highcut"
    assert m.resolve({"reverb.type": 3}) is None


def test_decode_request_and_unknowns():
    assert isinstance(decode(encode_dump_request()), DumpRequest)
    assert isinstance(decode(h("F0 41 10 42 12 F7")), Unknown)  # чужой производитель
    assert isinstance(decode(h("F0 43 7D 10 41 30 01 01 00 F7")), Unknown)  # короткое
    assert isinstance(decode(h("F0 43 7D 7E 00 F7")), Unknown)  # неизвестный тип
    assert isinstance(decode(h("90 40 7F")), Unknown)  # не SysEx


def test_split_stream():
    a = encode_param("amp.gain", 10)
    b = encode_dump_request()
    stream = b"\x90\x40\x7f" + a[:5] + b"\xf8" + a[5:] + b"\xf0\x43" + b + b"\x01"
    assert split_sysex_stream(stream) == [a, b]


def test_split_stream_aborts_on_status_byte():
    assert split_sysex_stream(b"\xf0\x43\x7d\x90\x01\xf7") == []


# ---- SafetyGate -----------------------------------------------------------------

@pytest.fixture
def gate():
    return SafetyGate()


def test_gate_allows_confirmed_param(gate):
    for p in PARAMS.values():
        gate.check(encode_param(p, p.default))
        gate.check(encode_param(p, p.maximum))


def test_gate_allows_request_and_dump(gate):
    gate.check(encode_dump_request())
    gate.check(encode_patch_dump(bytes(256)))


def test_gate_rejects_unknown_address(gate):
    with pytest.raises(UnsafeMessageError):
        gate.check(encode_param_change(0x70, 1))


def test_gate_rejects_out_of_range(gate):
    with pytest.raises(UnsafeMessageError):
        gate.check(encode_param_change(0x01, 101))  # Gain > 100
    with pytest.raises(UnsafeMessageError):
        gate.check(encode_param_change(0x1F, 0x05))  # вкл/выкл: только 00/7F


def test_gate_rejects_unknown_types(gate):
    for kind in (0x01, 0x40, 0x50, 0x70, 0x7F):
        with pytest.raises(UnsafeMessageError):
            gate.check(bytes([0xF0, 0x43, 0x7D, kind, 0x00, 0xF7]))
    with pytest.raises(UnsafeMessageError):
        gate.check(h("F0 7E 7F 06 01 F7"))  # универсальный запрос — не наш
    with pytest.raises(UnsafeMessageError):
        gate.check(h("F0 43 7D 60 44 54 41 31 F7"))  # heartbeat шлёт только комбик


def test_gate_rejects_bad_dump(gate):
    msg = bytearray(encode_patch_dump(bytes(256)))
    msg[-2] ^= 1
    with pytest.raises(UnsafeMessageError):
        gate.check(bytes(msg))


def test_gate_blocks_unconfirmed_system_until_override():
    msg = encode_system("system.lamp", False)
    assert not SafetyGate().is_allowed(msg)
    assert SafetyGate(ProtocolOverrides({"system.lamp"})).is_allowed(msg)
    # подтверждение lamp не открывает wide
    assert not SafetyGate(ProtocolOverrides({"system.lamp"})).is_allowed(
        encode_system("system.wide", True))
