"""Сценарии на настоящем окне приложения (отдельный процесс, offscreen)."""

import json
import os
import subprocess
import sys

import pytest

pytest.importorskip("PySide6")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def run_scenario(name, tmp_path):
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen", THR10EDITOR_HOME=str(tmp_path))
    r = subprocess.run([sys.executable, os.path.join(HERE, "app_scenario.py"), name],
                       cwd=ROOT, env=env, capture_output=True, text=True, timeout=120)
    line = next((l for l in r.stdout.splitlines() if l.startswith("RESULT ")), None)
    assert line, r.stdout + r.stderr
    res = json.loads(line[len("RESULT "):])
    assert "error" not in res, res
    assert res["warnings"] == [], res["warnings"]
    return res


def test_hotkeys_off_while_typing_and_click_outside_saves(tmp_path):
    r = run_scenario("typing", tmp_path)
    assert r["editing"]
    assert r["ab_while_typing"] == r["ab_before"] == "A"   # пробел и B не переключили A/B
    assert r["tap_while_typing"] == 0                      # T не нажал тап-темп
    assert r["delay_while_typing"] == r["delay_before"]
    assert r["name_after"].endswith(" B T x")              # клик вне поля сохранил имя
    assert r["ab_after_space"] == "B"                      # после — горячие клавиши работают


def test_multi_key_shortcuts_work(tmp_path):
    r = run_scenario("hotkeys", tmp_path)
    assert r["nested"] == []
    assert r["after_space"] == "B" and r["after_b"] == "A"


def test_midi_learn_can_be_cancelled(tmp_path):
    r = run_scenario("learn", tmp_path)
    assert r["started"] == "next"
    assert r["after_esc"] == "" and r["after_click"] == "" and r["after_toggle"] == ""
    assert r["next_binding"] == "не задано"


def test_stage_keyboard_and_track_data(tmp_path):
    r = run_scenario("stage", tmp_path)
    # пробел, пробел → 1, 2; ← ↑ → 1, 0; → ↓ PgDn → 1, 2, 3; PgUp → 2
    assert r["indices"] == [1, 2, 1, 0, 1, 2, 3, 2]
    assert r["chords_shown"] and r["tuning_shown"]
    # фон растягивается на весь экран без обрезки; обложка — GIF по центру
    assert r["bg_stretch"] and r["bg_ready"]
    assert r["cover_class"].startswith("QQuickAnimatedImage") and r["cover_ready"]
    assert r["cover_playing"] and r["cover_centered"]
    assert r["active_after_esc"] is False


def test_module_media_widget_in_cards(tmp_path):
    r = run_scenario("modulemedia", tmp_path)
    # 6 модулей (усилитель + 5 эффектов): у каждого кнопка в заголовке, пустые места скрыты
    assert r["boxes"] == 6 and r["buttons"] == 6 and r["visible_before"] == 0
    assert r["shown"] == ["amp", "mod"]
    mod, amp = r["media"]["mod"], r["media"]["amp"]
    assert mod["cls"].startswith("QQuickAnimatedImage") and mod["ready"] and mod["stretch"]
    assert amp["cls"].startswith("QQuickImage") and amp["ready"] and amp["stretch"]
    assert mod["h"] > 0 and abs(mod["w"] / mod["h"] - 2) < 0.1  # область 2:1 по ширине карточки
    assert amp["h"] > 0 and amp["w"] > 0
    assert r["after_clear"] == ["amp"]
