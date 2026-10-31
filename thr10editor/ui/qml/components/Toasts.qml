import QtQuick
import QtQuick.Controls.Basic
import THR10

// Всплывающие сообщения внизу окна. kind: info | success | warning | error.
// Появляются снизу с лёгким подъёмом, исчезают затуханием.
Item {
    id: root
    width: parent ? parent.width : 0
    height: column.implicitHeight

    function show(kind, text) {
        // одинаковое сообщение подряд не дублируем
        if (model.count > 0 && model.get(model.count - 1).text === text)
            return
        model.append({ kind: kind, text: text })
        if (model.count > 3)
            model.remove(0)
    }

    ListModel { id: model }

    Column {
        id: column
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        spacing: Theme.space.sm

        move: Transition { NumberAnimation { properties: "y"; duration: Theme.motion.normal; easing.type: Easing.OutCubic } }

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
                radius: Theme.radius.lg
                color: Theme.c.surface3
                border.width: 1
                border.color: Theme.c.borderStrong
                opacity: 0
                transform: Translate { id: lift; y: 12 }
                Component.onCompleted: appear.start()
                ParallelAnimation {
                    id: appear
                    NumberAnimation { target: toast; property: "opacity"; to: 1; duration: Theme.motion.normal; easing.type: Easing.OutCubic }
                    NumberAnimation { target: lift; property: "y"; to: 0; duration: Theme.motion.slow; easing.type: Easing.OutCubic }
                }
                SequentialAnimation {
                    id: vanish
                    NumberAnimation { target: toast; property: "opacity"; to: 0; duration: Theme.motion.normal }
                    ScriptAction { script: if (toast.index >= 0 && toast.index < model.count) model.remove(toast.index) }
                }

                Rectangle {  // блик
                    x: parent.radius; y: 1; width: parent.width - parent.radius * 2; height: 1
                    color: Theme.c.highlight
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
                MouseArea { anchors.fill: parent; onClicked: vanish.start() }
                Timer {
                    running: true
                    interval: toast.kind === "error" ? 7000 : toast.kind === "warning" ? 5000 : 3000
                    onTriggered: vanish.start()
                }
            }
        }
    }
}
