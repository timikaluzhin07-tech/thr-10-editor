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
        gradient: Gradient {
            GradientStop { position: 0.0; color: Theme.c.surfaceTop }
            GradientStop { position: 0.3; color: Theme.c.surface }
        }
        border.width: 1
        border.color: Theme.c.borderStrong
        Rectangle {
            x: parent.radius; y: 1; width: parent.width - parent.radius * 2; height: 1
            color: Theme.c.highlight
        }
    }

    contentItem: ColumnLayout {
        spacing: Theme.space.lg
        RowLayout {
            Layout.fillWidth: true
            Label {
                text: root.title
                font.pixelSize: Theme.fontSize.xl
                font.weight: Theme.weight.semibold
                font.letterSpacing: Theme.letterSpacing.tight * 0.5
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
