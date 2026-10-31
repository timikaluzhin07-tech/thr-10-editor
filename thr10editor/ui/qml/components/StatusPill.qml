import QtQuick
import QtQuick.Controls.Basic
import THR10

// Индикатор связи с комбиком: «LED» с мягким свечением + текст.
AbstractButton {
    id: root
    property string status: Backend.connStatus
    property string label: Backend.connText
    readonly property color ledColor: status === "connected" ? (Backend.isDemo ? Theme.c.info : Theme.c.success)
                                    : status === "connecting" || status === "no_response" ? Theme.c.warning
                                    : status === "error" ? Theme.c.danger
                                    : Theme.c.textFaint
    readonly property bool live: status === "connected" || status === "connecting"
    readonly property real ledSize: Theme.space.sm

    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    implicitHeight: Theme.size.control
    implicitWidth: Math.min(text_.implicitWidth + ledSize + Theme.space.sm + Theme.space.md * 2, Theme.space.xxxl * 7)
    Accessible.role: Accessible.Button
    Accessible.name: "Связь: " + label

    ToolTip.visible: hovered
    ToolTip.delay: 400
    ToolTip.text: label + "\nНажмите, чтобы выбрать порт (Ctrl+K)"

    background: Rectangle {
        radius: Theme.radius.md
        color: root.down ? Theme.c.surface3 : root.hovered ? Theme.c.surface2 : "transparent"
        border.width: 1
        border.color: root.hovered ? Theme.c.borderStrong : Theme.c.border
        Behavior on color { ColorAnimation { duration: Theme.motion.fast } }
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
        Row {
            anchors.centerIn: parent
            spacing: Theme.space.sm
            Item {
                width: root.ledSize; height: width
                anchors.verticalCenter: parent.verticalCenter
                // мягкое «дыхание» свечения, пока связь жива
                Rectangle {
                    anchors.centerIn: parent
                    width: parent.width * 2.6; height: width; radius: width / 2
                    color: root.ledColor
                    opacity: 0
                    SequentialAnimation on opacity {
                        running: root.live
                        loops: Animation.Infinite
                        NumberAnimation { from: 0.0; to: 0.28; duration: 1300; easing.type: Easing.InOutSine }
                        NumberAnimation { from: 0.28; to: 0.0; duration: 1300; easing.type: Easing.InOutSine }
                    }
                }
                Rectangle {
                    anchors.fill: parent
                    radius: width / 2
                    color: root.ledColor
                    border.width: 1
                    border.color: Qt.darker(root.ledColor, 1.4)
                    Behavior on color { ColorAnimation { duration: Theme.motion.normal } }
                    Rectangle {  // блик на «LED»
                        width: parent.width * 0.4; height: width; radius: width / 2
                        x: parent.width * 0.2; y: parent.height * 0.15
                        color: "#FFFFFF"
                        opacity: 0.45
                    }
                }
            }
            Label {
                id: text_
                text: root.label
                width: Math.max(0, Math.min(implicitWidth, root.width - Theme.space.md * 2 - root.ledSize - Theme.space.sm))
                elide: Text.ElideRight
                font.pixelSize: Theme.fontSize.sm
                font.weight: Theme.weight.medium
                color: Theme.c.text
                anchors.verticalCenter: parent.verticalCenter
            }
        }
    }
}
