import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Basic
import THR10
import "../components"

// Выбор пресета из файла с несколькими пресетами (.YDL, .syx, библиотека).
AppDialog {
    id: root
    title: "Пресеты из файла " + Backend.importedSource
    property bool libraryAvailable: false
    signal addAllRequested()

    Label {
        Layout.fillWidth: true
        text: "Найдено пресетов: " + Backend.importedPresets.length + ". Выберите, какой загрузить в редактор."
        color: Theme.c.textMuted
        wrapMode: Text.Wrap
    }

    Repeater {
        model: Backend.importedPresets
        delegate: Rectangle {
            required property var modelData
            Layout.fillWidth: true
            implicitHeight: Theme.size.controlLarge + Theme.space.xs
            radius: Theme.radius.md
            color: ma.containsMouse ? Theme.c.surface3 : Theme.c.surface2
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Theme.space.md
                anchors.rightMargin: Theme.space.sm
                spacing: Theme.space.md
                Label {
                    text: (modelData.index + 1) + "."
                    color: Theme.c.textFaint
                    font.features: { "tnum": 1 }
                }
                Label {
                    text: modelData.name
                    color: Theme.c.text
                    font.weight: Theme.weight.semibold
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
                Label {
                    text: modelData.summary
                    color: Theme.c.textMuted
                    font.pixelSize: Theme.fontSize.sm
                    elide: Text.ElideRight
                    Layout.maximumWidth: root.width * 0.4
                }
            }
            MouseArea {
                id: ma
                anchors.fill: parent
                hoverEnabled: true
                onClicked: { Backend.loadImported(modelData.index); root.close() }
            }
        }
    }

    footer: [
        Item { Layout.fillWidth: true },
        AppButton {
            visible: root.libraryAvailable
            variant: "primary"
            text: "Добавить все в библиотеку"
            iconName: "library"
            onClicked: { root.addAllRequested(); root.close() }
        },
        AppButton { text: "Закрыть"; onClicked: root.close() }
    ]
}
