import QtQuick
import QtQuick.Controls.Basic
import THR10

RangeSlider {
    id: root
    property color accent: Theme.c.accent
    implicitHeight: Theme.size.control * 0.7
    from: 0
    to: 1

    background: Rectangle {
        x: root.leftPadding
        y: root.topPadding + root.availableHeight / 2 - height / 2
        width: root.availableWidth
        height: Theme.space.xs
        radius: height / 2
        color: Theme.c.knobTrack
        Rectangle {
            x: root.first.visualPosition * parent.width
            width: (root.second.visualPosition - root.first.visualPosition) * parent.width
            height: parent.height
            radius: parent.radius
            color: root.accent
            opacity: root.enabled ? 1 : 0.4
        }
    }
    first.handle: Rectangle {
        x: root.leftPadding + root.first.visualPosition * (root.availableWidth - width)
        y: root.topPadding + root.availableHeight / 2 - height / 2
        width: Theme.space.md * 1.1; height: width; radius: width / 2
        color: Theme.c.knobFace
        border.width: 2
        border.color: root.accent
    }
    second.handle: Rectangle {
        x: root.leftPadding + root.second.visualPosition * (root.availableWidth - width)
        y: root.topPadding + root.availableHeight / 2 - height / 2
        width: Theme.space.md * 1.1; height: width; radius: width / 2
        color: Theme.c.knobFace
        border.width: 2
        border.color: root.accent
    }
}
