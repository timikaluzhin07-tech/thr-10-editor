import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Basic
import THR10
import "../components"

// Верхняя панель: знак, имя звука, связь, история, A/B, действия.
Rectangle {
    id: root
    property bool sidebarVisible: true
    property bool toolsVisible: true
    property bool hasTools: false
    readonly property bool narrow: width < Theme.space.xxxl * 24

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
    gradient: Gradient {
        GradientStop { position: 0.0; color: Theme.c.surfaceTop }
        GradientStop { position: 1.0; color: Theme.c.surface }
    }
    Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.c.border }

    component VDivider: Rectangle {
        Layout.preferredWidth: 1
        Layout.preferredHeight: Theme.size.control * 0.62
        Layout.leftMargin: Theme.space.xs
        Layout.rightMargin: Theme.space.xs
        color: Theme.c.border
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.space.md
        anchors.rightMargin: Theme.space.md
        spacing: Theme.space.xs

        IconButton {
            iconName: "panel-left"
            tip: root.sidebarVisible ? "Скрыть боковую панель" : "Показать боковую панель"
            shortcutHint: "Ctrl+B"
            checked: root.sidebarVisible
            onClicked: root.toggleSidebar()
        }

        LogoMark {
            visible: !root.narrow
            size: Theme.size.control * 0.82
            Layout.leftMargin: Theme.space.sm
            Layout.rightMargin: Theme.space.xs
        }

        // заголовок: подпись + имя звука (редактируется)
        Item {
            Layout.fillWidth: true
            Layout.minimumWidth: Theme.space.xxxl * 2.5
            Layout.preferredWidth: Theme.space.xxxl * 6
            Layout.maximumWidth: Theme.space.xxxl * 7
            implicitHeight: Theme.size.topbar - Theme.space.sm

            Label {
                id: caption
                x: Theme.space.sm
                y: Theme.space.xxs
                text: Backend.dirty ? "THR10 EDITOR  ·  ИЗМЕНЕНО" : "THR10 EDITOR"
                font.pixelSize: Theme.fontSize.xs * 0.95
                font.weight: Theme.weight.semibold
                font.letterSpacing: Theme.letterSpacing.caps
                color: Backend.dirty ? Theme.c.accent : Theme.c.textFaint
                Behavior on color { ColorAnimation { duration: Theme.motion.normal } }
            }
            TextField {
                id: nameField
                objectName: "presetNameField"
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                height: Theme.size.control * 0.95
                text: Backend.presetName
                font.pixelSize: Theme.fontSize.xl
                font.weight: Theme.weight.semibold
                font.letterSpacing: Theme.letterSpacing.tight * 0.4
                color: Theme.c.text
                selectByMouse: true
                selectionColor: Theme.c.selection
                leftPadding: Theme.space.sm
                rightPadding: Theme.space.sm
                topPadding: 0
                bottomPadding: Theme.space.xxs
                background: Rectangle {
                    radius: Theme.radius.md
                    color: nameField.activeFocus || nameField.hovered ? Theme.c.surface2 : "transparent"
                    border.width: nameField.activeFocus ? 1 : 0
                    border.color: Qt.rgba(Theme.c.accent.r, Theme.c.accent.g, Theme.c.accent.b, 0.7)
                    Behavior on color { ColorAnimation { duration: Theme.motion.fast } }
                }
                onEditingFinished: Backend.presetName = text
                Keys.onEscapePressed: { text = Backend.presetName; focus = false }
                ToolTip.visible: hovered && !activeFocus
                ToolTip.delay: 800
                ToolTip.text: "Имя звука (на комбик уходит латиницей, до 64 символов)"

                // мягкая смена имени при загрузке пресета
                property string shown: Backend.presetName
                onShownChanged: if (!activeFocus) nameFade.restart()
                SequentialAnimation {
                    id: nameFade
                    NumberAnimation { target: nameField; property: "opacity"; to: 0.15; duration: 60 }
                    NumberAnimation { target: nameField; property: "opacity"; to: 1; duration: Theme.motion.slow; easing.type: Easing.OutCubic }
                }
            }
        }

        VDivider { visible: !root.narrow }

        StatusPill {
            id: pill
            Layout.maximumWidth: root.narrow ? Theme.space.xxxl * 3.5 : Theme.space.xxxl * 5.5
            onClicked: root.connectionRequested(pill)
        }

        VDivider {}

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

        VDivider {}

        Segmented {
            id: ab
            small: true
            model: ["A", "B"]
            currentIndex: Backend.abActive === "A" ? 0 : 1
            onActivated: (i) => Backend.selectAB(i === 0 ? "A" : "B")
            implicitWidth: Theme.size.control * 2.3
            ToolTip.visible: abHover.hovered
            ToolTip.delay: 500
            ToolTip.text: "A/B-сравнение: Пробел или B. Другой слот: " + Backend.abOtherName
            HoverHandler { id: abHover }
        }
        IconButton {
            iconName: "copy"
            visible: !root.narrow
            tip: "Скопировать текущий звук в другой слот A/B"
            shortcutHint: "Ctrl+Shift+C"
            onClicked: Backend.copyToOtherSlot()
        }

        Item { objectName: "topBarSpacer"; Layout.fillWidth: true; Layout.fillHeight: true }

        IconButton {
            iconName: "stage"
            tip: "Режим «Сцена» для сет-листа"
            shortcutHint: "F5"
            onClicked: root.stageRequested()
        }
        AppButton {
            visible: !root.narrow
            compact: true
            text: "Отправить"
            iconName: "send"
            enabled: Backend.hasTransport
            tip: "Отправить звук в текущее состояние комбика (Ctrl+Enter)"
            onClicked: Backend.sendToAmp()
        }

        VDivider {}

        IconButton { iconName: "import"; tip: "Открыть файл пресета (.thrpreset, .syx, .YDL)"; shortcutHint: "Ctrl+O"; onClicked: root.openRequested() }
        IconButton { iconName: "export"; tip: "Экспорт звука в файл"; shortcutHint: "Ctrl+E"; onClicked: root.exportRequested() }

        VDivider { visible: !root.narrow }

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
