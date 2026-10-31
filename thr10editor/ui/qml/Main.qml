import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Basic
import QtQuick.Dialogs
import QtQuick.Window
import THR10
import "components"
import "views"

ApplicationWindow {
    id: win
    visible: true
    width: 1360
    height: 860
    minimumWidth: 720
    minimumHeight: 520
    title: (Backend.dirty ? "• " : "") + Backend.presetName + " — " + Backend.appName
    color: Theme.c.bg
    font.family: Theme.fontFamily
    font.pixelSize: Theme.fontSize.md

    Behavior on color { ColorAnimation { duration: Theme.motion.theme } }

    onWidthChanged: Theme.updateWindowSize(width, height)
    onHeightChanged: Theme.updateWindowSize(width, height)
    Component.onCompleted: Theme.updateWindowSize(width, height)

    property bool sidebarVisible: Backend.getSetting("sidebar_visible") !== false
    readonly property bool compact: width < 980
    onSidebarVisibleChanged: Backend.setSetting("sidebar_visible", sidebarVisible)

    // ---- горячие клавиши (один список и для Shortcut, и для справки) --------
    property var shortcutList: [
        { group: "Файл", seq: "Ctrl+N", text: "Новый звук (всё по умолчанию)", act: () => Backend.newSound() },
        { group: "Файл", seq: "Ctrl+O", text: "Открыть файл (.thrpreset, .syx, .YDL)", act: () => openDialog.open() },
        { group: "Файл", seq: "Ctrl+E", text: "Экспорт звука в файл", act: () => exportDialog.open() },
        { group: "Комбик", seq: "Ctrl+Return", label: ["Ctrl+Enter"], text: "Отправить звук в комбик", act: () => Backend.sendToAmp() },
        { group: "Комбик", seq: "Ctrl+D", text: "Считать состояние с комбика", act: () => Backend.requestState() },
        { group: "Комбик", seq: "Ctrl+K", text: "Подключение / выбор порта", act: () => connPopup.openAt(null) },
        { group: "Вид", seq: "Ctrl+Shift+L", text: "Тёмная / светлая тема", act: () => Theme.toggle() },
        { group: "Вид", seq: "Ctrl+B", text: "Боковая панель", act: () => win.toggleSidebar() },
        { group: "Вид", seq: ["Ctrl+=", "Ctrl++"], label: ["Ctrl +"], text: "Крупнее", act: () => Theme.zoomIn() },
        { group: "Вид", seq: "Ctrl+-", label: ["Ctrl −"], text: "Мельче", act: () => Theme.zoomOut() },
        { group: "Вид", seq: "Ctrl+0", text: "Масштаб 100%", act: () => Theme.zoomReset() },
        { group: "Вид", seq: "F11", text: "Во весь экран", act: () => win.toggleFullScreen() },
        { group: "Вид", seq: "Ctrl+J", text: "Журнал MIDI", act: () => logDrawer.opened ? logDrawer.close() : logDrawer.open() },
        { group: "Вид", seq: "Ctrl+,", text: "Настройки", act: () => settingsDialog.open() },
        { group: "Вид", seq: "F1", text: "Горячие клавиши", act: () => shortcutsDialog.open() },
        { group: "Ручка (в фокусе)", seq: "", label: ["↑ ↓"], text: "Изменить значение (Shift — точно)" },
        { group: "Ручка (в фокусе)", seq: "", label: ["PgUp", "PgDn"], text: "Крупный шаг" },
        { group: "Ручка (в фокусе)", seq: "", label: ["Home", "End"], text: "Минимум / максимум" },
        { group: "Ручка (в фокусе)", seq: "", label: ["Del"], text: "Значение по умолчанию (или двойной клик)" },
        { group: "Ручка (в фокусе)", seq: "", label: ["Enter"], text: "Ввести значение с клавиатуры" },
    ]
    property var extraShortcuts: []
    readonly property var allShortcuts: shortcutList.concat(extraShortcuts)

    function toggleSidebar() {
        if (compact)
            sideDrawer.opened ? sideDrawer.close() : sideDrawer.open()
        else
            sidebarVisible = !sidebarVisible
    }

    function toggleFullScreen() {
        visibility = visibility === Window.FullScreen ? Window.Windowed : Window.FullScreen
    }

    Instantiator {
        model: win.allShortcuts
        delegate: Shortcut {
            required property var modelData
            sequences: modelData.seq ? (Array.isArray(modelData.seq) ? modelData.seq : [modelData.seq]) : []
            enabled: modelData.seq !== "" && modelData.act !== undefined && (modelData.when === undefined || modelData.when())
            context: Qt.ApplicationShortcut
            onActivated: modelData.act()
        }
    }

    // ---- раскладка ---------------------------------------------------------
    header: TopBar {
        id: topBar
        sidebarVisible: win.compact ? sideDrawer.opened : win.sidebarVisible
        onToggleSidebar: win.toggleSidebar()
        onOpenRequested: openDialog.open()
        onExportRequested: exportDialog.open()
        onSettingsRequested: settingsDialog.open()
        onShortcutsRequested: shortcutsDialog.open()
        onLogRequested: logDrawer.opened ? logDrawer.close() : logDrawer.open()
        onConnectionRequested: (anchor) => connPopup.openAt(anchor)
    }

    property var sidebarTabs: [
        { title: "Комбик", component: slotsComp },
    ]
    Component { id: slotsComp; SlotsView { onWriteRequested: (i) => { writeDialog.slotIndex = i; writeDialog.open() } } }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        Sidebar {
            id: sidebar
            Layout.fillHeight: true
            Layout.preferredWidth: Theme.size.sidebar
            visible: win.sidebarVisible && !win.compact
            tabs: win.sidebarTabs
        }

        Flickable {
            id: center
            Layout.fillWidth: true
            Layout.fillHeight: true
            contentHeight: centerCol.implicitHeight + Theme.space.xl * 2
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: ScrollBar {}

            ColumnLayout {
                id: centerCol
                x: Theme.space.xl
                y: Theme.space.xl
                width: center.width - Theme.space.xl * 2
                spacing: Theme.space.lg

                AmpPanel {
                    Layout.fillWidth: true
                    onKnobContext: (p, k, x, y) => win.showKnobMenu(p, k, x, y)
                }
                EffectsGrid {
                    id: effects
                    Layout.fillWidth: true
                    Layout.preferredHeight: implicitHeight
                    extras: win.effectExtras
                    onKnobContext: (p, k, x, y) => win.showKnobMenu(p, k, x, y)
                }
            }
        }

        Loader {
            id: toolsLoader
            Layout.fillHeight: true
            Layout.preferredWidth: Theme.size.toolpanel
            active: win.toolsComponent !== null
            visible: active && win.toolsVisible && !win.compact
            sourceComponent: win.toolsComponent
        }
    }

    property var effectExtras: ({})
    property Component toolsComponent: null
    property bool toolsVisible: true

    // Боковая панель на узком окне — выезжающая
    Drawer {
        id: sideDrawer
        edge: Qt.LeftEdge
        width: Math.min(Theme.size.sidebar * 1.1, win.width * 0.85)
        height: win.height - topBar.height
        y: topBar.height
        modal: true
        background: Rectangle { color: Theme.c.surface }
        Sidebar {
            anchors.fill: parent
            tabs: win.sidebarTabs
        }
    }

    // ---- контекстное меню ручки --------------------------------------------
    property QtObject menuParam: null
    function showKnobMenu(p, knob, x, y) {
        menuParam = p
        const pt = knob.mapToItem(win.contentItem, x, y)
        knobMenu.x = pt.x
        knobMenu.y = pt.y
        knobMenu.open()
    }
    property list<QtObject> knobMenuExtra
    Menu {
        id: knobMenu
        MenuItem { text: "Сбросить к значению по умолчанию"; onTriggered: win.menuParam.reset() }
        MenuItem { text: "Ввести значение…"; enabled: false; visible: false }
    }

    // ---- всплывающие окна -------------------------------------------------
    ConnectionPopup {
        id: connPopup
        function openAt(anchor) {
            if (anchor) {
                const pt = anchor.mapToItem(win.contentItem, 0, anchor.height)
                x = Math.max(Theme.space.sm, Math.min(pt.x, win.width - width - Theme.space.sm))
                y = pt.y + Theme.space.xs - topBar.height
            } else {
                x = (win.width - width) / 2
                y = Theme.space.lg
            }
            open()
        }
    }
    SettingsDialog { id: settingsDialog }
    ShortcutsDialog { id: shortcutsDialog; shortcuts: win.allShortcuts }
    ImportDialog { id: importDialog }
    LogDrawer { id: logDrawer }

    AppDialog {
        id: writeDialog
        property int slotIndex: 0
        title: "Сохранение в ячейку " + (slotIndex + 1)
        maxWidth: Theme.space.xxxl * 10
        Label {
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            color: Theme.c.text
            text: "Звук отправлен в текущее состояние комбика.\n\nЧтобы сохранить его в ячейку " + (writeDialog.slotIndex + 1)
                  + ", удерживайте кнопку " + (writeDialog.slotIndex + 1) + " на комбике около 2 секунд (см. руководство THR)."
                  + "\n\nПрямая SysEx-команда записи в ячейку в открытых источниках не найдена, поэтому редактор её не отправляет (docs/PROTOCOL.md, раздел 6)."
        }
        footer: [
            Item { Layout.fillWidth: true },
            AppButton {
                visible: Backend.isDemo
                text: "Удержать кнопку на демо-комбике"
                onClicked: { Backend.demoStoreSlot(writeDialog.slotIndex); writeDialog.close() }
            },
            AppButton { variant: "primary"; text: "Понятно"; onClicked: writeDialog.close() }
        ]
    }

    FileDialog {
        id: openDialog
        title: "Открыть пресет"
        fileMode: FileDialog.OpenFile
        nameFilters: ["Все поддерживаемые (*.thrpreset *.json *.syx *.ydl *.YDL)",
                      "Пресет THR10 Editor (*.thrpreset *.json)",
                      "SysEx (*.syx)", "Библиотека THR Editor (*.ydl *.YDL)", "Все файлы (*)"]
        onAccepted: Backend.openFile(selectedFile)
    }
    FileDialog {
        id: exportDialog
        title: "Экспорт звука"
        fileMode: FileDialog.SaveFile
        nameFilters: ["Пресет THR10 Editor (*.thrpreset)", "SysEx-дамп (*.syx)", "Библиотека THR Editor (*.YDL)"]
        defaultSuffix: ["thrpreset", "syx", "YDL"][Math.max(0, selectedNameFilter.index)]
        onAccepted: Backend.exportCurrent(selectedFile, ["thrpreset", "syx", "ydl"][Math.max(0, selectedNameFilter.index)])
    }

    Connections {
        target: Backend
        function onToast(kind, text) { toasts.show(kind, text) }
        function onImportReady() { importDialog.open() }
    }

    Toasts {
        id: toasts
        anchors.bottom: parent.bottom
        anchors.bottomMargin: Theme.space.xl
        anchors.horizontalCenter: parent.horizontalCenter
        z: 1000
    }
}
