import time

import pytest

pytest.importorskip("PySide6")

from PySide6.QtGui import QGuiApplication  # noqa: E402

from thr10editor.model.preset import Preset  # noqa: E402
from thr10editor.protocol.params import default_values  # noqa: E402
from thr10editor.transport.controller_input import ControlEvent  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    return QGuiApplication.instance() or QGuiApplication([])


@pytest.fixture
def b(qapp, tmp_path):
    from thr10editor.ui.backend_full import FullBackend

    backend = FullBackend(str(tmp_path))
    yield backend
    backend.shutdown()


def pump(backend, seconds=0.2, step=0.005):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        backend.session.tick()
        backend.on_tick(time.monotonic())
        time.sleep(step)


# ---- undo / redo -----------------------------------------------------------------

def test_undo_redo_user_changes(b):
    g = b.param("amp.gain")
    g.beginGesture()
    for v in (51, 55, 60, 70):
        g.setValue(v)
    g.endGesture()
    b.param("amp.bass").setValue(10)
    assert b.canUndo and b.undoText == "Bass"
    b.undo()
    assert b.state["amp.bass"] == 50
    b.undo()
    assert b.state["amp.gain"] == 50  # весь жест — один шаг
    assert not b.canUndo
    b.redo()
    b.redo()
    assert b.state["amp.gain"] == 70 and b.state["amp.bass"] == 10


def test_undo_load_restores_name(b):
    b.presetName = "Old"
    b.load_preset(Preset("New", dict(default_values(), **{"amp.model": 3})))
    assert b.presetName == "New"
    b.undo()
    assert b.presetName == "Old" and b.state["amp.model"] == 0


def test_undo_reaches_amp(b):
    b.connectDemo()
    pump(b, 0.2)
    b.param("amp.treble").setValue(5)
    pump(b, 0.1)
    b.undo()
    pump(b, 0.1)
    assert b.session.transport.amp.values["amp.treble"] == b.state["amp.treble"] != 5


def test_initial_device_sync_not_in_history(b):
    b.connectDemo()
    pump(b, 0.2)
    assert b.presetName == "PRESET1"
    assert not b.canUndo


def test_device_knob_is_undoable(b):
    b.connectDemo()
    pump(b, 0.2)
    b.demoTurnKnob("amp.middle", 2)
    pump(b, 0.05)
    assert b.undoText == "Ручка на комбике"
    b.undo()
    assert b.state["amp.middle"] != 2


# ---- A/B ----------------------------------------------------------------------------

def test_ab_switch_keeps_separate_sounds_and_histories(b):
    b.param("amp.gain").setValue(11)
    b.toggleAB()
    assert b.abActive == "B" and b.state["amp.gain"] == 11  # B — копия A
    assert not b.canUndo  # у B своя история
    b.param("amp.gain").setValue(99)
    b.toggleAB()
    assert b.abActive == "A" and b.state["amp.gain"] == 11
    assert b.canUndo
    b.toggleAB()
    assert b.state["amp.gain"] == 99


def test_ab_switch_sends_single_dump(b):
    b.connectDemo()
    pump(b, 0.2)
    b.toggleAB()
    b.param("amp.model").setValue(4)
    pump(b, 0.1)
    amp = b.session.transport.amp
    amp.received.clear()
    b.toggleAB()
    pump(b, 0.2)
    from thr10editor.protocol.sysex import PatchDump, decode

    assert [type(decode(m)) for m in amp.received] == [PatchDump]
    assert amp.values["amp.model"] == 0


# ---- библиотека -------------------------------------------------------------------------

def test_library_save_update_and_search(b, tmp_path):
    b.presetName = "Blues"
    b.saveCurrentAs("Blues", "Live", "blues, clean", True, "")
    pid = b.currentPresetId
    assert pid and b.libraryTotal == 1 and not b.dirty
    b.param("amp.gain").setValue(3)
    assert b.dirty
    assert b.saveCurrent() is True
    assert b.library.get(pid).values["amp.gain"] == 3
    b.libSearch = "blu"
    assert b.libraryCount == 1
    b.libSearch = "metal"
    assert b.libraryCount == 0
    b.libSearch = ""
    b.libTag = "clean"
    assert b.libraryCount == 1
    b.libTag = "clean"  # повторный клик снимает фильтр
    assert b.libTag == ""
    # сохранилось на диск
    from thr10editor.model.library import Library

    assert len(Library(str(tmp_path / "library.json"))) == 1


def test_save_current_without_library_preset_returns_false(b):
    assert b.saveCurrent() is False


def test_import_files_to_library(b, tmp_path):
    from fixtures import s3_ydl

    path = tmp_path / "THR10C.YDL"
    path.write_bytes(s3_ydl())
    b.importFilesToLibrary([str(path)])
    assert b.libraryTotal == 2
    assert "Импорт/THR10C" in b.folderPaths


def test_export_library(b, tmp_path):
    b.saveCurrentAs("One", "", "", False, "")
    b.saveCurrentAs("Two", "", "", False, "")
    out = tmp_path / "lib.ydl"
    b.exportLibrary(str(out), "ydl", False)
    assert len(b.read_presets_from_file(str(out))) == 2


# ---- сет-лист и сцена -------------------------------------------------------------------

