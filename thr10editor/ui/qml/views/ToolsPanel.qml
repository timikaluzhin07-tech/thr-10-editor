import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Basic
import THR10
import "../components"

// Правая панель: рандомайзер, морфинг, автоматизация (LFO), тап-темп.
Rectangle {
    id: root
    property alias currentIndex: tabs.currentIndex
    color: Theme.c.surface
    Behavior on color { ColorAnimation { duration: Theme.motion.theme } }
    Rectangle { anchors.left: parent.left; width: 1; height: parent.height; color: Theme.c.border }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.space.md
        anchors.topMargin: Theme.space.sm
        anchors.leftMargin: Theme.space.md + 1
        spacing: Theme.space.md

        TabStrip {
            id: tabs
            Layout.fillWidth: true
            model: ["Рандом", "Морфинг", "LFO", "Тап"]
            onCurrentIndexChanged: switchAnim.restart()
        }

        StackLayout {
            id: stack
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: tabs.currentIndex
            transform: Translate { id: stackShift }

            // ---------------- Рандомайзер ----------------
            ColumnLayout {
                spacing: Theme.space.sm
                AppButton {
                    Layout.fillWidth: true
                    variant: "primary"
                    text: "Случайный звук"
                    iconName: "dice"
                    tip: "Ctrl+Shift+R. Отменить — Ctrl+Z"
                    onClicked: Backend.randomize()
                }
                RowLayout {
                    Layout.fillWidth: true
                    Label { text: "Сила"; color: Theme.c.text; font.pixelSize: Theme.fontSize.sm }
                    AppSlider {
                        Layout.fillWidth: true
                        from: 5; to: 100; stepSize: 5
                        value: Backend.randomAmount
                        onMoved: Backend.randomAmount = value
                    }
                    Label {
                        text: Backend.randomAmount + "%"
                        color: Theme.c.textMuted
                        font.pixelSize: Theme.fontSize.sm
                        font.features: { "tnum": 1 }
                        Layout.preferredWidth: Theme.space.xxl
                    }
                }
                component Opt: RowLayout {
                    property alias checked: sw.checked
                    property alias text: lbl.text
                    signal toggled(bool on)
                    spacing: Theme.space.sm
                    ToggleSwitch { id: sw; onToggled: parent.toggled(checked) }
                    Label { id: lbl; color: Theme.c.text; font.pixelSize: Theme.fontSize.sm; Layout.fillWidth: true; wrapMode: Text.Wrap }
                }
                Opt { text: "Менять типы эффектов"; checked: Backend.randomTypes; onToggled: (on) => Backend.randomTypes = on }
                Opt { text: "Включать/выключать блоки"; checked: Backend.randomSwitches; onToggled: (on) => Backend.randomSwitches = on }
                Opt { text: "Менять модель и кабинет"; checked: Backend.randomAmp; onToggled: (on) => Backend.randomAmp = on }

                RowLayout {
                    Layout.fillWidth: true
                    Layout.topMargin: Theme.space.sm
                    SectionLabel { text: "Границы и замки"; Layout.fillWidth: true }
                    AppButton { compact: true; variant: "ghost"; text: "Сброс"; onClicked: Backend.resetRandomBounds() }
                }
                Label {
                    Layout.fillWidth: true
                    text: "Замок — параметр не меняется (по умолчанию Master, чтобы не было резкого скачка громкости). Замок ставится и правым кликом по ручке."
                    color: Theme.c.textFaint
                    font.pixelSize: Theme.fontSize.xs
                    wrapMode: Text.Wrap
                }
                ListView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    spacing: Theme.space.xxs
                    model: Backend.randomParams
                    ScrollBar.vertical: ScrollBar {}
                    delegate: ColumnLayout {
                        id: rp
                        required property var modelData
                        readonly property QtObject p: Backend.param(modelData.key)
                        width: ListView.view.width - Theme.space.sm
                        spacing: 0
                        SectionLabel {
                            visible: rp.modelData.groupFirst
                            text: rp.modelData.group
                            topPadding: Theme.space.sm
                            bottomPadding: Theme.space.xxs
                        }
                        RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.space.xs
                        IconButton {
                            boxSize: Theme.size.control * 0.75
                            iconName: rp.modelData.locked ? "lock" : "unlock"
                            iconColor: rp.modelData.locked ? Theme.c.accent : Theme.c.textFaint
                            tip: rp.modelData.locked ? "Разблокировать" : "Заблокировать"
                            onClicked: rp.p.toggleLock()
                        }
                        Label {
                            text: rp.modelData.label
                            color: rp.modelData.locked ? Theme.c.textFaint : Theme.c.text
                            font.pixelSize: Theme.fontSize.xs
                            Layout.preferredWidth: Theme.space.xxxl * 2.35
                            elide: Text.ElideRight
                        }
                        AppRangeSlider {
                            id: rs
                            Layout.fillWidth: true
                            enabled: !rp.modelData.locked
                            accent: Theme.c[rp.modelData.accent]
                            first.value: rp.modelData.lo
                            second.value: rp.modelData.hi
                            first.onMoved: Backend.setRandomBounds(rp.modelData.key, first.value, second.value)
                            second.onMoved: Backend.setRandomBounds(rp.modelData.key, first.value, second.value)
                            ToolTip.visible: hovered
                            ToolTip.text: rp.p.formatPosition(first.value) + " … " + rp.p.formatPosition(second.value)
                        }
                        }
                    }
                }
            }

            // ---------------- Морфинг ----------------
            ColumnLayout {
                spacing: Theme.space.sm
                Label {
                    Layout.fillWidth: true
                    text: "Плавный переход от текущего звука к выбранному. Ручки двигаются в «музыкальной» шкале; переключатели и типы меняются на середине."
                    color: Theme.c.textMuted
                    font.pixelSize: Theme.fontSize.sm
                    wrapMode: Text.Wrap
                }
                SectionLabel { text: "Куда" }
                AppCombo {
                    Layout.fillWidth: true
                    model: Backend.morphTargets.map(t => t.name)
                    currentIndex: Math.max(0, Backend.morphTargets.findIndex(t => t.id === Backend.morphTarget))
                    onActivated: (i) => Backend.morphTarget = Backend.morphTargets[i].id
                }
                SectionLabel { text: "Время: " + Backend.morphDuration.toFixed(1) + " с" }
                AppSlider {
                    Layout.fillWidth: true
                    from: 0; to: 1
                    // логарифмическая шкала 0,2…60 с
                    value: Math.log(Backend.morphDuration / 0.2) / Math.log(300)
                    onMoved: Backend.morphDuration = 0.2 * Math.pow(300, value)
                }
                SectionLabel { text: "Кривая" }
                Segmented {
                    Layout.fillWidth: true
                    small: true
                    model: ["Линейно", "Плавно", "Разгон", "Торможение"]
                    currentIndex: Backend.morphCurves.indexOf(Backend.morphCurve)
                    onActivated: (i) => Backend.morphCurve = Backend.morphCurves[i]
                }
                Rectangle {
                    Layout.fillWidth: true
                    Layout.topMargin: Theme.space.sm
                    height: Theme.space.sm
                    radius: height / 2
                    color: Theme.c.knobTrack
                    Rectangle {
                        width: parent.width * Backend.morphProgress
                        height: parent.height
                        radius: parent.radius
                        color: Theme.c.accent
                    }
                }
                AppButton {
                    Layout.fillWidth: true
                    variant: Backend.morphRunning ? "secondary" : "primary"
                    text: Backend.morphRunning ? "Остановить" : "Начать морфинг"
                    iconName: Backend.morphRunning ? "stop" : "morph"
                    tip: "Ctrl+M"
                    onClicked: Backend.morphRunning ? Backend.stopMorph() : Backend.startMorph()
                }
                Item { Layout.fillHeight: true }
            }

            // ---------------- LFO ----------------
            ColumnLayout {
                spacing: Theme.space.sm
                Label {
                    Layout.fillWidth: true
                    text: "Медленная автоматизация: параметр «плавает» вокруг текущего значения. Обновления не чаще " + Backend.lfoRateLimit + " раз/с на параметр."
                    color: Theme.c.textMuted
                    font.pixelSize: Theme.fontSize.sm
                    wrapMode: Text.Wrap
                }
                RowLayout {
                    Layout.fillWidth: true
                    AppCombo {
                        id: addCombo
                        Layout.fillWidth: true
                        model: Backend.automatableParams.map(p => p.name)
                    }
                    IconButton {
                        iconName: "plus"
                        tip: "Добавить LFO"
                        onClicked: Backend.addLfo(Backend.automatableParams[addCombo.currentIndex].key)
                    }
                }
                AppButton {
                    Layout.fillWidth: true
                    variant: Backend.automationRunning ? "secondary" : "primary"
                    text: Backend.automationRunning ? "Остановить (вернуть значения)" : "Запустить"
                    iconName: Backend.automationRunning ? "stop" : "play"
                    tip: "Ctrl+L"
                    onClicked: Backend.toggleAutomation()
                }
                ListView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    spacing: Theme.space.sm
                    model: Backend.lfos
                    ScrollBar.vertical: ScrollBar {}
                    delegate: Rectangle {
                        id: lfo
                        required property var modelData
                        width: ListView.view.width - Theme.space.sm
                        implicitHeight: lc.implicitHeight + Theme.space.md * 2
                        radius: Theme.radius.md
                        color: Theme.c.surface2
                        border.width: 1
                        border.color: Theme.c.border
                        ColumnLayout {
                            id: lc
                            anchors.fill: parent
                            anchors.margins: Theme.space.md
                            spacing: Theme.space.xs
                            RowLayout {
                                Layout.fillWidth: true
                                Rectangle { width: Theme.space.sm; height: width; radius: width / 2; color: Theme.c[lfo.modelData.accent] }
                                Label {
                                    text: lfo.modelData.group + ": " + lfo.modelData.label + (lfo.modelData.active ? "" : " (тип неактивен)")
                                    color: Theme.c.text
                                    font.weight: Theme.weight.semibold
                                    font.pixelSize: Theme.fontSize.sm
                                    Layout.fillWidth: true
                                    elide: Text.ElideRight
                                }
                                ToggleSwitch {
                                    checked: lfo.modelData.enabled
                                    onToggled: Backend.setLfoField(lfo.modelData.id, "enabled", checked)
                                }
                                IconButton {
                                    boxSize: Theme.size.control * 0.8
                                    iconName: "trash"; tip: "Удалить LFO"
                                    onClicked: Backend.removeLfo(lfo.modelData.id)
                                }
                            }
                            AppCombo {
                                Layout.fillWidth: true
                                model: Backend.waveforms
                                currentIndex: lfo.modelData.waveformIndex
                                onActivated: (i) => Backend.setLfoField(lfo.modelData.id, "waveform", i)
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                Label { text: "Скорость"; color: Theme.c.textMuted; font.pixelSize: Theme.fontSize.xs; Layout.preferredWidth: Theme.space.xxxl * 1.3 }
                                AppSlider {
                                    id: rate
                                    Layout.fillWidth: true
                                    // 0,01…5 Гц, логарифмически
                                    from: 0; to: 1
                                    value: Math.log(lfo.modelData.rate / 0.01) / Math.log(500)
                                    onMoved: Backend.setLfoField(lfo.modelData.id, "rate", 0.01 * Math.pow(500, value))
                                }
                                Label {
                                    readonly property real hz: 0.01 * Math.pow(500, rate.value)
                                    text: hz >= 1 ? hz.toFixed(2) + " Гц" : (1 / hz).toFixed(1) + " с"
                                    color: Theme.c.textMuted
                                    font.pixelSize: Theme.fontSize.xs
                                    font.features: { "tnum": 1 }
                                    Layout.preferredWidth: Theme.space.xxxl * 1.2
                                }
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                Label { text: "Глубина"; color: Theme.c.textMuted; font.pixelSize: Theme.fontSize.xs; Layout.preferredWidth: Theme.space.xxxl * 1.3 }
                                AppSlider {
                                    id: depth
                                    Layout.fillWidth: true
                                    from: 0; to: 1
                                    value: lfo.modelData.depth
                                    onMoved: Backend.setLfoField(lfo.modelData.id, "depth", value)
                                }
                                Label {
                                    text: Math.round(depth.value * 100) + "%"
                                    color: Theme.c.textMuted
                                    font.pixelSize: Theme.fontSize.xs
                                    font.features: { "tnum": 1 }
                                    Layout.preferredWidth: Theme.space.xxxl * 1.2
                                }
                            }
                        }
                    }
                }
            }

            // ---------------- Тап-темп ----------------
            ColumnLayout {
                spacing: Theme.space.md
                Label {
                    Layout.fillWidth: true
                    text: "Нажимайте в такт: клавиша T или кнопка ниже. Время дилея считается из темпа и доли."
                    color: Theme.c.textMuted
                    font.pixelSize: Theme.fontSize.sm
                    wrapMode: Text.Wrap
                }
                Rectangle {
                    id: tapPad
                    Layout.fillWidth: true
                    Layout.preferredHeight: Theme.size.knobLarge * 1.6
                    radius: Theme.radius.xl
                    gradient: Gradient {
                        GradientStop { position: 0.0; color: tapMa.containsMouse ? Theme.c.surface3 : Theme.c.surface2 }
                        GradientStop { position: 1.0; color: Theme.c.surface2 }
                    }
                    border.width: 1
                    border.color: tapMa.pressed ? Theme.c.accent : Theme.c.border
                    // вспышка на каждый удар
                    Rectangle {
                        id: tapFlash
                        anchors.fill: parent
                        radius: parent.radius
                        color: Theme.c.glow
                        opacity: 0
                        NumberAnimation on opacity { id: tapPulse; running: false; from: 0.9; to: 0; duration: Theme.motion.flash; easing.type: Easing.OutQuad }
                    }
                    MouseArea {
                        id: tapMa
                        anchors.fill: parent
                        hoverEnabled: true
                        onPressed: { Backend.tapTempo(); tapPulse.restart() }
                    }
                    ColumnLayout {
                        anchors.centerIn: parent
                        spacing: Theme.space.xs
                        Label {
                            Layout.alignment: Qt.AlignHCenter
                            text: Backend.tapBpm > 0 ? Backend.tapBpm.toFixed(1) : "TAP"
                            color: Theme.c.text
                            font.pixelSize: Theme.fontSize.display
                            font.weight: Theme.weight.bold
                            font.features: { "tnum": 1 }
                        }
                        Label {
                            Layout.alignment: Qt.AlignHCenter
                            text: Backend.tapBpm > 0 ? "BPM · дилей " + Backend.param("delay.time").text : "нажмите несколько раз"
                            color: Theme.c.textMuted
                            font.pixelSize: Theme.fontSize.sm
                        }
                    }
                }
                SectionLabel { text: "Доля" }
                Segmented {
                    Layout.fillWidth: true
                    small: true
                    model: Backend.tapSubdivisions
                    currentIndex: Backend.tapSubdivisions.indexOf(Backend.tapSubdivision)
                    onActivated: (i) => Backend.tapSubdivision = Backend.tapSubdivisions[i]
                }
                Label {
                    Layout.fillWidth: true
                    text: "Единица времени дилея (0,1 мс) выведена из источников и требует проверки на железе — см. docs/HARDWARE_TEST.md."
                    color: Theme.c.textFaint
                    font.pixelSize: Theme.fontSize.xs
                    wrapMode: Text.Wrap
                }
                Item { Layout.fillHeight: true }
            }
        }
    }

    ParallelAnimation {
        id: switchAnim
        NumberAnimation { target: stack; property: "opacity"; from: 0; to: 1; duration: Theme.motion.normal; easing.type: Easing.OutCubic }
        NumberAnimation { target: stackShift; property: "x"; from: 6; to: 0; duration: Theme.motion.slow; easing.type: Easing.OutCubic }
    }
}
