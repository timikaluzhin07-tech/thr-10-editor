import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Basic
import QtQuick.Dialogs
import THR10
import "../components"

// Данные трека сет-листа для режима «Сцена»: строй, аккорды, фон.
// Поля сохраняются при завершении ввода (клик вне поля / Enter / закрытие).
AppDialog {
    id: root
    property int trackIndex: -1
    readonly property var track: trackIndex >= 0 && trackIndex < Backend.setlistItems.length
                                 ? Backend.setlistItems[trackIndex] : null
    title: track ? "Трек " + (trackIndex + 1) + ": " + track.name : "Трек"
    maxWidth: Theme.space.xxxl * 12

    function openFor(index) {
        trackIndex = index
        tuning.editText = track ? track.tuning : ""
        chords.text = track ? track.chords : ""
        open()
    }
    function commit() {
        if (trackIndex < 0) return
        Backend.setTrackText(trackIndex, "tuning", tuning.editText)
        Backend.setTrackText(trackIndex, "chords", chords.text)
    }
    onClosed: commit()

    SectionLabel { text: "Строй гитары" }
    AppCombo {
        id: tuning
        Layout.fillWidth: true
        editable: true
        model: Backend.tuningSuggestions
        onActivated: commit()
        onAccepted: commit()
        onEditingFinished: commit()
    }
    Label {
        Layout.fillWidth: true
        text: "Выберите из списка или впишите свой, например «Open C» или «Drop A, 7 струн»."
        color: Theme.c.textFaint
        font.pixelSize: Theme.fontSize.xs
        wrapMode: Text.Wrap
    }

    SectionLabel { text: "Аккорды"; Layout.topMargin: Theme.space.sm }
    AppTextArea {
        id: chords
        Layout.fillWidth: true
        Layout.preferredHeight: Theme.size.control * 5
        placeholderText: "Am – F – C – G\nили по частям песни:\nКуплет: Am F C G\nПрипев: F G Am"
        onEditingFinished: commit()
    }
    Label {
        Layout.fillWidth: true
        text: "Enter — новая строка. Ctrl+Enter или клик вне поля — сохранить."
        color: Theme.c.textFaint
        font.pixelSize: Theme.fontSize.xs
    }

    SectionLabel { text: "Фон в режиме «Сцена»"; Layout.topMargin: Theme.space.sm }
    RowLayout {
        Layout.fillWidth: true
        spacing: Theme.space.md
        Rectangle {
            Layout.preferredWidth: Theme.size.control * 5.3
            Layout.preferredHeight: Theme.size.control * 3
            radius: Theme.radius.md
            color: Theme.c.surface2
            border.width: 1
            border.color: Theme.c.border
            clip: true
            Image {
                anchors.fill: parent
                anchors.margins: 1
                visible: root.track && root.track.hasBackground
                source: root.track ? root.track.background : ""
                fillMode: Image.PreserveAspectCrop
                asynchronous: true
                cache: false
            }
            Label {
                anchors.centerIn: parent
                visible: !(root.track && root.track.hasBackground)
                text: "Без фона"
                color: Theme.c.textFaint
                font.pixelSize: Theme.fontSize.sm
            }
        }
        ColumnLayout {
            spacing: Theme.space.xs
            AppButton {
                text: root.track && root.track.hasBackground ? "Заменить…" : "Выбрать картинку…"
                iconName: "import"
                onClicked: imageDialog.open()
            }
            AppButton {
                visible: root.track && root.track.hasBackground
                variant: "ghost"
                text: "Убрать фон"
                iconName: "trash"
                onClicked: Backend.clearTrackBackground(root.trackIndex)
            }
            Label {
                Layout.maximumWidth: Theme.space.xxxl * 4.5
                text: "PNG, JPG или WEBP. Картинка копируется в папку данных программы."
                color: Theme.c.textFaint
                font.pixelSize: Theme.fontSize.xs
                wrapMode: Text.Wrap
            }
        }
    }

    footer: [
        Item { Layout.fillWidth: true },
        AppButton { variant: "primary"; text: "Готово"; onClicked: root.close() }
    ]

    FileDialog {
        id: imageDialog
        title: "Фон для трека"
        fileMode: FileDialog.OpenFile
        nameFilters: ["Картинки (*.png *.jpg *.jpeg *.webp)", "Все файлы (*)"]
        onAccepted: Backend.setTrackBackground(root.trackIndex, selectedFile)
    }
}
