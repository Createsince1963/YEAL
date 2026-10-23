import QtQuick
import QtQuick.Controls.Basic

Switch {
    id: control
    implicitWidth: 46
    implicitHeight: 28
    padding: 0
    focusPolicy: Qt.StrongFocus
    indicator: Rectangle {
        implicitWidth: 46
        implicitHeight: 28
        radius: 14
        color: control.checked ? Theme.success : Theme.track
        border.width: control.visualFocus ? 2 : 0
        border.color: Theme.accent
        Behavior on color { ColorAnimation { duration: Theme.dur } }
        Rectangle {
            y: 2
            x: control.checked ? parent.width - width - 2 : 2
            width: 24
            height: 24
            radius: 12
            color: "#FFFFFF"
            Behavior on x { NumberAnimation { duration: Theme.dur; easing.type: Easing.OutCubic } }
        }
    }
    contentItem: Item {}
    Accessible.role: Accessible.CheckBox
}
