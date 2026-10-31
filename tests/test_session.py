from dataclasses import replace

import pytest

from thr10editor.app.session import EditorSession, LinkStatus
from thr10editor.model.state import Origin
from thr10editor.protocol.constants import Status
from thr10editor.protocol.params import PARAMS, ProtocolOverrides
from thr10editor.protocol.sysex import (
    ParamChange,
    PatchDump,
    decode,
    encode_param,
    encode_param_change,
)
from thr10editor.transport.base import Transport, TransportError
from thr10editor.transport.demo import DemoTransport


class Clock:
    def __init__(self):
        self.t = 100.0

    def __call__(self):
        return self.t


def run(session, clock, seconds, step=0.005):
    end = clock.t + seconds
    while clock.t < end:
        session.tick()
        clock.t += step


@pytest.fixture
def demo():
    clock = Clock()
    transport = DemoTransport(clock=clock)
    session = EditorSession(clock=clock)
    assert session.attach(transport)
    run(session, clock, 0.2)
    return session, transport, clock


def test_connect_reads_state(demo):
    session, transport, clock = demo
    assert session.status is LinkStatus.CONNECTED
    assert session.device_model == "THR10"
    assert session.got_state
    assert session.state.name == "PRESET1"
    assert session.state["amp.gain"] == 37


def test_user_change_reaches_amp(demo):
    session, transport, clock = demo
    session.state.set("amp.gain", 64, Origin.USER)
    run(session, clock, 0.05)
    assert transport.amp.values["amp.gain"] == 64


def test_device_knob_updates_ui_without_echo(demo):
    session, transport, clock = demo
    transport.amp.received.clear()
    events = []
    session.state.subscribe(lambda ch, o: events.append(o))
    transport.amp.turn_knob("amp.bass", 12)
    run(session, clock, 0.05)
    assert session.state["amp.bass"] == 12
    assert Origin.DEVICE in events
    sent = [decode(m) for m in transport.amp.received]
    assert not any(isinstance(m, ParamChange) for m in sent)


def test_type_change_sends_type_then_params(demo):
    session, transport, clock = demo
    transport.amp.received.clear()
    session.state.set("mod.flanger.speed", 91, Origin.USER)  # неактивен — не отправляется
    run(session, clock, 0.1)
    assert transport.amp.received == []
    session.state.set("mod.type", 1, Origin.USER)
    run(session, clock, 0.3)
    msgs = [decode(m) for m in transport.amp.received]
    assert msgs[0] == ParamChange(0x20, 1)
    assert ParamChange(0x21, 91) in msgs
    assert transport.amp.values["mod.flanger.speed"] == 91


def test_load_sends_single_dump(demo):
    session, transport, clock = demo
    transport.amp.received.clear()
    values = dict(session.state.values, **{"amp.model": 4, "amp.gain": 1, "delay.on": 1})
    session.state.replace(values, name="Loaded", origin=Origin.LOAD)
    run(session, clock, 0.2)
    msgs = [decode(m) for m in transport.amp.received]
    assert len(msgs) == 1 and isinstance(msgs[0], PatchDump)
    assert transport.amp.name == "Loaded" and transport.amp.values["amp.model"] == 4


def test_fast_drag_is_coalesced(demo):
    session, transport, clock = demo
    transport.amp.received.clear()
    for v in range(0, 101):
        session.state.set("amp.master", v, Origin.USER)
    run(session, clock, 0.2)
    msgs = [decode(m) for m in transport.amp.received]
    assert msgs == [ParamChange(0x02, 100)]


def test_echo_is_ignored(demo):
    session, transport, clock = demo
    session.state.set("amp.gain", 30, Origin.USER)
    run(session, clock, 0.03)
    session.state.set("amp.gain", 40, Origin.USER)
    # комбик «эхом» вернул старое значение — модель не должна откатиться
    session.handle_incoming(encode_param("amp.gain", 30))
    assert session.state["amp.gain"] == 40
    # а реальный поворот ручки (другое значение) применяется
    session.handle_incoming(encode_param("amp.gain", 77))
    assert session.state["amp.gain"] == 77


def test_slot_capture(demo):
    session, transport, clock = demo
    captured = []
    session.on_slot_captured.append(lambda i, d: captured.append((i, d.name)))
    session.arm_slot_capture(2)
    transport.amp.press_slot(2)
    run(session, clock, 0.05)
    assert captured == [(2, "PRESET3")]
    assert session.state.name == "PRESET3"
    assert session.capture_slot is None


