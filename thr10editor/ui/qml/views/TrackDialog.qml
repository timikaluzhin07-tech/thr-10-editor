import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Basic
import QtQuick.Dialogs
import THR10
import "../components"

// Данные трека сет-листа для режима «Сцена»: строй, аккорды, фон и обложка
// (картинка или GIF).
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

    // строка выбора картинки/GIF: превью, «Выбрать/Заменить», «Убрать»
    component MediaRow: RowLayout {
        id: mr
        property string field: "background"
        property bool has: false
        property url source: ""
        property bool gif: false
        property real previewAspect: 16 / 9
        property string emptyText: ""
        property string removeText: ""
        property string hint: ""
        Layout.fillWidth: true
        spacing: Theme.space.md
        Rectangle {
            Layout.preferredHeight: Theme.size.control * 3
            Layout.preferredWidth: Layout.preferredHeight * mr.previewAspect
            radius: Theme.radius.md
            color: Theme.c.surface2
            border.width: 1
            border.color: Theme.c.border
            MediaImage {
                anchors.fill: parent
                anchors.margins: 1
                visible: mr.has
                source: mr.has ? mr.source : ""
                gif: mr.gif
                fillMode: Image.Stretch
            }
            Label {
                anchors.centerIn: parent
                visible: !mr.has
                text: mr.emptyText
                color: Theme.c.textFaint
                font.pixelSize: Theme.fontSize.sm
            }
        }
        ColumnLayout {
            spacing: Theme.space.xs
            AppButton {
                text: mr.has ? "Заменить…" : "Выбрать картинку или GIF…"
                iconName: "image"
                onClicked: { imageDialog.field = mr.field; imageDialog.open() }
            }
            AppButton {
                visible: mr.has
                variant: "ghost"
                text: mr.removeText
                iconName: "trash"
                onClicked: Backend.clearTrackMedia(root.trackIndex, mr.field)
            }
            Label {
                Layout.maximumWidth: Theme.space.xxxl * 4.5
                text: mr.hint
                color: Theme.c.textFaint
                font.pixelSize: Theme.fontSize.xs
                wrapMode: Text.Wrap
            }
        }
    }

    SectionLabel { text: "Фон в режиме «Сцена»"; Layout.topMargin: Theme.space.sm }
    MediaRow {
        field: "background"
        has: root.track ? root.track.hasBackground : false
        source: root.track ? root.track.background : ""
        gif: root.track ? root.track.backgroundGif : false
        emptyText: "Без фона"
        removeText: "Убрать фон"
        hint: "PNG, JPG, WEBP или GIF. Растягивается на весь экран (без обрезки) и слегка затемняется."
    }

    SectionLabel { text: "Обложка трека"; Layout.topMargin: Theme.space.sm }
    MediaRow {
        field: "cover"
        previewAspect: 1
        has: root.track ? root.track.hasCover : false
        source: root.track ? root.track.cover : ""
        gif: root.track ? root.track.coverGif : false
        emptyText: "Нет"
        removeText: "Убрать обложку"
        hint: "Показывается по центру поверх фона. Файлы копируются в папку данных программы."
    }

    footer: [
        Item { Layout.fillWidth: true },
        AppButton { variant: "primary"; text: "Готово"; onClicked: root.close() }
    ]

    FileDialog {
        id: imageDialog
        property string field: "background"
        title: field === "cover" ? "Обложка трека" : "Фон для трека"
        fileMode: FileDialog.OpenFile
        nameFilters: ["Картинки и GIF (*.png *.jpg *.jpeg *.webp *.gif)", "Все файлы (*)"]
        onAccepted: Backend.setTrackMedia(root.trackIndex, field, selectedFile)
    }
}
