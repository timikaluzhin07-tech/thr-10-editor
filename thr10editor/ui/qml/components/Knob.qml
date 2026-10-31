import QtQuick
import QtQuick.Shapes
import QtQuick.Controls.Basic
import THR10

// Ручка параметра.
//  * перетаскивание вверх/вниз (и вбок), Shift — точная подстройка ×0,1;
//  * колесо мыши (Shift — точно);
//  * двойной клик — значение по умолчанию;
//  * клик по числу — ввод с клавиатуры (в единицах отображения);
//  * стрелки, PgUp/PgDn, Home/End, Delete (сброс), Enter (ввод) при фокусе;
//  * правый клик — меню (сброс, замок рандомайзера, LFO).
FocusScope {
    id: root

    property QtObject param: null
    property color accent: Theme.c.accent
    property real diameter: Theme.size.knob
    property bool dimmed: false

    signal contextRequested(QtObject param, real x, real y)

    readonly property bool dragging: dragArea.pressed && dragArea.dragMoved
    property real shownPos: param ? param.position : 0
    Behavior on shownPos {
        enabled: !dragArea.pressed
        NumberAnimation { duration: Theme.motion.fast; easing.type: Easing.OutCubic }
    }

    implicitWidth: Math.max(diameter + Theme.space.sm, labelText.implicitWidth)
    implicitHeight: column.implicitHeight
    activeFocusOnTab: true
    opacity: dimmed ? 0.55 : 1.0
    Behavior on opacity { NumberAnimation { duration: Theme.motion.normal } }

    Accessible.role: Accessible.Dial
    Accessible.name: param ? param.label : ""
    Accessible.description: param ? param.text : ""

    Column {
        id: column
        anchors.horizontalCenter: parent.horizontalCenter
        spacing: Theme.space.xs

        Label {
            id: labelText
            anchors.horizontalCenter: parent.horizontalCenter
            text: root.param ? root.param.label.toUpperCase() : ""
            font.pixelSize: Theme.fontSize.xs
            font.weight: Theme.weight.semibold
            font.letterSpacing: Theme.letterSpacing.caps
            color: root.activeFocus ? root.accent : Theme.c.textMuted
            Behavior on color { ColorAnimation { duration: Theme.motion.fast } }
        }

        Item {
            id: dial
            width: root.diameter
            height: root.diameter
            anchors.horizontalCenter: parent.horizontalCenter

            readonly property real stroke: Theme.size.knobStroke
            readonly property real r: width / 2 - stroke / 2 - 1

            // фокус
            Rectangle {
                anchors.centerIn: parent
                width: parent.width + Theme.size.focusRing * 4
                height: width
                radius: width / 2
                color: "transparent"
                border.width: Theme.size.focusRing
                border.color: Theme.c.focus
                visible: root.activeFocus && !dragArea.pressed
                opacity: 0.6
            }

            Shape {
                anchors.fill: parent
                preferredRendererType: Shape.CurveRenderer
                // дорожка
                ShapePath {
                    strokeColor: Theme.c.knobTrack
                    strokeWidth: dial.stroke
                    fillColor: "transparent"
                    capStyle: ShapePath.RoundCap
                    PathAngleArc {
                        centerX: dial.width / 2; centerY: dial.height / 2
                        radiusX: dial.r; radiusY: dial.r
                        startAngle: 135; sweepAngle: 270
                    }
                }
                // значение
                ShapePath {
                    strokeColor: root.accent
                    strokeWidth: dial.stroke
                    fillColor: "transparent"
                    capStyle: ShapePath.RoundCap
                    PathAngleArc {
                        centerX: dial.width / 2; centerY: dial.height / 2
                        radiusX: dial.r; radiusY: dial.r
                        startAngle: 135; sweepAngle: Math.max(0.01, 270 * root.shownPos)
                    }
                }
            }

            // метка значения по умолчанию
            Rectangle {
                readonly property real a: (135 + 270 * (root.param ? root.param.defaultPosition : 0)) * Math.PI / 180
                width: 3; height: 3; radius: 1.5
                color: Theme.c.textFaint
                x: dial.width / 2 + (dial.r + dial.stroke) * Math.cos(a) - width / 2
                y: dial.height / 2 + (dial.r + dial.stroke) * Math.sin(a) - height / 2
            }

            // лицевая часть
            Rectangle {
                id: face
                anchors.centerIn: parent
                width: parent.width * 0.64
                height: width
                radius: width / 2
                color: dragArea.containsMouse || dragArea.pressed ? Theme.c.surface3 : Theme.c.knobFace
                border.width: 1
                border.color: Theme.c.border
                Behavior on color { ColorAnimation { duration: Theme.motion.fast } }

                Item {
                    anchors.fill: parent
                    rotation: -135 + 270 * root.shownPos
                    Rectangle {
                        width: Math.max(2, face.width * 0.07)
                        height: face.height * 0.3
                        radius: width / 2
                        color: Theme.c.knobPointer
                        anchors.horizontalCenter: parent.horizontalCenter
                        y: face.height * 0.08
                    }
                }
            }

            // замок рандомайзера
            Rectangle {
                visible: root.param && root.param.locked
                width: Theme.size.icon; height: width; radius: width / 2
                color: Theme.c.surface2
                border.color: Theme.c.border
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.rightMargin: -Theme.space.xs
                Icon { anchors.centerIn: parent; name: "lock"; size: parent.width * 0.62; color: Theme.c.textMuted }
            }

            // LFO
            Rectangle {
                visible: root.param && root.param.automated
                width: Theme.size.icon; height: width; radius: width / 2
                color: Theme.c.surface2
                border.color: root.accent
                anchors.left: parent.left
                anchors.top: parent.top
                anchors.leftMargin: -Theme.space.xs
                Icon { anchors.centerIn: parent; name: "wave"; size: parent.width * 0.62; color: root.accent }
            }

            MouseArea {
                id: dragArea
                anchors.fill: parent
                hoverEnabled: true
                acceptedButtons: Qt.LeftButton | Qt.RightButton
                cursorShape: Qt.SizeVerCursor
                preventStealing: true
                property real lastX: 0
                property real lastY: 0
                property real dragPos: 0
                property bool dragMoved: false
                property real wheelAccum: 0

                onPressed: (mouse) => {
                    root.forceActiveFocus()
                    if (mouse.button === Qt.RightButton) {
                        root.contextRequested(root.param, mouse.x, mouse.y)
                        return
                    }
                    lastX = mouse.x; lastY = mouse.y
                    dragPos = root.param ? root.param.position : 0
                    dragMoved = false
                    if (root.param) root.param.beginGesture()
                }
                onPositionChanged: (mouse) => {
                    if (!pressed || !root.param || (mouse.buttons & Qt.LeftButton) === 0) return
                    const fine = (mouse.modifiers & Qt.ShiftModifier) ? 0.1 : 1.0
                    const delta = (lastY - mouse.y) + (mouse.x - lastX)
                    lastX = mouse.x; lastY = mouse.y
                    if (delta === 0) return
                    dragMoved = true
                    dragPos = Math.max(0, Math.min(1, dragPos + delta * fine / (Theme.scale * 220)))
                    root.param.setPosition(dragPos)
                }
                onReleased: (mouse) => {
                    if (mouse.button === Qt.LeftButton && root.param) root.param.endGesture()
                }
                onCanceled: if (root.param) root.param.endGesture()
                onDoubleClicked: (mouse) => {
                    if (mouse.button === Qt.LeftButton && root.param) root.param.reset()
                }
                onWheel: (wheel) => {
                    if (!root.param) return
                    const d = wheel.angleDelta.y !== 0 ? wheel.angleDelta.y : wheel.angleDelta.x
                    wheelAccum += d
                    const notches = Math.trunc(wheelAccum / 120)
                    if (notches === 0) return
                    wheelAccum -= notches * 120
                    const st = (wheel.modifiers & Qt.ShiftModifier) ? root.param.fineStep : root.param.coarseStep
                    root.param.beginGesture()
                    root.param.step(notches * st)
                    root.param.endGesture()
                }
            }

            ToolTip.visible: dragArea.containsMouse && !dragArea.pressed && root.param !== null && root.param.hint !== ""
            ToolTip.delay: 900
            ToolTip.text: root.param ? root.param.hint + "\nДвойной клик — сброс, Shift — точно" : ""
        }

        // значение / ввод
        Item {
            width: Math.max(root.diameter, valueLabel.implicitWidth)
            height: valueLabel.implicitHeight + Theme.space.xs
            anchors.horizontalCenter: parent.horizontalCenter

            Label {
                id: valueLabel
                anchors.centerIn: parent
                visible: !editor.visible
                text: root.param ? root.param.text : ""
                font.pixelSize: Theme.fontSize.sm
                font.weight: Theme.weight.medium
                font.features: { "tnum": 1 }
                color: root.dragging ? root.accent : Theme.c.text
                Behavior on color { ColorAnimation { duration: Theme.motion.fast } }
                MouseArea {
                    anchors.fill: parent
                    anchors.margins: -Theme.space.xs
                    cursorShape: Qt.IBeamCursor
                    onClicked: root.startEdit()
                }
            }

            TextField {
                id: editor
                visible: false
                anchors.centerIn: parent
                width: Math.max(root.diameter, implicitWidth)
                horizontalAlignment: TextInput.AlignHCenter
                font.pixelSize: Theme.fontSize.sm
                color: Theme.c.text
                selectByMouse: true
                padding: Theme.space.xxs
                background: Rectangle {
                    radius: Theme.radius.sm
                    color: Theme.c.surface2
                    border.width: 1
                    border.color: editor.bad ? Theme.c.danger : Theme.c.accent
                }
                property bool bad: false
                onAccepted: {
                    if (root.param && root.param.setFromText(text)) {
                        visible = false
                        root.forceActiveFocus()
                    } else {
                        bad = true
                    }
                }
                onTextEdited: bad = false
                onActiveFocusChanged: if (!activeFocus) visible = false
                Keys.onEscapePressed: { visible = false; root.forceActiveFocus() }
            }
        }
    }

    function startEdit() {
        if (!param) return
        editor.text = param.text
        editor.bad = false
        editor.visible = true
        editor.forceActiveFocus()
        editor.selectAll()
    }

    Keys.onPressed: (event) => {
        if (!param) return
        const fine = (event.modifiers & Qt.ShiftModifier) !== 0
        const st = fine ? param.fineStep : param.coarseStep
        let handled = true
        switch (event.key) {
        case Qt.Key_Up: case Qt.Key_Right: param.beginGesture(); param.step(st); param.endGesture(); break
        case Qt.Key_Down: case Qt.Key_Left: param.beginGesture(); param.step(-st); param.endGesture(); break
        case Qt.Key_PageUp: param.beginGesture(); param.step(st * 10); param.endGesture(); break
        case Qt.Key_PageDown: param.beginGesture(); param.step(-st * 10); param.endGesture(); break
        case Qt.Key_Home: param.beginGesture(); param.setValue(param.minimum); param.endGesture(); break
        case Qt.Key_End: param.beginGesture(); param.setValue(param.maximum); param.endGesture(); break
        case Qt.Key_Delete: case Qt.Key_Backspace: param.reset(); break
        case Qt.Key_Return: case Qt.Key_Enter: startEdit(); break
        default: handled = false
        }
        event.accepted = handled
    }
}
