import json

import pytest

from thr10editor.model.preset import Preset, normalize_folder, normalize_tags
from thr10editor.model.state import Origin, ToneState
from thr10editor.protocol.params import PARAMS, default_values


def test_state_set_notifies_once_with_origin():
    s = ToneState()
    events = []
    s.subscribe(lambda ch, o: events.append((ch, o)))
    assert s.set("amp.gain", 70, Origin.USER)
    assert events == [({"amp.gain": (50, 70)}, Origin.USER)]
    assert not s.set("amp.gain", 70)  # без изменений — без уведомления
    assert len(events) == 1


def test_state_clamps():
    s = ToneState()
    s.set("amp.gain", 1000)
    assert s["amp.gain"] == 100


def test_state_bulk_update_single_notification():
    s = ToneState()
    events = []
    s.subscribe(lambda ch, o: events.append((ch, o)))
    ch = s.update({"amp.gain": 1, "amp.bass": 2, "unknown": 5}, Origin.LOAD)
    assert set(ch) == {"amp.gain", "amp.bass"}
    assert len(events) == 1 and events[0][1] is Origin.LOAD


def test_state_replace_fills_defaults():
    s = ToneState({"amp.gain": 10})
    s.replace({"amp.bass": 3}, name="X")
    assert s.name == "X"
    assert s["amp.gain"] == PARAMS["amp.gain"].default
    assert s["amp.bass"] == 3


def test_state_unsubscribe_and_active():
    s = ToneState()
    events = []
    unsub = s.subscribe(lambda ch, o: events.append(ch))
    unsub()
    s.set("amp.gain", 3)
    assert events == []
    s.set("reverb.type", 3)
    assert s.is_active("reverb.spring.reverb") and not s.is_active("reverb.time")


def test_preset_dict_roundtrip():
    p = Preset("Blues", dict(default_values(), **{"amp.gain": 77}), folder=" Live / Blues/ ",
               tags=["Clean", "clean", " live "], favorite=True, notes="n")
    assert p.folder == "Live/Blues"
    assert p.tags == ["clean", "live"]
    q = Preset.from_dict(json.loads(json.dumps(p.to_dict())))
    assert q == p


def test_preset_file_dict():
    p = Preset("A", {})
    assert Preset.from_file_dict(p.to_file_dict()) == p
    with pytest.raises(ValueError):
        Preset.from_file_dict({"format": "other"})


def test_preset_from_dict_validation():
    with pytest.raises(ValueError):
        Preset.from_dict({"name": "x"})
    with pytest.raises(ValueError):
        Preset.from_dict([1, 2])
    p = Preset.from_dict({"name": "", "values": {"amp.gain": "bad", "amp.bass": 7.6}})
    assert p.name == "Без имени" and p.values["amp.bass"] == 7


def test_preset_patch_roundtrip():
    p = Preset("Lead", dict(default_values(), **{"amp.model": 2, "delay.on": 1}))
    q = Preset.from_patch(p.to_patch(), base=p.values)
    assert q.name == "Lead" and q.values == p.values


def test_preset_copy_new_identity():
    p = Preset("A", {})
    c = p.copy(new_identity=True)
    assert c.id != p.id and c.values == p.values


def test_normalizers():
    assert normalize_folder("a\\b//c/") == "a/b/c"
    assert normalize_tags("x, Y ,x") == ["x", "y"]