def test_stage_navigation_and_pedal(b):
    ids = []
    for n in ("Intro", "Verse", "Solo"):
        b.load_preset(Preset(n, dict(default_values(), **{"amp.gain": len(ids) * 10})))
        b.saveCurrentAs(n, "Гиг", "", False, "")
        ids.append(b.currentPresetId)
        b.addToSetlist(ids[-1])
    assert [i["name"] for i in b.setlistItems] == ["Intro", "Verse", "Solo"]
    b.moveSetlistItem(2, 0)
    assert b.setlistItems[0]["name"] == "Solo"
    b.startStage(0)
    assert b.stageActive and b.presetName == "Solo" and b.stageNextName == "Intro"
    b.stageNext()
    assert b.presetName == "Intro" and b.stagePrevName == "Solo"
    # педаль: обучение и нажатие
    b.learnController("next")
    b._on_controller_event(ControlEvent("cc", 0, 80, 127))
    b._on_controller_event(ControlEvent("cc", 0, 80, 0))
    b._on_controller_event(ControlEvent("cc", 0, 80, 127))
    assert b.presetName == "Verse"
    b.stageNext()
    assert b.presetName == "Verse"  # конец списка
    b.stopStage()
    assert not b.stageActive


def test_stage_empty_setlist_warns(b):
    msgs = []
    b.toast.connect(lambda k, t: msgs.append(k))
    b.startStage(0)
    assert not b.stageActive and msgs == ["warning"]


# ---- тап-темп ---------------------------------------------------------------------------------

def test_tap_tempo_sets_delay(b, monkeypatch):
    t = [100.0]
    monkeypatch.setattr(b.tap, "clock", lambda: t[0])
    for _ in range(4):
        b.tapTempo()
        t[0] += 0.5
    assert b.tapBpm == pytest.approx(120)
    assert b.state["delay.time"] == 5000
    b.tapSubdivision = "1/8"
    assert b.state["delay.time"] == 2500


# ---- рандомайзер ------------------------------------------------------------------------------

def test_randomizer_lock_and_undo(b):
    before = b.state.values
    b.param("amp.treble").toggleLock()
    b.param("delay.on").toggleLock()
    b.param("amp.model").toggleLock()
    assert b.param("amp.treble").locked and b.param("amp.master").locked
    for _ in range(15):
        b.randomize()
        after = b.state.values
        for k in ("amp.treble", "amp.master", "delay.on", "amp.model"):
            assert after[k] == before[k], k
    assert b.state.values != before
    for _ in range(15):
        b.undo()
    assert b.state.values == before


def test_randomizer_changes_switches_in_app(b):
    seen = set()
    for _ in range(20):
        b.randomize()
        seen.add((b.state["gate.on"], b.state["reverb.type"]))
    assert len(seen) > 3
    keys = {p["key"]: p for p in b.randomParams}
    assert keys["gate.on"]["kind"] == "switch" and keys["amp.model"]["kind"] == "choice"


def test_random_bounds_setting(b):
    b.setRandomBounds("amp.gain", 0.9, 1.0)
    b.randomAmount = 100
    for _ in range(10):
        b.randomize()
        assert b.state["amp.gain"] >= 90


# ---- морфинг ----------------------------------------------------------------------------------

def test_morph_to_library_preset(b):
    b.saveCurrentAs("Target", "", "", False, "")
    target = b.currentPresetId
    b.library.get(target).values["amp.gain"] = 100
    b.load_preset(Preset("Start", dict(default_values(), **{"amp.gain": 0})))
    b.morphDuration = 0.2
    b.morphTo(target)
    assert b.morphRunning
    mids = set()
    for _ in range(60):
        b.on_tick(time.monotonic())
        mids.add(b.state["amp.gain"])
        time.sleep(0.005)
        if not b.morphRunning:
            break
    assert not b.morphRunning
    assert b.state["amp.gain"] == 100 and b.presetName == "Target"
    assert len(mids) > 3  # были промежуточные значения
    b.undo()
    assert b.state["amp.gain"] == 0 and b.presetName == "Start"


def test_morph_stops_on_user_change(b):
    b.toggleAB()
    b.param("amp.gain").setValue(100)
    b.toggleAB()
    b.morphTarget = "__ab__"
    b.morphDuration = 10
    b.startMorph()
    b.on_tick(time.monotonic())
    b.param("amp.bass").setValue(1)
    assert not b.morphRunning


# ---- LFO --------------------------------------------------------------------------------------

def test_lfo_runs_and_restores(b):
    b.param("amp.master").setValue(50)
    b.addLfo("amp.master")
    lfo = b.lfos[0]
    b.setLfoField(lfo["id"], "rate", 5.0)
    b.setLfoField(lfo["id"], "depth", 0.8)
    assert b.param("amp.master").automated
    history_len = len(b.history)
    b.startAutomation()
    seen = set()
    for _ in range(100):
        b.on_tick(time.monotonic())
        seen.add(b.state["amp.master"])
        time.sleep(0.003)
    b.stopAutomation()
    assert len(seen) > 3
    assert b.state["amp.master"] == 50
    assert len(b.history) == history_len  # автоматизация не засоряет историю


def test_lfo_toggle_for_key(b):
    b.toggleLfoForKey("amp.bass")
    assert b.param("amp.bass").automated
    b.toggleLfoForKey("amp.bass")
    assert not b.param("amp.bass").automated
