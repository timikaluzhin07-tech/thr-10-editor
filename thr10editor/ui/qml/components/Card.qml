import QtQuick
import QtQuick.Layouts
import THR10

// Карточка-поверхность. Содержимое раскладывается вертикально.
Rectangle {
    id: root
    default property alias content: col.data
    property real padding: Theme.space.lg
    property alias spacing: col.spacing

    radius: Theme.radius.lg
    color: Theme.c.surface
    border.width: 1
    border.color: Theme.c.border
    implicitHeight: col.implicitHeight + padding * 2
    implicitWidth: col.implicitWidth + padding * 2
    Behavior on color { ColorAnimation { duration: Theme.motion.theme } }
    Behavior on border.color { ColorAnimation { duration: Theme.motion.theme } }

    ColumnLayout {
        id: col
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: root.padding
        spacing: Theme.space.md
    }
}
