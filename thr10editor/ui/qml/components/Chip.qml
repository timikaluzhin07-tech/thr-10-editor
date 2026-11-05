import QtQuick
import QtQuick.Controls.Basic
import THR10

// Чип: тег, фильтр. checkable — выбираемый.
AbstractButton {
    id: root
    property color accent: Theme.c.accent
    property bool removable: false
    signal removeClicked()
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    implicitHeight: Theme.size.control * 0.72
    implicitWidth: row.implicitWidth + Theme.space.sm * 2
    font.pixelSize: Theme.fontSize.sm

    background: Rectangle {
        radius: Theme.radius.sm
        color: root.checked ? Theme.c.accentSoft : root.hovered ? Theme.c.surface3 : Theme.c.surface2
        border.width: 1
        border.color: root.checked ? Qt.rgba(root.accent.r, root.accent.g, root.accent.b, 0.5) : Theme.c.border
        Behavior on color { ColorAnimation { duration: Theme.motion.fast } }
        Rectangle {
            anchors.fill: parent
            anchors.margins: -Theme.size.focusRing * 2
            radius: Theme.radius.sm + Theme.size.focusRing * 2
            color: "transparent"
            border.width: Theme.size.focusRing
            border.color: Theme.c.focus
            opacity: 0.55
            visible: root.visualFocus
        }
    }
    contentItem: Item {
        Row {
            id: row
            anchors.centerIn: parent
            spacing: Theme.space.xs
            Label {
                text: root.text
                font: root.font
                color: root.checked ? root.accent : Theme.c.textMuted
                anchors.verticalCenter: parent.verticalCenter
            }
            Icon {
                visible: root.removable
                name: "close"
                size: Theme.size.icon * 0.7
                color: Theme.c.textFaint
                anchors.verticalCenter: parent.verticalCenter
                MouseArea { anchors.fill: parent; anchors.margins: -4; onClicked: root.removeClicked() }
            }
        }
    }
}
