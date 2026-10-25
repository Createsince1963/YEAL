import QtQuick
import QtQuick.Controls.Basic

TextField {
    id: control
    implicitHeight: Theme.touch + 4
    leftPadding: Theme.s3
    rightPadding: Theme.s3
    font.pixelSize: Theme.body
    color: Theme.text
    placeholderTextColor: Theme.textTertiary
    selectionColor: Theme.accentSoft
    selectedTextColor: Theme.text
    verticalAlignment: TextInput.AlignVCenter
    background: Rectangle {
        radius: Theme.radius
        color: Theme.field
        border.width: control.activeFocus ? 2 : 1
        border.color: control.activeFocus ? Theme.accent : Theme.separator
    }
}
