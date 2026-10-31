import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Basic
import QtQuick.Shapes
import THR10
import "../components"

// Режим «Сцена»: крупно текущий пресет, соседние, навигация.
Rectangle {
    id: root
    color: Theme.c.bg
    visible: opacity > 0
    opacity: Backend.stageActive ? 1 : 0
    Behavior on opacity { NumberAnimation { duration: Theme.motion.slow; easing.type: Easing.OutCubic } }

    // тёплое свечение за именем пресета
    Shape {
        anchors.fill: parent
        preferredRendererType: Shape.CurveRenderer
        ShapePath {
            strokeWidth: -1
            strokeColor: "transparent"
            fillGradient: RadialGradient {
                centerX: root.width / 2
                centerY: root.height * 0.45
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

    // перехват мыши, чтобы клики не уходили в редактор
    MouseArea { anchors.fill: parent; acceptedButtons: Qt.AllButtons; onWheel: (w) => w.accepted = true }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.space.xxxl
        spacing: Theme.space.xl

        RowLayout {
            Layout.fillWidth: true
            Label {
                text: Backend.currentSetlistName
                color: Theme.c.textMuted
                font.pixelSize: Theme.fontSize.xl
                font.weight: Theme.weight.medium
                Layout.fillWidth: true
                elide: Text.ElideRight
            }
            StatusPill { }
            AppButton { text: "Выйти (Esc)"; iconName: "close"; onClicked: Backend.stopStage() }
        }

        Item { Layout.fillHeight: true }

        Label {
            Layout.fillWidth: true
            horizontalAlignment: Text.AlignHCenter
            text: String(Backend.stageIndex + 1).padStart(2, "0") + "  /  " + String(Backend.stageCount).padStart(2, "0")
            color: Theme.c.accent
            font.pixelSize: Theme.fontSize.stageSub * 0.8
            font.weight: Theme.weight.semibold
            font.letterSpacing: Theme.letterSpacing.caps
            font.features: { "tnum": 1 }
        }
        Label {
            id: current
            Layout.fillWidth: true
            horizontalAlignment: Text.AlignHCenter
            text: Backend.presetName
            color: Theme.c.text
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
            color: Theme.c.textMuted
            font.pixelSize: Theme.fontSize.stageSub
        }

        Item { Layout.fillHeight: true }

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
                gradient: Gradient {
                    GradientStop { position: 0.0; color: navMa.containsMouse ? Theme.c.surface3 : Theme.c.surfaceTop }
                    GradientStop { position: 1.0; color: navMa.pressed ? Theme.c.surface3 : Theme.c.surface }
                }
                border.width: 1
                border.color: navMa.containsMouse ? Theme.c.borderStrong : Theme.c.border
                opacity: name ? 1 : 0.35
                MouseArea { id: navMa; anchors.fill: parent; hoverEnabled: true; onClicked: nc.activated() }
                RowLayout {
                    anchors.fill: parent
                    anchors.margins: Theme.space.xl
                    spacing: Theme.space.lg
                    layoutDirection: nc.forward ? Qt.RightToLeft : Qt.LeftToRight
                    Icon { name: nc.forward ? "chevron-right" : "chevron-left"; size: Theme.size.icon * 2.4; color: Theme.c.textMuted }
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: Theme.space.xs
                        Label {
                            Layout.fillWidth: true
                            horizontalAlignment: nc.forward ? Text.AlignRight : Text.AlignLeft
                            text: nc.caption
                            color: Theme.c.textFaint
                            font.pixelSize: Theme.fontSize.md
                        }
                        Label {
                            Layout.fillWidth: true
                            horizontalAlignment: nc.forward ? Text.AlignRight : Text.AlignLeft
                            text: nc.name || "—"
                            color: Theme.c.text
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
