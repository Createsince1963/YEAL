import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

MenuItem {
    id: control
    property string iconName: ""
    property bool destructive: false
    property bool marked: false   // shows a check mark

    implicitHeight: Theme.compact ? 44 : 34
    implicitWidth: 200
    leftPadding: Theme.s3
    rightPadding: Theme.s3
    hoverEnabled: true

    background: Rectangle {
        radius: 6
        color: control.highlighted || control.hovered ? Theme.hover : "transparent"
        anchors.fill: parent
        anchors.margins: 3
    }
    contentItem: RowLayout {
        spacing: Theme.s2
        Icon {
            visible: control.iconName !== ""
            name: control.iconName
            size: 16
            color: !control.enabled ? Theme.textTertiary : control.destructive ? Theme.danger : Theme.textSecondary
        }
        Text {
            text: control.text
            font.pixelSize: Theme.body
            color: !control.enabled ? Theme.textTertiary : control.destructive ? Theme.danger : Theme.text
            elide: Text.ElideRight
            Layout.fillWidth: true
        }
        Icon { visible: control.marked; name: "check"; size: 16; color: Theme.accent }
    }
}
