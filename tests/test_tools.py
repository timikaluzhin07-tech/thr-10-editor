import random

import pytest

from thr10editor.model.taper import from_position, to_position
from thr10editor.model.tools import (
    WAVEFORMS,
    ABCompare,
    Automation,
    Morph,
    RandomizerConfig,
    SetlistPlayer,
    TapTempo,
    delay_value_for,
    interpolate,
    randomize,
    wave,
)
from thr10editor.protocol.params import PARAMS, Kind, default_values
from thr10editor.transport.controller_input import Binding, ControlEvent, ControllerMapper


class Clock:
    def __init__(self, t=0.0):
        self.t = t

    def __call__(self):
        return self.t


def V(**kw):
    v = default_values()
    v.update({k.replace("__", "."): x for k, x in kw.items()})
    return v


# ---- taper ---------------------------------------------------------------------

def test_taper_roundtrip():
    for p in PARAMS.values():
        if p.kind is Kind.RANGE:
            for v in (p.minimum, p.default, p.maximum):
                assert from_position(p, to_position(p, v)) == v, p.key


# ---- A/B -----------------------------------------------------------------------

def test_ab_switch_and_copy():
    ab = ABCompare()
    a = V(amp__gain=10)
    b_first = ab.switch("A sound", a)
    assert ab.active == "B" and b_first.values == a  # B начинается с копии A
    b = V(amp__gain=90)
    back = ab.switch("B sound", b)
    assert ab.active == "A" and back.values["amp.gain"] == 10 and back.name == "A sound"
    again = ab.switch("A sound", back.values)
    assert again.values["amp.gain"] == 90
    ab.copy_to_other("B sound", again.values)
    assert ab.peek_other().values["amp.gain"] == 90


# ---- сет-лист ----------------------------------------------------------------------

def test_setlist_player():
    s = SetlistPlayer(["a", "b", "c"])
    assert s.current == "a"
    assert s.next() == "b" and s.next() == "c" and s.next() == "c"
    assert s.prev() == "b"
    assert s.goto(10) == "c" and s.goto(-5) == "a"
    assert s.peek(1) == "b" and s.peek(-1) is None
    w = SetlistPlayer(["a", "b"], wrap=True)
    w.next()
    assert w.next() == "a" and w.peek(-1) == "b"
    assert SetlistPlayer([]).next() is None


# ---- тап-темп ----------------------------------------------------------------------

def test_tap_tempo_120_bpm():
    c = Clock()
    t = TapTempo(clock=c)
    assert t.tap() is None
    for _ in range(4):
        c.t += 0.5
        ms = t.tap()
    assert ms == pytest.approx(500)
    assert t.bpm == pytest.approx(120)


def test_tap_tempo_resets_after_pause():
    c = Clock()
    t = TapTempo(clock=c, timeout=2.0)
    t.tap()
    c.t = 0.4
    t.tap()
    c.t = 5.0
    assert t.tap() is None and t.taps == 1


@pytest.mark.parametrize("sub,expected", [("1/4", 5000), ("1/8", 2500), ("1/8.", 3750),
                                          ("1/8T", 1667)])
def test_delay_value_for(sub, expected):
    # 500 мс четверть при единице 0,1 мс
    assert delay_value_for(500, sub) == (expected, False)


def test_delay_value_clamped():
    v, clamped = delay_value_for(2000, "1/4")  # 2 с > 999,9 мс
    assert v == 9999 and clamped


# ---- рандомайзер ---------------------------------------------------------------------

def _discrete_keys():
    return [k for k, p in PARAMS.items() if p.kind is not Kind.RANGE]


def test_randomize_default_lock_is_master_only():
    cfg = RandomizerConfig()
    assert cfg.locked == {"amp.master"}
    cur = V(amp__master=33)
    for seed in range(20):
        assert randomize(cur, cfg, random.Random(seed))["amp.master"] == 33


def test_randomize_changes_switches_and_choices():
    """Вкл/выкл блоков, модель, кабинет, типы эффектов и Ratio/Knee тоже меняются."""
    cfg = RandomizerConfig()
    rng = random.Random(0)
    seen: dict[str, set[int]] = {k: set() for k in _discrete_keys()}
    for _ in range(80):
        out = randomize(default_values(), cfg, rng)
        for k in seen:
            seen[k].add(out[k])
    for k, vals in seen.items():
        p = PARAMS[k]
        assert len(vals) == p.maximum - p.minimum + 1, (k, vals)  # встретились все варианты


