import QtQuick
import QtQuick.Controls.Basic
import THR10

// Переключатель вкл/выкл в стиле дизайн-системы.
AbstractButton {
    id: root
    property color accent: Theme.c.accent
    checkable: true
    focusPolicy: Qt.StrongFocus
    implicitWidth: Theme.size.control * 1.15
    implicitHeight: Theme.size.control * 0.62
    hoverEnabled: true

    Accessible.role: Accessible.CheckBox
    Accessible.checked: checked

    background: Rectangle {
        radius: height / 2
        color: root.checked ? root.accent : (root.hovered ? Theme.c.surface3 : Theme.c.surface2)
        border.width: root.checked ? 0 : 1
        border.color: Theme.c.borderStrong
        Behavior on color { ColorAnimation { duration: Theme.motion.fast } }

        Rectangle {
            anchors.fill: parent
            anchors.margins: -Theme.size.focusRing * 2
            radius: height / 2
            color: "transparent"
            border.width: Theme.size.focusRing
            border.color: Theme.c.focus
            opacity: 0.6
            visible: root.visualFocus
        }
    }

    contentItem: Item {
        Rectangle {
            id: thumb
            width: root.height - Theme.space.xs * 1.5
            height: width
            radius: width / 2
            y: (root.height - height) / 2
            x: root.checked ? root.width - width - Theme.space.xs * 0.75 : Theme.space.xs * 0.75
            color: root.checked ? Theme.c.accentText : Theme.c.textMuted
            Behavior on x { NumberAnimation { duration: Theme.motion.normal; easing.type: Easing.OutCubic } }
            Behavior on color { ColorAnimation { duration: Theme.motion.fast } }
        }
    }
    padding: 0
}
