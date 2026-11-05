import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Basic
import THR10
import "../components"

// Усилитель: модель, кабинет и пять больших ручек — главная секция окна.
Card {
    id: root
    readonly property QtObject model: Backend.param("amp.model")
    readonly property QtObject cab: Backend.param("amp.cab")
    signal knobContext(QtObject param, Item knob, real x, real y)

    padding: Theme.space.xl
    spacing: Theme.space.lg

    // цветная риска блока
    Rectangle {
        parent: root
        x: 0
        y: root.padding + Theme.space.xs
        width: 2
        height: Theme.size.control * 0.8
        radius: 1
        color: Theme.c.groupAmp
    }

    RowLayout {
        Layout.fillWidth: true
        spacing: Theme.space.md

        ColumnLayout {
            spacing: 0
            Label {
                text: "УСИЛИТЕЛЬ"
                font.pixelSize: Theme.fontSize.sm
                font.weight: Theme.weight.bold
                font.letterSpacing: Theme.letterSpacing.caps
                color: Theme.c.text
            }
            Label {
                id: modelName
                text: root.model.text + "  ·  " + root.cab.text
                font.pixelSize: Theme.fontSize.xs
                font.letterSpacing: Theme.letterSpacing.caps * 0.5
                color: Theme.c.textMuted
                Behavior on text {
                    SequentialAnimation {
                        NumberAnimation { target: modelName; property: "opacity"; to: 0.25; duration: 70 }
                        PropertyAction {}
                        NumberAnimation { target: modelName; property: "opacity"; to: 1; duration: Theme.motion.normal }
                    }
                }
            }
        }
        Item { Layout.fillWidth: true }
        Label {
            visible: Backend.deviceModel !== "" && Backend.deviceModel !== "THR10"
            text: Backend.deviceModel + ": названия моделей могут отличаться"
            color: Theme.c.warning
            font.pixelSize: Theme.fontSize.xs
            elide: Text.ElideRight
            Layout.maximumWidth: root.width * 0.35
        }
        IconButton {
            objectName: "moduleMediaButton"
            iconName: "image"
            boxSize: Theme.size.control * 0.85
            iconColor: mediaBox.has ? Theme.c.textMuted : Theme.c.textFaint
            tip: mediaBox.has ? "Заменить картинку блока" : "Добавить фото или GIF в блок (или перетащите файл на карточку)"
            onClicked: mediaBox.pick()
        }
        Label {
            text: "КАБИНЕТ"
            font.pixelSize: Theme.fontSize.xs
            font.weight: Theme.weight.semibold
            font.letterSpacing: Theme.letterSpacing.caps
            color: Theme.c.textFaint
        }
        AppCombo {
            Layout.preferredWidth: Theme.space.xxxl * 3.3
            model: root.cab.options
            currentIndex: root.cab.value
            onActivated: (i) => { root.cab.beginGesture(); root.cab.setValue(i); root.cab.endGesture() }
        }
    }

    Segmented {
        Layout.fillWidth: true
        model: root.model.options
        currentIndex: root.model.value
        onActivated: (i) => { root.model.beginGesture(); root.model.setValue(i); root.model.endGesture() }
    }

    // разделитель
    Rectangle { Layout.fillWidth: true; height: 1; color: Theme.c.border }

    // ручки и картинка блока: картинка справа, если ручки помещаются в один ряд,
    // иначе — полосой под ручками
    GridLayout {
        id: ampBody
        Layout.fillWidth: true
        Layout.topMargin: Theme.space.xs
        columnSpacing: Theme.space.xl
        rowSpacing: Theme.space.lg
        readonly property real knobRowWidth: 5 * (Theme.size.knobLarge + Theme.space.xl) - Theme.space.lg
        readonly property real mediaWidth: Theme.size.knobLarge * 2.4
        readonly property bool side: width >= knobRowWidth + columnSpacing + mediaWidth
        columns: !mediaBox.has || side ? 2 : 1

        GridLayout {
            id: knobsGrid
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignVCenter
            readonly property int cell: Theme.size.knobLarge + Theme.space.xl
            columns: Math.max(1, Math.min(5, Math.floor((width + Theme.space.lg) / cell)))
            columnSpacing: Theme.space.lg
            rowSpacing: Theme.space.lg
            Repeater {
                model: ["amp.gain", "amp.master", "amp.bass", "amp.middle", "amp.treble"]
                delegate: Item {
                    required property string modelData
                    Layout.fillWidth: true
                    implicitHeight: knob.implicitHeight
                    implicitWidth: knob.implicitWidth
                    Knob {
                        id: knob
                        anchors.horizontalCenter: parent.horizontalCenter
                        param: Backend.param(modelData)
                        diameter: Theme.size.knobLarge
                        onContextRequested: (p, x, y) => root.knobContext(p, this, x, y)
                    }
                }
            }
        }

        // фото или GIF усилителя — растягивается на свою область без обрезки
        ModuleMedia {
            id: mediaBox
            groupKey: "amp"
            title: "Усилитель"
            aspect: ampBody.side ? 0 : 3
            Layout.fillWidth: !ampBody.side
            Layout.fillHeight: ampBody.side
            Layout.preferredWidth: ampBody.side ? ampBody.mediaWidth : -1
            Layout.minimumHeight: ampBody.side ? Theme.size.knobLarge : 0
        }
    }

    MediaDropArea {
        parent: root
        anchors.fill: parent
        media: mediaBox
    }
}
