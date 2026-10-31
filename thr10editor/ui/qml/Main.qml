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
    readonly property bool editing: !Backend.stageActive
    property var extraShortcuts: [
        { group: "Звук", seq: "Ctrl+Z", text: "Отменить", act: () => Backend.undo(), when: () => win.editing },
        { group: "Звук", seq: ["Ctrl+Y", "Ctrl+Shift+Z"], label: ["Ctrl+Y", "Ctrl+Shift+Z"], text: "Повторить", act: () => Backend.redo(), when: () => win.editing },
        { group: "Звук", seq: ["Space", "B"], label: ["Пробел", "B"], text: "A/B: переключить слот", act: () => Backend.toggleAB(), when: () => win.editing },
        { group: "Звук", seq: "Ctrl+Shift+C", text: "A/B: копировать текущий звук в другой слот", act: () => Backend.copyToOtherSlot(), when: () => win.editing },
        { group: "Звук", seq: "T", text: "Тап-темп дилея", act: () => Backend.tapTempo() },
        { group: "Звук", seq: "Ctrl+Shift+R", text: "Случайный звук (рандомайзер)", act: () => Backend.randomize(), when: () => win.editing },
        { group: "Звук", seq: "Ctrl+M", text: "Морфинг: старт / стоп", act: () => Backend.morphRunning ? Backend.stopMorph() : Backend.startMorph() },
        { group: "Звук", seq: "Ctrl+L", text: "Автоматизация (LFO): старт / стоп", act: () => Backend.toggleAutomation() },
        { group: "Библиотека", seq: "Ctrl+S", text: "Сохранить (обновить пресет или добавить в библиотеку)", act: () => win.save(), when: () => win.editing },
        { group: "Библиотека", seq: "Ctrl+Shift+S", text: "Сохранить как новый пресет", act: () => presetDialog.openNew(), when: () => win.editing },
        { group: "Библиотека", seq: "Ctrl+F", text: "Поиск в библиотеке", act: () => win.focusSearch(), when: () => win.editing },
        { group: "Вид", seq: "Ctrl+T", text: "Панель инструментов", act: () => win.toolsVisible = !win.toolsVisible },
        { group: "Сцена", seq: "F5", text: "Режим «Сцена» для текущего сет-листа", act: () => win.startStage(0), when: () => win.editing },
        { group: "Сцена", seq: ["Right", "Down", "PgDown", "Space"], label: ["→", "↓", "PgDn", "Пробел"], text: "Следующий пресет", act: () => Backend.stageNext(), when: () => Backend.stageActive },
        { group: "Сцена", seq: ["Left", "Up", "PgUp", "Backspace"], label: ["←", "↑", "PgUp"], text: "Предыдущий пресет", act: () => Backend.stagePrev(), when: () => Backend.stageActive },
        { group: "Сцена", seq: "Esc", text: "Выйти из режима «Сцена»", act: () => win.stopStage(), when: () => Backend.stageActive },
    ]
    readonly property var allShortcuts: shortcutList.concat(extraShortcuts)

    function save() {
        if (!Backend.saveCurrent())
            presetDialog.openNew()
    }
    signal searchRequested()
    function focusSearch() {
        if (compact) sideDrawer.open(); else sidebarVisible = true
        sidebar.currentIndex = 0
        searchRequested()
    }
    property int visibilityBeforeStage: Window.Windowed
    function startStage(index) {
        Backend.startStage(index)
        if (Backend.stageActive) {
            visibilityBeforeStage = visibility
            visibility = Window.FullScreen
        }
    }
    function stopStage() {
        Backend.stopStage()
        visibility = visibilityBeforeStage === Window.FullScreen ? Window.FullScreen
                   : visibilityBeforeStage === Window.Maximized ? Window.Maximized : Window.Windowed
    }

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
        visible: !Backend.stageActive
        sidebarVisible: win.compact ? sideDrawer.opened : win.sidebarVisible
        onToggleSidebar: win.toggleSidebar()
        onOpenRequested: openDialog.open()
        onExportRequested: exportDialog.open()
        onSettingsRequested: settingsDialog.open()
        onShortcutsRequested: shortcutsDialog.open()
        onLogRequested: logDrawer.opened ? logDrawer.close() : logDrawer.open()
        onConnectionRequested: (anchor) => connPopup.openAt(anchor)
        hasTools: true
        toolsVisible: win.toolsVisible
        onToggleTools: win.toolsVisible = !win.toolsVisible
        onStageRequested: win.startStage(0)
    }

    property var sidebarTabs: [
        { title: "Библиотека", component: libComp },
        { title: "Комбик", component: slotsComp },
        { title: "Сет-листы", component: setlistComp },
    ]
    Component { id: slotsComp; SlotsView { onWriteRequested: (i) => { writeDialog.slotIndex = i; writeDialog.open() } } }
    Component {
        id: libComp
        LibraryView {
            id: lv
            onEditRequested: (id) => presetDialog.openFor(id)
            onSaveRequested: win.save()
            Connections { target: win; function onSearchRequested() { lv.focusSearch() } }
        }
    }
    Component { id: setlistComp; SetlistView { onStageRequested: (i) => win.startStage(i) } }

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

    property var effectExtras: ({ "delay": tapComp })
    property Component toolsComponent: toolsComp
    property bool toolsVisible: Backend.getSetting("tools_visible") !== false
    onToolsVisibleChanged: Backend.setSetting("tools_visible", toolsVisible)

    Component { id: toolsComp; ToolsPanel { } }
    Component {
        id: tapComp
        AppButton {
            compact: true
            variant: "ghost"
            iconName: "tap"
            text: Backend.tapBpm > 0 ? Backend.tapBpm.toFixed(0) + " BPM" : "Tap"
            tip: "Тап-темп: нажимайте в такт (клавиша T). Доля: " + Backend.tapSubdivision
            onPressed: Backend.tapTempo()
        }
    }

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
    Menu {
        id: knobMenu
        MenuItem { text: "Сбросить к значению по умолчанию"; onTriggered: win.menuParam.reset() }
        MenuItem {
            text: win.menuParam && win.menuParam.locked ? "Снять замок рандомайзера" : "Замок для рандомайзера"
            onTriggered: win.menuParam.toggleLock()
        }
        MenuItem {
            text: win.menuParam && win.menuParam.automated ? "Убрать автоматизацию (LFO)" : "Автоматизация (LFO)"
            onTriggered: { Backend.toggleLfoForKey(win.menuParam.key); win.toolsVisible = true }
        }
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
    ImportDialog { id: importDialog; libraryAvailable: true; onAddAllRequested: Backend.addImportedToLibrary() }
    PresetDialog { id: presetDialog }
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

    StageView {
        anchors.fill: parent
        z: 500
    }

    Toasts {
        id: toasts
        anchors.bottom: parent.bottom
        anchors.bottomMargin: Theme.space.xl
        anchors.horizontalCenter: parent.horizontalCenter
        z: 1000
    }
}
