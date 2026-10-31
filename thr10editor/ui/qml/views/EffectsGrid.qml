import QtQuick
import QtQuick.Layouts
import THR10
import "../components"

// Сетка карточек эффектов: 1–3 колонки по ширине.
Item {
    id: root
    property var extras: ({})  // ключ группы → компонент для заголовка
    signal knobContext(QtObject param, Item knob, real x, real y)

    readonly property int columns: width > Theme.space.xxxl * 20 ? 3 : width > Theme.space.xxxl * 12 ? 2 : 1
    readonly property real cardWidth: (width - Theme.space.lg * (columns - 1)) / columns

    implicitHeight: Math.max(...colHeights())

    function colHeights() {
        const h = []
        for (let c = 0; c < columns; ++c) h.push(0)
        for (let i = 0; i < rep.count; ++i) {
            const it = rep.itemAt(i)
            if (it) h[i % columns] += it.implicitHeight + Theme.space.lg
        }
        return h
    }

    Repeater {
        id: rep
        model: Backend.effectGroups
        delegate: EffectCard {
            required property string modelData
            required property int index
            group: Backend.group(modelData)
            width: root.cardWidth
            x: (index % root.columns) * (root.cardWidth + Theme.space.lg)
            y: {
                let yy = 0
                for (let i = index % root.columns; i < index; i += root.columns) {
                    const it = rep.itemAt(i)
                    if (it) yy += it.implicitHeight + Theme.space.lg
                }
                return yy
            }
            height: implicitHeight
            Behavior on x { NumberAnimation { duration: Theme.motion.normal; easing.type: Easing.OutCubic } }
            Behavior on y { NumberAnimation { duration: Theme.motion.normal; easing.type: Easing.OutCubic } }
            headerComponent: root.extras[modelData] || null
            onKnobContext: (p, k, x, y) => root.knobContext(p, k, x, y)
        }
    }
}
