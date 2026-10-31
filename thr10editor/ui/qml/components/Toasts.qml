import QtQuick
import QtQuick.Controls.Basic
import THR10

// Всплывающие сообщения внизу окна. kind: info | success | warning | error.
Item {
    id: root
    width: parent ? parent.width : 0
    height: column.implicitHeight

    function show(kind, text) {
        model.append({ kind: kind, text: text, uid: Date.now() + Math.random() })
        if (model.count > 4)
            model.remove(0)
    }

    ListModel { id: model }

    Column {
        id: column
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        spacing: Theme.space.sm

        Repeater {
            model: model
            delegate: Rectangle {
                id: toast
                required property int index
                required property string kind
                required property string text
                readonly property color tone: kind === "error" ? Theme.c.danger
                                             : kind === "warning" ? Theme.c.warning
                                             : kind === "success" ? Theme.c.success
                                             : Theme.c.info
                width: Math.min(root.width - Theme.space.xl * 2, msg.implicitWidth + Theme.space.lg * 2 + Theme.size.icon + Theme.space.sm)
                height: Math.max(Theme.size.controlLarge, msg.implicitHeight + Theme.space.md * 2)
                anchors.horizontalCenter: parent.horizontalCenter
                radius: Theme.radius.md
                color: Theme.c.surface3
                border.width: 1
                border.color: Theme.c.borderStrong
                opacity: 0
                Component.onCompleted: appear.start()
                NumberAnimation { id: appear; target: toast; property: "opacity"; from: 0; to: 1; duration: Theme.motion.normal }

                Rectangle {
                    width: 3; radius: 1.5
                    anchors.left: parent.left; anchors.top: parent.top; anchors.bottom: parent.bottom
                    anchors.margins: Theme.space.sm
                    color: toast.tone
                }
                Row {
                    anchors.fill: parent
                    anchors.leftMargin: Theme.space.lg
                    anchors.rightMargin: Theme.space.lg
                    spacing: Theme.space.sm
                    Icon {
                        anchors.verticalCenter: parent.verticalCenter
                        name: toast.kind === "error" || toast.kind === "warning" ? "warning" : toast.kind === "success" ? "check" : "info"
                        color: toast.tone
                    }
                    Label {
                        id: msg
                        anchors.verticalCenter: parent.verticalCenter
                        width: Math.min(implicitWidth, root.width - Theme.space.xl * 4 - Theme.size.icon)
                        text: toast.text
                        wrapMode: Text.Wrap
                        color: Theme.c.text
                        font.pixelSize: Theme.fontSize.md
                    }
                }
                MouseArea { anchors.fill: parent; onClicked: model.remove(toast.index) }
                Timer {
                    running: true
                    interval: toast.kind === "error" ? 7000 : toast.kind === "warning" ? 5000 : 3200
                    onTriggered: if (toast.index >= 0 && toast.index < model.count) model.remove(toast.index)
                }
            }
        }
    }
}
