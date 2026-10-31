import QtQuick
import QtQuick.Shapes
import THR10

// Знак приложения: миниатюрная ручка с акцентной дугой.
Item {
    id: root
    property real size: Theme.size.control * 0.8
    implicitWidth: size
    implicitHeight: size

    Shape {
        anchors.fill: parent
        preferredRendererType: Shape.CurveRenderer
        ShapePath {
            strokeColor: Theme.c.knobTrack
            strokeWidth: root.size * 0.11
            fillColor: "transparent"
            capStyle: ShapePath.RoundCap
            PathAngleArc {
                centerX: root.size / 2; centerY: root.size / 2
                radiusX: root.size * 0.42; radiusY: root.size * 0.42
                startAngle: 135; sweepAngle: 270
            }
        }
        ShapePath {
            strokeColor: Theme.c.accent
            strokeWidth: root.size * 0.11
            fillColor: "transparent"
            capStyle: ShapePath.RoundCap
            PathAngleArc {
                centerX: root.size / 2; centerY: root.size / 2
                radiusX: root.size * 0.42; radiusY: root.size * 0.42
                startAngle: 135; sweepAngle: 200
            }
        }
    }
    Rectangle {
        anchors.centerIn: parent
        width: root.size * 0.5; height: width; radius: width / 2
        gradient: Gradient {
            GradientStop { position: 0.0; color: Theme.c.knobFaceTop }
            GradientStop { position: 1.0; color: Theme.c.knobFaceBottom }
        }
        border.width: 1
        border.color: Theme.c.knobRim
        Item {
            anchors.fill: parent
            rotation: 65
            Rectangle {
                width: Math.max(1.5, root.size * 0.06); height: parent.height * 0.32
                radius: width / 2
                anchors.horizontalCenter: parent.horizontalCenter
                y: parent.height * 0.1
                color: Theme.c.knobPointer
            }
        }
    }
}
