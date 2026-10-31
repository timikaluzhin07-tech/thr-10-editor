import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Basic
import THR10
import "../components"

// Боковая панель с вкладками. Вкладки задаются списком {title, component}.
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
        anchors.rightMargin: Theme.space.md + 1
        spacing: Theme.space.md

        Segmented {
            id: tabs_
            Layout.fillWidth: true
            small: true
            visible: root.tabs.length > 1
            model: root.tabs.map(t => t.title)
            onActivated: (i) => currentIndex = i
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: tabs_.currentIndex
            Repeater {
                model: root.tabs
                delegate: Loader {
                    required property var modelData
                    sourceComponent: modelData.component
                }
            }
        }
    }
}
