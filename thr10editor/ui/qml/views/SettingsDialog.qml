import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Basic
import THR10
import "../components"

AppDialog {
    id: root
    title: "Настройки"

    component Row2: RowLayout {
        property alias label: lbl.text
        property alias hint: hintLbl.text
        default property alias control: holder.data
        Layout.fillWidth: true
        spacing: Theme.space.md
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 0
            Label { id: lbl; color: Theme.c.text; font.pixelSize: Theme.fontSize.md; Layout.fillWidth: true; wrapMode: Text.Wrap }
            Label { id: hintLbl; visible: text !== ""; color: Theme.c.textMuted; font.pixelSize: Theme.fontSize.sm; Layout.fillWidth: true; wrapMode: Text.Wrap }
        }
        Item { id: holder; implicitWidth: childrenRect.width; implicitHeight: childrenRect.height }
    }

    SectionLabel { text: "Внешний вид" }
    Row2 {
        label: "Тема"
        Segmented {
            model: ["Тёмная", "Светлая"]
            currentIndex: Theme.dark ? 0 : 1
            onActivated: (i) => Theme.setMode(i === 0 ? "dark" : "light")
        }
    }
    Row2 {
        label: "Масштаб интерфейса"
        hint: "Ctrl + / Ctrl − / Ctrl 0. Плюс автоматическая подстройка под размер окна."
        Segmented {
            model: ["80%", "90%", "100%", "110%", "125%", "140%", "160%"]
            readonly property var zooms: [0.8, 0.9, 1.0, 1.1, 1.25, 1.4, 1.6]
            currentIndex: Math.max(0, zooms.indexOf(Theme.zoom))
            small: true
            onActivated: (i) => Theme.setZoom(zooms[i])
        }
    }

    SectionLabel { text: "Подключение"; Layout.topMargin: Theme.space.md }
    Row2 {
        label: "Подключаться при запуске"
        hint: "К последнему порту или к найденному THR"
        ToggleSwitch {
            checked: Backend.getSetting("auto_connect")
            onToggled: Backend.setSetting("auto_connect", checked)
        }
    }
    Row2 {
        label: "Демо-режим, если комбик не найден"
        ToggleSwitch {
            checked: Backend.getSetting("start_demo_if_no_device")
            onToggled: Backend.setSetting("start_demo_if_no_device", checked)
        }
    }
    Row2 {
        label: "Интервал отправки, мс"
        hint: "Не чаще одного сообщения за этот интервал. Применяется после перезапуска."
        SpinBox {
            from: 5; to: 200; stepSize: 5
            value: Backend.getSetting("send_interval_ms")
            onValueModified: Backend.setSetting("send_interval_ms", value)
        }
    }

    SectionLabel { text: "Комбик (не подтверждено)"; Layout.topMargin: Theme.space.md }
    Label {
        Layout.fillWidth: true
        wrapMode: Text.Wrap
        color: Theme.c.warning
        font.pixelSize: Theme.fontSize.sm
        text: Backend.systemConfirmed
              ? "Команды подтверждены в protocol_overrides.json и отправляются на комбик."
              : "Команды Lamp и Wide описаны одним источником и не подтверждены. Они работают только в демо и не отправляются на комбик, пока вы не подтвердите их перехватом трафика (docs/PROTOCOL.md)."
    }
    Row2 {
        label: "Подсветка (Lamp)"
        ToggleSwitch { checked: Backend.lamp; onToggled: Backend.setSystem("system.lamp", checked) }
    }
    Row2 {
        label: "Широкое стерео (Wide)"
        ToggleSwitch { checked: Backend.wide; onToggled: Backend.setSystem("system.wide", checked) }
    }

    SectionLabel { text: "Данные"; Layout.topMargin: Theme.space.md }
    Label {
        Layout.fillWidth: true
        text: "Папка: " + Backend.dataDir + "\nБиблиотека, настройки, журнал и protocol_overrides.json хранятся здесь."
        color: Theme.c.textMuted
        font.pixelSize: Theme.fontSize.sm
        wrapMode: Text.WrapAnywhere
    }
    Label {
        Layout.fillWidth: true
        text: Backend.appName + " " + Backend.version + " · неофициальный проект, не связан с Yamaha Corporation"
        color: Theme.c.textFaint
        font.pixelSize: Theme.fontSize.xs
    }
}
