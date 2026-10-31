import QtQuick
import QtQuick.Controls.Basic
import THR10

Slider {
    id: root
    property color accent: Theme.c.accent
    implicitHeight: Theme.size.control * 0.8
    hoverEnabled: true

    background: Rectangle {
        x: root.leftPadding
        y: root.topPadding + root.availableHeight / 2 - height / 2
        width: root.availableWidth
        height: Theme.space.xs
        radius: height / 2
        color: Theme.c.knobTrack
        Rectangle {
            width: root.visualPosition * parent.width
            height: parent.height
            radius: parent.radius
            color: root.accent
        }
    }
    handle: Rectangle {
        x: root.leftPadding + root.visualPosition * (root.availableWidth - width)
        y: root.topPadding + root.availableHeight / 2 - height / 2
        width: Theme.space.lg; height: width; radius: width / 2
        color: root.pressed ? root.accent : Theme.c.knobFace
        border.width: 2
        border.color: root.accent
        Behavior on color { ColorAnimation { duration: Theme.motion.fast } }
    }
}
