import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Basic
import THR10

// Карточка блока эффектов: кнопка питания с «LED», заголовок, тип, ручки сеткой,
// необязательная картинка/GIF внизу.
// Выключенный блок не прячется: ручки гаснут (серые дуги), но остаются доступны.
Card {
    id: root
    property QtObject group: null
    property real knobSize: Theme.size.knobSmall
    property Component headerComponent: null
    readonly property color groupColor: group ? Theme.c[group.accent] : Theme.c.accent
    readonly property bool active: !group || !group.hasSwitch || group.enabled

    signal knobContext(QtObject param, Item knob, real x, real y)

    spacing: Theme.space.md

    // цветная риска блока у левого края
    Rectangle {
        parent: root
        x: 0
        y: root.padding + Theme.space.xs
        width: 2
        height: Theme.size.control * 0.8
        radius: 1
        color: root.groupColor
        opacity: root.active ? 0.9 : 0.3
        Behavior on opacity { NumberAnimation { duration: Theme.motion.normal } }
    }

    RowLayout {
        Layout.fillWidth: true
        spacing: Theme.space.sm

        PowerButton {
            visible: root.group && root.group.hasSwitch
            checked: root.group ? root.group.enabled : false
            onToggled: root.group.setEnabled(checked)
        }
        Label {
            text: root.group ? root.group.title.toUpperCase() : ""
            font.pixelSize: Theme.fontSize.sm
            font.weight: Theme.weight.bold
            font.letterSpacing: Theme.letterSpacing.caps
            color: root.active ? Theme.c.text : Theme.c.textMuted
            Layout.fillWidth: true
            elide: Text.ElideRight
            Behavior on color { ColorAnimation { duration: Theme.motion.normal } }
        }
        IconButton {
            objectName: "moduleMediaButton"
            iconName: "image"
            boxSize: Theme.size.control * 0.85
            iconColor: mediaBox.has ? Theme.c.textMuted : Theme.c.textFaint
            tip: mediaBox.has ? "Заменить картинку блока" : "Добавить фото или GIF в блок (или перетащите файл на карточку)"
            onClicked: mediaBox.pick()
        }
        Loader {
            active: root.headerComponent !== null
            sourceComponent: root.headerComponent
            Layout.alignment: Qt.AlignVCenter
        }
    }

    Segmented {
        visible: root.group && root.group.typeOptions.length > 0
        Layout.fillWidth: true
        small: true
        model: root.group ? root.group.typeOptions : []
        currentIndex: root.group ? root.group.typeIndex : 0
        onActivated: (i) => root.group.setType(i)
    }

    // ручки ровной сеткой
    GridLayout {
        id: knobs
        Layout.fillWidth: true
        Layout.topMargin: Theme.space.xs
        readonly property int cell: root.knobSize + Theme.space.lg
        columns: Math.max(1, Math.min(root.group ? root.group.knobKeys.length : 1,
                                      Math.floor((width + Theme.space.sm) / cell)))
        columnSpacing: Theme.space.sm
        rowSpacing: Theme.space.md

        Repeater {
            model: root.group ? root.group.knobKeys : []
            delegate: Item {
                required property string modelData
                Layout.fillWidth: true
                implicitHeight: knob.implicitHeight
                implicitWidth: knob.implicitWidth
                Knob {
                    id: knob
                    anchors.horizontalCenter: parent.horizontalCenter
                    param: Backend.param(modelData)
                    diameter: root.knobSize
                    dimmed: !root.active
                    onContextRequested: (p, x, y) => root.knobContext(p, this, x, y)
                }
            }
        }
    }

    Repeater {
        model: root.group ? root.group.choiceKeys : []
        delegate: RowLayout {
            required property string modelData
            readonly property QtObject p: Backend.param(modelData)
            Layout.fillWidth: true
            spacing: Theme.space.sm
            Label {
                text: p.label.toUpperCase()
                font.pixelSize: Theme.fontSize.xs
                font.weight: Theme.weight.semibold
                font.letterSpacing: Theme.letterSpacing.caps
                color: Theme.c.textMuted
                Layout.preferredWidth: Theme.space.xxxl * 1.1
            }
            Segmented {
                Layout.fillWidth: true
                small: true
                accented: false
                model: p.options
                currentIndex: p.value
                onActivated: (i) => { p.beginGesture(); p.setValue(i); p.endGesture() }
            }
        }
    }

    // фото или GIF блока (растягивается по ширине карточки без обрезки)
    ModuleMedia {
        id: mediaBox
        Layout.fillWidth: true
        Layout.topMargin: Theme.space.xs
        groupKey: root.group ? root.group.key : ""
        title: root.group ? root.group.title : ""
    }

    MediaDropArea {
        parent: root
        anchors.fill: parent
        media: mediaBox
    }
}
