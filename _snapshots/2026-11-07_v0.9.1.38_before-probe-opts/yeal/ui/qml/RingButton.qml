import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Shapes

// Round icon button with a progress ring around it (determinate or spinning).
ToolButton {
    id: control
    property string iconName: "x"
    property real progress: 0
    property bool indeterminate: false
    property string tip: ""

    implicitWidth: Theme.touch
    implicitHeight: Theme.touch
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus

    background: Rectangle {
        radius: width / 2
        color: control.down ? Theme.pressed : control.hovered ? Theme.hover : "transparent"
        border.width: control.visualFocus ? 2 : 0
        border.color: Theme.accent
    }
    contentItem: Item {
        Shape {
            id: ring
            anchors.centerIn: parent
            width: 30
            height: 30
            preferredRendererType: Shape.CurveRenderer
            layer.samples: 4
            ShapePath {
                strokeColor: Theme.track
                strokeWidth: 3
                fillColor: "transparent"
                PathAngleArc { centerX: 15; centerY: 15; radiusX: 13; radiusY: 13; startAngle: 0; sweepAngle: 360 }
            }
            ShapePath {
                strokeColor: Theme.accentFill
                strokeWidth: 3
                fillColor: "transparent"
                capStyle: ShapePath.RoundCap
                PathAngleArc {
                    centerX: 15; centerY: 15; radiusX: 13; radiusY: 13
                    startAngle: -90
                    sweepAngle: control.indeterminate ? 100 : 360 * Math.max(0.02, Math.min(1, control.progress))
                }
            }
            RotationAnimator on rotation {
                running: control.indeterminate && control.visible && !Theme.reducedMotion
                from: 0; to: 360; duration: 1100; loops: Animation.Infinite
            }
        }
        Icon {
            anchors.centerIn: parent
            name: control.iconName
            size: 14
            strokeWidth: 2.2
            color: control.hovered ? Theme.text : Theme.textSecondary
        }
    }
    ToolTip.visible: tip !== "" && hovered && !Theme.compact
    ToolTip.delay: 600
    ToolTip.text: tip
    Accessible.role: Accessible.Button
    Accessible.name: tip
}
