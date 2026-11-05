import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Basic
import QtQuick.Shapes
import THR10
import "../components"

// Режим «Сцена»: крупно текущий пресет, обложка, строй и аккорды, соседние треки.
// Клавиши обрабатываются на уровне всего режима (FocusScope), а не кнопками:
//   Пробел, →, ↓, PgDn — следующий трек;  ←, ↑, PgUp, Backspace — предыдущий;
//   Esc — выход. Кнопки режима не принимают фокус, поэтому пробел их не «нажимает».
FocusScope {
    id: root
    signal exitRequested()

    readonly property bool onImage: Backend.stageBackground !== ""
    readonly property color ink: onImage ? "#F3F4F6" : Theme.c.text
    readonly property color inkMuted: onImage ? "#D2D6DC" : Theme.c.textMuted
    readonly property color inkFaint: onImage ? "#AEB4BC" : Theme.c.textFaint

    visible: opacity > 0
    opacity: Backend.stageActive ? 1 : 0
    Behavior on opacity { NumberAnimation { duration: Theme.motion.slow; easing.type: Easing.OutCubic } }

    function takeFocus() { root.forceActiveFocus() }
    Connections {
        target: Backend
        function onStageChanged() { if (Backend.stageActive && !root.activeFocus) root.takeFocus() }
    }

    Keys.onPressed: (event) => {
        if (!Backend.stageActive) return
        switch (event.key) {
        case Qt.Key_Space: case Qt.Key_Right: case Qt.Key_Down: case Qt.Key_PageDown:
            Backend.stageNext(); event.accepted = true; break
        case Qt.Key_Left: case Qt.Key_Up: case Qt.Key_PageUp: case Qt.Key_Backspace:
            Backend.stagePrev(); event.accepted = true; break
        case Qt.Key_Escape:
            root.exitRequested(); event.accepted = true; break
        default:
            break
        }
    }

    Rectangle { anchors.fill: parent; color: Theme.c.bg }

    // фон трека (картинка или GIF): растягивается на весь экран без обрезки
    MediaImage {
        id: bg
        objectName: "stageBackground"
        anchors.fill: parent
        source: Backend.stageBackground
        gif: Backend.stageBackgroundGif
        fillMode: Image.Stretch
        visible: root.onImage && ready
        opacity: visible ? 1 : 0
        Behavior on opacity { NumberAnimation { duration: Theme.motion.slow } }
    }
    // затемнение поверх картинки — текст читается на любом фоне
    Rectangle {
        anchors.fill: parent
        visible: bg.visible
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#B3000000" }
            GradientStop { position: 0.5; color: "#8C000000" }
            GradientStop { position: 1.0; color: "#C7000000" }
        }
    }

    // тёплое свечение за именем (только на обычном фоне темы)
    Shape {
        anchors.fill: parent
        visible: !root.onImage
        preferredRendererType: Shape.CurveRenderer
        ShapePath {
            strokeWidth: -1
            strokeColor: "transparent"
            fillGradient: RadialGradient {
                centerX: root.width / 2
                centerY: root.height * 0.42
                centerRadius: Math.max(root.width, root.height) * 0.55
                focalX: centerX
                focalY: centerY
                GradientStop { position: 0.0; color: Theme.c.bgGlow }
                GradientStop { position: 1.0; color: "transparent" }
            }
            startX: 0; startY: 0
            PathLine { x: root.width; y: 0 }
            PathLine { x: root.width; y: root.height }
            PathLine { x: 0; y: root.height }
            PathLine { x: 0; y: 0 }
        }
    }

    // клики не уходят в редактор; любой клик возвращает фокус режиму сцены
    MouseArea {
        anchors.fill: parent
        acceptedButtons: Qt.AllButtons
        onPressed: root.takeFocus()
        onWheel: (w) => w.accepted = true
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.space.xxxl
        spacing: Theme.space.lg

        RowLayout {
            Layout.fillWidth: true
            Label {
                text: Backend.currentSetlistName
                color: root.inkMuted
                font.pixelSize: Theme.fontSize.xl
                font.weight: Theme.weight.medium
                Layout.fillWidth: true
                elide: Text.ElideRight
            }
            StatusPill { focusPolicy: Qt.NoFocus }
            AppButton {
                focusPolicy: Qt.NoFocus
                text: "Выйти (Esc)"
                iconName: "close"
                onClicked: root.exitRequested()
            }
        }

        Item { Layout.fillHeight: true; Layout.preferredHeight: 1 }

        Label {
            Layout.fillWidth: true
            horizontalAlignment: Text.AlignHCenter
            text: String(Backend.stageIndex + 1).padStart(2, "0") + "  /  " + String(Backend.stageCount).padStart(2, "0")
            color: root.onImage ? "#F2B35A" : Theme.c.accent
            font.pixelSize: Theme.fontSize.stageSub * 0.8
            font.weight: Theme.weight.semibold
            font.letterSpacing: Theme.letterSpacing.caps
            font.features: { "tnum": 1 }
        }
        // обложка трека: по центру поверх фона, в своих пропорциях
        Item {
            id: coverBox
            visible: Backend.stageCover !== ""
            Layout.fillWidth: true
            Layout.preferredHeight: root.height * (Backend.stageChords !== "" ? 0.2 : 0.3)
            Layout.minimumHeight: Theme.size.control * 2
            Layout.topMargin: Theme.space.sm
            Layout.bottomMargin: Theme.space.sm
            Rectangle {
                id: coverFrame
                anchors.centerIn: parent
                height: Math.min(parent.height, parent.width / cover.aspect)
                width: height * cover.aspect
                radius: Theme.radius.lg
                color: "#33000000"
                border.width: 1
                border.color: root.onImage ? "#4DFFFFFF" : Theme.c.borderStrong
                opacity: cover.ready ? 1 : 0
                Behavior on opacity { NumberAnimation { duration: Theme.motion.slow } }
                MediaImage {
                    id: cover
                    objectName: "stageCover"
                    anchors.fill: parent
                    anchors.margins: 1
                    source: Backend.stageCover
                    gif: Backend.stageCoverGif
                    fillMode: Image.Stretch
                }
            }
        }
        Label {
            id: current
            Layout.fillWidth: true
            horizontalAlignment: Text.AlignHCenter
            text: Backend.presetName
            color: root.ink
            font.pixelSize: Math.min(Theme.fontSize.stage, root.width / Math.max(6, text.length) * 1.6)
            font.weight: Theme.weight.bold
            font.letterSpacing: Theme.letterSpacing.tight
            wrapMode: Text.Wrap
            maximumLineCount: 2
            elide: Text.ElideRight
            Behavior on text {
                SequentialAnimation {
                    NumberAnimation { target: current; property: "opacity"; to: 0.2; duration: 60 }
                    PropertyAction {}
                    NumberAnimation { target: current; property: "opacity"; to: 1; duration: Theme.motion.normal }
                }
            }
        }
        Label {
            Layout.fillWidth: true
            horizontalAlignment: Text.AlignHCenter
            text: Backend.stageSummary
            color: root.inkMuted
            font.pixelSize: Theme.fontSize.stageSub * 0.85
        }

        // строй гитары
        Rectangle {
            visible: Backend.stageTuning !== ""
            Layout.alignment: Qt.AlignHCenter
            Layout.topMargin: Theme.space.md
            implicitWidth: tuningRow.implicitWidth + Theme.space.xl * 2
            implicitHeight: tuningRow.implicitHeight + Theme.space.md * 2
            radius: Theme.radius.lg
            color: root.onImage ? "#59000000" : Theme.c.surface2
            border.width: 1
            border.color: root.onImage ? "#4DFFFFFF" : Theme.c.borderStrong
            Row {
                id: tuningRow
                anchors.centerIn: parent
                spacing: Theme.space.md
                Label {
                    anchors.verticalCenter: parent.verticalCenter
                    text: "СТРОЙ"
                    color: root.inkFaint
                    font.pixelSize: Theme.fontSize.sm * 1.2
                    font.weight: Theme.weight.semibold
                    font.letterSpacing: Theme.letterSpacing.caps
                }
                Label {
                    anchors.verticalCenter: parent.verticalCenter
                    text: Backend.stageTuning
                    color: root.ink
                    font.pixelSize: Theme.fontSize.stageSub * 1.25
                    font.weight: Theme.weight.bold
                }
            }
        }

        // аккорды: крупно, шрифт уменьшается, если текста много
        Label {
            id: chords
            visible: Backend.stageChords !== ""
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.preferredHeight: root.height * 0.3
            Layout.maximumHeight: root.height * 0.38
            Layout.topMargin: Theme.space.sm
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignTop
            text: Backend.stageChords
            color: root.ink
            wrapMode: Text.Wrap
            fontSizeMode: Text.Fit
            font.pixelSize: Theme.fontSize.stageSub * 1.6
            minimumPixelSize: Theme.fontSize.md
            font.weight: Theme.weight.semibold
            lineHeight: 1.15
        }

        Item { Layout.fillHeight: true; Layout.preferredHeight: 1 }

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.space.xl
            component NavCard: Rectangle {
                id: nc
                property string caption
                property string name
                property bool forward
                signal activated()
                Layout.fillWidth: true
                Layout.preferredHeight: Theme.size.controlLarge * 2.6
                radius: Theme.radius.lg
                color: root.onImage ? (navMa.containsMouse ? "#80000000" : "#59000000") : "transparent"
                gradient: root.onImage ? null : themed
                Gradient {
                    id: themed
                    GradientStop { position: 0.0; color: navMa.containsMouse ? Theme.c.surface3 : Theme.c.surfaceTop }
                    GradientStop { position: 1.0; color: navMa.pressed ? Theme.c.surface3 : Theme.c.surface }
                }
                border.width: 1
                border.color: root.onImage ? "#40FFFFFF" : navMa.containsMouse ? Theme.c.borderStrong : Theme.c.border
                opacity: name ? 1 : 0.35
                MouseArea {
                    id: navMa
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: { nc.activated(); root.takeFocus() }
                }
                RowLayout {
                    anchors.fill: parent
                    anchors.margins: Theme.space.xl
                    spacing: Theme.space.lg
                    layoutDirection: nc.forward ? Qt.RightToLeft : Qt.LeftToRight
                    Icon { name: nc.forward ? "chevron-right" : "chevron-left"; size: Theme.size.icon * 2.4; color: root.inkMuted }
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: Theme.space.xs
                        Label {
                            Layout.fillWidth: true
                            horizontalAlignment: nc.forward ? Text.AlignRight : Text.AlignLeft
                            text: nc.caption
                            color: root.inkFaint
                            font.pixelSize: Theme.fontSize.md
                        }
                        Label {
                            Layout.fillWidth: true
                            horizontalAlignment: nc.forward ? Text.AlignRight : Text.AlignLeft
                            text: nc.name || "—"
                            color: root.ink
                            font.pixelSize: Theme.fontSize.stageSub
                            font.weight: Theme.weight.semibold
                            elide: Text.ElideRight
                        }
                    }
                }
            }
            NavCard { caption: "Предыдущий  ←"; name: Backend.stagePrevName; onActivated: Backend.stagePrev() }
            NavCard { caption: "Следующий  →  / Пробел"; name: Backend.stageNextName; forward: true; onActivated: Backend.stageNext() }
        }
    }
}
