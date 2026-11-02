import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Basic
import THR10
import "../components"

// Сет-листы: упорядоченные списки пресетов для выступления.
ColumnLayout {
    id: root
    spacing: Theme.space.sm
    signal stageRequested(int index)

    RowLayout {
        Layout.fillWidth: true
        spacing: Theme.space.xs
        AppCombo {
            id: combo
            Layout.fillWidth: true
            model: Backend.setlists.map(s => s.name + "  (" + s.count + ")")
            currentIndex: Backend.setlists.findIndex(s => s.id === Backend.currentSetlistId)
            onActivated: (i) => Backend.currentSetlistId = Backend.setlists[i].id
        }
        IconButton { iconName: "plus"; tip: "Новый сет-лист"; onClicked: nameDialog.openFor("") }
        IconButton {
            iconName: "edit"; tip: "Переименовать"
            enabled: Backend.currentSetlistId !== ""
            onClicked: nameDialog.openFor(Backend.currentSetlistId)
        }
        IconButton {
            iconName: "trash"; tip: "Удалить сет-лист"
            enabled: Backend.currentSetlistId !== ""
            onClicked: Backend.deleteSetlist(Backend.currentSetlistId)
        }
    }

    AppButton {
        Layout.fillWidth: true
        variant: "primary"
        text: "Режим «Сцена»"
        iconName: "stage"
        enabled: Backend.setlistItems.length > 0
        tip: "Полноэкранный режим для выступления (F5). ← → / Пробел / PgUp PgDn / педаль"
        onClicked: root.stageRequested(0)
    }

    Label {
        Layout.fillWidth: true
        visible: Backend.setlistItems.length === 0
        text: "Пусто. Добавьте пресеты: правый клик в библиотеке → «Добавить в сет-лист» или кнопка ниже."
        wrapMode: Text.Wrap
        color: Theme.c.textFaint
        font.pixelSize: Theme.fontSize.sm
    }

    ListView {
        id: list
        Layout.fillWidth: true
        Layout.fillHeight: true
        clip: true
        spacing: Theme.space.xxs
        model: Backend.setlistItems
        ScrollBar.vertical: ScrollBar {}
        delegate: Rectangle {
            id: item
            required property var modelData
            width: ListView.view.width
            height: Theme.size.controlLarge + Theme.space.xs
            radius: Theme.radius.md
            color: ma.containsMouse ? Theme.c.surface2 : "transparent"
            Behavior on color { ColorAnimation { duration: Theme.motion.fast } }
            MouseArea {
                id: ma
                anchors.fill: parent
                hoverEnabled: true
                onDoubleClicked: root.stageRequested(item.modelData.index)
                onClicked: if (!item.modelData.missing) Backend.loadPreset(item.modelData.id)
            }
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Theme.space.sm
                spacing: Theme.space.sm
                Label {
                    text: String(item.modelData.index + 1).padStart(2, "0")
                    color: Theme.c.textFaint
                    font.weight: Theme.weight.semibold
                    font.features: { "tnum": 1 }
                    Layout.preferredWidth: Theme.space.xl
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 0
                    Label {
                        Layout.fillWidth: true
                        text: item.modelData.name
                        color: item.modelData.missing ? Theme.c.danger : Theme.c.text
                        elide: Text.ElideRight
                    }
                    Label {
                        Layout.fillWidth: true
                        text: [item.modelData.summary,
                               item.modelData.tuning,
                               item.modelData.chords ? "аккорды" : "",
                               item.modelData.hasBackground ? "фон" : ""].filter(x => x).join("  ·  ")
                        color: Theme.c.textMuted
                        font.pixelSize: Theme.fontSize.xs
                        elide: Text.ElideRight
                    }
                }
                IconButton {
                    boxSize: Theme.size.control * 0.8
                    iconName: "edit"; tip: "Строй, аккорды и фон для сцены"
                    enabled: !item.modelData.missing
                    onClicked: trackDialog.openFor(item.modelData.index)
                }
                IconButton {
                    boxSize: Theme.size.control * 0.8
                    iconName: "arrow-up"; tip: "Выше"
                    enabled: item.modelData.index > 0
                    onClicked: Backend.moveSetlistItem(item.modelData.index, item.modelData.index - 1)
                }
                IconButton {
                    boxSize: Theme.size.control * 0.8
                    iconName: "arrow-down"; tip: "Ниже"
                    enabled: item.modelData.index < list.count - 1
                    onClicked: Backend.moveSetlistItem(item.modelData.index, item.modelData.index + 1)
                }
                IconButton {
                    boxSize: Theme.size.control * 0.8
                    iconName: "close"; tip: "Убрать из сет-листа"
                    onClicked: Backend.removeSetlistItem(item.modelData.index)
                }
            }
        }
    }

    AppButton {
        Layout.fillWidth: true
        text: "Добавить текущий звук"
        iconName: "plus"
        onClicked: Backend.addCurrentToSetlist()
    }

    // MIDI-контроллер / педаль
    Rectangle {
        Layout.fillWidth: true
        implicitHeight: ctrlCol.implicitHeight + Theme.space.md * 2
        radius: Theme.radius.md
        color: "transparent"
        border.width: 1
        border.color: Theme.c.border
        ColumnLayout {
            id: ctrlCol
            anchors.fill: parent
            anchors.margins: Theme.space.md
            spacing: Theme.space.xs
            SectionLabel { text: "Педаль / MIDI-контроллер" }
            RowLayout {
                Layout.fillWidth: true
                AppCombo {
                    Layout.fillWidth: true
                    model: Backend.controllerPorts
                    currentIndex: Math.max(0, Backend.controllerPorts.indexOf(Backend.controllerPort))
                    onActivated: (i) => Backend.setControllerPort(Backend.controllerPorts[i])
                }
                IconButton { iconName: "refresh"; tip: "Обновить список"; onClicked: Backend.refreshControllerPorts() }
            }
            RowLayout {
                Layout.fillWidth: true
                AppButton {
                    compact: true
                    text: Backend.controllerLearning === "next" ? "Нажмите педаль…" : "Следующий"
                    checked: Backend.controllerLearning === "next"
                    onClicked: Backend.learnController("next")
                }
                Label { text: Backend.controllerLearning === "next" ? "Esc или клик — отмена" : Backend.nextBinding; color: Backend.controllerLearning === "next" ? Theme.c.accent : Theme.c.textMuted; font.pixelSize: Theme.fontSize.xs; elide: Text.ElideRight; Layout.fillWidth: true }
            }
            RowLayout {
                Layout.fillWidth: true
                AppButton {
                    compact: true
                    text: Backend.controllerLearning === "prev" ? "Нажмите педаль…" : "Предыдущий"
                    checked: Backend.controllerLearning === "prev"
                    onClicked: Backend.learnController("prev")
                }
                Label { text: Backend.controllerLearning === "prev" ? "Esc или клик — отмена" : Backend.prevBinding; color: Backend.controllerLearning === "prev" ? Theme.c.accent : Theme.c.textMuted; font.pixelSize: Theme.fontSize.xs; elide: Text.ElideRight; Layout.fillWidth: true }
            }
            RowLayout {
                spacing: Theme.space.sm
                ToggleSwitch { checked: Backend.pcSelects; onToggled: Backend.pcSelects = checked }
                Label { text: "Program Change выбирает номер в сет-листе"; color: Theme.c.text; font.pixelSize: Theme.fontSize.sm; wrapMode: Text.Wrap; Layout.fillWidth: true }
            }
            Label {
                Layout.fillWidth: true
                text: "Педали-«клавиатуры» (PageUp/PageDown, стрелки) работают в режиме «Сцена» без настройки."
                color: Theme.c.textFaint
                font.pixelSize: Theme.fontSize.xs
                wrapMode: Text.Wrap
            }
        }
    }

    AppDialog {
        id: nameDialog
        property string sid: ""
        title: sid ? "Переименовать сет-лист" : "Новый сет-лист"
        maxWidth: Theme.space.xxxl * 8
        function openFor(id) {
            sid = id
            nm.text = id ? Backend.currentSetlistName : ""
            open()
            nm.forceActiveFocus()
        }
        AppTextField { id: nm; Layout.fillWidth: true; placeholderText: "Например, «Клуб, 12 мая»"; onAccepted: ok.clicked() }
        footer: [
            Item { Layout.fillWidth: true },
            AppButton { text: "Отмена"; onClicked: nameDialog.close() },
            AppButton {
                id: ok
                variant: "primary"; text: "OK"
                onClicked: {
                    if (nameDialog.sid) Backend.renameSetlist(nameDialog.sid, nm.text)
                    else Backend.newSetlist(nm.text)
                    nameDialog.close()
                }
            }
        ]
    }

    TrackDialog { id: trackDialog }
}
