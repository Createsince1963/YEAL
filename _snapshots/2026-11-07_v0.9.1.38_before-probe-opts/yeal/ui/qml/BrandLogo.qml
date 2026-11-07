import QtQuick
import QtQuick.Shapes

// The MediaOrbit logo drawn as a vector (sharp at every size): the play mark with the download arrow's colours and the name with
// its slogan. `withText: false` draws just the mark.
Item {
    id: root
    property real markSize: 48
    property bool withText: true
    property color nameColor: Theme.text
    property color sloganColor: Theme.textSecondary

    implicitWidth: withText ? markSize + gap + Math.max(name.implicitWidth, slogan.implicitWidth) : markSize
    implicitHeight: markSize
    readonly property real gap: markSize * 0.28

    // a polygon with rounded corners as an SVG path (points in 0..1, scaled to `size`)
    function rounded(points, r, size) {
        var n = points.length, d = ""
        for (var i = 0; i < n; ++i) {
            var p0 = points[(i + n - 1) % n], p1 = points[i], p2 = points[(i + 1) % n]
            var v1 = [p0[0] - p1[0], p0[1] - p1[1]], v2 = [p2[0] - p1[0], p2[1] - p1[1]]
            var l1 = Math.hypot(v1[0], v1[1]), l2 = Math.hypot(v2[0], v2[1])
            var k = Math.min(r, l1 / 2, l2 / 2)
            var a = [p1[0] + v1[0] / l1 * k, p1[1] + v1[1] / l1 * k], b = [p1[0] + v2[0] / l2 * k, p1[1] + v2[1] / l2 * k]
            d += (i === 0 ? "M " : "L ") + (a[0] * size) + " " + (a[1] * size) + " "
            d += "Q " + (p1[0] * size) + " " + (p1[1] * size) + " " + (b[0] * size) + " " + (b[1] * size) + " "
        }
        return d + "Z"
    }

    Shape {
        id: mark
        width: root.markSize; height: root.markSize
        anchors.verticalCenter: parent.verticalCenter
        preferredRendererType: Shape.CurveRenderer          // smooth edges without an offscreen layer
        ShapePath {                          // the play shape in blue gradient
            strokeColor: "transparent"
            fillGradient: LinearGradient {
                x1: 0; y1: 0; x2: root.markSize; y2: root.markSize
                GradientStop { position: 0.0; color: "#1FE0F5" }
                GradientStop { position: 0.55; color: "#2D84F6" }
                GradientStop { position: 1.0; color: "#7358F0" }
            }
            PathSvg { path: root.rounded([[0.10, 0.06], [0.96, 0.50], [0.10, 0.94]], 0.17, root.markSize) }
        }
        ShapePath {                          // the darker lobe at the lower left
            strokeColor: "transparent"
            fillGradient: LinearGradient {
                x1: 0; y1: root.markSize * 0.5; x2: root.markSize * 0.6; y2: root.markSize
                GradientStop { position: 0.0; color: "#1E6BFF" }
                GradientStop { position: 1.0; color: "#2B3FD8" }
            }
            PathSvg { path: root.rounded([[0.10, 0.55], [0.52, 0.76], [0.10, 0.94]], 0.15, root.markSize) }
        }
        ShapePath {                          // the dark play triangle inside
            strokeColor: "transparent"
            fillColor: "#0B1420"
            PathSvg { path: root.rounded([[0.33, 0.30], [0.70, 0.50], [0.33, 0.70]], 0.07, root.markSize) }
        }
    }
    Column {
        visible: root.withText
        anchors.left: mark.right; anchors.leftMargin: root.gap
        anchors.verticalCenter: parent.verticalCenter
        spacing: root.markSize * 0.04
        Text {
            id: name
            text: "MediaOrbit"
            color: root.nameColor
            font.pixelSize: root.markSize * 0.46
            font.weight: Font.DemiBold
        }
        Text {
            id: slogan
            text: "Download. Play. Keep."
            color: root.sloganColor
            font.pixelSize: root.markSize * 0.22
            font.letterSpacing: root.markSize * 0.012
        }
    }
    Accessible.role: Accessible.Graphic
    Accessible.name: "MediaOrbit"
}
