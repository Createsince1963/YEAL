import QtQuick
import QtQuick.Layouts

// Rounded card with an optional caption above (Apple "inset grouped" style).
ColumnLayout {
    id: root
    property string title: ""
    property string footer: ""
    default property alias rows: card.data
    spacing: Theme.s2

    Text {
        visible: root.title !== ""
        text: root.title.toUpperCase()
        font.pixelSize: Theme.caption
        font.letterSpacing: 0.4
        color: Theme.textSecondary
        Layout.leftMargin: Theme.s3
        Accessible.role: Accessible.Heading
    }
    Rectangle {
        Layout.fillWidth: true
        implicitHeight: card.implicitHeight
        radius: Theme.radiusCard
        color: Theme.surface
        border.width: Theme.dark ? 0 : 1
        border.color: Theme.separator
        ColumnLayout {
            id: card
            anchors.left: parent.left
            anchors.right: parent.right
            spacing: 0
        }
    }
    Text {
        visible: root.footer !== ""
        text: root.footer
        font.pixelSize: Theme.caption
        color: Theme.textSecondary
        wrapMode: Text.Wrap
        Layout.fillWidth: true
        Layout.leftMargin: Theme.s3
        Layout.rightMargin: Theme.s3
    }
}
