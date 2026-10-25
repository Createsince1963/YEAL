import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// Album / playlist / mix page of the TIDAL DIY view. Compact header (cover, facts, one action bar) and the track
// table as the main content; more albums, similar artists, credits and info sit in tabs instead of below.
Item {
    id: page
    property var ctl
    property string kind: "album"        // album | playlist | mix
    property string itemId: ""
    property var seed: ({})              // what the tile already knew (shown until the page is loaded)
    property string tab: "tracks"
    TidalRequest { id: req; route: page.kind; arg: page.itemId }
    readonly property var info: req.data || page.seed || ({})
    readonly property var tracks: (req.data && req.data.items) ? req.data.items : []
    readonly property bool mine: page.kind === "playlist" && !!info.mine
    readonly property string source: (page.kind === "album" ? qsTr("Album") : page.kind === "playlist" ? qsTr("Playlist") : qsTr("Mix")) + ": " + (info.title || "")
    property int favTick: 0
    Connections { target: tidal; function onFavoritesChanged() { page.favTick++ } }
    readonly property bool fav: favTick >= 0 && tidal.isFavorite(page.kind, page.itemId)

    // the artist page (for "More albums" / "Similar artists") is loaded only when needed
    TidalRequest { id: artistReq; auto: false; route: "artist"; arg: page.info.artistId || "" }
    readonly property bool wantArtist: page.kind === "album" && (page.tab === "more" || page.tab === "similar" || page.tracks.length > 0 && page.tracks.length <= 4)
    onWantArtistChanged: if (wantArtist && !artistReq.data && !artistReq.loading && (info.artistId || "") !== "") artistReq.reload()
    Connections { target: req; function onLoaded() { if (page.wantArtist && !artistReq.data) artistReq.reload() } }
    TidalRequest { id: creditsReq; auto: false; route: "credits"; arg: page.itemId }

    function totalTime() {
        var s = 0
        for (var i = 0; i < tracks.length; ++i) s += tracks[i].duration || 0
        return s || info.duration || 0
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.s3

        // ---- compact header
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.s4
            Rectangle {
                implicitWidth: 120; implicitHeight: 120; radius: 10
                color: Theme.field
                clip: true
                Image { anchors.fill: parent; source: page.info.coverLarge || page.info.cover || ""; sourceSize.width: 320; fillMode: Image.PreserveAspectCrop; asynchronous: true }
            }
            ColumnLayout {
                Layout.fillWidth: true
                spacing: Theme.s1
                Text {
                    text: (page.kind === "album" ? (page.info.type === "SINGLE" ? qsTr("SINGLE") : page.info.type === "EP" ? "EP" : qsTr("ALBUM"))
                           : page.kind === "playlist" ? qsTr("PLAYLIST") : qsTr("MIX"))
                    color: Theme.textSecondary; font.pixelSize: Theme.caption; font.letterSpacing: 0.6
                }
                Text {
                    text: page.info.title || ""
                    color: Theme.text; font.pixelSize: Theme.title; font.weight: Font.DemiBold
                    elide: Text.ElideRight; Layout.fillWidth: true
                }
                RowLayout {
                    spacing: Theme.s2
                    Text {
                        text: page.info.subtitle || ""
                        color: artistHover.hovered ? Theme.accent : Theme.text
                        font.pixelSize: Theme.body
                        HoverHandler { id: artistHover; enabled: !!page.info.artistId; cursorShape: Qt.PointingHandCursor }
                        TapHandler { enabled: !!page.info.artistId; onTapped: page.ctl.open({ kind: "artist", id: page.info.artistId, title: page.info.subtitle }) }
                    }
                    Text {
                        text: [page.info.year || "", page.tracks.length ? qsTr("%1 titles").arg(page.tracks.length) : (page.info.tracks ? qsTr("%1 titles").arg(page.info.tracks) : ""),
                               page.ctl ? page.ctl.fmtLong(page.totalTime()) : ""].filter(function (x) { return x !== "" }).join(" · ")
                        color: Theme.textSecondary; font.pixelSize: Theme.footnote
                    }
                    Badge { visible: page.info.quality === "MAX"; text: "MAX"; kind: "accent" }
                    Badge { visible: page.info.quality === "HiFi"; text: "HiFi" }
                }
                Text {
                    visible: text !== ""
                    text: page.kind === "playlist" ? (page.info.description || "") : (page.info.copyright || "")
                    color: Theme.textTertiary; font.pixelSize: Theme.caption
                    elide: Text.ElideRight; maximumLineCount: 1; Layout.fillWidth: true
                }
                // ---- one action bar
                Flow {
                    Layout.fillWidth: true
                    Layout.topMargin: Theme.s1
                    spacing: Theme.s1
                    AppButton { text: qsTr("Play"); iconName: "play"; kind: "primary"; enabled: page.tracks.length > 0
                                onClicked: tidal.playerObject.playItems(page.tracks, 0, page.source) }
                    AppButton { text: qsTr("Shuffle"); iconName: "shuffle"; enabled: page.tracks.length > 0
                                onClicked: tidal.playerObject.shuffleItems(page.tracks, page.source) }
                    IconButton { iconName: "queue"; tip: qsTr("Add to the queue"); enabled: page.tracks.length > 0
                                 onClicked: tidal.playerObject.queueAdd(page.tracks) }
                    IconButton { visible: page.kind !== "mix"; iconName: "heart"; tint: page.fav ? Theme.accent : Theme.textSecondary
                                 tip: page.fav ? qsTr("Remove from collection") : qsTr("Add to collection")
                                 onClicked: tidal.toggleFavorite(page.kind, page.itemId) }
                    IconButton { iconName: "download"; tip: list.pickedCount > 0 ? qsTr("Download the selected titles") : qsTr("Download all")
                                 onClicked: list.pickedCount > 0 ? page.ctl.download(list.pickedItems()) : page.ctl.download([page.info]) }
                    IconButton { iconName: "doc"; tip: qsTr("Save as HTML link list (Tidal links, nothing is downloaded)")
                                 onClicked: tidal.saveLinklist(page.kind, page.itemId) }
                    IconButton { iconName: "share"; tip: qsTr("Copy link"); onClicked: tidal.copyLink(page.info.url || "") }
                    IconButton { visible: page.mine; iconName: "pencil"; tip: qsTr("Rename playlist")
                                 onClicked: page.ctl.askName(qsTr("Rename playlist"), page.info.title || "", function (t) { tidal.renamePlaylist(page.itemId, t) }) }
                    IconButton { visible: page.mine; iconName: "trash"; tip: qsTr("Delete playlist")
                                 onClicked: page.ctl.confirm(qsTr("Delete the playlist \"%1\" in your Tidal account?").arg(page.info.title || ""),
                                                             function () { tidal.deletePlaylist(page.itemId); page.ctl.back() }) }
                    IconButton { iconName: "open"; tip: qsTr("Open in TIDAL Web"); onClicked: page.ctl.openInWeb(page.info.url || "") }
                }
            }
        }

        // ---- tabs
        Segmented {
            id: tabs
            Layout.fillWidth: true
            Layout.maximumWidth: 640
            current: page.tab
            options: page.kind === "album"
                     ? [{ text: qsTr("Titles"), value: "tracks" }, { text: qsTr("More albums"), value: "more" },
                        { text: qsTr("Similar artists"), value: "similar" }, { text: qsTr("Credits"), value: "credits" }, { text: qsTr("Info"), value: "info" }]
                     : [{ text: qsTr("Titles"), value: "tracks" }, { text: qsTr("Info"), value: "info" }]
            onActivated: (v) => { page.tab = v; if (v === "credits" && !creditsReq.data) creditsReq.reload() }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: Theme.s4
            visible: page.tab === "tracks"
            TidalTrackList {
                id: list
                Layout.fillWidth: true
                Layout.fillHeight: true
                items: page.tracks
                ctl: page.ctl
                source: page.source
                albumNumbers: page.kind === "album"
                showAlbum: page.kind !== "album"
                showCover: page.kind !== "album"
                playlistId: page.mine ? page.itemId : ""
            }
            // few titles (single / EP): more of the artist right next to it, so the page is not empty
            TidalGrid {
                visible: page.kind === "album" && page.tracks.length > 0 && page.tracks.length <= 4
                Layout.preferredWidth: Math.min(page.width * 0.45, 520)
                Layout.fillHeight: true
                ctl: page.ctl
                title: qsTr("More by %1").arg(page.info.subtitle || "")
                items: artistReq.data ? artistReq.data.albums.concat(artistReq.data.singles).filter(function (a) { return a.id !== page.itemId }) : []
            }
        }
        TidalGrid {
            visible: page.tab === "more"
            Layout.fillWidth: true
            Layout.fillHeight: true
            ctl: page.ctl
            items: artistReq.data ? artistReq.data.albums.concat(artistReq.data.singles).filter(function (a) { return a.id !== page.itemId }) : []
        }
        TidalGrid {
            visible: page.tab === "similar"
            Layout.fillWidth: true
            Layout.fillHeight: true
            ctl: page.ctl
            items: artistReq.data ? artistReq.data.similar : []
        }
        ListView {      // credits per track
            visible: page.tab === "credits"
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            spacing: Theme.s2
            model: visible && creditsReq.data ? creditsReq.data : []
            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
            delegate: ColumnLayout {
                required property var modelData
                required property int index
                width: ListView.view.width - Theme.s2
                spacing: 2
                Text { text: (index + 1) + ". " + modelData.title; color: Theme.text; font.pixelSize: Theme.footnote; font.weight: Font.Medium }
                Repeater {
                    model: modelData.credits
                    delegate: Text {
                        required property var modelData
                        text: modelData.role + ": " + modelData.names
                        color: Theme.textSecondary; font.pixelSize: Theme.caption
                        wrapMode: Text.Wrap; Layout.fillWidth: true; leftPadding: Theme.s4
                    }
                }
            }
            TidalStatus { anchors.centerIn: parent; request: creditsReq; empty: false }
        }
        ColumnLayout {  // info
            visible: page.tab === "info"
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: Theme.s2
            Repeater {
                model: [[qsTr("Title"), page.info.title], [qsTr("By"), page.info.subtitle], [qsTr("Released"), page.info.date],
                        [qsTr("Titles"), page.tracks.length], [qsTr("Length"), page.ctl ? page.ctl.fmtLong(page.totalTime()) : ""],
                        [qsTr("Quality"), page.info.quality], ["©", page.info.copyright], [qsTr("Description"), page.info.description],
                        [qsTr("Link"), page.info.url]].filter(function (r) { return r[1] !== undefined && r[1] !== "" && r[1] !== 0 })
                delegate: RowLayout {
                    required property var modelData
                    Layout.fillWidth: true
                    spacing: Theme.s3
                    Text { text: modelData[0]; color: Theme.textSecondary; font.pixelSize: Theme.footnote; Layout.preferredWidth: 110 }
                    TextEdit { text: String(modelData[1]); readOnly: true; selectByMouse: true; color: Theme.text; font.pixelSize: Theme.footnote; wrapMode: Text.Wrap; Layout.fillWidth: true }
                }
            }
            Item { Layout.fillHeight: true }
        }
    }
    TidalStatus { anchors.centerIn: parent; request: req; empty: false }
}
