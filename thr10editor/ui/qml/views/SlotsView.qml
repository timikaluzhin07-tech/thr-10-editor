import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Basic
import THR10
import "../components"

// Пять пользовательских ячеек комбика.
Flickable {
    id: root
    signal writeRequested(int index)
    contentHeight: col.implicitHeight + Theme.space.lg
    clip: true
    boundsBehavior: Flickable.StopAtBounds
    ScrollBar.vertical: ScrollBar {}

    ColumnLayout {
        id: col
        width: root.width
        spacing: Theme.space.sm

        Label {
            Layout.fillWidth: true
            text: "Ячейки 1–5 комбика. «Считать» — нажмите кнопку ячейки на комбике, редактор поймает её дамп. «Записать» — звук уходит в комбик, сохраняете удержанием кнопки ячейки."
            wrapMode: Text.Wrap
            color: Theme.c.textMuted
            font.pixelSize: Theme.fontSize.sm
        }

        Repeater {
            model: Backend.slots
            delegate: Rectangle {
                id: slot
                required property var modelData
                readonly property int idx: modelData.index
                readonly property bool capturing: Backend.captureSlot === idx
                Layout.fillWidth: true
                implicitHeight: slotCol.implicitHeight + Theme.space.md * 2
                radius: Theme.radius.md
                color: capturing ? Theme.c.accentSoft : Theme.c.surface2
                border.width: 1
                border.color: capturing ? Theme.c.accent : Theme.c.border
                Behavior on color { ColorAnimation { duration: Theme.motion.fast } }

                ColumnLayout {
                    id: slotCol
                    anchors.fill: parent
                    anchors.margins: Theme.space.md
                    spacing: Theme.space.sm

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.space.md
                        Rectangle {
                            width: Theme.size.control; height: width; radius: Theme.radius.sm
                            color: Theme.c.surface3
                            Label {
                                anchors.centerIn: parent
                                text: slot.idx + 1
                                font.pixelSize: Theme.fontSize.lg
                                font.weight: Theme.weight.bold
                                color: Theme.c.groupAmp
                            }
                        }
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 0
                            Label {
                                Layout.fillWidth: true
                                text: slot.modelData.known ? slot.modelData.name : "Не считана"
                                color: slot.modelData.known ? Theme.c.text : Theme.c.textFaint
                                font.pixelSize: Theme.fontSize.md
                                font.weight: Theme.weight.semibold
                                elide: Text.ElideRight
                            }
                            Label {
                                Layout.fillWidth: true
                                visible: text !== ""
                                text: slot.modelData.summary + (slot.modelData.time ? " · " + slot.modelData.time : "")
                                color: Theme.c.textMuted
                                font.pixelSize: Theme.fontSize.xs
                                elide: Text.ElideRight
                            }
                        }
                    }

                    Label {
                        visible: slot.capturing
                        Layout.fillWidth: true
                        text: "Нажмите кнопку " + (slot.idx + 1) + " на комбике…"
                        color: Theme.c.accent
                        font.pixelSize: Theme.fontSize.sm
                        wrapMode: Text.Wrap
                    }

                    Flow {
                        Layout.fillWidth: true
                        spacing: Theme.space.xs
                        AppButton {
                            compact: true
                            visible: !slot.capturing
                            text: "Считать"
                            iconName: "download"
                            enabled: Backend.hasTransport
                            tip: "Поймать дамп ячейки при нажатии её кнопки на комбике"
                            onClicked: Backend.readSlot(slot.idx)
                        }
                        AppButton {
                            compact: true
                            visible: slot.capturing && Backend.isDemo
                            variant: "primary"
                            text: "Нажать на демо-комбике"
                            onClicked: Backend.demoPressSlot(slot.idx)
                        }
                        AppButton {
                            compact: true
                            visible: slot.capturing
                            variant: "ghost"
                            text: "Отмена"
                            onClicked: Backend.cancelSlotCapture()
                        }
                        AppButton {
                            compact: true
                            visible: !slot.capturing
                            text: "Открыть"
                            enabled: slot.modelData.known
                            tip: "Загрузить известное содержимое ячейки в редактор"
                            onClicked: Backend.loadSlot(slot.idx)
                        }
                        AppButton {
                            compact: true
                            visible: !slot.capturing
                            text: "Записать"
                            iconName: "upload"
                            enabled: Backend.hasTransport
                            tip: "Отправить текущий звук в комбик для сохранения в ячейку"
                            onClicked: { Backend.writeSlot(slot.idx); root.writeRequested(slot.idx) }
                        }
                    }
                }
            }
        }

        // Симуляция действий на демо-комбике
        Rectangle {
            visible: Backend.isDemo
            Layout.fillWidth: true
            Layout.topMargin: Theme.space.md
            implicitHeight: demoCol.implicitHeight + Theme.space.md * 2
            radius: Theme.radius.md
            color: "transparent"
            border.width: 1
            border.color: Theme.c.border
            ColumnLayout {
                id: demoCol
                anchors.fill: parent
                anchors.margins: Theme.space.md
                spacing: Theme.space.sm
                SectionLabel { text: "Демо-комбик" }
                Label {
                    Layout.fillWidth: true
                    text: "Проверка синхронизации без железа: «повернуть» ручку на комбике или выключить его питание."
                    wrapMode: Text.Wrap
                    color: Theme.c.textMuted
                    font.pixelSize: Theme.fontSize.sm
                }
                Flow {
                    Layout.fillWidth: true
                    spacing: Theme.space.xs
                    AppButton { compact: true; text: "Покрутить ручку"; iconName: "refresh"; onClicked: Backend.demoRandomKnob() }
                    AppButton {
                        compact: true
                        property bool off: false
                        text: off ? "Включить питание" : "Выключить питание"
                        iconName: "power"
                        onClicked: { off = !off; Backend.demoPower(!off) }
                    }
                }
            }
        }
    }
}