def test_randomize_locks_work_for_switches_and_choices():
    locked = {"delay.on", "reverb.on", "amp.model", "mod.type", "amp.cab", "comp.rack.ratio"}
    cfg = RandomizerConfig(locked=locked)
    cur = V(delay__on=1, reverb__on=0, amp__model=4, mod__type=2, amp__cab=5,
            comp__rack__ratio=3)
    rng = random.Random(5)
    for _ in range(60):
        out = randomize(cur, cfg, rng)
        for k in locked:
            assert out[k] == cur[k], k
    # незаблокированные переключатели при этом меняются
    outs = [randomize(cur, cfg, random.Random(i)) for i in range(30)]
    assert {o["gate.on"] for o in outs} == {0, 1}
    assert len({o["comp.type"] for o in outs}) == 2


def test_randomize_amount_is_probability_for_discrete():
    cur = default_values()
    never = RandomizerConfig(locked=set(), amount=0.0)
    for i in range(20):
        out = randomize(cur, never, random.Random(i))
        for k in _discrete_keys():
            assert out[k] == cur[k]


def test_randomize_bounds_and_amount():
    cfg = RandomizerConfig(locked=set(), bounds={"amp.gain": (0.2, 0.4)})
    rng = random.Random(7)
    for _ in range(50):
        out = randomize(V(amp__gain=0), cfg, rng)
        assert 20 <= out["amp.gain"] <= 40
    small = RandomizerConfig(locked=set(), amount=0.1)
    out = randomize(V(amp__bass=50), small, random.Random(3))
    assert abs(out["amp.bass"] - 50) <= 6


def test_randomize_values_always_valid():
    cfg = RandomizerConfig(locked=set())
    rng = random.Random(42)
    for _ in range(100):
        out = randomize(default_values(), cfg, rng)
        for k, p in PARAMS.items():
            assert p.minimum <= out[k] <= p.maximum


# ---- морфинг ------------------------------------------------------------------------

def test_interpolate_endpoints_and_midpoint():
    a = V(amp__gain=0, amp__model=0, delay__on=0)
    b = V(amp__gain=100, amp__model=4, delay__on=1)
    assert interpolate(a, b, 0) == a
    assert interpolate(a, b, 1) == b
    mid = interpolate(a, b, 0.5)
    assert mid["amp.gain"] == 50
    assert mid["amp.model"] == 4 and mid["delay.on"] == 1  # дискретные — на середине
    q = interpolate(a, b, 0.25)
    assert q["amp.model"] == 0 and q["amp.gain"] == 25


def test_interpolate_log_param_in_position_space():
    a, b = V(delay__time=10), V(delay__time=1000)
    mid = interpolate(a, b, 0.5)["delay.time"]
    assert 95 <= mid <= 105  # геометрическое среднее ≈ 100, а не 505


def test_morph_progress_and_curve():
    c = Clock()
    m = Morph(V(amp__gain=0), V(amp__gain=100), 2.0, "linear", clock=c)
    c.t = 1.0
    vals, done = m.values()
    assert vals["amp.gain"] == 50 and not done
    c.t = 2.5
    vals, done = m.values()
    assert vals["amp.gain"] == 100 and done
    s = Morph(V(amp__gain=0), V(amp__gain=100), 2.0, "smooth", clock=Clock())
    assert s.values(0.5)[0]["amp.gain"] < 25  # smoothstep медленнее в начале


def test_monotonic_morph_steps():
    c = Clock()
    m = Morph(V(amp__treble=0), V(amp__treble=100), 1.0, "smooth", clock=c)
    last = -1
    for i in range(0, 101):
        c.t = i / 100
        v = m.values()[0]["amp.treble"]
        assert v >= last
        last = v


# ---- LFO -------------------------------------------------------------------------------

@pytest.mark.parametrize("shape", WAVEFORMS)
def test_wave_range(shape):
    for i in range(200):
        assert -1.0 <= wave(shape, i / 37.0, seed=5) <= 1.0


