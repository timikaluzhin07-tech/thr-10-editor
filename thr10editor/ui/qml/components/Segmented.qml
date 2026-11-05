import QtQuick
import QtQuick.Controls.Basic
import THR10

// Сегментный переключатель: сплошная «дорожка», выбранный сегмент приподнят,
// индикатор плавно переезжает. Если ширина задана больше нужной — сегменты
// растягиваются поровну.
Rectangle {
    id: root
    property var model: []
    property int currentIndex: 0
    property color accent: Theme.c.accent
    property bool small: false
    property bool accented: true
    signal activated(int index)

    readonly property int count: model ? model.length : 0
    readonly property real pad: 2
    readonly property real segH: implicitHeight - pad * 2
    // Ширина сегментов: поровну, если всем хватает места; иначе — пропорционально
    // естественной ширине (длинные подписи не вылезают за край).
    readonly property var naturals: {
        const out = []
        for (let i = 0; i < rep.count; ++i) {
            const it = rep.itemAt(i)
            out.push(it ? it.naturalW : 0)
        }
        return out
    }
    readonly property real naturalWidth: naturals.reduce((a, b) => a + b, 0) + pad * 2
    readonly property real innerWidth: width - pad * 2
    readonly property bool equalFit: count > 0 && innerWidth / count >= Math.max(0, ...naturals)
    function segmentWidth(i) {
        if (count === 0) return 0
        if (equalFit) return innerWidth / count
        const total = naturalWidth - pad * 2
        return total > 0 ? naturals[i] * innerWidth / total : innerWidth / count
    }

    implicitHeight: small ? Theme.size.control * 0.86 : Theme.size.control
    implicitWidth: naturalWidth
    radius: Theme.radius.md
    color: Theme.c.surface2
    border.width: 1
    border.color: Theme.c.border

    // приподнятый выбранный сегмент
    Rectangle {
        id: indicator
        readonly property Item target: rep.count > root.currentIndex && root.currentIndex >= 0 ? rep.itemAt(root.currentIndex) : null
        visible: target !== null
        x: target ? row.x + target.x : 0
        y: root.pad
        width: target ? target.width : 0
        height: root.segH
        radius: Theme.radius.md - 1.5
        gradient: Gradient {
            GradientStop { position: 0.0; color: Theme.c.surface3 }
            GradientStop { position: 1.0; color: Qt.darker(Theme.c.surface3, Theme.dark ? 1.08 : 1.02) }
        }
        border.width: 1
        border.color: Theme.c.borderStrong
        Behavior on x { NumberAnimation { duration: Theme.motion.normal; easing.type: Easing.OutCubic } }
        Behavior on width { NumberAnimation { duration: Theme.motion.normal; easing.type: Easing.OutCubic } }
        // тонкая акцентная риска снизу
        Rectangle {
            visible: root.accented
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 2
            width: Math.min(parent.width * 0.4, Theme.space.xl)
            height: 2
            radius: 1
            color: root.accent
        }
    }

    Row {
        id: row
        x: root.pad
        y: root.pad
        width: root.width - root.pad * 2
        height: root.segH

        Repeater {
            id: rep
            model: root.model
            delegate: AbstractButton {
                id: opt
                required property int index
                required property string modelData
                readonly property bool selected: index === root.currentIndex
                readonly property real naturalW: lbl.implicitWidth + (root.small ? Theme.space.md : Theme.space.lg) * 2
                width: root.segmentWidth(index)
                height: row.height
                focusPolicy: Qt.StrongFocus
                hoverEnabled: true
                onClicked: root.activated(index)
                Accessible.role: Accessible.RadioButton
                Accessible.name: modelData
                Accessible.checked: selected

                background: Item {
                    Rectangle {
                        anchors.fill: parent
                        radius: Theme.radius.md - 1.5
                        color: Theme.c.highlight
                        opacity: opt.hovered && !opt.selected ? 1 : 0
                        Behavior on opacity { NumberAnimation { duration: Theme.motion.fast } }
                    }
                    Rectangle {
                        anchors.fill: parent
                        anchors.margins: -1
                        radius: Theme.radius.md
                        color: "transparent"
                        border.width: Theme.size.focusRing
                        border.color: Theme.c.focus
                        opacity: 0.55
                        visible: opt.visualFocus
                    }
                }
                contentItem: Label {
                    id: lbl
                    text: opt.modelData
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    elide: Text.ElideRight
                    font.pixelSize: root.small ? Theme.fontSize.sm : Theme.fontSize.md
                    font.weight: opt.selected ? Theme.weight.semibold : Theme.weight.medium
                    color: opt.selected ? Theme.c.text : opt.hovered ? Theme.c.text : Theme.c.textMuted
                    Behavior on color { ColorAnimation { duration: Theme.motion.fast } }
                }
                padding: 0
                leftPadding: Theme.space.xs
                rightPadding: Theme.space.xs
            }
        }
    }
}
