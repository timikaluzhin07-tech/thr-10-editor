import QtQuick
import QtQuick.Controls.Basic
import THR10

ComboBox {
    id: root
    implicitHeight: Theme.size.control
    font.pixelSize: Theme.fontSize.md
    hoverEnabled: true

    delegate: ItemDelegate {
        id: item
        required property int index
        required property var modelData
        width: root.popup.width - Theme.space.sm
        height: Theme.size.control
        highlighted: root.highlightedIndex === index
        contentItem: Label {
            text: typeof item.modelData === "string" ? item.modelData : (item.modelData[root.textRole] || "")
            color: item.index === root.currentIndex ? Theme.c.accent : Theme.c.text
            font.pixelSize: Theme.fontSize.md
            elide: Text.ElideRight
            verticalAlignment: Text.AlignVCenter
        }
        background: Rectangle {
            radius: Theme.radius.sm
            color: item.highlighted ? Theme.c.surface3 : "transparent"
        }
    }

    indicator: Icon {
        x: root.width - width - Theme.space.sm
        y: (root.height - height) / 2
        name: "chevron-down"
        size: Theme.size.icon * 0.9
        color: Theme.c.textMuted
    }

    contentItem: Label {
        leftPadding: Theme.space.md
        rightPadding: Theme.size.icon + Theme.space.md
        text: root.displayText
        font: root.font
        color: Theme.c.text
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }

    background: Rectangle {
        radius: Theme.radius.md
        color: root.down ? Theme.c.surface3 : Theme.c.surface2
        border.width: 1
        border.color: root.visualFocus || root.popup.visible ? Theme.c.accent : root.hovered ? Theme.c.borderStrong : Theme.c.border
    }

    popup: Popup {
        y: root.height + Theme.space.xs
        width: root.width
        implicitHeight: Math.min(contentItem.implicitHeight + Theme.space.sm, Theme.size.control * 9)
        padding: Theme.space.xs
        contentItem: ListView {
            clip: true
            implicitHeight: contentHeight
            model: root.popup.visible ? root.delegateModel : null
            currentIndex: root.highlightedIndex
            ScrollIndicator.vertical: ScrollIndicator {}
        }
        background: Rectangle {
            radius: Theme.radius.md
            color: Theme.c.surface
            border.width: 1
            border.color: Theme.c.borderStrong
        }
    }
}
