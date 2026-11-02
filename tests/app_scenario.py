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
