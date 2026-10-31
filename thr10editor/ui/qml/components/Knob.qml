import QtQuick
import QtQuick.Shapes
import QtQuick.Controls.Basic
import THR10

// Ручка параметра (дизайн «Studio Graphite»).
//  * перетаскивание вверх/вниз (и вбок), Shift — точная подстройка ×0,1;
//  * колесо мыши (Shift — точно); двойной клик — значение по умолчанию;
//  * клик по числу — ввод с клавиатуры (в единицах отображения);
//  * стрелки, PgUp/PgDn, Home/End, Delete (сброс), Enter (ввод) при фокусе;
//  * правый клик — меню (сброс, замок рандомайзера, LFO).
// Визуально: шкала с рисками, объёмная лицевая часть, тонкая дуга значения с
// мягким свечением; короткая вспышка, если значение пришло с комбика.
FocusScope {
    id: root

    property QtObject param: null
    property color accent: Theme.c.accent
    property real diameter: Theme.size.knob
    property bool dimmed: false          // блок выключен
    property bool showTicks: true

    signal contextRequested(QtObject param, real x, real y)

    readonly property bool dragging: dragArea.pressed && dragArea.dragMoved
    readonly property bool hot: dragArea.containsMouse || dragArea.pressed || root.activeFocus
    property bool mouseFocus: false
    onActiveFocusChanged: if (!activeFocus) mouseFocus = false

    // Отображаемое положение с плавным переходом (кроме перетаскивания).
    property real shownPos: param ? param.position : 0
    Behavior on shownPos {
        enabled: !dragArea.pressed
        NumberAnimation { duration: Theme.motion.value; easing.type: Easing.OutCubic }
    }

    // Яркость свечения: покой → наведение → перетаскивание; вспышка поверх.
    property real flashLevel: 0
    property real glowLevel: root.dimmed ? 0
                                    : Math.min(1, (root.dragging ? 1 : root.hot ? 0.75 : 0.4) + flashLevel)
    Behavior on glowLevel { NumberAnimation { duration: Theme.motion.normal } }

    NumberAnimation {
        id: flashAnim
        target: root; property: "flashLevel"
        from: 0.9; to: 0
        duration: Theme.motion.flash
        easing.type: Easing.OutQuad
    }
    Connections {
        target: root.param
        ignoreUnknownSignals: true
        function onFlash() { flashAnim.restart() }
    }

    implicitWidth: Math.max(diameter + Theme.space.sm, labelText.implicitWidth)
    implicitHeight: column.implicitHeight
    activeFocusOnTab: true

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
            color: root.dragging ? root.accent : root.dimmed ? Theme.c.textFaint : Theme.c.textMuted
            Behavior on color { ColorAnimation { duration: Theme.motion.fast } }
        }

        Item {
            id: dial
            width: root.diameter
            height: root.diameter
            anchors.horizontalCenter: parent.horizontalCenter

            readonly property real c: width / 2
            readonly property real stroke: Theme.size.knobStroke
            readonly property real tickLen: Math.max(3, width * 0.055)
            readonly property real arcR: c - tickLen - width * 0.045 - stroke / 2
            readonly property real faceD: (arcR - stroke / 2 - width * 0.06) * 2

            // фокус с клавиатуры
            Rectangle {
                anchors.centerIn: parent
                width: parent.width + Theme.size.focusRing * 3
                height: width
                radius: width / 2
                color: "transparent"
                border.width: Theme.size.focusRing
                border.color: Theme.c.focus
                opacity: 0.55
                visible: root.activeFocus && !root.mouseFocus
            }

            // риски шкалы (11 штук, крайние и средняя — длиннее)
            Repeater {
                model: root.showTicks ? 11 : 0
                delegate: Item {
                    required property int index
                    readonly property bool major: index === 0 || index === 5 || index === 10
                    width: dial.width
                    height: dial.height
                    rotation: -135 + index * 27
                    Rectangle {
                        width: parent.major ? 1.5 : 1
                        height: parent.major ? dial.tickLen : dial.tickLen * 0.65
                        radius: width / 2
                        x: dial.c - width / 2
                        y: parent.major ? 0 : dial.tickLen * 0.35
                        color: Theme.c.knobTick
                        antialiasing: true
                    }
                }
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
                        centerX: dial.c; centerY: dial.c
                        radiusX: dial.arcR; radiusY: dial.arcR
                        startAngle: 135; sweepAngle: 270
                    }
                }
            }

            // свечение под дугой значения
            Shape {
                anchors.fill: parent
                preferredRendererType: Shape.CurveRenderer
                opacity: root.glowLevel
                visible: opacity > 0.01 && root.shownPos > 0.002
                ShapePath {
                    strokeColor: Theme.c.glow
                    strokeWidth: dial.stroke * 3.4
                    fillColor: "transparent"
                    capStyle: ShapePath.RoundCap
                    PathAngleArc {
                        centerX: dial.c; centerY: dial.c
                        radiusX: dial.arcR; radiusY: dial.arcR
                        startAngle: 135; sweepAngle: Math.max(0.01, 270 * root.shownPos)
                    }
                }
            }

            // дуга значения
            Shape {
                anchors.fill: parent
                preferredRendererType: Shape.CurveRenderer
                ShapePath {
                    strokeColor: root.dimmed ? Theme.c.textFaint : root.accent
                    strokeWidth: dial.stroke
                    fillColor: "transparent"
                    capStyle: ShapePath.RoundCap
                    PathAngleArc {
                        centerX: dial.c; centerY: dial.c
                        radiusX: dial.arcR; radiusY: dial.arcR
                        startAngle: 135; sweepAngle: Math.max(0.01, 270 * root.shownPos)
                    }
                }
            }

            // метка значения по умолчанию
            Rectangle {
                readonly property real a: (135 + 270 * (root.param ? root.param.defaultPosition : 0)) * Math.PI / 180
                readonly property real r: dial.arcR - dial.stroke * 1.6
                width: 2; height: 2; radius: 1
                color: Theme.c.textFaint
                opacity: 0.8
                x: dial.c + r * Math.cos(a) - width / 2
                y: dial.c + r * Math.sin(a) - height / 2
            }

            // тень лицевой части
            Rectangle {
                width: dial.faceD + 2
                height: width
                radius: width / 2
                x: dial.c - width / 2
                y: dial.c - width / 2 + dial.faceD * 0.045
                color: Theme.c.shadow
                opacity: 0.6
            }

            // лицевая часть: фаска + градиент
            Rectangle {
                id: bevel
                width: dial.faceD
                height: width
                radius: width / 2
                x: dial.c - width / 2
                y: dial.c - height / 2
                gradient: Gradient {
                    GradientStop { position: 0.0; color: Theme.c.knobBevel }
                    GradientStop { position: 1.0; color: Theme.c.knobRim }
                }
                Rectangle {
                    id: face
                    anchors.fill: parent
                    anchors.margins: Math.max(1, dial.faceD * 0.035)
                    radius: width / 2
                    gradient: Gradient {
                        GradientStop { position: 0.0; color: Theme.c.knobFaceTop }
                        GradientStop { position: 1.0; color: Theme.c.knobFaceBottom }
                    }
                    // подсветка при наведении
                    Rectangle {
                        anchors.fill: parent
                        radius: width / 2
                        color: Theme.c.highlight
                        opacity: dragArea.containsMouse || dragArea.pressed ? 1 : 0
                        Behavior on opacity { NumberAnimation { duration: Theme.motion.fast } }
                    }
                }
                // указатель
                Item {
                    anchors.fill: parent
                    rotation: -135 + 270 * root.shownPos
                    Rectangle {
                        width: Math.max(2, dial.faceD * 0.055)
                        height: dial.faceD * 0.3
                        radius: width / 2
                        anchors.horizontalCenter: parent.horizontalCenter
                        y: dial.faceD * 0.09
                        color: root.dragging ? root.accent : Theme.c.knobPointer
                        opacity: root.dimmed ? 0.5 : 1
                        Behavior on color { ColorAnimation { duration: Theme.motion.fast } }
                    }
                }
            }

            // замок рандомайзера
            Rectangle {
                visible: root.param && root.param.locked
                width: Theme.size.icon * 0.95; height: width; radius: width / 2
                color: Theme.c.surface3
                anchors.right: parent.right
                anchors.top: parent.top
                Icon { anchors.centerIn: parent; name: "lock"; size: parent.width * 0.62; color: Theme.c.textMuted; strokeWidth: 2.2 }
            }

            // LFO
            Rectangle {
                visible: root.param && root.param.automated
                width: Theme.size.icon * 0.95; height: width; radius: width / 2
                color: Theme.c.surface3
                border.width: 1
                border.color: root.accent
                anchors.left: parent.left
                anchors.top: parent.top
                Icon { anchors.centerIn: parent; name: "wave"; size: parent.width * 0.62; color: root.accent; strokeWidth: 2.2 }
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
                    root.mouseFocus = true
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
                    dragMoved = false
                }
                onCanceled: { if (root.param) root.param.endGesture(); dragMoved = false }
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
            height: valueLabel.implicitHeight + Theme.space.xxs
            anchors.horizontalCenter: parent.horizontalCenter

            // поле значения проявляется при наведении — подсказка «можно ввести число»
            Rectangle {
                anchors.centerIn: valueLabel
                width: valueLabel.implicitWidth + Theme.space.md
                height: valueLabel.implicitHeight + Theme.space.xxs * 2
                radius: Theme.radius.sm
                color: Theme.c.surface2
                border.width: 1
                border.color: Theme.c.border
                visible: !editor.visible
                opacity: valueHover.hovered ? 1 : 0
                Behavior on opacity { NumberAnimation { duration: Theme.motion.fast } }
            }
            HoverHandler { id: valueHover }

            Label {
                id: valueLabel
                anchors.centerIn: parent
                visible: !editor.visible
                text: root.param ? root.param.text : ""
                font.pixelSize: Theme.fontSize.sm
                font.weight: Theme.weight.medium
                font.features: { "tnum": 1 }
                color: root.dragging ? root.accent : root.dimmed ? Theme.c.textFaint : Theme.c.text
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
                font.features: { "tnum": 1 }
                color: Theme.c.text
                selectionColor: Theme.c.selection
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
