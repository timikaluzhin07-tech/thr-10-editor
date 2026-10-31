import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Basic
import THR10

// Модальный диалог дизайн-системы.
Popup {
    id: root
    property string title: ""
    default property alias content: body.data
    property alias footer: footerRow.data
    property real maxWidth: Theme.space.xxxl * 12

    parent: Overlay.overlay
    modal: true
    focus: true
    anchors.centerIn: parent
    width: Math.min(maxWidth, (parent ? parent.width : 800) - Theme.space.xxl * 2)
    height: Math.min(implicitHeight, (parent ? parent.height : 600) - Theme.space.xxl * 2)
    padding: Theme.space.xl
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

    Overlay.modal: Rectangle { color: Theme.c.scrim }

    enter: Transition {
        NumberAnimation { property: "opacity"; from: 0; to: 1; duration: Theme.motion.normal }
        NumberAnimation { property: "scale"; from: 0.97; to: 1; duration: Theme.motion.normal; easing.type: Easing.OutCubic }
    }
    exit: Transition {
        NumberAnimation { property: "opacity"; from: 1; to: 0; duration: Theme.motion.fast }
    }

    background: Rectangle {
        radius: Theme.radius.xl
        color: Theme.c.surface
        border.width: 1
        border.color: Theme.c.borderStrong
    }

    contentItem: ColumnLayout {
        spacing: Theme.space.lg
        RowLayout {
            Layout.fillWidth: true
            Label {
                text: root.title
                font.pixelSize: Theme.fontSize.xl
                font.weight: Theme.weight.semibold
                color: Theme.c.text
                Layout.fillWidth: true
                elide: Text.ElideRight
            }
            IconButton { iconName: "close"; tip: "Закрыть"; shortcutHint: "Esc"; onClicked: root.close() }
        }
        Flickable {
            id: flick
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.preferredHeight: body.implicitHeight
            contentHeight: body.implicitHeight
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: ScrollBar { policy: flick.contentHeight > flick.height ? ScrollBar.AsNeeded : ScrollBar.AlwaysOff }
            ColumnLayout {
                id: body
                width: flick.width
                spacing: Theme.space.md
            }
        }
        RowLayout {
            id: footerRow
            Layout.fillWidth: true
            spacing: Theme.space.sm
            visible: children.length > 0
        }
    }
}
