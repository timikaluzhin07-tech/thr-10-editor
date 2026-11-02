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
