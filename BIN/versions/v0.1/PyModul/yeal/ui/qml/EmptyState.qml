import QtQuick
import QtQuick.Layouts

ColumnLayout {
    id: root
    property string iconName: "download"
    property string title
    property string subtitle
    property string actionText: ""
    signal action()
    spacing: Theme.s3

    Rectangle {
        visible: root.iconName !== ""
        implicitWidth: 72
        implicitHeight: 72
        radius: 36
        color: Theme.accentSoft
        Layout.alignment: Qt.AlignHCenter
        Icon { anchors.centerIn: parent; name: root.iconName; size: 32; color: Theme.accent; strokeWidth: 1.5 }
    }
    Text {
        text: root.title
        font.pixelSize: Theme.headline
        font.weight: Font.DemiBold
        color: Theme.text
        horizontalAlignment: Text.AlignHCenter
        Layout.alignment: Qt.AlignHCenter
        Layout.topMargin: Theme.s2
    }
    Text {
        text: root.subtitle
        font.pixelSize: Theme.body
        color: Theme.textSecondary
        wrapMode: Text.Wrap
        horizontalAlignment: Text.AlignHCenter
        Layout.preferredWidth: 340
        Layout.maximumWidth: 340
        Layout.alignment: Qt.AlignHCenter
    }
    AppButton {
        visible: root.actionText !== ""
        text: root.actionText
        kind: "primary"
        Layout.alignment: Qt.AlignHCenter
        Layout.topMargin: Theme.s2
        onClicked: root.action()
    }
}
