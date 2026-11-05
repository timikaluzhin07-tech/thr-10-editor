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

def test_library_save_and_search(b, tmp_path):
    b.presetName = "Blues"
    b.saveCurrentAs("Blues", "Live", "blues, clean", True, "")
    pid = b.currentPresetId
    assert pid and b.libraryTotal == 1 and not b.dirty
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


def _custom_sound(b):
    """Звук, далёкий от значений по умолчанию, включая неактивные варианты."""
    import random

    from thr10editor.protocol.params import PARAMS

    rng = random.Random(11)
    vals = {k: rng.randint(p.minimum, p.maximum) for k, p in PARAMS.items()}
    vals.update({"amp.gain": 3, "delay.on": 1, "reverb.type": 3, "mod.type": 1,
                 "mod.chorus.speed": 99})
    b.load_preset(Preset("Custom", vals))
    b.param("amp.treble").setValue(7)  # правка после загрузки
    return b.state.values


def test_save_always_creates_new_preset_with_actual_values(b):
    sound = _custom_sound(b)
    b.saveCurrentAs("First", "", "", False, "")
    first = b.currentPresetId
    # дальнейшая правка и повторное «Сохранить» — новый пресет, старый не тронут
    b.param("amp.bass").setValue(1)
    sound2 = b.state.values
    b.saveCurrentAs("Second", "", "", False, "")
    second = b.currentPresetId
    assert first != second and b.libraryTotal == 2
    assert b.library.get(first).values == sound          # ровно то, что звучало
    assert b.library.get(second).values == sound2
    assert b.library.get(first).values["amp.bass"] != 1  # первый не перезаписан
    # звук в редакторе не изменился ни на один параметр, новый пресет активен
    assert b.state.values == sound2
    assert b.currentPresetId == second and not b.dirty
    assert b.library.get(second).values != b.library.get(first).values


def test_save_same_name_does_not_overwrite(b):
    _custom_sound(b)
    b.saveCurrentAs("Same", "", "", False, "")
    a = b.currentPresetId
    b.param("amp.middle").setValue(2)
    b.saveCurrentAs("Same", "", "", False, "")
    assert b.libraryTotal == 2 and b.currentPresetId != a
    assert b.library.get(a).values["amp.middle"] != 2


def test_overwrite_is_explicit(b):
    _custom_sound(b)
    b.saveCurrentAs("Target", "Live", "x", False, "n")
    target = b.currentPresetId
    b.saveCurrentAs("Other", "", "", False, "")
    other = b.currentPresetId
    other_vals = b.library.get(other).values
    b.param("amp.gain").setValue(88)
    assert b.overwritePreset(target) is True
    t = b.library.get(target)
    assert t.values == b.state.values and t.values["amp.gain"] == 88
    assert (t.name, t.folder, t.tags, t.notes) == ("Target", "Live", ["x"], "n")
    assert b.library.get(other).values == other_vals
    assert b.currentPresetId == target and b.presetName == "Target"
    assert b.overwritePreset("nope") is False


def test_add_current_to_setlist_never_overwrites(b):
    _custom_sound(b)
    b.saveCurrentAs("Song", "", "", False, "")
    pid = b.currentPresetId
    saved = b.library.get(pid).values
    b.param("amp.gain").setValue(77)  # изменили звук
    b.addCurrentToSetlist()
    assert b.library.get(pid).values == saved
    assert b.libraryTotal == 2
    assert b.setlistItems[-1]["id"] == b.currentPresetId != pid


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


# ---- данные трека сет-листа -----------------------------------------------------------

def _image(tmp_path, name="bg.png", fmt="PNG"):
    from PySide6.QtGui import QColor, QImage

    img = QImage(64, 32, QImage.Format.Format_RGB32)
    img.fill(QColor("#335577"))
    path = tmp_path / "src" / name
    path.parent.mkdir(exist_ok=True)
    assert img.save(str(path), fmt)
    return path