def test_wave_shapes():
    assert wave("sine", 0.25) == pytest.approx(1)
    assert wave("triangle", 0.0) == -1 and wave("triangle", 0.5) == 1
    assert wave("square", 0.1) == 1 and wave("square", 0.6) == -1
    assert wave("saw_up", 0.0) == -1 and wave("saw_down", 0.0) == 1
    assert wave("random", 3.1, 1) == wave("random", 3.9, 1)  # sample & hold
    with pytest.raises(ValueError):
        wave("nope", 0)


def test_automation_modulates_around_base_and_restores():
    c = Clock()
    auto = Automation(max_rate_hz=20, clock=c)
    auto.add("amp.master", waveform="sine", rate_hz=1.0, depth=0.4)
    auto.start(V(amp__master=50))
    c.t = 0.25
    assert auto.tick() == {"amp.master": 70}  # 50 + 0.5*0.4*100
    c.t = 0.75
    assert auto.tick() == {"amp.master": 30}
    assert auto.stop() == {"amp.master": 50}
    assert auto.tick() == {}


def test_automation_rate_limit():
    c = Clock()
    auto = Automation(max_rate_hz=10, clock=c)
    auto.add("amp.gain", waveform="saw_up", rate_hz=5.0, depth=1.0)
    auto.start(default_values())
    emitted = 0
    for i in range(1000):  # 1 секунда шагами по 1 мс
        c.t = i / 1000
        emitted += len(auto.tick())
    assert emitted <= 11


def test_automation_only_ranges_and_one_per_key():
    auto = Automation()
    with pytest.raises(ValueError):
        auto.add("amp.model")
    auto.add("amp.gain", depth=0.1)
    auto.add("amp.gain", depth=0.9)
    assert len(auto.lfos) == 1 and auto.lfos[0].depth == 0.9
    l = auto.add("amp.bass", rate_hz=100, depth=5)
    assert l.rate_hz == 5.0 and l.depth == 1.0  # ограничено


def test_automation_rebase():
    c = Clock()
    auto = Automation(clock=c)
    auto.add("amp.bass", waveform="square", rate_hz=1, depth=0.2)
    auto.start(V(amp__bass=50))
    auto.rebase("amp.bass", 80)
    c.t = 0.1
    assert auto.tick()["amp.bass"] == 90


# ---- MIDI-контроллер ----------------------------------------------------------------

def test_controller_learn_and_edges():
    m = ControllerMapper()
    m.learn("next")
    assert m.handle(ControlEvent("cc", 0, 64, 127))[0] == "learned"
    assert m.handle(ControlEvent("cc", 0, 64, 0)) is None  # отпускание
    assert m.handle(ControlEvent("cc", 0, 64, 127)) == ("next", None)
    assert m.handle(ControlEvent("cc", 0, 64, 127)) is None  # удержание — без повтора
    m.handle(ControlEvent("cc", 0, 64, 0))
    m.prev = Binding("note", None, 60)
    assert m.handle(ControlEvent("note", 3, 60, 100)) == ("prev", None)
    assert m.handle(ControlEvent("cc", 1, 64, 127)) is None  # другой канал


def test_controller_program_change_select():
    m = ControllerMapper(pc_selects=True)
    assert m.handle(ControlEvent("pc", 0, 4)) == ("goto", 4)
    b = Binding.from_dict(Binding("pc", 0, 9).to_dict())
    m.next = b
    assert m.handle(ControlEvent("pc", 0, 9)) == ("next", None)
    assert Binding.from_dict({"kind": "zzz"}) is None


def test_controller_learn_cancel_keeps_binding():
    m = ControllerMapper(next_binding=Binding("cc", 0, 10))
    m.learn("next")
    assert m.learning == "next"
    m.learn("next")  # повторное нажатие той же кнопки — отмена
    assert m.learning is None and m.next == Binding("cc", 0, 10)
    m.learn("prev")
    m.cancel_learn()  # Esc / клик мимо
    assert m.learning is None and m.prev is None
    # после отмены события не переназначают привязку
    assert m.handle(ControlEvent("cc", 0, 99, 127)) is None
    assert m.next == Binding("cc", 0, 10)
