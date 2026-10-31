import QtQuick
import QtQuick.Controls.Basic
import THR10

// Кнопка питания блока эффектов: значок с «LED»-подсветкой, мягкое свечение
// при включении.
AbstractButton {
    id: root
    property color accent: Theme.c.accent
    checkable: true
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    implicitWidth: Theme.size.control * 0.86
    implicitHeight: implicitWidth
    Accessible.role: Accessible.CheckBox
    Accessible.checked: checked
    Accessible.name: "Вкл/выкл блока"

    ToolTip.visible: hovered
    ToolTip.delay: 600
    ToolTip.text: checked ? "Выключить блок" : "Включить блок"

    background: Item {
        // свечение
        Rectangle {
            anchors.centerIn: parent
            width: parent.width * 1.55
            height: width
            radius: width / 2
            color: Theme.c.glow
            opacity: root.checked ? 0.55 : 0
            scale: root.checked ? 1 : 0.6
            Behavior on opacity { NumberAnimation { duration: Theme.motion.slow; easing.type: Easing.OutCubic } }
            Behavior on scale { NumberAnimation { duration: Theme.motion.slow; easing.type: Easing.OutBack } }
        }
        Rectangle {
            anchors.fill: parent
            radius: width / 2
            gradient: Gradient {
                GradientStop { position: 0.0; color: root.down ? Theme.c.surface2 : Theme.c.surface3 }
                GradientStop { position: 1.0; color: Theme.c.surface2 }
            }
            border.width: 1
            border.color: root.checked ? root.accent : root.hovered ? Theme.c.borderStrong : Theme.c.border
            Behavior on border.color { ColorAnimation { duration: Theme.motion.normal } }
        }
        Rectangle {
            anchors.fill: parent
            anchors.margins: -Theme.size.focusRing * 2
            radius: width / 2
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
            name: "power"
            size: root.width * 0.52
            strokeWidth: 2.4
            color: root.checked ? root.accent : root.hovered ? Theme.c.textMuted : Theme.c.textFaint
            Behavior on color { ColorAnimation { duration: Theme.motion.normal } }
        }
    }
    padding: 0
}
