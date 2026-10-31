import itertools

import pytest

from thr10editor.protocol import constants as C
from thr10editor.protocol.params import (
    GROUPS,
    PARAMS,
    TYPE_KEYS,
    Kind,
    ProtocolOverrides,
    default_values,
    keys_affected_by_type,
    normalize_values,
    resolve_address,
)


def test_addresses_and_defaults_valid():
    for p in PARAMS.values():
        assert 0 <= p.address <= 0x7F
        assert p.minimum <= p.default <= p.maximum, p.key
        assert p.maximum <= 0x3FFF
        if p.width == 1 and p.kind is Kind.RANGE:
            assert p.maximum <= 0x7F, p.key
        assert C.PATCH_PARAM_BASE + p.address + p.width <= C.PATCH_SIZE - 1


@pytest.mark.parametrize("comp,mod,rev", list(itertools.product(range(2), range(4), range(4))))
def test_no_overlap_for_any_type_combination(comp, mod, rev):
    vals = dict(default_values(), **{"comp.type": comp, "mod.type": mod, "reverb.type": rev})
    used: dict[int, str] = {}
    for p in PARAMS.values():
        if not p.is_active(vals):
            continue
        for a in range(p.address, p.address + p.width):
            assert a not in used, f"{p.key} пересекается с {used[a]} по адресу 0x{a:02X}"
            used[a] = p.key


def test_resolve_address_respects_type():
    assert resolve_address(0x11, {"comp.type": 0}).key == "comp.stomp.sustain"
    assert resolve_address(0x11, {"comp.type": 1}).key == "comp.rack.threshold"
    assert resolve_address(0x12, {"comp.type": 1}) is None  # младший байт threshold
    assert resolve_address(0x41, {"reverb.type": 3}).key == "reverb.spring.reverb"
    assert resolve_address(0x41, {"reverb.type": 2}).key == "reverb.time"
    assert resolve_address(0x23, {"mod.type": 2}) is None  # у Tremolo нет 0x23
    assert resolve_address(0x7E, {}) is None


def test_groups_cover_switches_and_types():
    for g in GROUPS:
        if g.switch_key:
            assert PARAMS[g.switch_key].kind is Kind.SWITCH
        if g.type_key:
            assert g.type_key in TYPE_KEYS
            assert keys_affected_by_type(g.type_key)


def test_normalize_values():
    v = normalize_values({"amp.gain": 500, "junk": 1, "amp.master": -3})
    assert v["amp.gain"] == 100 and v["amp.master"] == 0 and "junk" not in v
    assert set(v) == set(PARAMS)


@pytest.mark.parametrize("key,value,text", [
    ("delay.time", 3500, "350 мс"),
    ("delay.time", 15, "1.5 мс"),
    ("delay.highcut", 16001, "Thru"),
    ("delay.lowcut", 21, "Thru"),
    ("delay.lowcut", 500, "500 Гц"),
    ("reverb.highcut", 2500, "2.5 кГц"),
    ("reverb.highcut", 16000, "16 кГц"),
    ("reverb.time", 25, "2.5 с"),
    ("reverb.pre", 200, "20.0 мс"),
    ("reverb.lowratio", 14, "1.4"),
    ("amp.model", 3, "Brit Hi"),
    ("comp.on", 1, "Вкл"),
    ("amp.gain", 42, "42"),
])
def test_format(key, value, text):
    assert PARAMS[key].format(value) == text


@pytest.mark.parametrize("key,text,value", [
    ("delay.time", "350", 3500),
    ("delay.time", "350 мс", 3500),
    ("delay.time", "99999", 9999),
    ("delay.highcut", "thru", 16001),
    ("delay.lowcut", "Thru", 21),
    ("reverb.highcut", "2.5k", 2500),
    ("reverb.highcut", "2,5 кГц", 2500),
    ("reverb.time", "2,5", 25),
    ("reverb.highratio", "0.7", 7),
    ("amp.model", "lead", 2),
    ("amp.model", "4", 4),
    ("amp.gain", "120", 100),
    ("comp.on", "выкл", 0),
])
def test_parse(key, text, value):
    assert PARAMS[key].parse(text) == value


def test_parse_invalid():
    assert PARAMS["amp.gain"].parse("") is None
    assert PARAMS["amp.gain"].parse("abc") is None
    assert PARAMS["comp.on"].parse("maybe") is None


def test_format_parse_roundtrip_all():
    for p in PARAMS.values():
        for v in {p.minimum, p.default, p.maximum, (p.minimum + p.maximum) // 2}:
            parsed = p.parse(p.format(v))
            assert parsed is not None, (p.key, v)
            # округление отображения допускает погрешность в пределах шага отображения
            tol = 10 if p.key.endswith("highcut") or p.key.endswith("lowcut") else 0
            assert abs(parsed - v) <= tol, (p.key, v, p.format(v), parsed)


def test_switch_raw_mapping():
    p = PARAMS["delay.on"]
    assert p.to_raw(1) == 0x00 and p.to_raw(0) == 0x7F
    assert p.from_raw(0x00) == 1 and p.from_raw(0x7F) == 0


def test_overrides_from_json():
    o = ProtocolOverrides.from_json({"confirmed": ["system.lamp"]})
    assert "system.lamp" in o.confirmed
    assert ProtocolOverrides.from_json("garbage").confirmed == set()
