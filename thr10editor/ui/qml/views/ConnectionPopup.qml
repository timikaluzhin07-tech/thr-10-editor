import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Basic
import THR10
import "../components"

// Выбор порта и управление подключением.
Popup {
    id: root
    width: Math.min(Theme.space.xxxl * 9, parent ? parent.width : 400)
    padding: Theme.space.lg
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    onOpened: Backend.refreshPorts()

    enter: Transition {
        NumberAnimation { property: "opacity"; from: 0; to: 1; duration: Theme.motion.fast }
        NumberAnimation { property: "y"; from: root.y - Theme.space.sm; to: root.y; duration: Theme.motion.normal; easing.type: Easing.OutCubic }
    }

    background: Rectangle {
        radius: Theme.radius.lg
        color: Theme.c.surface
        border.width: 1
        border.color: Theme.c.borderStrong
    }

    contentItem: ColumnLayout {
        spacing: Theme.space.md

        Label {
            text: "Подключение"
            font.pixelSize: Theme.fontSize.lg
            font.weight: Theme.weight.semibold
            color: Theme.c.text
        }
        Label {
            Layout.fillWidth: true
            text: Backend.connText
            wrapMode: Text.Wrap
            color: Backend.connStatus === "error" ? Theme.c.danger
                 : Backend.connStatus === "no_response" ? Theme.c.warning : Theme.c.textMuted
            font.pixelSize: Theme.fontSize.sm
        }

        SectionLabel { text: "Порт" }
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.space.sm
            AppCombo {
                id: combo
                Layout.fillWidth: true
                model: Backend.ports
                currentIndex: Math.max(0, Backend.ports.indexOf(Backend.selectedPort))
            }
            IconButton { iconName: "refresh"; tip: "Обновить список портов"; onClicked: Backend.refreshPorts() }
        }
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.space.sm
            AppButton {
                variant: "primary"
                text: "Подключить"
                iconName: "plug"
                Layout.fillWidth: true
                onClicked: Backend.connectPort(combo.currentText)
            }
            AppButton {
                text: "Отключить"
                enabled: Backend.hasTransport
                onClicked: Backend.disconnectDevice()
            }
        }
        AppButton {
            Layout.fillWidth: true
            text: "Считать состояние с комбика"
            iconName: "download"
            enabled: Backend.hasTransport
            tip: "Ctrl+D"
            onClicked: Backend.requestState()
        }
        Label {
            Layout.fillWidth: true
            text: "Комбик не виден? Проверьте драйвер Yamaha Steinberg USB, кабель и питание. Закройте официальный THR Editor — он занимает MIDI-порт."
            wrapMode: Text.Wrap
            color: Theme.c.textFaint
            font.pixelSize: Theme.fontSize.xs
        }
    }
}
