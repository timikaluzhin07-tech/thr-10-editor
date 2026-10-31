import QtQuick
import QtQuick.Shapes
import THR10
import "../Icons.js" as Icons

// Векторная иконка из набора Lucide (штрих 2 px в сетке 24×24).
Item {
    id: root
    property string name: ""
    property color color: Theme.c.text
    property real size: Theme.size.icon
    property real strokeWidth: 2

    implicitWidth: size
    implicitHeight: size

    Shape {
        width: 24
        height: 24
        scale: root.size / 24
        transformOrigin: Item.TopLeft
        preferredRendererType: Shape.CurveRenderer
        ShapePath {
            strokeColor: root.color
            strokeWidth: root.strokeWidth
            fillColor: "transparent"
            capStyle: ShapePath.RoundCap
            joinStyle: ShapePath.RoundJoin
            PathSvg { path: Icons.paths[root.name] || "" }
        }
    }
}
