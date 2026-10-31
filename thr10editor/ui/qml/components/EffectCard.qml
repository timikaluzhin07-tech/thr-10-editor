import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Basic
import THR10

// Карточка блока эффектов: метка цвета, заголовок, переключатель, тип, ручки.
Card {
    id: root
    property QtObject group: null
    property real knobSize: Theme.size.knobSmall
    property Component headerComponent: null
    readonly property color accent: group ? Theme.c[group.accent] : Theme.c.accent

    signal knobContext(QtObject param, Item knob, real x, real y)

    spacing: Theme.space.md

    RowLayout {
        Layout.fillWidth: true
        spacing: Theme.space.sm

        Rectangle {
            width: Theme.space.sm; height: width; radius: width / 2
            color: root.accent
            opacity: root.group && root.group.enabled ? 1 : 0.35
            Behavior on opacity { NumberAnimation { duration: Theme.motion.fast } }
        }
        Label {
            text: root.group ? root.group.title : ""
            font.pixelSize: Theme.fontSize.lg
            font.weight: Theme.weight.semibold
            color: Theme.c.text
            Layout.fillWidth: true
            elide: Text.ElideRight
        }
        Loader {
            active: root.headerComponent !== null
            sourceComponent: root.headerComponent
            Layout.alignment: Qt.AlignVCenter
        }
        ToggleSwitch {
            visible: root.group && root.group.hasSwitch
            accent: root.accent
            checked: root.group ? root.group.enabled : false
            onToggled: root.group.setEnabled(checked)
            ToolTip.visible: hovered
            ToolTip.delay: 600
            ToolTip.text: checked ? "Выключить блок" : "Включить блок"
        }
    }

    Segmented {
        visible: root.group && root.group.typeOptions.length > 0
        Layout.fillWidth: true
        small: true
        accent: root.accent
        model: root.group ? root.group.typeOptions : []
        currentIndex: root.group ? root.group.typeIndex : 0
        onActivated: (i) => root.group.setType(i)
    }

    Flow {
        id: knobs
        Layout.fillWidth: true
        spacing: Theme.space.md
        opacity: root.group && root.group.hasSwitch && !root.group.enabled ? 0.55 : 1
        Behavior on opacity { NumberAnimation { duration: Theme.motion.normal } }

        Repeater {
            model: root.group ? root.group.knobKeys : []
            delegate: Knob {
                required property string modelData
                param: Backend.param(modelData)
                accent: root.accent
                diameter: root.knobSize
                onContextRequested: (p, x, y) => root.knobContext(p, this, x, y)
            }
        }
    }

    Repeater {
        model: root.group ? root.group.choiceKeys : []
        delegate: RowLayout {
            required property string modelData
            readonly property QtObject p: Backend.param(modelData)
            Layout.fillWidth: true
            spacing: Theme.space.sm
            opacity: knobs.opacity
            Label {
                text: p.label.toUpperCase()
                font.pixelSize: Theme.fontSize.xs
                font.weight: Theme.weight.semibold
                font.letterSpacing: Theme.letterSpacing.caps
                color: Theme.c.textMuted
                Layout.preferredWidth: Theme.space.xxxl * 1.1
            }
            Segmented {
                Layout.fillWidth: true
                small: true
                accent: root.accent
                model: p.options
                currentIndex: p.value
                onActivated: (i) => { p.beginGesture(); p.setValue(i); p.endGesture() }
            }
        }
    }
}
