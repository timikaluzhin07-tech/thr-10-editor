import QtQuick
import QtQuick.Controls.Basic
import THR10

// Многострочное поле ввода. Enter — новая строка; завершение ввода —
// клик вне поля или Ctrl+Enter (общий механизм InputGuard).
TextArea {
    id: root
    font.pixelSize: Theme.fontSize.md
    color: Theme.c.text
    placeholderTextColor: Theme.c.textFaint
    selectionColor: Theme.c.selection
    selectedTextColor: Theme.c.text
    selectByMouse: true
    wrapMode: TextEdit.Wrap
    leftPadding: Theme.space.md
    rightPadding: Theme.space.md
    topPadding: Theme.space.sm
    bottomPadding: Theme.space.sm
    background: Rectangle {
        radius: Theme.radius.md
        color: Theme.c.surface2
        border.width: 1
        border.color: root.activeFocus ? Qt.rgba(Theme.c.accent.r, Theme.c.accent.g, Theme.c.accent.b, 0.7)
                    : root.hovered ? Theme.c.borderStrong : Theme.c.border
        Behavior on border.color { ColorAnimation { duration: Theme.motion.fast } }
        Rectangle {
            x: parent.radius; y: 1; width: parent.width - parent.radius * 2; height: 1
            color: Theme.c.shadow
            opacity: 0.35
        }
    }
}
