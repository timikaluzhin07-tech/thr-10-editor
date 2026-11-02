"""Сценарии на настоящем окне приложения (запускается тестами в отдельном процессе).

    python tests/app_scenario.py <сценарий>

Печатает строку «RESULT {json}». Использует самопроверку приложения, подменяя
её сценарием.
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, QPointF, Qt, QTimer  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402

import thr10editor.ui.selftest as selftest  # noqa: E402

SCENARIO = sys.argv[1]
result: dict = {}


def find(window, name):
    return window.findChild(object, name)


def click_item(window, item, dx=0.5, dy=0.5):
    p = item.mapToScene(QPointF(item.width() * dx, item.height() * dy))
    QTest.mouseClick(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
                     QPoint(int(p.x()), int(p.y())))


def type_text(window, text):
    for ch in text:
        QTest.keyClick(window, ch)


def key(window, k, mod=Qt.KeyboardModifier.NoModifier):
    QTest.keyClick(window, k, mod)
    QTest.qWait(30)


def scenario_typing(app, backend, window):
    field = find(window, "presetNameField")
    result["ab_before"] = backend.abActive
    result["delay_before"] = backend.param("delay.time").value
    click_item(window, field, 0.9)
    QTest.qWait(30)
    result["editing"] = bool(window.activeFocusItem() is not None and
                             window.activeFocusItem().inherits("QQuickTextInput"))
    key(window, Qt.Key.Key_End)
    type_text(window, " B T x")
    QTest.qWait(30)
    result["ab_while_typing"] = backend.abActive
    result["tap_while_typing"] = backend.tapCount
    result["delay_while_typing"] = backend.param("delay.time").value
    # клик в пустую область верхней панели (подпись THR10 EDITOR)
    click_item(window, find(window, "topBarSpacer"))
    QTest.qWait(50)
    result["name_after"] = backend.presetName
    key(window, Qt.Key.Key_Space)   # теперь горячие клавиши снова работают
    result["ab_after_space"] = backend.abActive


def scenario_hotkeys(app, backend, window):
    from PySide6.QtCore import QObject
    sc = [o for o in window.findChildren(QObject) if "Shortcut" in o.metaObject().className()]
    # ни одно сочетание не должно быть «вложенным списком» (такое молча не работает)
    result["nested"] = [str(o.property("sequences")) for o in sc
                        if any(isinstance(x, list) for x in (o.property("sequences") or []))]
    key(window, Qt.Key.Key_Space)
    result["after_space"] = backend.abActive
    key(window, Qt.Key.Key_B)
    result["after_b"] = backend.abActive


def scenario_learn(app, backend, window):
    res = {}
    backend.learnController("next")
    res["started"] = backend.controllerLearning
    key(window, Qt.Key.Key_Escape)
    res["after_esc"] = backend.controllerLearning
    backend.learnController("prev")
    QTest.mouseClick(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
                     QPoint(700, 500))
    QTest.qWait(30)
    res["after_click"] = backend.controllerLearning
    backend.learnController("next")
    backend.learnController("next")
    res["after_toggle"] = backend.controllerLearning
    res["next_binding"] = backend.nextBinding
    result.update(res)


def scenario_stage(app, backend, window):
    from PySide6.QtCore import QMetaObject, Q_ARG, QObject
    from PySide6.QtGui import QColor, QImage

    from thr10editor.model.preset import Preset
    from thr10editor.protocol.params import default_values

    for i in range(4):
        backend.load_preset(Preset(f"Track {i + 1}", dict(default_values(), **{"amp.gain": i * 10})))
        backend.saveCurrentAs(f"Track {i + 1}", "", "", False, "")
        backend.addToSetlist(backend.currentPresetId)
    backend.setTrackText(1, "chords", "Am – F – C – G")
    backend.setTrackText(1, "tuning", "Drop D")
    img = QImage(80, 40, QImage.Format.Format_RGB32)
    img.fill(QColor("#884422"))
    path = os.path.join(os.environ["THR10EDITOR_HOME"], "bg_src.png")
    img.save(path)
    backend.setTrackBackground(1, path)
    # как у пользователя: фокус стоит на кнопке, с которой открывают сцену
    buttons = [o for o in window.findChildren(QObject)
               if o.metaObject().className().startswith("AppButton") and o.property("visible")]
    buttons[0].forceActiveFocus()
    QMetaObject.invokeMethod(window, "startStage", Q_ARG("QVariant", 0))
    QTest.qWait(50)
    seq = []
    for k in (Qt.Key.Key_Space, Qt.Key.Key_Space, Qt.Key.Key_Left, Qt.Key.Key_Up,
              Qt.Key.Key_Right, Qt.Key.Key_Down, Qt.Key.Key_PageDown, Qt.Key.Key_PageUp):
        key(window, k)
        seq.append(backend.stageIndex)
    result["indices"] = seq
    backend.stageGoto(1)
    QTest.qWait(80)
    stage = next(o for o in window.findChildren(QObject)
                 if o.metaObject().className().startswith("StageView"))
    texts = [o.property("text") for o in stage.findChildren(QObject)
             if o.metaObject().className().startswith("QQuickLabel") or "Label" in o.metaObject().className()]
    result["chords_shown"] = "Am – F – C – G" in texts
    result["tuning_shown"] = "Drop D" in texts
    imgs = [o for o in stage.findChildren(QObject) if "QQuickImage" in o.metaObject().className()]
    if imgs:
        im = imgs[0]
        result["bg_ready"] = im.property("progress") == 1.0 and im.property("visible")
        # PreserveAspectCrop: картинка покрывает экран целиком, пропорции сохранены (2:1)
        pw, ph = im.property("paintedWidth"), im.property("paintedHeight")
        w, h = im.width(), im.height()
        result["bg_fill_crop"] = (pw >= w - 1 and ph >= h - 1 and abs(pw / ph - 2.0) < 0.02)
    else:
        result["bg_ready"] = result["bg_fill_crop"] = False
    if os.environ.get("SHOT"):
        window.grabWindow().save(os.environ["SHOT"])
    key(window, Qt.Key.Key_Escape)
    result["active_after_esc"] = backend.stageActive


def scenario_trackdialog(app, backend, window):
    """Открыть диалог трека (для визуальной проверки, SHOT=путь.png)."""
    from PySide6.QtCore import QMetaObject, Q_ARG, QObject

    from thr10editor.model.preset import Preset
    from thr10editor.protocol.params import default_values
    backend.load_preset(Preset("Song", default_values()))
    backend.saveCurrentAs("Song", "", "", False, "")
    backend.addToSetlist(backend.currentPresetId)
    backend.setTrackText(0, "chords", "Куплет: Am F C G\nПрипев: F G Am")
    backend.setTrackText(0, "tuning", "Drop D")
    for o in window.findChildren(QObject):
        if o.metaObject().className().startswith("Sidebar"):
            o.setProperty("currentIndex", 2)
    QTest.qWait(100)
    def all_objects(root):
        out, stack, seen = [], [root], set()
        while stack:
            o = stack.pop()
            k = id(o) if False else hash(o)
            if k in seen:
                continue
            seen.add(k)
            out.append(o)
            stack.extend(o.children())
            if hasattr(o, "childItems"):
                stack.extend(o.childItems())
        return out
    objs = all_objects(window)
    dlg = next(o for o in objs if o.metaObject().className().startswith("TrackDialog"))
    QMetaObject.invokeMethod(dlg, "openFor", Q_ARG("QVariant", 0))
    QTest.qWait(400)
    result["opened"] = bool(dlg.property("opened"))
    if os.environ.get("SHOT"):
        window.grabWindow().save(os.environ["SHOT"])


def run(app, backend, theme, window, seconds, screenshot, warnings, exit_code):
    def go():
        try:
            globals()["scenario_" + SCENARIO](app, backend, window)
        except Exception as e:  # noqa: BLE001
            result["error"] = repr(e)
        result["warnings"] = warnings
        print("RESULT " + json.dumps(result, ensure_ascii=False))
        sys.stdout.flush()
        app.quit()

    QTimer.singleShot(900, go)


selftest.run_selftest = run
from thr10editor.ui.app import main  # noqa: E402

sys.exit(main(["--selftest", "1", "--size", "1440x900"]))
