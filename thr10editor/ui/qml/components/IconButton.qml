import QtQuick
import QtQuick.Controls.Basic
import THR10

// Квадратная кнопка-иконка с подсказкой и горячей клавишей.
AbstractButton {
    id: root
    property string iconName: ""
    property string tip: ""
    property string shortcutHint: ""
    property color iconColor: Theme.c.textMuted
    property real boxSize: Theme.size.control

    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    implicitWidth: boxSize
    implicitHeight: boxSize
    Accessible.role: Accessible.Button
    Accessible.name: tip

    ToolTip.visible: hovered && tip !== ""
    ToolTip.delay: 500
    ToolTip.text: shortcutHint ? tip + "   " + shortcutHint : tip

    background: Rectangle {
        radius: Theme.radius.md
        color: root.checked ? Theme.c.accentSoft : root.down ? Theme.c.surface3 : root.hovered ? Theme.c.surface2 : "transparent"
        border.width: root.checked ? 1 : 0
        border.color: Qt.rgba(Theme.c.accent.r, Theme.c.accent.g, Theme.c.accent.b, 0.45)
        Behavior on color { ColorAnimation { duration: Theme.motion.fast } }
        Rectangle {
            anchors.fill: parent
            anchors.margins: -Theme.size.focusRing
            radius: Theme.radius.md + Theme.size.focusRing
            color: "transparent"
            border.width: Theme.size.focusRing
            border.color: Theme.c.focus
            opacity: 0.55
            visible: root.visualFocus
        }
    }
    contentItem: Item {
        Icon {
            anchors.centerIn: parent
            name: root.iconName
            size: Theme.size.icon
            color: !root.enabled ? Theme.c.textFaint : root.checked ? Theme.c.accent : root.hovered ? Theme.c.text : root.iconColor
            opacity: root.enabled ? 1 : 0.6
            Behavior on color { ColorAnimation { duration: Theme.motion.fast } }
        }
    }
}
