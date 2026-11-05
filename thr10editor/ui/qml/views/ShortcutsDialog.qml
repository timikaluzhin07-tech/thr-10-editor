import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Basic
import THR10
import "../components"

// Список горячих клавиш (строится из того же списка, что и сами сочетания).
AppDialog {
    id: root
    title: "Горячие клавиши"
    property var shortcuts: []

    readonly property var groups: {
        const out = []
        for (const s of shortcuts) {
            if (!s.text) continue
            let g = out.find(x => x.name === s.group)
            if (!g) { g = { name: s.group, items: [] }; out.push(g) }
            g.items.push(s)
        }
        return out
    }

    Repeater {
        model: root.groups
        delegate: ColumnLayout {
            required property var modelData
            Layout.fillWidth: true
            spacing: Theme.space.xs
            SectionLabel { text: modelData.name; Layout.topMargin: Theme.space.sm }
            Repeater {
                model: modelData.items
                delegate: RowLayout {
                    required property var modelData
                    Layout.fillWidth: true
                    spacing: Theme.space.md
                    Label {
                        text: modelData.text
                        color: Theme.c.text
                        font.pixelSize: Theme.fontSize.md
                        Layout.fillWidth: true
                        wrapMode: Text.Wrap
                    }
                    Row {
                        spacing: Theme.space.xs
                        Repeater {
                            model: modelData.label || (Array.isArray(modelData.seq) ? modelData.seq : [modelData.seq])
                            delegate: Rectangle {
                                required property string modelData
                                implicitWidth: keyLbl.implicitWidth + Theme.space.md
                                implicitHeight: keyLbl.implicitHeight + Theme.space.xs * 1.5
                                radius: Theme.radius.sm
                                color: Theme.c.surface2
                                border.width: 1
                                border.color: Theme.c.borderStrong
                                Label {
                                    id: keyLbl
                                    anchors.centerIn: parent
                                    text: modelData
                                    font.pixelSize: Theme.fontSize.sm
                                    font.weight: Theme.weight.medium
                                    color: Theme.c.text
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
