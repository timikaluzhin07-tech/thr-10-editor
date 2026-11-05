import QtQuick
import QtQuick.Layouts
import THR10

// Карточка-поверхность: лёгкий вертикальный градиент, тонкий блик сверху,
// граница чуть светлеет при наведении. Содержимое — вертикально.
// appearIndex ≥ 0 — плавное появление при запуске (со сдвигом по порядку).
Rectangle {
    id: root
    default property alias content: col.data
    property real padding: Theme.space.lg
    property alias spacing: col.spacing
    property int appearIndex: -1

    radius: Theme.radius.lg
    gradient: Gradient {
        GradientStop { position: 0.0; color: Theme.c.surfaceTop }
        GradientStop { position: 0.35; color: Theme.c.surface }
    }
    border.width: 1
    border.color: hover.hovered ? Theme.c.borderStrong : Theme.c.border
    implicitHeight: col.implicitHeight + padding * 2
    implicitWidth: col.implicitWidth + padding * 2
    Behavior on border.color { ColorAnimation { duration: Theme.motion.normal } }

    HoverHandler { id: hover }

    // блик по верхней кромке
    Rectangle {
        x: root.radius
        y: 1
        width: root.width - root.radius * 2
        height: 1
        color: Theme.c.highlight
    }

    ColumnLayout {
        id: col
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: root.padding
        spacing: Theme.space.md
    }

    // появление
    transform: Translate { id: shift; y: 0 }
    Component.onCompleted: if (appearIndex >= 0) appear.start()
    SequentialAnimation {
        id: appear
        PropertyAction { target: root; property: "opacity"; value: 0 }
        PropertyAction { target: shift; property: "y"; value: 10 }
        PauseAnimation { duration: root.appearIndex * Theme.motion.stagger }
        ParallelAnimation {
            NumberAnimation { target: root; property: "opacity"; to: 1; duration: Theme.motion.appear; easing.type: Easing.OutCubic }
            NumberAnimation { target: shift; property: "y"; to: 0; duration: Theme.motion.appear; easing.type: Easing.OutCubic }
        }
    }
}
