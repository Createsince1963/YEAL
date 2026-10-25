import QtQuick
import QtQuick.Controls.Basic

ToolButton {
    id: control
    property string iconName
    property color tint: Theme.textSecondary
    property string tip: ""

    implicitWidth: Theme.touch
    implicitHeight: Theme.touch
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus

    background: Rectangle {
        radius: Theme.radius
        color: control.down ? Theme.pressed : control.hovered ? Theme.hover : "transparent"
        border.width: control.visualFocus ? 2 : 0
        border.color: Theme.accent
    }
    contentItem: Item {
        Icon {
            anchors.centerIn: parent
            name: control.iconName
            size: 20
            color: control.enabled ? (control.hovered ? Theme.text : control.tint) : Theme.textTertiary
        }
    }
    ToolTip.visible: tip !== "" && hovered && !Theme.compact
    ToolTip.delay: 600
    ToolTip.text: tip
    Accessible.role: Accessible.Button
    Accessible.name: tip !== "" ? tip : iconName
}
