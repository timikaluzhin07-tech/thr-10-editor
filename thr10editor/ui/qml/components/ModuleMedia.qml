import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Dialogs
import THR10

// Фото или GIF в карточке модуля (усилитель, компрессор, модуляция…).
// Картинка растягивается на всю область без обрезки. Пока картинки нет, область
// не занимает места: добавить можно кнопкой в заголовке карточки (pick())
// или перетащив файл на карточку. При наведении — «Заменить» и «Убрать».
Item {
    id: root
    property string groupKey: ""
    property string title: ""
    // высота = ширина / aspect (в карточках эффектов); 0 — размер задаёт раскладка
    property real aspect: 2
    readonly property var entry: groupKey !== "" && Backend.moduleMedia[groupKey] ? Backend.moduleMedia[groupKey] : null
    readonly property bool has: entry !== null

    function pick() { dialog.open() }
    function remove() { Backend.clearModuleMedia(groupKey) }
    function dropUrls(urls) { return urls && urls.length > 0 && Backend.setModuleMedia(groupKey, urls[0]) }

    visible: has
    implicitHeight: has && aspect > 0 ? Math.round(width / aspect) : 0

    Rectangle {
        anchors.fill: parent
        radius: Theme.radius.sm
        color: Theme.c.surface2
    }
    MediaImage {
        id: img
        objectName: "moduleMedia"
        anchors.fill: parent
        anchors.margins: 1
        source: root.has ? root.entry.url : ""
        gif: root.has && root.entry.gif
        fillMode: Image.Stretch
        opacity: ready ? 1 : 0
        Behavior on opacity { NumberAnimation { duration: Theme.motion.slow } }
    }
    Rectangle {
        anchors.fill: parent
        radius: Theme.radius.sm
        color: "transparent"
        border.width: 1
        border.color: Theme.c.border
    }

    HoverHandler { id: hover }

    // действия поверх картинки — проявляются при наведении
    Rectangle {
        anchors.top: parent.top
        anchors.right: parent.right
        anchors.margins: Theme.space.sm
        width: actions.implicitWidth + Theme.space.xs * 2
        height: actions.implicitHeight + Theme.space.xs * 2
        radius: Theme.radius.md
        color: "#A6000000"
        opacity: hover.hovered ? 1 : 0
        visible: opacity > 0
        Behavior on opacity { NumberAnimation { duration: Theme.motion.fast } }
        Row {
            id: actions
            anchors.centerIn: parent
            spacing: Theme.space.xs
            IconButton {
                iconName: "image"
                iconColor: "#F3F4F6"
                boxSize: Theme.size.control * 0.85
                focusPolicy: Qt.NoFocus
                tip: "Заменить картинку"
                onClicked: root.pick()
            }
            IconButton {
                iconName: "trash"
                iconColor: "#F3F4F6"
                boxSize: Theme.size.control * 0.85
                focusPolicy: Qt.NoFocus
                tip: "Убрать картинку"
                onClicked: root.remove()
            }
        }
    }

    FileDialog {
        id: dialog
        title: root.title ? "Картинка для блока «" + root.title + "»" : "Картинка для блока"
        fileMode: FileDialog.OpenFile
        nameFilters: ["Картинки и GIF (*.png *.jpg *.jpeg *.webp *.gif)", "Все файлы (*)"]
        onAccepted: Backend.setModuleMedia(root.groupKey, selectedFile)
    }
}