def _setlist_with_tracks(b, n=2):
    for i in range(n):
        b.load_preset(Preset(f"Song {i + 1}", dict(default_values(), **{"amp.gain": i})))
        b.saveCurrentAs(f"Song {i + 1}", "", "", False, "")
        b.addToSetlist(b.currentPresetId)


def test_track_chords_and_tuning_saved_with_setlist(b, tmp_path):
    from thr10editor.model.library import Library

    _setlist_with_tracks(b)
    b.setTrackText(0, "chords", "Куплет: Am – F – C – G\nПрипев: F G Am")
    b.setTrackText(0, "tuning", "  Drop D ")
    b.setTrackText(1, "tuning", "Eb Standard")
    items = b.setlistItems
    assert items[0]["chords"].startswith("Куплет") and items[0]["tuning"] == "Drop D"
    lib = Library(str(tmp_path / "library.json"))  # сохранено на диск вместе с сет-листом
    t = lib.setlists[0].items
    assert t[0].chords == "Куплет: Am – F – C – G\nПрипев: F G Am"
    assert (t[0].tuning, t[1].tuning) == ("Drop D", "Eb Standard")
    assert "Drop D" in b.tuningSuggestions and "Standard E" in b.tuningSuggestions


def test_track_background_is_copied_replaced_and_removed(b, tmp_path):
    _setlist_with_tracks(b)
    src = _image(tmp_path)
    assert b.setTrackBackground(0, str(src)) is True
    bg_dir = tmp_path / "backgrounds"
    files = list(bg_dir.iterdir())
    assert len(files) == 1 and files[0].read_bytes() == src.read_bytes()
    src.unlink()  # исходник удалён — фон остаётся
    assert b.setlistItems[0]["hasBackground"] and b.setlistItems[0]["background"].startswith("file:")
    # замена: старый файл удаляется
    src2 = _image(tmp_path, "new.webp", "WEBP")
    assert b.setTrackBackground(0, str(src2)) is True
    files2 = list(bg_dir.iterdir())
    assert len(files2) == 1 and files2[0].suffix == ".webp" and files2[0] != files[0]
    b.clearTrackBackground(0)
    assert not b.setlistItems[0]["hasBackground"] and list(bg_dir.iterdir()) == []


def test_track_background_rejects_non_images(b, tmp_path):
    _setlist_with_tracks(b, 1)
    bad = tmp_path / "notes.txt"
    bad.write_text("hello")
    assert b.setTrackBackground(0, str(bad)) is False
    fake = tmp_path / "fake.png"
    fake.write_text("not an image")
    assert b.setTrackBackground(0, str(fake)) is False
    assert not b.setlistItems[0]["hasBackground"]


def test_stage_shows_track_data(b, tmp_path):
    _setlist_with_tracks(b, 3)
    b.setTrackText(1, "chords", "C G Am F")
    b.setTrackText(1, "tuning", "Drop C")
    b.setTrackBackground(1, str(_image(tmp_path)))
    b.startStage(0)
    assert b.stageChords == "" and b.stageBackground == ""
    b.stageNext()
    assert (b.stageChords, b.stageTuning) == ("C G Am F", "Drop C")
    assert b.stageBackground.startswith("file:")
    b.startStage(2)
    assert b.presetName == "Song 3"
    b.deletePreset(b.setlistItems[1]["id"])  # трек с фоном удалён — файл тоже
    assert list((tmp_path / "backgrounds").iterdir()) == []


# ---- GIF, обложка трека, картинки в карточках модулей (версия 1.3) -------------

def _gif(tmp_path, name="anim.gif"):
    from gif_sample import write_gif

    path = tmp_path / "src" / name
    path.parent.mkdir(exist_ok=True)
    return write_gif(path, 3)


