import QtQuick
import QtQuick.Controls.Basic
import THR10

TextField {
    id: root
    property string iconName: ""
    implicitHeight: Theme.size.control
    leftPadding: iconName ? Theme.size.icon + Theme.space.md : Theme.space.md
    rightPadding: Theme.space.md
    font.pixelSize: Theme.fontSize.md
    color: Theme.c.text
    placeholderTextColor: Theme.c.textFaint
    selectionColor: Theme.c.selection
    selectedTextColor: Theme.c.text
    selectByMouse: true
    background: Rectangle {
        radius: Theme.radius.md
        color: Theme.c.surface2
        border.width: 1
        border.color: root.activeFocus ? Theme.c.accent : root.hovered ? Theme.c.borderStrong : Theme.c.border
        Behavior on border.color { ColorAnimation { duration: Theme.motion.fast } }
        Icon {
            visible: root.iconName !== ""
            name: root.iconName
            color: Theme.c.textFaint
            size: Theme.size.icon * 0.9
            anchors.verticalCenter: parent.verticalCenter
            x: Theme.space.sm
        }
    }
}
