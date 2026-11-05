import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Basic
import THR10
import "../components"

// Боковая панель с вкладками. Вкладки задаются списком {title, component}.
// При смене вкладки содержимое мягко проявляется.
Rectangle {
    id: root
    property var tabs: []
    property alias currentIndex: tabs_.currentIndex
    color: Theme.c.surface
    Behavior on color { ColorAnimation { duration: Theme.motion.theme } }
    Rectangle { anchors.right: parent.right; width: 1; height: parent.height; color: Theme.c.border }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.space.md
        anchors.topMargin: Theme.space.sm
        anchors.rightMargin: Theme.space.md + 1
        spacing: Theme.space.md

        TabStrip {
            id: tabs_
            Layout.fillWidth: true
            visible: root.tabs.length > 1
            model: root.tabs.map(t => t.title)
            onCurrentIndexChanged: switchAnim.restart()
        }

        StackLayout {
            id: stack
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: tabs_.currentIndex
            transform: Translate { id: stackShift }
            Repeater {
                model: root.tabs
                delegate: Loader {
                    required property var modelData
                    sourceComponent: modelData.component
                }
            }
        }
    }

    ParallelAnimation {
        id: switchAnim
        NumberAnimation { target: stack; property: "opacity"; from: 0; to: 1; duration: Theme.motion.normal; easing.type: Easing.OutCubic }
        NumberAnimation { target: stackShift; property: "x"; from: -6; to: 0; duration: Theme.motion.slow; easing.type: Easing.OutCubic }
    }
}
