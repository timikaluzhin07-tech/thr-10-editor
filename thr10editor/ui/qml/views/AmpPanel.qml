import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Basic
import THR10
import "../components"

// Усилитель: модель, кабинет, пять больших ручек.
Card {
    id: root
    readonly property QtObject model: Backend.param("amp.model")
    readonly property QtObject cab: Backend.param("amp.cab")
    readonly property color accent: Theme.c.groupAmp
    signal knobContext(QtObject param, Item knob, real x, real y)

    padding: Theme.space.xl
    spacing: Theme.space.lg

    RowLayout {
        Layout.fillWidth: true
        spacing: Theme.space.sm
        Rectangle { width: Theme.space.sm; height: width; radius: width / 2; color: root.accent }
        Label {
            text: "Усилитель"
            font.pixelSize: Theme.fontSize.lg
            font.weight: Theme.weight.semibold
            color: Theme.c.text
        }
        Item { Layout.fillWidth: true }
        Label {
            visible: Backend.deviceModel !== "" && Backend.deviceModel !== "THR10"
            text: "Подключён " + Backend.deviceModel + ": названия моделей могут отличаться"
            color: Theme.c.warning
            font.pixelSize: Theme.fontSize.sm
            elide: Text.ElideRight
            Layout.maximumWidth: root.width * 0.5
        }
    }

    GridLayout {
        Layout.fillWidth: true
        columns: root.width > Theme.space.xxxl * 16 ? 2 : 1
        columnSpacing: Theme.space.xl
        rowSpacing: Theme.space.md

        ColumnLayout {
            Layout.fillWidth: true
            spacing: Theme.space.sm
            SectionLabel { text: "Модель" }
            Segmented {
                Layout.fillWidth: true
                accent: root.accent
                model: root.model.options
                currentIndex: root.model.value
                onActivated: (i) => { root.model.beginGesture(); root.model.setValue(i); root.model.endGesture() }
            }
        }
        ColumnLayout {
            Layout.fillWidth: true
            spacing: Theme.space.sm
            SectionLabel { text: "Кабинет" }
            Segmented {
                Layout.fillWidth: true
                small: true
                accent: root.accent
                model: root.cab.options
                currentIndex: root.cab.value
                onActivated: (i) => { root.cab.beginGesture(); root.cab.setValue(i); root.cab.endGesture() }
            }
        }
    }

    Flow {
        Layout.fillWidth: true
        Layout.topMargin: Theme.space.sm
        spacing: Theme.space.xl
        Repeater {
            model: ["amp.gain", "amp.master", "amp.bass", "amp.middle", "amp.treble"]
            delegate: Knob {
                required property string modelData
                param: Backend.param(modelData)
                accent: root.accent
                diameter: Theme.size.knobLarge
                onContextRequested: (p, x, y) => root.knobContext(p, this, x, y)
            }
        }
    }
}
