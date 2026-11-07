import QtQuick
import QtQuick.Controls.Basic

TextField {
    id: control
    implicitHeight: Theme.touch + 4
    leftPadding: Theme.s3
    font.pixelSize: Theme.body
    color: Theme.text
    placeholderTextColor: Theme.textTertiary
    selectionColor: Theme.accentSoft
    selectedTextColor: Theme.text
    verticalAlignment: TextInput.AlignVCenter
    // secret: a password field with a "Show" / "Hide" switch at its right end
    property bool secret: false
    property bool revealed: false
    echoMode: secret && !revealed ? TextInput.Password : TextInput.Normal
    readonly property bool masked: echoMode === TextInput.Password
    rightPadding: secret ? Theme.s3 + 48 : Theme.s3          // room for the Show / Hide switch
    background: Rectangle {
        radius: Theme.radius
        color: Theme.field
        border.width: control.activeFocus ? 2 : 1
        border.color: control.activeFocus ? Theme.accent : Theme.separator
        Text {
            id: toggle
            visible: control.secret
            anchors.right: parent.right; anchors.rightMargin: Theme.s3
            anchors.verticalCenter: parent.verticalCenter
            text: control.revealed ? qsTr("Hide") : qsTr("Show")
            color: Theme.accent; font.pixelSize: Theme.footnote; font.weight: Font.Medium
            Accessible.role: Accessible.Button; Accessible.name: control.revealed ? qsTr("Hide the password") : qsTr("Show the password")
            HoverHandler { cursorShape: Qt.PointingHandCursor }
            TapHandler { onTapped: control.revealed = !control.revealed }
        }
    }
}
