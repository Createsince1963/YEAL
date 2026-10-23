import QtQuick
import QtQuick.Layouts

Rectangle {
    id: root
    property var items: []
    property int currentIndex: 0
    signal selected(int index)

    implicitWidth: 224
    property bool onRight: false
    property bool rowNav: false          // three buttons in one row (wide bar next to the browser view)
    readonly property alias slot: panelSlot
    color: Theme.sidebar

    Rectangle {
        width: 1
        height: parent.height
        anchors.right: root.onRight ? undefined : parent.right
        anchors.left: root.onRight ? parent.left : undefined
        color: Theme.separator
    }
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.s3
        spacing: Theme.s1

        RowLayout {
            spacing: Theme.s3
            Layout.leftMargin: Theme.s2
            Layout.topMargin: Theme.s2
            Layout.bottomMargin: Theme.s4
            Image {
                source: "assets/icon.png"
                sourceSize.width: 128
                sourceSize.height: 128
                Layout.preferredWidth: 36
                Layout.preferredHeight: 36
                smooth: true
                Accessible.ignored: true
            }
            Text {
                text: "Yeal"
                font.pixelSize: Theme.headline + 1
                font.weight: Font.DemiBold
                color: Theme.text
            }
        }
        RowLayout {
            visible: root.rowNav
            spacing: Theme.s1
            Layout.fillWidth: true
            Repeater {
                model: root.rowNav ? root.items : []
                delegate: NavItem {
                    required property var modelData
                    required property int index
                    iconName: modelData.icon
                    text: modelData.text
                    badge: modelData.badge || 0
                    selected: root.currentIndex === index
                    tight: true
                    Layout.fillWidth: true
                    Layout.preferredWidth: 1
                    onClicked: root.selected(index)
                }
            }
        }
        Repeater {
            model: root.rowNav ? [] : root.items
            delegate: NavItem {
                required property var modelData
                required property int index
                iconName: modelData.icon
                text: modelData.text
                badge: modelData.badge || 0
                selected: root.currentIndex === index
                Layout.fillWidth: true
                onClicked: root.selected(index)
            }
        }
        Item { id: panelSlot; Layout.fillWidth: true; Layout.fillHeight: true; Layout.topMargin: Theme.s3 }
        Text {
            text: qsTr("Yeal %1").arg(backend.appVersion)
            font.pixelSize: Theme.caption
            color: Theme.textSecondary
            Layout.leftMargin: Theme.s2
        }
        Text {
            text: qsTr("yt-dlp %1").arg(backend.ytdlpVersion)
            font.pixelSize: Theme.caption
            color: Theme.textTertiary
            Layout.leftMargin: Theme.s2
            Layout.bottomMargin: Theme.s1
        }
    }
}
