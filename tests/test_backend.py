import os
import subprocess
import sys

import pytest

pytest.importorskip("PySide6")

from PySide6.QtGui import QGuiApplication  # noqa: E402

from fixtures import s3_ydl  # noqa: E402
from thr10editor.model.preset import Preset  # noqa: E402
from thr10editor.protocol.params import default_values  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(scope="module")
def qapp():
    return QGuiApplication.instance() or QGuiApplication([])


@pytest.fixture
def backend(qapp, tmp_path):
    from thr10editor.ui.backend_full import FullBackend

    b = FullBackend(str(tmp_path))
    yield b
    b.shutdown()


def pump(backend, seconds=0.3, step=0.005):
    """Прогнать такты сессии (без цикла событий Qt)."""
    import time

    end = time.monotonic() + seconds
    while time.monotonic() < end:
        backend.session.tick()
        time.sleep(step)


def test_param_item_roundtrip(backend):
    gain = backend.param("amp.gain")
    gain.setValue(77)
    assert backend.state["amp.gain"] == 77 and gain.value == 77 and gain.text == "77"
    assert gain.setFromText("12")
    assert backend.state["amp.gain"] == 12
    assert not gain.setFromText("abc")
    gain.reset()
    assert gain.value == 50


def test_log_taper_position(backend):
    t = backend.param("delay.time")
    t.setPosition(0.0)
    assert t.value == 1
    t.setPosition(1.0)
    assert t.value == 9999
    t.setPosition(0.5)
    assert 90 <= t.value <= 110  # середина логарифмической шкалы ≈ √9999 ≈ 100
    assert abs(t.position - 0.5) < 0.01


def test_group_type_switch_updates_knobs(backend):
    mod = backend.group("mod")
    assert mod.knobKeys == ["mod.chorus.speed", "mod.chorus.depth", "mod.chorus.mix"]
    mod.setType(1)
    assert mod.typeIndex == 1
    assert "mod.flanger.spread" in mod.knobKeys
    comp = backend.group("comp")
    comp.setType(1)
    assert comp.choiceKeys == ["comp.rack.ratio", "comp.rack.knee"]
    mod.setEnabled(True)
    assert backend.state["mod.on"] == 1 and mod.enabled


def test_dirty_tracking(backend):
    backend.load_preset(Preset("Clean", default_values()))
    assert not backend.dirty
    backend.param("amp.bass").setValue(3)
    assert backend.dirty
    backend.param("amp.bass").setValue(50)
    assert not backend.dirty
    backend.presetName = "Other"
    assert backend.dirty and backend.presetName == "Other"


def test_demo_connect_and_sync(backend):
    backend.connectDemo()
    pump(backend, 0.3)
    assert backend.connStatus == "connected"
    assert backend.isDemo and backend.deviceModel == "THR10"
    assert backend.presetName == "PRESET1"
    backend.demoTurnKnob("amp.middle", 3)
    pump(backend, 0.05)
    assert backend.param("amp.middle").value == 3
    backend.param("amp.master").setValue(11)
    pump(backend, 0.1)
    assert backend.session.transport.amp.values["amp.master"] == 11


def test_slots_capture_and_persist(backend, tmp_path):
    backend.connectDemo()
    pump(backend, 0.2)
    backend.readSlot(3)
    assert backend.captureSlot == 3
    backend.demoPressSlot(3)
    pump(backend, 0.1)
    assert backend.captureSlot == -1
    assert backend.slots[3]["name"] == "PRESET4" and backend.slots[3]["known"]
    assert os.path.exists(tmp_path / "slots.json")
    backend.param("amp.gain").setValue(1)
    backend.loadSlot(3)
    assert backend.state["amp.model"] == 3


def test_write_slot_sends_dump(backend):
    backend.connectDemo()
    pump(backend, 0.2)
    backend.param("amp.treble").setValue(1)
    pump(backend, 0.1)
    backend.writeSlot(0)
    pump(backend, 0.2)
    amp = backend.session.transport.amp
    assert amp.values["amp.treble"] == 1
    backend.demoStoreSlot(0)
    assert amp.slots[0][1]["amp.treble"] == 1


@pytest.mark.parametrize("fmt", ["thrpreset", "syx", "ydl"])
def test_export_import_roundtrip(backend, tmp_path, fmt):
    backend.load_preset(Preset("Round Trip", dict(default_values(), **{"amp.model": 2,
                                                                      "delay.on": 1,
                                                                      "delay.time": 4321})))
    path = str(tmp_path / f"x.{fmt}")
    backend.exportCurrent(path, fmt)
    presets = backend.read_presets_from_file(path)
    assert len(presets) == 1
    p = presets[0]
    assert p.name == "Round Trip"
    assert p.values["amp.model"] == 2 and p.values["delay.time"] == 4321


def test_open_real_ydl_offers_choice(backend, tmp_path):
    path = tmp_path / "THR10C.YDL"
    path.write_bytes(s3_ydl())
    got = []
    backend.importReady.connect(lambda: got.append(True))
    backend.openFile(str(path))
    assert got and [p["name"] for p in backend.importedPresets] == ["model1", "model2"]
    backend.loadImported(1)
    assert backend.presetName == "model2" and backend.state["amp.model"] == 1


def test_open_bad_file_reports_error(backend, tmp_path):
    path = tmp_path / "bad.syx"
    path.write_bytes(b"not a sysex")
    msgs = []
    backend.toast.connect(lambda k, t: msgs.append(k))
    backend.openFile(str(path))
    assert msgs == ["error"]


def test_system_settings_demo(backend):
    backend.connectDemo()
    pump(backend, 0.1)
    backend.setSystem("system.lamp", False)
    pump(backend, 0.1)
    assert backend.lamp is False
    assert backend.session.transport.amp.system["system.lamp"] is False
    assert backend.systemConfirmed is False


def test_qml_selftest_loads_without_warnings(tmp_path):
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen", THR10EDITOR_HOME=str(tmp_path))
    shot = tmp_path / "shot.png"
    r = subprocess.run([sys.executable, "-m", "thr10editor", "--selftest", "1.6",
                        "--screenshot", str(shot)], cwd=ROOT, env=env,
                       capture_output=True, text=True, timeout=120)
    assert "SELFTEST OK" in r.stdout, r.stdout + r.stderr
    assert r.returncode == 0
    assert shot.exists() and shot.stat().st_size > 10_000
