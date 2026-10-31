import QtQuick
import QtQuick.Controls.Basic
import THR10

// Вкладки с подчёркиванием: акцентная линия плавно переезжает под выбранную.
Item {
    id: root
    property var model: []
    property int currentIndex: 0
    signal activated(int index)

    implicitHeight: Theme.size.control
    implicitWidth: row.implicitWidth

    Rectangle {
        anchors.bottom: parent.bottom
        width: parent.width
        height: 1
        color: Theme.c.border
    }

    Row {
        id: row
        height: parent.height
        spacing: Theme.space.lg
        Repeater {
            id: rep
            model: root.model
            delegate: AbstractButton {
                id: tab
                required property int index
                required property string modelData
                readonly property bool selected: index === root.currentIndex
                height: row.height
                hoverEnabled: true
                focusPolicy: Qt.StrongFocus
                onClicked: { root.currentIndex = index; root.activated(index) }
                Accessible.role: Accessible.PageTab
                Accessible.name: modelData
                contentItem: Label {
                    text: tab.modelData
                    verticalAlignment: Text.AlignVCenter
                    font.pixelSize: Theme.fontSize.md
                    font.weight: tab.selected ? Theme.weight.semibold : Theme.weight.medium
                    color: tab.selected ? Theme.c.text : tab.hovered ? Theme.c.text : Theme.c.textMuted
                    Behavior on color { ColorAnimation { duration: Theme.motion.fast } }
                }
                background: Rectangle {
                    color: "transparent"
                    border.width: tab.visualFocus ? Theme.size.focusRing : 0
                    border.color: Theme.c.focus
                    radius: Theme.radius.sm
                }
                padding: 0
            }
        }
    }

    Rectangle {
        id: underline
        readonly property Item target: rep.count > root.currentIndex && root.currentIndex >= 0 ? rep.itemAt(root.currentIndex) : null
        anchors.bottom: parent.bottom
        height: 2
        radius: 1
        color: Theme.c.accent
        x: target ? target.x : 0
        width: target ? target.width : 0
        Behavior on x { NumberAnimation { duration: Theme.motion.normal; easing.type: Easing.OutCubic } }
        Behavior on width { NumberAnimation { duration: Theme.motion.normal; easing.type: Easing.OutCubic } }
    }
}
