import QtQuick
import QtQuick.Layouts

// Rounded card with an optional caption above (Apple "inset grouped" style).
ColumnLayout {
    id: root
    property string title: ""
    property string footer: ""
    property string icon: ""
    property bool collapsible: false
    property bool collapsed: false
    default property alias rows: card.data
    spacing: Theme.s2

    RowLayout {
        visible: root.title !== ""
        Layout.fillWidth: true
        Layout.leftMargin: Theme.s3
        Layout.rightMargin: Theme.s3
        spacing: Theme.s2
        Icon {
            visible: root.icon !== ""
            name: root.icon
            size: 16
            color: Theme.textSecondary
        }
        Text {
            text: root.title.toUpperCase()
            font.pixelSize: Theme.caption
            font.letterSpacing: 0.4
            color: Theme.textSecondary
            Layout.fillWidth: true
            Accessible.role: Accessible.Heading
        }
        Icon {
            visible: root.collapsible
            name: "chevronDown"
            size: 15
            color: Theme.textSecondary
            rotation: root.collapsed ? -90 : 0
            Behavior on rotation { NumberAnimation { duration: 120 } }
        }
        TapHandler {
            enabled: root.collapsible
            onTapped: root.collapsed = !root.collapsed
        }
    }
    Rectangle {
        visible: !root.collapsed
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
        visible: !root.collapsed && root.footer !== ""
        text: root.footer
        font.pixelSize: Theme.caption
        color: Theme.textSecondary
        wrapMode: Text.Wrap
        Layout.fillWidth: true
        Layout.leftMargin: Theme.s3
        Layout.rightMargin: Theme.s3
    }
}
