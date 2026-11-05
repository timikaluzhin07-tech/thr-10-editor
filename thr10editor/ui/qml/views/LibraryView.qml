import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Basic
import QtQuick.Dialogs
import THR10
import "../components"

// Библиотека: поиск, папки, теги, избранное.
ColumnLayout {
    id: root
    spacing: Theme.space.sm
    signal editRequested(string presetId)
    signal saveRequested()

    function focusSearch() { search.forceActiveFocus(); search.selectAll() }

    RowLayout {
        Layout.fillWidth: true
        spacing: Theme.space.xs
        AppTextField {
            id: search
            Layout.fillWidth: true
            iconName: "search"
            placeholderText: "Поиск: имя, тег, модель, эффект"
            text: Backend.libSearch
            onTextEdited: Backend.libSearch = text
            Keys.onEscapePressed: { text = ""; Backend.libSearch = "" }
        }
        IconButton {
            iconName: "star"
            tip: "Только избранное"
            checkable: true
            checked: Backend.libFavoritesOnly
            onClicked: Backend.libFavoritesOnly = checked
        }
    }

    // Папки
    RowLayout {
        Layout.fillWidth: true
        spacing: Theme.space.xs
        AppCombo {
            id: folderCombo
            Layout.fillWidth: true
            model: ["Все папки"].concat(Backend.folders.map(f => "  ".repeat(f.depth) + f.name + "  (" + f.count + ")"))
            currentIndex: Backend.libFolder === "" ? 0 : Backend.folderPaths.indexOf(Backend.libFolder) + 1
            onActivated: (i) => Backend.libFolder = i === 0 ? "" : Backend.folderPaths[i - 1]
        }
        IconButton { iconName: "folder-plus"; tip: "Новая папка"; onClicked: folderDialog.openFor("") }
        IconButton {
            iconName: "edit"
            tip: "Переименовать папку"
            enabled: Backend.libFolder !== ""
            onClicked: folderDialog.openFor(Backend.libFolder)
        }
        IconButton {
            iconName: "trash"
            tip: "Удалить папку (пресеты поднимутся на уровень выше)"
            enabled: Backend.libFolder !== ""
            onClicked: Backend.deleteFolder(Backend.libFolder)
        }
    }

    // Теги
    Flow {
        Layout.fillWidth: true
        spacing: Theme.space.xs
        visible: Backend.tags.length > 0
        Repeater {
            model: Backend.tags.slice(0, 16)
            delegate: Chip {
                required property var modelData
                text: "#" + modelData.tag
                checkable: true
                checked: Backend.libTag === modelData.tag
                onClicked: Backend.libTag = modelData.tag
            }
        }
    }

    Label {
        Layout.fillWidth: true
        text: Backend.libraryTotal === 0 ? "Библиотека пуста. Сохраните текущий звук (Ctrl+S) или импортируйте файлы."
              : "Показано " + Backend.libraryCount + " из " + Backend.libraryTotal
        color: Theme.c.textFaint
        font.pixelSize: Theme.fontSize.xs
        wrapMode: Text.Wrap
    }

    ListView {
        id: list
        Layout.fillWidth: true
        Layout.fillHeight: true
        clip: true
        spacing: Theme.space.xxs
        model: Backend.libraryModel
        boundsBehavior: Flickable.StopAtBounds
        ScrollBar.vertical: ScrollBar {}
        reuseItems: true

        delegate: Rectangle {
            id: row
            required property int index
            required property string presetId
            required property string name
            required property string folder
            required property string tags
            required property bool favorite
            required property string summary
            required property bool isCurrent
            width: ListView.view.width
            implicitHeight: col.implicitHeight + Theme.space.sm * 2
            radius: Theme.radius.md
            color: isCurrent ? Theme.c.surface3 : rowMa.containsMouse ? Theme.c.surface2 : "transparent"
            Behavior on color { ColorAnimation { duration: Theme.motion.fast } }
            // акцентная полоса у выбранного
            Rectangle {
                width: 2
                radius: 1
                height: parent.height - Theme.space.md
                anchors.verticalCenter: parent.verticalCenter
                x: 0
                color: Theme.c.accent
                opacity: row.isCurrent ? 1 : 0
                Behavior on opacity { NumberAnimation { duration: Theme.motion.normal } }
            }

            MouseArea {
                id: rowMa
                anchors.fill: parent
                hoverEnabled: true
                acceptedButtons: Qt.LeftButton | Qt.RightButton
                onClicked: (m) => {
                    if (m.button === Qt.RightButton) { menu.presetId = row.presetId; menu.popup() }
                    else Backend.loadPreset(row.presetId)
                }
                onDoubleClicked: root.editRequested(row.presetId)
            }

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Theme.space.sm
                anchors.rightMargin: Theme.space.xs
                spacing: Theme.space.xs
                ColumnLayout {
                    id: col
                    Layout.fillWidth: true
                    spacing: 0
                    Label {
                        Layout.fillWidth: true
                        text: row.name
                        font.pixelSize: Theme.fontSize.md
                        font.weight: row.isCurrent ? Theme.weight.semibold : Theme.weight.medium
                        color: Theme.c.text
                        elide: Text.ElideRight
                    }
                    Label {
                        Layout.fillWidth: true
                        text: row.summary + (row.folder ? "  ·  " + row.folder : "")
                        font.pixelSize: Theme.fontSize.xs
                        color: Theme.c.textMuted
                        elide: Text.ElideRight
                    }
                    Label {
                        Layout.fillWidth: true
                        visible: row.tags !== ""
                        text: "#" + row.tags.split(", ").join("  #")
                        font.pixelSize: Theme.fontSize.xs
                        color: Theme.c.textFaint
                        elide: Text.ElideRight
                    }
                }
                IconButton {
                    boxSize: Theme.size.control * 0.85
                    iconName: "star"
                    iconColor: row.favorite ? Theme.c.accent : Theme.c.textFaint
                    opacity: row.favorite || rowMa.containsMouse || hovered ? 1 : 0.0
                    Behavior on opacity { NumberAnimation { duration: Theme.motion.fast } }
                    tip: row.favorite ? "Убрать из избранного" : "В избранное"
                    onClicked: Backend.toggleFavorite(row.presetId)
                }
            }
        }
    }

    Menu {
        id: menu
        property string presetId: ""
        MenuItem { text: "Загрузить"; onTriggered: Backend.loadPreset(menu.presetId) }
        MenuItem { text: "Свойства…"; onTriggered: root.editRequested(menu.presetId) }
        MenuItem { text: "Дублировать"; onTriggered: Backend.duplicatePreset(menu.presetId) }
        MenuItem { text: "Добавить в сет-лист"; onTriggered: Backend.addToSetlist(menu.presetId) }
        MenuItem { text: "Морфинг к этому пресету"; onTriggered: Backend.morphTo(menu.presetId) }
        MenuSeparator {}
        MenuItem { text: "Перезаписать текущим звуком…"; onTriggered: overwriteDialog.openFor(menu.presetId) }
        MenuItem { text: "Удалить"; onTriggered: Backend.deletePreset(menu.presetId) }
    }

    RowLayout {
        Layout.fillWidth: true
        spacing: Theme.space.xs
        AppButton {
            Layout.fillWidth: true
            text: "Сохранить звук"
            iconName: "save"
            tip: "Сохранить текущий звук как новый пресет (Ctrl+S). Существующие пресеты не перезаписываются"
            onClicked: root.saveRequested()
        }
        IconButton { iconName: "import"; tip: "Импорт файлов в библиотеку (.YDL, .syx, .thrpreset)"; onClicked: importFiles.open() }
        IconButton { iconName: "export"; tip: "Экспорт показанных пресетов"; onClicked: exportFiles.open() }
    }

    FileDialog {
        id: importFiles
        title: "Импорт в библиотеку"
        fileMode: FileDialog.OpenFiles
        nameFilters: ["Все поддерживаемые (*.thrpreset *.json *.syx *.ydl *.YDL)", "Все файлы (*)"]
        onAccepted: Backend.importFilesToLibrary(selectedFiles)
    }
    FileDialog {
        id: exportFiles
        title: "Экспорт библиотеки"
        fileMode: FileDialog.SaveFile
        nameFilters: ["Библиотека THR10 Editor (*.json)", "SysEx (*.syx)", "Библиотека THR Editor (*.YDL)"]
        defaultSuffix: ["json", "syx", "YDL"][Math.max(0, selectedNameFilter.index)]
        onAccepted: Backend.exportLibrary(selectedFile, ["json", "syx", "ydl"][Math.max(0, selectedNameFilter.index)], true)
    }

    AppDialog {
        id: folderDialog
        property string oldPath: ""
        title: oldPath ? "Переименовать папку" : "Новая папка"
        maxWidth: Theme.space.xxxl * 8
        function openFor(path) { oldPath = path; folderName.text = path; open(); folderName.forceActiveFocus() }
        Label { text: "Вложенность — через «/», например «Концерты/Клуб»"; color: Theme.c.textMuted; font.pixelSize: Theme.fontSize.sm }
        AppTextField { id: folderName; Layout.fillWidth: true; onAccepted: okBtn.clicked() }
        footer: [
            Item { Layout.fillWidth: true },
            AppButton { text: "Отмена"; onClicked: folderDialog.close() },
            AppButton {
                id: okBtn
                variant: "primary"
                text: "OK"
                onClicked: {
                    if (folderDialog.oldPath) Backend.renameFolder(folderDialog.oldPath, folderName.text)
                    else Backend.newFolder(folderName.text)
                    folderDialog.close()
                }
            }
        ]
    }

    AppDialog {
        id: overwriteDialog
        property string presetId: ""
        property string presetName: ""
        title: "Перезаписать пресет?"
        maxWidth: Theme.space.xxxl * 9
        function openFor(id) {
            const info = Backend.presetInfo(id)
            if (!info.id) return
            presetId = id
            presetName = info.name
            open()
        }
        Label {
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            color: Theme.c.text
            text: "Значения пресета «" + overwriteDialog.presetName + "» будут заменены текущим звуком редактора. Имя, папка и теги останутся. Это действие нельзя отменить."
        }
        footer: [
            Item { Layout.fillWidth: true },
            AppButton { text: "Отмена"; onClicked: overwriteDialog.close() },
            AppButton {
                variant: "danger"
                text: "Перезаписать"
                onClicked: { Backend.overwritePreset(overwriteDialog.presetId); overwriteDialog.close() }
            }
        ]
    }
}
