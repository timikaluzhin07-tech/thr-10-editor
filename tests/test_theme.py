import pytest

from thr10editor.ui.theme import auto_scale, contrast, load_tokens, parse_color

TOKENS = load_tokens()
THEMES = TOKENS["themes"]


def test_themes_have_same_keys():
    keys = [set(t) for t in THEMES.values()]
    assert all(k == keys[0] for k in keys)


def test_colors_parse():
    for theme in THEMES.values():
        for value in theme.values():
            parse_color(value)


@pytest.mark.parametrize("mode", list(THEMES))
def test_contrast(mode):
    c = THEMES[mode]
    assert contrast(c["text"], c["bg"]) >= 7
    assert contrast(c["text"], c["surface"]) >= 7
    assert contrast(c["textMuted"], c["surface"]) >= 4.5
    assert contrast(c["textMuted"], c["surface2"]) >= 4.5
    assert contrast(c["textFaint"], c["surface"]) >= 3
    assert contrast(c["accentText"], c["accent"]) >= 4.5
    for key in ("accent", "success", "warning", "danger", "info", "groupAmp", "groupComp",
                "groupMod", "groupDelay", "groupReverb", "groupGate"):
        assert contrast(c[key], c["surface"]) >= 3, key


def test_groups_have_colors():
    from thr10editor.protocol.params import GROUPS

    for g in GROUPS:
        for theme in THEMES.values():
            assert g.accent in theme


def test_auto_scale_bounds_and_step():
    assert auto_scale(1360, 860, TOKENS) == 1.0
    assert auto_scale(400, 300, TOKENS) == TOKENS["scale"]["min"]
    assert auto_scale(10000, 10000, TOKENS) == TOKENS["scale"]["max"]
    s = auto_scale(1500, 1000, TOKENS)
    assert abs(s / TOKENS["scale"]["step"] - round(s / TOKENS["scale"]["step"])) < 1e-6


def test_parse_color_formats():
    assert parse_color("#FF0000") == (1, 0, 0, 1)
    r, g, b, a = parse_color("#80000000")
    assert abs(a - 128 / 255) < 1e-9
    with pytest.raises(ValueError):
        parse_color("#123")


def test_theme_provider_qt():
    pytest.importorskip("PySide6")
    from PySide6.QtGui import QGuiApplication

    from thr10editor.ui.theme_provider import ThemeProvider, load_fonts

    app = QGuiApplication.instance() or QGuiApplication([])
    families = load_fonts()
    assert "Inter" in families
    t = ThemeProvider()
    assert t.dark and t.fontFamily == "Inter"
    seen = []
    t.changed.connect(lambda: seen.append("c"))
    t.metricsChanged.connect(lambda: seen.append("m"))
    t.toggle()
    assert not t.dark and t.c["bg"].name().upper() == THEMES["light"]["bg"]
    t.updateWindowSize(2720, 1720)
    assert t.scale == 1.6 and t.space["md"] == pytest.approx(12 * 1.6)
    t.zoomIn()
    assert t.scale == 1.6 * 1.1 or t.zoom == 1.1
    t.zoomReset()
    assert t.zoom == 1.0
    assert seen.count("c") == 1 and seen.count("m") >= 2
    assert t.alpha("accent", 0.5).alphaF() == pytest.approx(0.5, abs=0.01)
    del app