def test_track_background_accepts_gif(b, tmp_path):
    _setlist_with_tracks(b, 1)
    src = _gif(tmp_path)
    assert b.setTrackBackground(0, str(src)) is True
    item = b.setlistItems[0]
    assert item["hasBackground"] and item["backgroundGif"] and item["background"].endswith(".gif")
    files = list((tmp_path / "backgrounds").iterdir())
    assert len(files) == 1 and files[0].read_bytes() == src.read_bytes()
    b.startStage(0)
    assert b.stageBackgroundGif is True and b.stageBackground.endswith(".gif")


def test_video_files_are_rejected(b, tmp_path):
    _setlist_with_tracks(b, 1)
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"\x00\x00\x00\x18ftypmp42")
    assert b.setTrackMedia(0, "background", str(video)) is False
    assert b.setModuleMedia("comp", str(video)) is False
    assert not b.setlistItems[0]["hasBackground"] and b.moduleMedia == {}


def test_track_cover_set_replace_clear_independent_of_background(b, tmp_path):
    _setlist_with_tracks(b, 2)
    bg_dir = tmp_path / "backgrounds"
    assert b.setTrackMedia(0, "background", str(_image(tmp_path))) is True
    assert b.setTrackMedia(0, "cover", str(_gif(tmp_path))) is True
    item = b.setlistItems[0]
    assert item["hasCover"] and item["coverGif"] and item["hasBackground"]
    assert item["cover"] != item["background"] and len(list(bg_dir.iterdir())) == 2
    # обложка на сцене — отдельно от фона; у второго трека её нет
    b.startStage(0)
    assert b.stageCover.endswith(".gif") and b.stageCoverGif and b.stageBackground.endswith(".png")
    b.stageNext()
    assert b.stageCover == "" and b.stageCoverGif is False
    # замена обложки: старый файл удаляется, фон не трогается
    assert b.setTrackMedia(0, "cover", str(_image(tmp_path, "c.jpg", "JPG"))) is True
    names = sorted(p.suffix for p in bg_dir.iterdir())
    assert names == [".jpg", ".png"] and not b.setlistItems[0]["coverGif"]
    b.clearTrackMedia(0, "cover")
    assert not b.setlistItems[0]["hasCover"] and b.setlistItems[0]["hasBackground"]
    assert [p.suffix for p in bg_dir.iterdir()] == [".png"]
    # неизвестное поле не принимается
    assert b.setTrackMedia(0, "chords", str(_image(tmp_path))) is False


def test_module_media_set_persist_and_clear(b, qapp, tmp_path):
    from thr10editor.ui.backend_full import FullBackend

    seen = []
    b.moduleMediaChanged.connect(lambda: seen.append(1))
    assert b.setModuleMedia("comp", str(_gif(tmp_path))) is True
    assert b.setModuleMedia("amp", str(_image(tmp_path))) is True
    assert b.setModuleMedia("nope", str(_image(tmp_path))) is False
    mm = b.moduleMedia
    assert set(mm) == {"comp", "amp"} and mm["comp"]["gif"] and not mm["amp"]["gif"]
    assert mm["comp"]["url"].startswith("file:") and len(seen) == 2
    bg_dir = tmp_path / "backgrounds"
    assert len(list(bg_dir.iterdir())) == 2
    # картинки модулей переживают перезапуск и уборку файлов фонов сет-листа
    _setlist_with_tracks(b, 1)
    b.setTrackBackground(0, str(_image(tmp_path, "t.png")))
    b.clearTrackBackground(0)
    assert len(list(bg_dir.iterdir())) == 2
    b.shutdown()
    b2 = FullBackend(str(tmp_path))
    try:
        assert set(b2.moduleMedia) == {"comp", "amp"}
        # замена — старый файл удалён; удаление — файл удалён
        assert b2.setModuleMedia("comp", str(_image(tmp_path, "c2.webp", "WEBP"))) is True
        assert len(list(bg_dir.iterdir())) == 2 and not b2.moduleMedia["comp"]["gif"]
        b2.clearModuleMedia("comp")
        b2.clearModuleMedia("amp")
        assert b2.moduleMedia == {} and list(bg_dir.iterdir()) == []
    finally:
        b2.shutdown()
