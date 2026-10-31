import itertools
import random

import pytest

from fixtures import s3_patch
from thr10editor.protocol import constants as C
from thr10editor.protocol.params import PARAMS, default_values
from thr10editor.protocol.patch import decode_patch, encode_patch, sanitize_name


def test_s3_model1_all_minimums():
    """Реальный пресет «model1» из THR10C.YDL (S3) — все параметры на минимуме."""
    d = decode_patch(s3_patch("model1"))
    v = d.values
    assert d.name == "model1"
    assert d.warnings == []
    assert v["amp.model"] == 0 and v["amp.cab"] == 0
    for k in ("amp.gain", "amp.master", "amp.bass", "amp.middle", "amp.treble"):
        assert v[k] == 0
    for k in ("comp.on", "mod.on", "delay.on", "reverb.on", "gate.on"):
        assert v[k] == 0, k  # 7F = выключено
    # минимумы из S1 совпадают с реальными байтами
    assert v["delay.time"] == 1
    assert v["delay.highcut"] == 1000
    assert v["delay.lowcut"] == 21
    assert v["reverb.type"] == 0
    assert v["reverb.time"] == 3
    assert v["reverb.pre"] == 1
    assert v["reverb.lowcut"] == 21
    assert v["reverb.highcut"] == 1000
    assert v["reverb.highratio"] == 1
    assert v["reverb.lowratio"] == 1


def test_s3_model2_crunch_us2x12():
    v = decode_patch(s3_patch("model2")).values
    assert v["amp.model"] == 1  # Crunch
    assert v["amp.cab"] == 1  # US 2x12


def test_s3_reencode_matches_except_unknown_bytes():
    original = s3_patch("model1")
    d = decode_patch(original)
    again = encode_patch(d.name, d.values)
    # отличаться может только байт 255 (обнуляется) и 0x24 (параметр неактивного типа
    # модуляции Flanger.Feedback — в Chorus он не используется)
    diff = [i for i in range(256) if original[i] != again[i]]
    assert set(diff) <= {255, 128 + 0x24}


def _random_values(rng: random.Random, types: dict[str, int]) -> dict[str, int]:
    vals = {k: rng.randint(p.minimum, p.maximum) for k, p in PARAMS.items()}
    vals.update(types)
    return vals


@pytest.mark.parametrize("comp,mod,rev", list(itertools.product(range(2), range(4), range(4))))
def test_roundtrip_all_type_combinations(comp, mod, rev):
    rng = random.Random(comp * 100 + mod * 10 + rev)
    vals = _random_values(rng, {"comp.type": comp, "mod.type": mod, "reverb.type": rev})
    patch = encode_patch("Test", vals)
    assert len(patch) == 256 and patch[255] == 0
    assert all(b <= 0x7F for b in patch)
    decoded = decode_patch(patch, base=vals)
    assert decoded.values == vals
    # без base — активные параметры совпадают
    decoded2 = decode_patch(patch)
    for k, p in PARAMS.items():
        if p.is_active(vals):
            assert decoded2.values[k] == vals[k], k


def test_active_variant_only_written():
    vals = default_values()
    vals.update({"comp.type": 1, "comp.rack.threshold": 600, "comp.stomp.sustain": 99})
    patch = encode_patch("x", vals)
    # threshold = 600 = 4*128 + 88 по адресам 0x11, 0x12
    assert patch[128 + 0x11] == 4 and patch[128 + 0x12] == 88


def test_inactive_values_from_base():
    base = default_values()
    base["mod.flanger.speed"] = 77
    vals = dict(base, **{"mod.type": 0})
    d = decode_patch(encode_patch("x", vals), base=base)
    assert d.values["mod.flanger.speed"] == 77


def test_out_of_range_warns_and_clamps():
    patch = bytearray(256)
    patch[128 + 0x01] = 120  # Gain > 100
    patch[128 + 0x00] = 9  # нет такой модели
    d = decode_patch(bytes(patch))
    assert d.values["amp.gain"] == 100
    assert d.values["amp.model"] == 7
    assert len(d.warnings) >= 2


def test_name_encoding():
    patch = encode_patch("Blues Lead", default_values())
    assert patch[:10] == b"Blues Lead" and patch[10] == 0
    assert decode_patch(patch).name == "Blues Lead"


def test_sanitize_name():
    assert sanitize_name("Чистый звук") == "Chistyy zvuk"
    assert sanitize_name("Ёж") == "Ezh"
    assert sanitize_name("a™b") == "a?b"
    assert len(sanitize_name("x" * 200)) == C.PATCH_NAME_SIZE


def test_decode_wrong_size():
    with pytest.raises(ValueError):
        decode_patch(bytes(10))
