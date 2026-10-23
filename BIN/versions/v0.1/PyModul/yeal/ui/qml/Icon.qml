import QtQuick
import QtQuick.Shapes

Item {
    id: root
    property string name
    property color color: Theme.text
    property real size: 20
    property real strokeWidth: 1.75
    implicitWidth: size
    implicitHeight: size
    Accessible.ignored: true

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
            PathSvg { path: IconPaths.d[root.name] || "" }
        }
    }
}
