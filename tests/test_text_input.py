"""Общий механизм завершения ввода (InputGuard) на живой QML-сцене."""

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QPoint, Qt  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402
from PySide6.QtQuick import QQuickView  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402

from thr10editor.ui.text_input import TextInputGuard  # noqa: E402

QML = b"""
import QtQuick
import QtQuick.Controls.Basic
Rectangle {
    width: 400; height: 300
    property string saved: ""
    property int shortcutHits: 0
    property alias field: field
    property alias area: area
    TextField {
        id: field
        objectName: "field"
        x: 10; y: 10; width: 200; height: 30
        onEditingFinished: parent.saved = text
    }
    TextArea {
        id: area
        objectName: "area"
        x: 10; y: 60; width: 200; height: 80
    }
    Rectangle { objectName: "empty"; x: 250; y: 200; width: 100; height: 80; color: "gray" }
}
"""


@pytest.fixture(scope="module")
def qapp():
    return QGuiApplication.instance() or QGuiApplication([])


@pytest.fixture
def scene(qapp):
    view = QQuickView()
    view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
    from PySide6.QtCore import QByteArray, QUrl
    from PySide6.QtQml import QQmlComponent

    comp = QQmlComponent(view.engine())
    comp.setData(QByteArray(QML), QUrl())
    root = comp.create()
    assert root is not None, comp.errorString()
    view.setContent(QUrl(), comp, root)
    view.resize(400, 300)
    view.show()
    QTest.qWaitForWindowExposed(view)
    guard = TextInputGuard()
    guard.attach(view)
    yield view, root, guard
    view.close()


def type_text(view, text):
    for ch in text:
        QTest.keyClick(view, ch)


def field(root, name):
    return root.findChild(object, name)


def test_click_outside_finishes_and_saves(scene):
    view, root, guard = scene
    f = field(root, "field")
    QTest.mouseClick(view, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(50, 25))
    assert f.hasActiveFocus() and guard.editing
    type_text(view, "Clean Lead")  # пробел — обычный символ
    QTest.mouseClick(view, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(300, 240))
    QTest.qWait(20)
    assert not f.hasActiveFocus() and not guard.editing
    assert root.property("saved") == "Clean Lead"


def test_click_inside_keeps_editing(scene):
    view, root, guard = scene
    f = field(root, "field")
    QTest.mouseClick(view, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(50, 25))
    QTest.mouseClick(view, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(150, 25))
    QTest.qWait(20)
    assert f.hasActiveFocus() and guard.editing


def test_enter_finishes_single_line(scene):
    view, root, guard = scene
    f = field(root, "field")
    QTest.mouseClick(view, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(50, 25))
    type_text(view, "Drop D")
    QTest.keyClick(view, Qt.Key.Key_Return)
    QTest.qWait(20)
    assert root.property("saved") == "Drop D"
    assert not f.hasActiveFocus() and not guard.editing


def test_multiline_enter_is_newline_ctrl_enter_finishes(scene):
    view, root, guard = scene
    a = field(root, "area")
    QTest.mouseClick(view, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(50, 90))
    type_text(view, "Am F")
    QTest.keyClick(view, Qt.Key.Key_Return)
    type_text(view, "C G")
    QTest.qWait(20)
    assert a.hasActiveFocus() and a.property("text") == "Am F\nC G"
    QTest.keyClick(view, Qt.Key.Key_Return, Qt.KeyboardModifier.ControlModifier)
    QTest.qWait(20)
    assert not a.hasActiveFocus() and a.property("text") == "Am F\nC G"


def test_editing_flag_tracks_focus(scene):
    view, root, guard = scene
    assert not guard.editing
    field(root, "area").forceActiveFocus()
    assert guard.editing
    guard.finish()
    assert not guard.editing
