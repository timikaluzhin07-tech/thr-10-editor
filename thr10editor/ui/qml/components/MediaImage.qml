import QtQuick

// Картинка или анимированный GIF. По умолчанию растягивается на всю область
// (Image.Stretch) — без обрезки; для обложки используется PreserveAspectFit.
Item {
    id: root
    property url source: ""
    property bool gif: false
    property int fillMode: Image.Stretch
    readonly property bool ready: loader.item !== null && loader.item.status === Image.Ready
    // пропорции исходной картинки (ширина / высота), 1 — пока не загружена
    readonly property real aspect: ready && loader.item.implicitHeight > 0
                                   ? loader.item.implicitWidth / loader.item.implicitHeight : 1

    Loader {
        id: loader
        anchors.fill: parent
        active: root.source.toString() !== ""
        sourceComponent: root.gif ? animated : still
    }
    Component {
        id: still
        Image {
            source: root.source
            fillMode: root.fillMode
            asynchronous: true
            cache: false
            smooth: true
            mipmap: true
        }
    }
    Component {
        id: animated
        AnimatedImage {
            source: root.source
            fillMode: root.fillMode
            asynchronous: true
            cache: false
            smooth: true
            playing: root.visible
        }
    }
}