def test_device_type_change_triggers_resync(demo):
    session, transport, clock = demo
    transport.amp.received.clear()
    transport.amp.turn_knob("reverb.type", 3)
    run(session, clock, 0.5)
    kinds = [type(decode(m)).__name__ for m in transport.amp.received]
    assert kinds == ["DumpRequest"]
    assert session.state["reverb.type"] == 3


def test_no_response_and_recovery(demo):
    session, transport, clock = demo
    transport.amp.powered = False
    run(session, clock, 3.0, step=0.05)
    assert session.status is LinkStatus.NO_RESPONSE
    transport.amp.powered = True
    run(session, clock, 0.6, step=0.05)
    assert session.status is LinkStatus.CONNECTED


def test_bad_checksum_dump_ignored(demo):
    session, transport, clock = demo
    raw = bytearray(transport.amp.current_dump())
    raw[-2] ^= 1
    before = session.state.values
    session.handle_incoming(bytes(raw))
    assert session.state.values == before
    assert any(e.direction == "error" for e in session.log)


# ---- строгий транспорт (как реальный MIDI) ------------------------------------

class StrictTransport(Transport):
    kind = "midi"
    accepts_unconfirmed = False

    def __init__(self, fail_send=False):
        self.sent = []
        self._open = False
        self.fail_send = fail_send

    @property
    def name(self):
        return "Strict"

    @property
    def is_open(self):
        return self._open

    def open(self):
        self._open = True

    def close(self):
        self._open = False

    def send(self, msg):
        if self.fail_send:
            raise TransportError("кабель выдернут")
        self.sent.append(msg)

    def poll(self):
        return []


def test_unconfirmed_param_not_sent(monkeypatch):
    monkeypatch.setitem(PARAMS, "amp.gain",
                        replace(PARAMS["amp.gain"], status=Status.UNCONFIRMED))
    clock = Clock()
    session = EditorSession(clock=clock)
    t = StrictTransport()
    session.attach(t)
    run(session, clock, 0.05)
    t.sent.clear()
    session.state.set("amp.gain", 5, Origin.USER)
    session.state.set("amp.bass", 5, Origin.USER)
    run(session, clock, 0.1)
    msgs = [decode(m) for m in t.sent]
    assert msgs == [ParamChange(0x03, 5)]
    assert "amp.gain" in session.local_only
    # дамп при неподтверждённом параметре заменяется отдельными сообщениями без него
    t.sent.clear()
    session.push_full_state()
    session.sender.flush()
    addresses = {decode(m).address for m in t.sent}
    assert 0x01 not in addresses and 0x03 in addresses


def test_unconfirmed_param_sent_after_override(monkeypatch):
    monkeypatch.setitem(PARAMS, "amp.gain",
                        replace(PARAMS["amp.gain"], status=Status.UNCONFIRMED))
    clock = Clock()
    session = EditorSession(clock=clock, overrides=ProtocolOverrides({"amp.gain"}))
    t = StrictTransport()
    session.attach(t)
    session.state.set("amp.gain", 5, Origin.USER)
    session.sender.flush()
    assert encode_param_change(0x01, 5) in t.sent


def test_system_settings_blocked_on_real_transport():
    clock = Clock()
    session = EditorSession(clock=clock)
    t = StrictTransport()
    session.attach(t)
    assert session.set_system("system.lamp", False) is False
    assert session.system["system.lamp"] is False
    session2 = EditorSession(clock=clock, overrides=ProtocolOverrides({"system.lamp"}))
    session2.attach(StrictTransport())
    assert session2.set_system("system.lamp", False) is True


def test_transport_error_and_reconnect():
    clock = Clock()
    session = EditorSession(clock=clock)
    session.reconnect_factory = lambda: StrictTransport()
    session.attach(StrictTransport(fail_send=True))
    session.tick()  # запрос состояния → ошибка отправки
    assert session.status is LinkStatus.ERROR
    assert session.transport is None
    clock.t += 3.1
    session.tick()
    assert session.transport is not None
    assert session.status is LinkStatus.CONNECTING


def test_attach_failure_reports_error():
    class Broken(StrictTransport):
        def open(self):
            raise TransportError("порт занят")

    session = EditorSession(clock=Clock())
    assert session.attach(Broken()) is False
    assert session.status is LinkStatus.ERROR and "порт занят" in session.status_text


def test_offline_changes_are_local():
    session = EditorSession(clock=Clock())
    session.state.set("amp.gain", 1, Origin.USER)
    session.tick()
    assert session.status is LinkStatus.OFFLINE
