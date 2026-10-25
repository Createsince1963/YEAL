import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// Artist page of the TIDAL DIY view: compact header, then tabs for top tracks, albums, singles & EPs, videos
// and similar artists.
Item {
    id: page
    property var ctl
    property string itemId: ""
    property var seed: ({})
    property string tab: "top"
    TidalRequest { id: req; route: "artist"; arg: page.itemId }
    readonly property var info: req.data || page.seed || ({})
    property int favTick: 0
    Connections { target: tidal; function onFavoritesChanged() { page.favTick++ } }
    readonly property bool fav: favTick >= 0 && tidal.isFavorite("artist", page.itemId)
    readonly property var top: req.data ? req.data.top : []

    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.s3
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.s4
            Rectangle {
                implicitWidth: 110; implicitHeight: 110; radius: 55
                color: Theme.field
                clip: true
                Image { anchors.fill: parent; source: page.info.cover || ""; sourceSize.width: 320; fillMode: Image.PreserveAspectCrop; asynchronous: true }
            }
            ColumnLayout {
                Layout.fillWidth: true
                spacing: Theme.s1
                Text { text: qsTr("ARTIST"); color: Theme.textSecondary; font.pixelSize: Theme.caption; font.letterSpacing: 0.6 }
                Text { text: page.info.title || ""; color: Theme.text; font.pixelSize: Theme.largeTitle; font.weight: Font.DemiBold; elide: Text.ElideRight; Layout.fillWidth: true }
                Text {
                    visible: !!req.data
                    text: req.data ? qsTr("%1 albums · %2 singles & EPs · %3 videos").arg(req.data.albums.length).arg(req.data.singles.length).arg(req.data.videos.length) : ""
                    color: Theme.textSecondary; font.pixelSize: Theme.footnote
                }
                Flow {
                    Layout.fillWidth: true
                    spacing: Theme.s1
                    AppButton { text: qsTr("Play"); iconName: "play"; kind: "primary"; enabled: page.top.length > 0
                                onClicked: tidal.playerObject.playItems(page.top, 0, qsTr("Artist: ") + (page.info.title || "")) }
                    AppButton { text: qsTr("Shuffle"); iconName: "shuffle"; enabled: page.top.length > 0
                                onClicked: tidal.playerObject.shuffleItems(page.top, qsTr("Artist: ") + (page.info.title || "")) }
                    IconButton { iconName: "heart"; tint: page.fav ? Theme.accent : Theme.textSecondary
                                 tip: page.fav ? qsTr("Unfollow") : qsTr("Follow (add to collection)")
                                 onClicked: tidal.toggleFavorite("artist", page.itemId) }
                    IconButton { iconName: "download"; tip: qsTr("Download the artist (TIDAL options: artist singles)")
                                 onClicked: page.ctl.download([page.info]) }
                    IconButton { iconName: "share"; tip: qsTr("Copy link"); onClicked: tidal.copyLink(page.info.url || "") }
                    IconButton { iconName: "open"; tip: qsTr("Open in TIDAL Web"); onClicked: page.ctl.openInWeb(page.info.url || "") }
                }
            }
        }
        Segmented {
            Layout.fillWidth: true
            Layout.maximumWidth: 640
            current: page.tab
            options: [{ text: qsTr("Top tracks"), value: "top" }, { text: qsTr("Albums"), value: "albums" },
                      { text: qsTr("Singles & EPs"), value: "singles" }, { text: qsTr("Videos"), value: "videos" },
                      { text: qsTr("Similar"), value: "similar" }]
            onActivated: (v) => page.tab = v
        }
        TidalTrackList {
            visible: page.tab === "top"
            Layout.fillWidth: true
            Layout.fillHeight: true
            items: page.top
            ctl: page.ctl
            source: qsTr("Artist: ") + (page.info.title || "")
        }
        TidalGrid {
            visible: page.tab !== "top"
            Layout.fillWidth: true
            Layout.fillHeight: true
            ctl: page.ctl
            items: req.data ? (req.data[page.tab] || []) : []
        }
    }
    TidalStatus { anchors.centerIn: parent; request: req; empty: false }
}
