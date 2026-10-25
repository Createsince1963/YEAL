import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// The playlist panel of the track player: a search field and four tabs - Queue (what plays next, click to jump,
// X removes), Playlists (click plays), Search results (click plays) and Lyrics (timed lines follow the music,
// click a line to jump there).
Rectangle {
    id: panel
    property var ctl                               // TidalHome
    property string tab: "queue"                   // queue | playlists | results | lyrics | library | played
    property bool showTabs: true                   // false: the panel is one card of the planet view and shows just its tab
    property bool showSearch: true
    property string query: ""
    property var player: tidal.playerObject
    property bool local: false                     // downloaded files: tabs Library and Queue, the field filters the library
    property string filter: ""
    readonly property var libraryShown: {
        var lib = player.library || [], f = filter.toLowerCase(), out = []
        for (var i = 0; i < lib.length; ++i)
            if (f === "" || ((lib[i].title || "") + " " + (lib[i].subtitle || "") + " " + (lib[i].source || "")).toLowerCase().indexOf(f) >= 0)
                out.push({ item: lib[i], index: i })
        return out
    }
    onTabChanged: if (local && tab === "library") player.refreshLibrary()
    Component.onCompleted: if (local) player.refreshLibrary()

    radius: 26
    color: Theme.surface
    border.width: 1
    border.color: Qt.alpha(Theme.text, 0.18)
    clip: true

    TidalRequest { id: req; route: panel.query !== "" ? "search" : ""; arg: panel.query }
    readonly property var found: req.data && req.data.tracks ? req.data.tracks : []

    // one list row: cover, title, artist, length
    component Row_: Rectangle {
        id: row
        property string cover
        property string title
        property string sub
        property string time
        property bool current: false
        property bool removable: false
        signal activated()
        signal removed()
        signal menu()
        width: ListView.view ? ListView.view.width - 6 : 200
        height: 46
        radius: 10
        color: current ? Qt.alpha(Theme.text, 0.10) : hover.hovered ? Qt.alpha(Theme.text, 0.06) : "transparent"
        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 6; anchors.rightMargin: 8
            spacing: Theme.s2
            Rectangle {
                implicitWidth: 34; implicitHeight: 34; radius: 5
                color: Theme.field; clip: true
                Image { anchors.fill: parent; source: row.cover; sourceSize.width: 80; fillMode: Image.PreserveAspectCrop; asynchronous: true }
            }
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 0
                Text { text: row.title; Layout.fillWidth: true; elide: Text.ElideRight
                       color: row.current ? Theme.text : Theme.text; font.pixelSize: Theme.footnote
                       font.weight: row.current ? Font.Bold : Font.Medium }
                Text { text: row.sub; Layout.fillWidth: true; elide: Text.ElideRight
                       color: Theme.textSecondary; font.pixelSize: Theme.caption }
            }
            Text { text: row.time; color: Theme.textTertiary; font.pixelSize: Theme.caption; font.family: "Consolas" }
            IconButton { visible: row.removable && hover.hovered; implicitWidth: 24; implicitHeight: 24; iconName: "x"
                         tip: qsTr("Remove"); onClicked: row.removed() }
        }
        HoverHandler { id: hover; cursorShape: Qt.PointingHandCursor }
        TapHandler { onTapped: row.activated() }
        TapHandler { acceptedButtons: Qt.RightButton; onTapped: row.menu() }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.s3
        spacing: Theme.s2

        AppField {
            id: search
            visible: panel.showSearch
            Layout.fillWidth: true
            implicitHeight: 36
            placeholderText: panel.local ? qsTr("Filter your downloads") : qsTr("What do you want to listen to?")
            onTextChanged: if (panel.local) panel.filter = text
            background: Rectangle { radius: height / 2; color: Qt.alpha(Theme.text, 0.07) }
            leftPadding: 38
            onAccepted: {
                if (panel.local || text.trim() === "") return
                panel.query = text.trim()
                panel.tab = "results"
            }
            Icon { anchors.left: parent.left; anchors.leftMargin: 12; anchors.verticalCenter: parent.verticalCenter
                   name: "search"; size: 16; color: Theme.textTertiary }
        }
        Row {
            visible: panel.showTabs
            spacing: Theme.s4
            Layout.leftMargin: Theme.s2
            Repeater {
                model: panel.local ? [{ t: qsTr("Library"), v: "library" }, { t: qsTr("Queue"), v: "queue" }, { t: qsTr("Played"), v: "played" }]
                                   : [{ t: qsTr("Queue"), v: "queue" }, { t: qsTr("Playlists"), v: "playlists" },
                                      { t: qsTr("Search results"), v: "results" }, { t: qsTr("Lyrics"), v: "lyrics" },
                                      { t: qsTr("Played"), v: "played" }]
                delegate: Text {
                    required property var modelData
                    text: modelData.t
                    color: panel.tab === modelData.v ? Theme.text : Theme.textTertiary
                    font.pixelSize: Theme.footnote
                    font.weight: panel.tab === modelData.v ? Font.Bold : Font.Normal
                    HoverHandler { cursorShape: Qt.PointingHandCursor }
                    TapHandler { onTapped: panel.tab = modelData.v }
                }
            }
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: ["queue", "playlists", "results", "library", "lyrics", "played"].indexOf(panel.tab)

            // ---- queue
            ListView {
                id: queueList
                clip: true
                spacing: 2
                model: panel.player.queueModel
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
                onVisibleChanged: if (visible && panel.player.currentIndex >= 0) positionViewAtIndex(panel.player.currentIndex, ListView.Beginning)
                delegate: Row_ {
                    required property var model
                    required property int index
                    cover: model.cover
                    title: model.title
                    sub: model.subtitle
                    time: panel.ctl ? panel.ctl.fmt(model.duration) : ""
                    current: model.isCurrent
                    removable: true
                    onActivated: panel.player.playIndex(index)
                    onRemoved: panel.player.removeAt(index)
                }
                TidalQueueDrop { anchors.fill: parent; list: queueList; z: 5 }
                Text {
                    anchors.centerIn: parent
                    visible: queueList.count === 0
                    width: parent.width - 2 * Theme.s4
                    horizontalAlignment: Text.AlignHCenter; wrapMode: Text.Wrap
                    text: qsTr("Nothing queued. Pick a playlist, search for a song or drag titles here.")
                    color: Theme.textTertiary; font.pixelSize: Theme.caption
                }
            }

            // ---- playlists
            ListView {
                clip: true
                spacing: 2
                model: tidal.playlists
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
                delegate: Row_ {
                    required property var modelData
                    cover: modelData.cover || ""
                    title: modelData.title || ""
                    sub: modelData.mine ? qsTr("%1 titles").arg(modelData.tracks) : (modelData.subtitle || "")
                    onActivated: panel.ctl.playItem(modelData)
                    onMenu: panel.ctl.itemMenu(modelData, [])
                }
            }

            // ---- search results
            ListView {
                id: resultList
                clip: true
                spacing: 2
                model: panel.found
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
                delegate: Row_ {
                    required property var modelData
                    required property int index
                    cover: modelData.cover || ""
                    title: modelData.title || ""
                    sub: modelData.subtitle || ""
                    time: panel.ctl ? panel.ctl.fmt(modelData.duration) : ""
                    onActivated: panel.player.playItems(panel.found, index, qsTr("Search: %1").arg(panel.query))
                    onMenu: panel.ctl.itemMenu(modelData, [])
                }
                TidalStatus { anchors.centerIn: parent; request: req; empty: panel.query !== "" && panel.found.length === 0 }
                Text {
                    anchors.centerIn: parent
                    visible: panel.query === ""
                    text: qsTr("Type in the search field above and press Enter.")
                    color: Theme.textTertiary; font.pixelSize: Theme.caption
                }
            }

            // ---- library of finished downloads (player for downloaded files)
            ListView {
                id: libList
                clip: true
                spacing: 2
                model: panel.libraryShown
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
                delegate: Row_ {
                    required property var modelData
                    cover: modelData.item.cover || ""
                    title: modelData.item.title || ""
                    sub: (modelData.item.subtitle || "") + (modelData.item.source && modelData.item.source !== modelData.item.title ? "  ·  " + modelData.item.source : "")
                    current: !!panel.player.current && panel.player.current.id === modelData.item.id
                    onActivated: panel.player.playLibrary(modelData.index)
                }
                Text {
                    anchors.centerIn: parent
                    visible: libList.count === 0
                    width: parent.width - 2 * Theme.s4
                    horizontalAlignment: Text.AlignHCenter; wrapMode: Text.Wrap
                    text: panel.filter !== "" ? qsTr("Nothing found.") : qsTr("Finished audio downloads appear here.")
                    color: Theme.textTertiary; font.pixelSize: Theme.caption
                }
            }

            // ---- played songs of this session, newest first
            ListView {
                id: playedList
                clip: true
                spacing: 2
                model: panel.player.history
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
                delegate: Row_ {
                    required property var modelData
                    required property int index
                    cover: modelData.cover || ""
                    title: modelData.title || ""
                    sub: modelData.subtitle || ""
                    current: index === 0
                    onActivated: panel.player.playHistory(index)
                }
                Text {
                    anchors.centerIn: parent
                    visible: playedList.count === 0
                    width: parent.width - 2 * Theme.s4
                    horizontalAlignment: Text.AlignHCenter; wrapMode: Text.Wrap
                    text: qsTr("The songs you listened to appear here.")
                    color: Theme.textTertiary; font.pixelSize: Theme.caption
                }
            }

            // ---- lyrics
            ListView {
                id: lyr
                clip: true
                readonly property var synced: panel.player.lyrics && panel.player.lyrics.synced ? panel.player.lyrics.synced : []
                readonly property int line: {
                    var pos = panel.player.position, n = -1
                    for (var i = 0; i < synced.length; ++i) { if (synced[i][0] <= pos) n = i; else break }
                    return n
                }
                onLineChanged: if (line >= 0 && visible) positionViewAtIndex(line, ListView.Center)
                model: synced.length ? synced : (panel.player.lyrics && panel.player.lyrics.text ? panel.player.lyrics.text.split("\n") : [])
                ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
                delegate: Text {
                    required property var modelData
                    required property int index
                    width: lyr.width - Theme.s2
                    text: lyr.synced.length ? modelData[1] : modelData
                    color: lyr.synced.length && index === lyr.line ? Theme.text : (lyr.synced.length && index < lyr.line ? Theme.textTertiary : Theme.textSecondary)
                    font.pixelSize: lyr.synced.length && index === lyr.line ? Theme.body : Theme.footnote
                    font.weight: lyr.synced.length && index === lyr.line ? Font.Bold : Font.Normal
                    wrapMode: Text.Wrap
                    topPadding: 3; bottomPadding: 3
                    TapHandler { enabled: lyr.synced.length > 0; onTapped: panel.player.seek(lyr.synced[index][0]) }
                }
                Text {
                    anchors.centerIn: parent
                    visible: lyr.count === 0
                    text: panel.player.currentIndex < 0 ? qsTr("Lyrics appear here while a song plays.") : qsTr("No lyrics for this song.")
                    color: Theme.textTertiary; font.pixelSize: Theme.caption
                }
            }
        }
    }
}
