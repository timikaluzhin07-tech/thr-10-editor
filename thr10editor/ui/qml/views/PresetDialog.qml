import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Basic
import THR10
import "../components"

// Сохранение текущего звука в библиотеку / свойства пресета.
AppDialog {
    id: root
    property string presetId: ""   // пусто — сохранение текущего звука как нового
    title: presetId ? "Свойства пресета" : "Сохранить в библиотеку"
    maxWidth: Theme.space.xxxl * 10

    function openNew() {
        presetId = ""
        nameField.text = Backend.presetName
        folderField.editText = Backend.libFolder
        tagsField.text = ""
        notesField.text = ""
        fav.checked = false
        open()
        nameField.forceActiveFocus()
        nameField.selectAll()
    }
    function openFor(id) {
        const info = Backend.presetInfo(id)
        if (!info.id) return
        presetId = id
        nameField.text = info.name
        folderField.editText = info.folder
        tagsField.text = info.tags
        notesField.text = info.notes
        fav.checked = info.favorite
        open()
    }

    SectionLabel { text: "Имя" }
    AppTextField { id: nameField; Layout.fillWidth: true; onAccepted: saveBtn.clicked() }
    SectionLabel { text: "Папка" }
    AppCombo {
        id: folderField
        Layout.fillWidth: true
        editable: true
        model: Backend.folderPaths
    }
    SectionLabel { text: "Теги (через запятую)" }
    AppTextField { id: tagsField; Layout.fillWidth: true; placeholderText: "clean, blues, live" }
    SectionLabel { text: "Заметки" }
    AppTextField { id: notesField; Layout.fillWidth: true }
    RowLayout {
        spacing: Theme.space.sm
        ToggleSwitch { id: fav }
        Label { text: "В избранное"; color: Theme.c.text }
    }

    footer: [
        Item { Layout.fillWidth: true },
        AppButton { text: "Отмена"; onClicked: root.close() },
        AppButton {
            id: saveBtn
            variant: "primary"
            text: root.presetId ? "Сохранить" : "Добавить в библиотеку"
            onClicked: {
                const folder = folderField.editText
                if (root.presetId)
                    Backend.updatePresetMeta(root.presetId, nameField.text, folder, tagsField.text, fav.checked, notesField.text)
                else
                    Backend.saveCurrentAs(nameField.text, folder, tagsField.text, fav.checked, notesField.text)
                root.close()
            }
        }
    ]
}
