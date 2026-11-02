import QtQuick
import THR10

// Перетаскивание картинки/GIF на карточку модуля: рамка-подсказка и импорт.
DropArea {
    id: root
    property Item media: null  // ModuleMedia карточки
    z: 5
    keys: ["text/uri-list"]
    onEntered: (drag) => { if (!drag.hasUrls) drag.accepted = false }
    onDropped: (drop) => {
        if (drop.hasUrls && root.media && root.media.dropUrls(drop.urls))
            drop.acceptProposedAction()
    }
    Rectangle {
        anchors.fill: parent
        radius: Theme.radius.lg
        color: Theme.c.accentSoft
        border.width: 1
        border.color: Theme.c.accent
        opacity: root.containsDrag ? 1 : 0
        visible: opacity > 0
        Behavior on opacity { NumberAnimation { duration: Theme.motion.fast } }
    }
}
