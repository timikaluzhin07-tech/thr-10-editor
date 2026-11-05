import QtQuick
import QtQuick.Controls.Basic
import THR10

// Числовое поле со стрелками в стиле дизайн-системы.
SpinBox {
    id: root
    editable: true
    implicitHeight: Theme.size.control
    implicitWidth: Theme.size.control * 3.6
    font.pixelSize: Theme.fontSize.md
    hoverEnabled: true

    contentItem: TextInput {
        text: root.displayText
        font: root.font
        color: Theme.c.text
        selectionColor: Theme.c.selection
        horizontalAlignment: Qt.AlignHCenter
        verticalAlignment: Qt.AlignVCenter
        readOnly: !root.editable
        validator: root.validator
        inputMethodHints: Qt.ImhFormattedNumbersOnly
        selectByMouse: true
    }

    component StepButton: Rectangle {
        property bool pressed: false
        property bool hovered: false
        property string icon: ""
        implicitWidth: root.height
        implicitHeight: root.height
        color: pressed ? Theme.c.surface3 : hovered ? Theme.c.surface2 : "transparent"
        radius: Theme.radius.md
        Icon { anchors.centerIn: parent; name: parent.icon; size: Theme.size.icon * 0.85; color: Theme.c.textMuted }
    }

    up.indicator: StepButton {
        x: root.width - width
        height: root.height
        pressed: root.up.pressed
        hovered: root.up.hovered
        icon: "plus"
    }
    down.indicator: StepButton {
        x: 0
        height: root.height
        pressed: root.down.pressed
        hovered: root.down.hovered
        icon: "minus"
    }

    background: Rectangle {
        radius: Theme.radius.md
        color: Theme.c.surface2
        border.width: 1
        border.color: root.activeFocus ? Qt.rgba(Theme.c.accent.r, Theme.c.accent.g, Theme.c.accent.b, 0.7)
                    : root.hovered ? Theme.c.borderStrong : Theme.c.border
    }
}
