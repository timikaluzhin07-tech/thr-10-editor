import pytest

from thr10editor.protocol import constants as C
from thr10editor.protocol.params import ProtocolOverrides
from thr10editor.protocol.sysex import (
    Heartbeat,
    ParamChange,
    PatchDump,
    UnsafeMessageError,
    decode,
    encode_dump_request,
    encode_param,
    encode_param_change,
    encode_system,
)
from thr10editor.transport import midi as midi_mod
from thr10editor.transport.base import TransportError
from thr10editor.transport.demo import DemoAmp, DemoTransport
from thr10editor.transport.midi import MidiTransport, PortPair, all_port_pairs, find_thr_ports
from thr10editor.transport.sender import RateLimitedSender


class Clock:
    def __init__(self, t=0.0):
        self.t = t

    def __call__(self):
        return self.t


# ---- RateLimitedSender ----------------------------------------------------------

def make_sender(clock, **kw):
    sent = []
    s = RateLimitedSender(sent.append, clock=clock, **kw)
    return s, sent


def test_sender_rate_limit_over_one_second():
    clock = Clock()
    s, sent = make_sender(clock, min_interval=0.02)
    for i in range(300):
        s.submit(f"k{i}", bytes([i & 0x7F]))
    while clock.t <= 1.0:
        s.pump()
        clock.t += 0.005
    assert 49 <= len(sent) <= 52


def test_sender_coalesces_same_key():
    clock = Clock()
    s, sent = make_sender(clock)
    for v in range(100):
        s.submit("gain", bytes([v]))
    assert s.pending == 1 and s.coalesced == 99
    s.pump()
    assert sent == [bytes([99])]


def test_sender_barrier_preserves_order():
    clock = Clock()
    s, sent = make_sender(clock)
    s.submit("a", b"a1")
    s.submit("type", b"t", barrier=True)
    s.submit("a", b"a2")
    s.submit("a", b"a3")
    assert s.pending_keys() == ["a", "type", "a"]
    s.flush()
    assert sent == [b"a1", b"t", b"a3"]


def test_sender_dump_replaces_queue_and_waits_after():
    clock = Clock()
    s, sent = make_sender(clock, min_interval=0.02)
    s.submit("a", b"a")
    s.submit("b", b"b")
    s.submit_dump(b"DUMP")
    s.submit("c", b"c")
    assert s.pump() == 1 and sent == [b"DUMP"]
    clock.t = 0.05
    assert s.pump() == 0
    clock.t = 0.061
    assert s.pump() == 1 and sent[-1] == b"c"


def test_sender_late_timer_bursts_at_most_two():
    clock = Clock()
    s, sent = make_sender(clock, min_interval=0.02)
    for i in range(10):
        s.submit(f"k{i}", b"x")
    s.pump()
    clock.t = 1.0
    assert s.pump() == 2


# ---- DemoAmp / DemoTransport ------------------------------------------------------

def test_demo_responds_to_request():
    amp = DemoAmp(clock=Clock())
    amp.receive(encode_dump_request())
    out = amp.take()
    assert len(out) == 1
    m = decode(out[0])
    assert isinstance(m, PatchDump) and m.checksum_ok


def test_demo_applies_param_and_knob_turn():
    amp = DemoAmp(clock=Clock())
    amp.receive(encode_param("amp.gain", 11))
    assert amp.values["amp.gain"] == 11
    amp.turn_knob("amp.treble", 99)
    m = decode(amp.take()[0])
    assert m == ParamChange(0x05, 99)


def test_demo_heartbeat_period():
    clock = Clock()
    t = DemoTransport(clock=clock)
    t.open()
    beats = 0
    while clock.t < 2.0:
        beats += sum(isinstance(decode(x), Heartbeat) for x in t.poll())
        clock.t += 0.05
    assert 4 <= beats <= 5


def test_demo_slots_and_power():
    amp = DemoAmp(clock=Clock())
    amp.press_slot(2)
    assert amp.name == "PRESET3"
    amp.take()
    amp.powered = False
    amp.tick()
    amp.receive(encode_dump_request())
    assert amp.take() == []  # выключенный комбик молчит


def test_demo_rejects_garbage():
    t = DemoTransport(clock=Clock())
    t.open()
    with pytest.raises(TransportError):
        t.send(b"\xf0\x43\x7d\x7e\xf7")
    t.close()
    with pytest.raises(TransportError):
        t.send(encode_dump_request())


def test_demo_system_commands():
    amp = DemoAmp(clock=Clock())
    amp.receive(encode_system("system.lamp", False))
    assert amp.system["system.lamp"] is False


# ---- MIDI ---------------------------------------------------------------------

def test_find_thr_ports():
    ins = ["Microsoft GS Wavetable 0", "THR10 1"]
    outs = ["Microsoft GS Wavetable Synth 0", "THR10 2"]
    assert find_thr_ports(ins, outs) == PortPair("THR10 1", "THR10 2")
    assert find_thr_ports(["Other"], ["Other"]) is None
    assert all_port_pairs(["A 0", "B 1"], ["B 3", "A 2"]) == [PortPair("A 0", "A 2"),
                                                             PortPair("B 1", "B 3")]


class FakePort:
    def __init__(self, name, incoming=None):
        self.name = name
        self.sent = []
        self.incoming = incoming or []
        self.closed = False

    def send(self, m):
        self.sent.append(m)

    def iter_pending(self):
        out, self.incoming = self.incoming, []
        return out

    def close(self):
        self.closed = True


class FakeMsg:
    def __init__(self, type_, data=()):
        self.type = type_
        self.data = list(data)


class FakeMido:
    def __init__(self):
        self.inp = FakePort("in", [FakeMsg("sysex", [0x43, 0x7D, 0x60, 0x44, 0x54, 0x41, 0x31]),
                                   FakeMsg("note_on")])
        self.out = FakePort("out")

    def open_input(self, name):
        return self.inp

    def open_output(self, name):
        return self.out

    def Message(self, type_, data):  # noqa: N802 — имитация API mido
        return FakeMsg(type_, data)


@pytest.fixture
def fake_mido(monkeypatch):
    fake = FakeMido()
    monkeypatch.setattr(midi_mod, "_mido", lambda: fake)
    return fake


def test_midi_send_through_gate(fake_mido):
    t = MidiTransport(PortPair("THR10", "THR10"))
    t.open()
    t.send(encode_param("amp.master", 40))
    assert fake_mido.out.sent[0].data == list(encode_param("amp.master", 40)[1:-1])
    with pytest.raises(UnsafeMessageError):
        t.send(encode_param_change(0x70, 1))
    with pytest.raises(UnsafeMessageError):
        t.send(encode_system("system.lamp", True))
    assert len(fake_mido.out.sent) == 1


def test_midi_overrides_allow_system(fake_mido):
    t = MidiTransport(PortPair("THR10", "THR10"), ProtocolOverrides({"system.wide"}))
    t.open()
    t.send(encode_system("system.wide", True))
    assert len(fake_mido.out.sent) == 1


def test_midi_poll_returns_full_sysex(fake_mido):
    t = MidiTransport(PortPair("THR10", "THR10"))
    t.open()
    msgs = t.poll()
    assert msgs == [C.HEARTBEAT_PREFIX + bytes([0x31, 0xF7])]
    t.close()
    assert fake_mido.inp.closed and fake_mido.out.closed and not t.is_open


def test_midi_send_when_closed():
    t = MidiTransport(PortPair("x", "x"))
    with pytest.raises(TransportError):
        t.send(encode_dump_request())
