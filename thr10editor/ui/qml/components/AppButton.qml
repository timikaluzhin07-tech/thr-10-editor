import QtQuick
import QtQuick.Controls.Basic
import THR10

// Кнопка: variant = "primary" | "secondary" | "ghost" | "danger".
// primary — одна на экран/панель; secondary — приподнятая поверхность.
Button {
    id: root
    property string variant: "secondary"
    property string iconName: ""
    property string tip: ""
    property bool compact: false

    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    implicitHeight: compact ? Theme.size.control * 0.86 : Theme.size.control
    leftPadding: text ? (compact ? Theme.space.sm : Theme.space.md) : Theme.space.sm
    rightPadding: leftPadding
    topPadding: 0
    bottomPadding: 0
    font.pixelSize: compact ? Theme.fontSize.sm : Theme.fontSize.md
    font.weight: Theme.weight.semibold

    readonly property bool primary: variant === "primary"
    readonly property color fg: !enabled ? Theme.c.textFaint
                               : primary ? Theme.c.accentText
                               : variant === "danger" ? Theme.c.danger
                               : checked ? Theme.c.accent
                               : Theme.c.text

    ToolTip.visible: tip !== "" && hovered
    ToolTip.delay: 600
    ToolTip.text: tip

    background: Rectangle {
        radius: Theme.radius.md
        opacity: root.enabled ? 1 : 0.55
        border.width: root.variant === "ghost" ? 0 : 1
        border.color: root.primary ? Qt.darker(Theme.c.accent, 1.25)
                    : root.checked ? Theme.c.accent
                    : root.variant === "danger" ? Theme.c.danger
                    : root.hovered ? Theme.c.borderStrong : Theme.c.border
        gradient: Gradient {
            GradientStop {
                position: 0.0
                color: root.primary ? (root.hovered ? Theme.c.accentHover : Theme.c.accent)
                     : root.variant === "ghost" ? (root.down ? Theme.c.surface3 : root.hovered ? Theme.c.surface2 : "transparent")
                     : (root.down ? Theme.c.surface2 : Theme.c.surface3)
            }
            GradientStop {
                position: 1.0
                color: root.primary ? Qt.darker(root.hovered ? Theme.c.accentHover : Theme.c.accent, 1.12)
                     : root.variant === "ghost" ? (root.down ? Theme.c.surface3 : root.hovered ? Theme.c.surface2 : "transparent")
                     : (root.down ? Theme.c.surface2 : root.hovered ? Theme.c.surface3 : Theme.c.surface2)
            }
        }
        Behavior on border.color { ColorAnimation { duration: Theme.motion.fast } }
        // блик сверху
        Rectangle {
            visible: root.variant !== "ghost"
            x: parent.radius; y: 1
            width: parent.width - parent.radius * 2; height: 1
            color: Theme.c.highlight
            opacity: root.primary ? 0.6 : 1
        }
        Rectangle {
            anchors.fill: parent
            anchors.margins: -Theme.size.focusRing * 2
            radius: Theme.radius.md + Theme.size.focusRing * 2
            color: "transparent"
            border.width: Theme.size.focusRing
            border.color: Theme.c.focus
            opacity: 0.55
            visible: root.visualFocus
        }
    }

    contentItem: Item {
        implicitWidth: contentRow.implicitWidth
        implicitHeight: contentRow.implicitHeight
        Row {
            id: contentRow
            anchors.centerIn: parent
            spacing: Theme.space.sm
            Icon {
                visible: root.iconName !== ""
                name: root.iconName
                color: root.fg
                size: Theme.size.icon * (root.compact ? 0.85 : 0.95)
                anchors.verticalCenter: parent.verticalCenter
            }
            Label {
                visible: root.text !== ""
                text: root.text
                font: root.font
                color: root.fg
                anchors.verticalCenter: parent.verticalCenter
            }
        }
    }
}
