import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Basic
import THR10
import "../components"

// Верхняя панель: пресет, связь, действия.
Rectangle {
    id: root
    property bool sidebarVisible: true
    property bool toolsVisible: true
    property bool hasTools: false
    readonly property bool narrow: width < Theme.space.xxxl * 22

    signal openRequested()
    signal exportRequested()
    signal settingsRequested()
    signal shortcutsRequested()
    signal logRequested()
    signal toggleSidebar()
    signal toggleTools()
    signal connectionRequested(Item anchor)
    signal stageRequested()

    implicitHeight: Theme.size.topbar
    color: Theme.c.surface
    Behavior on color { ColorAnimation { duration: Theme.motion.theme } }
    Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.c.border }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.space.md
        anchors.rightMargin: Theme.space.md
        spacing: Theme.space.sm

        IconButton {
            iconName: "panel-left"
            tip: root.sidebarVisible ? "Скрыть боковую панель" : "Показать боковую панель"
            shortcutHint: "Ctrl+B"
            checked: root.sidebarVisible
            onClicked: root.toggleSidebar()
        }

        // логотип
        Rectangle {
            visible: !root.narrow
            width: Theme.size.control; height: width; radius: Theme.radius.md
            color: Theme.c.accent
            Label {
                anchors.centerIn: parent
                text: "THR"
                font.pixelSize: Theme.fontSize.xs
                font.weight: Theme.weight.bold
                color: Theme.c.accentText
            }
        }

        // имя пресета
        Item {
            Layout.fillWidth: true
            Layout.minimumWidth: Theme.space.xxxl * 2.5
            Layout.preferredWidth: Theme.space.xxxl * 6
            Layout.maximumWidth: Theme.space.xxxl * 8
            implicitHeight: Theme.size.control
            TextField {
                id: nameField
                anchors.fill: parent
                text: Backend.presetName
                font.pixelSize: Theme.fontSize.xl
                font.weight: Theme.weight.semibold
                color: Theme.c.text
                selectByMouse: true
                selectionColor: Theme.c.selection
                leftPadding: Theme.space.sm
                rightPadding: Theme.space.lg
                background: Rectangle {
                    radius: Theme.radius.md
                    color: nameField.activeFocus ? Theme.c.surface2 : nameField.hovered ? Theme.c.surface2 : "transparent"
                    border.width: nameField.activeFocus ? 1 : 0
                    border.color: Theme.c.accent
                }
                onEditingFinished: Backend.presetName = text
                Keys.onEscapePressed: { text = Backend.presetName; focus = false }
                ToolTip.visible: hovered && !activeFocus
                ToolTip.delay: 800
                ToolTip.text: "Имя звука (на комбик уходит латиницей, до 64 символов)"
            }
            Rectangle {
                visible: Backend.dirty
                width: Theme.space.sm; height: width; radius: width / 2
                color: Theme.c.accent
                x: Math.min(nameField.leftPadding + nameField.contentWidth + Theme.space.sm, parent.width - width - Theme.space.xs)
                anchors.verticalCenter: parent.verticalCenter
                ToolTip.visible: dirtyMa.containsMouse
                ToolTip.text: "Есть несохранённые изменения"
                MouseArea { id: dirtyMa; anchors.fill: parent; anchors.margins: -4; hoverEnabled: true }
            }
        }

        StatusPill {
            id: pill
            Layout.maximumWidth: root.narrow ? Theme.space.xxxl * 3.5 : Theme.space.xxxl * 6
            onClicked: root.connectionRequested(pill)
        }

        IconButton {
            iconName: "undo"
            enabled: Backend.canUndo
            tip: Backend.canUndo ? "Отменить: " + Backend.undoText : "Отменить"
            shortcutHint: "Ctrl+Z"
            onClicked: Backend.undo()
        }
        IconButton {
            iconName: "redo"
            enabled: Backend.canRedo
            tip: Backend.canRedo ? "Повторить: " + Backend.redoText : "Повторить"
            shortcutHint: "Ctrl+Y"
            onClicked: Backend.redo()
        }

        // A/B
        Rectangle {
            id: ab
            implicitWidth: abRow.implicitWidth + Theme.space.xs
            implicitHeight: Theme.size.control
            radius: Theme.radius.md
            color: Theme.c.surface2
            border.width: 1
            border.color: Theme.c.border
            ToolTip.visible: abHover.hovered
            ToolTip.delay: 500
            ToolTip.text: "A/B-сравнение: Пробел или B. Другой слот: " + Backend.abOtherName
            HoverHandler { id: abHover }
            Row {
                id: abRow
                anchors.centerIn: parent
                spacing: Theme.space.xxs
                Repeater {
                    model: ["A", "B"]
                    delegate: AbstractButton {
                        id: abBtn
                        required property string modelData
                        readonly property bool active: Backend.abActive === modelData
                        width: Theme.size.control - Theme.space.xs
                        height: Theme.size.control - Theme.space.sm
                        hoverEnabled: true
                        focusPolicy: Qt.StrongFocus
                        onClicked: Backend.selectAB(modelData)
                        Accessible.name: "Слот " + modelData
                        background: Rectangle {
                            radius: Theme.radius.sm
                            color: abBtn.active ? Theme.c.accent : abBtn.hovered ? Theme.c.surface3 : "transparent"
                            Behavior on color { ColorAnimation { duration: Theme.motion.fast } }
                        }
                        contentItem: Label {
                            text: abBtn.modelData
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                            font.pixelSize: Theme.fontSize.md
                            font.weight: Theme.weight.bold
                            color: abBtn.active ? Theme.c.accentText : Theme.c.textMuted
                        }
                    }
                }
            }
        }
        IconButton {
            iconName: "copy"
            visible: !root.narrow
            tip: "Скопировать текущий звук в другой слот A/B"
            shortcutHint: "Ctrl+Shift+C"
            onClicked: Backend.copyToOtherSlot()
        }

        Item { Layout.fillWidth: true }

        IconButton {
            iconName: "stage"
            tip: "Режим «Сцена» для сет-листа"
            shortcutHint: "F5"
            onClicked: root.stageRequested()
        }

        AppButton {
            visible: !root.narrow
            variant: "secondary"
            text: "Отправить"
            iconName: "send"
            enabled: Backend.hasTransport
            tip: "Отправить звук в текущее состояние комбика (Ctrl+Enter)"
            onClicked: Backend.sendToAmp()
        }
        IconButton { iconName: "import"; tip: "Открыть файл пресета (.thrpreset, .syx, .YDL)"; shortcutHint: "Ctrl+O"; onClicked: root.openRequested() }
        IconButton { iconName: "export"; tip: "Экспорт звука в файл"; shortcutHint: "Ctrl+E"; onClicked: root.exportRequested() }
        IconButton {
            iconName: Theme.dark ? "sun" : "moon"
            tip: Theme.dark ? "Светлая тема" : "Тёмная тема"
            shortcutHint: "Ctrl+Shift+L"
            onClicked: Theme.toggle()
        }
        IconButton { iconName: "log"; tip: "Журнал MIDI"; shortcutHint: "Ctrl+J"; visible: !root.narrow; onClicked: root.logRequested() }
        IconButton { iconName: "keyboard"; tip: "Горячие клавиши"; shortcutHint: "F1"; onClicked: root.shortcutsRequested() }
        IconButton { iconName: "settings"; tip: "Настройки"; shortcutHint: "Ctrl+,"; onClicked: root.settingsRequested() }
        IconButton {
            visible: root.hasTools
            iconName: "panel-right"
            tip: root.toolsVisible ? "Скрыть инструменты" : "Показать инструменты"
            shortcutHint: "Ctrl+T"
            checked: root.toolsVisible
            onClicked: root.toggleTools()
        }
    }
}
