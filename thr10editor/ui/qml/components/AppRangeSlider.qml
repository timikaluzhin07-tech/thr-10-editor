import QtQuick
import QtQuick.Controls.Basic
import THR10

RangeSlider {
    id: root
    property color accent: Theme.c.accent
    implicitHeight: Theme.size.control * 0.7
    from: 0
    to: 1
    hoverEnabled: true

    component Handle: Rectangle {
        property bool active: false
        width: Theme.space.md; height: width; radius: width / 2
        gradient: Gradient {
            GradientStop { position: 0.0; color: Theme.c.knobFaceTop }
            GradientStop { position: 1.0; color: Theme.c.knobFaceBottom }
        }
        border.width: 1
        border.color: active ? root.accent : Theme.c.textFaint
        scale: active ? 1.12 : 1
        Behavior on scale { NumberAnimation { duration: Theme.motion.fast } }
    }

    background: Rectangle {
        x: root.leftPadding
        y: root.topPadding + root.availableHeight / 2 - height / 2
        width: root.availableWidth
        height: 3
        radius: height / 2
        color: Theme.c.knobTrack
        Rectangle {
            x: root.first.visualPosition * parent.width
            width: (root.second.visualPosition - root.first.visualPosition) * parent.width
            height: parent.height
            radius: parent.radius
            color: root.accent
            opacity: root.enabled ? 0.9 : 0.35
        }
    }
    first.handle: Handle {
        x: root.leftPadding + root.first.visualPosition * (root.availableWidth - width)
        y: root.topPadding + root.availableHeight / 2 - height / 2
        active: root.first.pressed || root.first.hovered
        opacity: root.enabled ? 1 : 0.5
    }
    second.handle: Handle {
        x: root.leftPadding + root.second.visualPosition * (root.availableWidth - width)
        y: root.topPadding + root.availableHeight / 2 - height / 2
        active: root.second.pressed || root.second.hovered
        opacity: root.enabled ? 1 : 0.5
    }
}
