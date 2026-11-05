import QtQuick
import QtQuick.Controls.Basic
import THR10

// Переключатель вкл/выкл (настройки, опции): сдержанная дорожка, объёмный бегунок.
AbstractButton {
    id: root
    property color accent: Theme.c.accentFill
    checkable: true
    focusPolicy: Qt.StrongFocus
    implicitWidth: Theme.size.control * 1.1
    implicitHeight: Theme.size.control * 0.6
    hoverEnabled: true

    Accessible.role: Accessible.CheckBox
    Accessible.checked: checked

    background: Rectangle {
        radius: height / 2
        color: root.checked ? Qt.rgba(root.accent.r, root.accent.g, root.accent.b, 0.85) : Theme.c.surface3
        border.width: 1
        border.color: root.checked ? Qt.darker(root.accent, 1.2) : root.hovered ? Theme.c.borderStrong : Theme.c.border
        Behavior on color { ColorAnimation { duration: Theme.motion.normal } }
        Behavior on border.color { ColorAnimation { duration: Theme.motion.normal } }
        Rectangle {
            anchors.fill: parent
            anchors.margins: -Theme.size.focusRing * 2
            radius: height / 2
            color: "transparent"
            border.width: Theme.size.focusRing
            border.color: Theme.c.focus
            opacity: 0.55
            visible: root.visualFocus
        }
    }

    contentItem: Item {
        Rectangle {
            width: root.height - 4
            height: width
            radius: width / 2
            y: 2
            x: root.checked ? root.width - width - 2 : 2
            gradient: Gradient {
                GradientStop { position: 0.0; color: Theme.c.knobFaceTop }
                GradientStop { position: 1.0; color: Theme.c.knobFaceBottom }
            }
            border.width: 1
            border.color: Theme.c.knobRim
            Behavior on x { NumberAnimation { duration: Theme.motion.normal; easing.type: Easing.OutCubic } }
        }
    }
    padding: 0
}
