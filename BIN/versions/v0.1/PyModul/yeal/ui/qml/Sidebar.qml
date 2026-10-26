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
    property string player: "youtube"    // which player the right-hand side shows
    signal playerSelected(string player)
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
            Layout.fillWidth: true
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
            RowLayout {      // YouTube / TIDAL Web / TIDAL DIY switch (only next to the player view)
                id: playerRow
                visible: root.rowNav
                spacing: Theme.s2
                Layout.fillWidth: true
                Layout.leftMargin: Theme.s2
                readonly property bool narrow: width < 430     // short labels "Web" / "DIY" in a narrow bar
                PlayerButton {
                    iconName: "play"; text: "YouTube"; logo: "logo_youtube.png"
                    tip: qsTr("YouTube - the YouTube view")
                    selected: root.player === "youtube"
                    Layout.fillWidth: true; Layout.preferredWidth: 1
                    onClicked: root.playerSelected("youtube")
                }
                PlayerButton {
                    iconName: "music"; text: playerRow.narrow ? "Web" : "TIDAL Web"; logo: "logo_tidal.png"; logoLight: "logo_tidal_dark.png"
                    tip: qsTr("TIDAL Web - the TIDAL web player")
                    selected: root.player === "tidal"
                    Layout.fillWidth: true; Layout.preferredWidth: 1
                    onClicked: root.playerSelected("tidal")
                }
                PlayerButton {
                    iconName: "music"; text: playerRow.narrow ? "DIY" : "TIDAL DIY"; logo: "logo_tidal_diy.png"
                    tip: qsTr("TIDAL DIY - Yeal's own TIDAL view")
                    selected: root.player === "tidaldiy"
                    Layout.fillWidth: true; Layout.preferredWidth: 1
                    onClicked: root.playerSelected("tidaldiy")
                }
                PlayerButton {
                    iconName: "volume"; text: qsTr("Player"); logo: "logo_player.png"
                    tip: qsTr("Player - Yeal's own player for your downloaded songs (also plays on a speaker)")
                    selected: root.player === "local"
                    Layout.fillWidth: true; Layout.preferredWidth: 1
                    onClicked: root.playerSelected("local")
                }
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
