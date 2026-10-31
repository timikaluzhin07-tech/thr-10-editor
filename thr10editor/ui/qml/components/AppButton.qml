import QtQuick
import QtQuick.Controls.Basic
import THR10

// Кнопка: variant = "primary" | "secondary" | "ghost" | "danger".
Button {
    id: root
    property string variant: "secondary"
    property string iconName: ""
    property string tip: ""
    property bool compact: false

    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    implicitHeight: compact ? Theme.size.control * 0.85 : Theme.size.control
    leftPadding: text ? (compact ? Theme.space.sm : Theme.space.md) : Theme.space.sm
    rightPadding: leftPadding
    topPadding: 0
    bottomPadding: 0
    font.pixelSize: compact ? Theme.fontSize.sm : Theme.fontSize.md
    font.weight: Theme.weight.semibold

    readonly property color fg: !enabled ? Theme.c.textFaint
                               : variant === "primary" ? Theme.c.accentText
                               : variant === "danger" ? Theme.c.danger
                               : Theme.c.text
    readonly property color bg: variant === "primary" ? (root.down ? Theme.c.accentHover : root.hovered ? Theme.c.accentHover : Theme.c.accent)
                               : variant === "ghost" ? (root.down ? Theme.c.surface3 : root.hovered ? Theme.c.surface2 : "transparent")
                               : (root.down ? Theme.c.surface3 : root.hovered ? Theme.c.surface3 : Theme.c.surface2)

    ToolTip.visible: tip !== "" && hovered
    ToolTip.delay: 600
    ToolTip.text: tip

    background: Rectangle {
        radius: Theme.radius.md
        color: root.checked && root.variant !== "primary" ? Theme.c.accentSoft : root.bg
        opacity: root.enabled ? 1 : 0.6
        border.width: root.variant === "secondary" || root.variant === "danger" ? 1 : 0
        border.color: root.checked ? Theme.c.accent : root.variant === "danger" ? Theme.c.danger : Theme.c.border
        Behavior on color { ColorAnimation { duration: Theme.motion.fast } }
        Rectangle {
            anchors.fill: parent
            anchors.margins: -Theme.size.focusRing * 2
            radius: Theme.radius.md + Theme.size.focusRing * 2
            color: "transparent"
            border.width: Theme.size.focusRing
            border.color: Theme.c.focus
            opacity: 0.6
            visible: root.visualFocus
        }
    }

    contentItem: Row {
        spacing: Theme.space.sm
        Icon {
            visible: root.iconName !== ""
            name: root.iconName
            color: root.checked ? Theme.c.accent : root.fg
            size: Theme.size.icon * (root.compact ? 0.85 : 1)
            anchors.verticalCenter: parent.verticalCenter
        }
        Label {
            visible: root.text !== ""
            text: root.text
            font: root.font
            color: root.checked && root.variant !== "primary" ? Theme.c.accent : root.fg
            anchors.verticalCenter: parent.verticalCenter
        }
    }
}
