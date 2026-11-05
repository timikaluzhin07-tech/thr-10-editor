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
        height: 3
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
        width: Theme.space.md * 1.15; height: width; radius: width / 2
        gradient: Gradient {
            GradientStop { position: 0.0; color: Theme.c.knobFaceTop }
            GradientStop { position: 1.0; color: Theme.c.knobFaceBottom }
        }
        border.width: 1
        border.color: root.pressed || root.hovered ? root.accent : Theme.c.textFaint
        scale: root.pressed ? 1.12 : 1
        Behavior on scale { NumberAnimation { duration: Theme.motion.fast } }
        Behavior on border.color { ColorAnimation { duration: Theme.motion.fast } }
    }
}
