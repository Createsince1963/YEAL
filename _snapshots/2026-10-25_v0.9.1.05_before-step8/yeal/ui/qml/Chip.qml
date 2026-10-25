import QtQuick

// Toggle pill (e.g. optional extras). Emits toggled(checked) on user action only.
Rectangle {
    id: root
    property string text
    property bool checked: false
    signal toggled(bool checked)

    implicitHeight: 32
    implicitWidth: row.implicitWidth + 2 * Theme.s3
    radius: height / 2
    color: checked ? Theme.accentSoft : Theme.field
    border.width: activeFocus ? 2 : (checked ? 1 : 0)
    border.color: Theme.accent
    activeFocusOnTab: true
    Keys.onSpacePressed: root.toggled(!root.checked)
    Keys.onReturnPressed: root.toggled(!root.checked)
    Accessible.role: Accessible.CheckBox
    Accessible.name: text
    Accessible.checked: checked

    Row {
        id: row
        anchors.centerIn: parent
        spacing: 6
        Icon {
            visible: root.checked
            name: "check"
            size: 14
            strokeWidth: 2.2
            color: Theme.accent
            anchors.verticalCenter: parent.verticalCenter
        }
        Text {
            text: root.text
            font.pixelSize: Theme.footnote
            color: root.checked ? Theme.accent : Theme.textSecondary
            anchors.verticalCenter: parent.verticalCenter
        }
    }
    TapHandler { onTapped: root.toggled(!root.checked) }
}
