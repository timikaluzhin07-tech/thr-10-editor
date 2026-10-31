import QtQuick
import QtQuick.Controls.Basic
import THR10

// Индикатор состояния связи с комбиком.
AbstractButton {
    id: root
    property string status: Backend.connStatus
    property string label: Backend.connText
    readonly property color dotColor: status === "connected" ? (Backend.isDemo ? Theme.c.info : Theme.c.success)
                                    : status === "connecting" ? Theme.c.warning
                                    : status === "no_response" ? Theme.c.warning
                                    : status === "error" ? Theme.c.danger
                                    : Theme.c.textFaint

    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    implicitHeight: Theme.size.control
    implicitWidth: Math.min(row.implicitWidth + Theme.space.md * 2, Theme.space.xxxl * 7)
    Accessible.role: Accessible.Button
    Accessible.name: "Связь: " + label

    ToolTip.visible: hovered
    ToolTip.delay: 400
    ToolTip.text: label + "\nНажмите, чтобы выбрать порт"

    background: Rectangle {
        radius: Theme.radius.pill
        color: root.down ? Theme.c.surface3 : root.hovered ? Theme.c.surface2 : Theme.c.surface
        border.width: 1
        border.color: Theme.c.border
        Behavior on color { ColorAnimation { duration: Theme.motion.fast } }
        Rectangle {
            anchors.fill: parent
            anchors.margins: -Theme.size.focusRing * 2
            radius: Theme.radius.pill
            color: "transparent"
            border.width: Theme.size.focusRing
            border.color: Theme.c.focus
            opacity: 0.6
            visible: root.visualFocus
        }
    }

    contentItem: Item {
        Row {
            id: row
            anchors.centerIn: parent
            width: Math.min(implicitWidth, root.width - Theme.space.md * 2)
            spacing: Theme.space.sm
            Item {
                width: Theme.space.sm * 1.25; height: width
                anchors.verticalCenter: parent.verticalCenter
                Rectangle {
                    id: halo
                    anchors.centerIn: parent
                    width: parent.width; height: width; radius: width / 2
                    color: root.dotColor
                    opacity: 0
                    SequentialAnimation on opacity {
                        running: root.status === "connecting" || (root.status === "connected" && !Backend.isDemo)
                        loops: Animation.Infinite
                        NumberAnimation { from: 0.5; to: 0; duration: 1400; easing.type: Easing.OutQuad }
                    }
                    SequentialAnimation on scale {
                        running: halo.visible
                        loops: Animation.Infinite
                        NumberAnimation { from: 1; to: 2.4; duration: 1400; easing.type: Easing.OutQuad }
                    }
                }
                Rectangle {
                    anchors.fill: parent
                    radius: width / 2
                    color: root.dotColor
                    Behavior on color { ColorAnimation { duration: Theme.motion.normal } }
                }
            }
            Label {
                text: root.label
                width: Math.min(implicitWidth, row.width - Theme.space.sm * 2.25)
                elide: Text.ElideRight
                font.pixelSize: Theme.fontSize.sm
                font.weight: Theme.weight.medium
                color: Theme.c.text
                anchors.verticalCenter: parent.verticalCenter
            }
        }
    }
}
