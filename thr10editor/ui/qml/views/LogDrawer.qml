import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Basic
import THR10
import "../components"

// Журнал обмена с комбиком (для диагностики).
Drawer {
    id: root
    edge: Qt.BottomEdge
    height: Math.min(parent ? parent.height * 0.45 : 300, Theme.space.xxxl * 8)
    width: parent ? parent.width : 800
    modal: false
    interactive: true

    background: Rectangle {
        color: Theme.c.surface
        Rectangle { width: parent.width; height: 1; color: Theme.c.borderStrong }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.space.md
        spacing: Theme.space.sm

        RowLayout {
            Layout.fillWidth: true
            Label {
                text: "Журнал MIDI"
                font.pixelSize: Theme.fontSize.lg
                font.weight: Theme.weight.semibold
                color: Theme.c.text
            }
            Label {
                text: "последние сообщения сверху; полный журнал — " + Backend.dataDir + "/thr10editor.log"
                color: Theme.c.textFaint
                font.pixelSize: Theme.fontSize.xs
                elide: Text.ElideMiddle
                Layout.fillWidth: true
            }
            AppButton { compact: true; text: "Копировать"; iconName: "copy"; onClicked: Backend.copyLog() }
            AppButton { compact: true; variant: "ghost"; text: "Очистить"; onClicked: Backend.clearLog() }
            IconButton { iconName: "close"; tip: "Закрыть"; onClicked: root.close() }
        }

        ListView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            model: Backend.logItems
            spacing: 1
            ScrollBar.vertical: ScrollBar {}
            delegate: RowLayout {
                required property var modelData
                width: ListView.view.width
                spacing: Theme.space.sm
                Label {
                    text: modelData.time
                    color: Theme.c.textFaint
                    font.family: "monospace"
                    font.pixelSize: Theme.fontSize.xs
                }
                Label {
                    text: modelData.dir
                    Layout.preferredWidth: Theme.space.xxxl
                    color: modelData.dir === "error" ? Theme.c.danger : modelData.dir === "warn" ? Theme.c.warning
                         : modelData.dir === "in" ? Theme.c.info : modelData.dir === "out" ? Theme.c.accent : Theme.c.textMuted
                    font.family: "monospace"
                    font.pixelSize: Theme.fontSize.xs
                }
                Label {
                    text: modelData.text
                    color: Theme.c.text
                    font.pixelSize: Theme.fontSize.xs
                    Layout.preferredWidth: implicitWidth
                }
                Label {
                    text: modelData.raw
                    color: Theme.c.textFaint
                    font.family: "monospace"
                    font.pixelSize: Theme.fontSize.xs
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
            }
        }
    }
}
