import QtQuick
import QtQuick.Controls.Basic
import THR10

// Выбор одного варианта из нескольких (модель усилителя, тип эффекта).
// Переносится на новую строку, если не помещается.
Flow {
    id: root
    property var model: []
    property int currentIndex: 0
    property color accent: Theme.c.accent
    property bool small: false
    signal activated(int index)

    spacing: Theme.space.xs

    Repeater {
        model: root.model
        delegate: AbstractButton {
            id: opt
            required property int index
            required property string modelData
            readonly property bool selected: index === root.currentIndex
            focusPolicy: Qt.StrongFocus
            hoverEnabled: true
            implicitHeight: root.small ? Theme.size.control * 0.82 : Theme.size.control
            implicitWidth: lbl.implicitWidth + (root.small ? Theme.space.md : Theme.space.lg) * 2
            onClicked: root.activated(index)
            Accessible.role: Accessible.RadioButton
            Accessible.name: modelData
            Accessible.checked: selected

            background: Rectangle {
                radius: Theme.radius.pill
                color: "transparent"
                border.width: 1
                border.color: opt.selected ? root.accent : (opt.hovered ? Theme.c.borderStrong : Theme.c.border)
                Rectangle {
                    anchors.fill: parent
                    radius: parent.radius
                    color: root.accent
                    opacity: opt.selected ? 0.16 : (opt.hovered ? 0.06 : 0)
                    Behavior on opacity { NumberAnimation { duration: Theme.motion.fast } }
                }
                Behavior on border.color { ColorAnimation { duration: Theme.motion.fast } }
                Rectangle {
                    anchors.fill: parent
                    anchors.margins: -Theme.size.focusRing * 2
                    radius: Theme.radius.pill
                    color: "transparent"
                    border.width: Theme.size.focusRing
                    border.color: Theme.c.focus
                    opacity: 0.6
                    visible: opt.visualFocus
                }
            }
            contentItem: Label {
                id: lbl
                text: opt.modelData
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                font.pixelSize: root.small ? Theme.fontSize.sm : Theme.fontSize.md
                font.weight: opt.selected ? Theme.weight.semibold : Theme.weight.medium
                color: opt.selected ? root.accent : Theme.c.textMuted
                Behavior on color { ColorAnimation { duration: Theme.motion.fast } }
            }
        }
    }
}
