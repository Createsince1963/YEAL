import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// TIDAL DIY: Yeal's own TIDAL view (0.9.1). Created on first use by DownloadsPage.qml, then kept alive.
// Not signed in -> sign-in prompt with the subscription notice. Signed in: playlists | pages + queue, player bar below.
// Every page component gets this item as `ctl` and uses the functions below (open, playItem, itemMenu, download ...).
Item {
    id: home
    signal videoLink(string url)         // a TIDAL item was opened: canonical link for the workflow panel
    signal webRequested(string url)      // show this link in the TIDAL Web view

    // ---- state used by the pages
    readonly property int tileSize: backend.settings.tidal_tile_size || 140
    property string currentId: ""
    property var hist: []                // visited pages: { page, route, arg, title, kind, itemId, seed, items, more }
    property int pos: -1
    readonly property var cur: pos >= 0 && pos < hist.length ? hist[pos] : ({})
    readonly property string tab: cur.page === "shelf" && (cur.route === "home" || cur.route === "explore") ? cur.route
                                  : cur.page === "feed" ? "feed" : cur.page === "collection" ? "collection" : ""

    function pausePlayback() { tidal.playerObject.pause() }
    function setTileSize(v) { backend.setSetting("tidal_tile_size", Math.round(v)) }
    function fmt(sec) {
        sec = Math.max(0, Math.round(sec || 0))
        return Math.floor(sec / 60) + ":" + ("0" + (sec % 60)).slice(-2)
    }
    function fmtLong(sec) {
        var m = Math.round((sec || 0) / 60)
        if (m < 60) return qsTr("%1 min").arg(m)
        return qsTr("%1 h %2 min").arg(Math.floor(m / 60)).arg(("0" + (m % 60)).slice(-2))
    }

    // ---- navigation
    function go(desc) {
        var h = hist.slice(0, pos + 1)
        h.push(desc)
        hist = h
        pos = h.length - 1
        render()
    }
    function back() { if (pos > 0) { pos--; render() } }
    function forward() { if (pos < hist.length - 1) { pos++; render() } }
    function render() {
        currentId = cur.itemId || ""
        pageLoader.sourceComponent = null
        var p = cur.page
        pageLoader.sourceComponent = p === "detail" ? detailC : p === "artist" ? artistC : p === "grid" ? gridC
                                     : p === "feed" ? feedC : p === "collection" ? collectionC : shelfC
    }
    function goTab(t) {
        if (t === "feed") go({ page: "feed" })
        else if (t === "collection") go({ page: "collection" })
        else go({ page: "shelf", route: t, arg: "", title: "" })
    }
    function open(item) {
        if (!item) return
        if (item.url) home.videoLink(item.url)
        var k = item.kind
        if (k === "album" || k === "playlist" || k === "mix")
            go({ page: "detail", kind: k, itemId: String(item.id), seed: item })
        else if (k === "artist")
            go({ page: "artist", itemId: String(item.id), seed: item })
        else if (k === "link")
            go({ page: "shelf", route: "page", arg: String(item.id), title: item.title || "" })
        else if (k === "track")
            playItem(item)
        else if (k === "video")
            openInWeb(item.url)
    }
    function openList(title, more, items) {
        go({ page: "grid", title: title, route: more !== "" ? "more" : "", arg: more || "", items: more !== "" ? [] : items })
    }
    function search(text) { go({ page: "shelf", route: "search", arg: text, title: qsTr("Search: %1").arg(text) }) }
    function openInWeb(url) { if (url) home.webRequested(url) }

    // ---- playing
    property string _playReq: ""
    property string _playTitle: ""
    function playItem(item) {
        if (!item) return
        if (item.kind === "track") { tidal.playerObject.playItems([item], 0, ""); return }
        if (item.kind === "video") { openInWeb(item.url); return }
        if (["album", "playlist", "mix", "artist"].indexOf(item.kind) < 0) return
        _playTitle = item.title || ""
        _playReq = tidal.load(item.kind, String(item.id))
    }
    Connections {
        target: tidal
        function onPageLoaded(rid, route, data) {
            if (rid !== home._playReq) return
            home._playReq = ""
            var list = data ? (data.items || data.top || []) : []
            if (list.length) tidal.playerObject.playItems(list, 0, home._playTitle)
        }
        function onPageFailed(rid, route, message) {
            if (rid === home._playReq) { home._playReq = ""; backend.notify(message) }
        }
    }

    // ---- downloads
    function download(items) {
        var urls = []
        for (var i = 0; i < (items || []).length; ++i) if (items[i] && items[i].url) urls.push(items[i].url)
        if (urls.length === 0) { backend.notify(qsTr("Nothing to download.")); return }
        tidal.download(urls)
    }

    // ---- small dialogs: ask for a name, confirm
    property var _nameDone: null
    property var _confirmDone: null
    function askName(title, text, done) {
        nameDialog.title = title
        nameField.text = text || ""
        _nameDone = done
        nameDialog.open()
        nameField.forceActiveFocus()
        nameField.selectAll()
    }
    function confirm(text, done) {
        confirmText.text = text
        _confirmDone = done
        confirmDialog.open()
    }

    // ---- playlists: pick one (or create a new one) for the given track ids
    property var _pickIds: []
    function addToPlaylist(trackIds) {
        _pickIds = trackIds || []
        listMenu.popup()
    }

    // ---- context menu of tiles, rows and playlists
    function itemMenu(item, extra) {
        itemMenuPopup.it = item
        itemMenuPopup.extra = extra || []
        itemMenuPopup.popup()
    }
    AppMenu {
        id: itemMenuPopup
        property var it: ({})
        property var extra: []
        readonly property bool isTrack: it.kind === "track"
        readonly property bool listable: ["album", "playlist", "mix"].indexOf(it.kind) >= 0
        readonly property bool favable: ["track", "album", "artist", "playlist"].indexOf(it.kind) >= 0 && !it.mine
        property int favTick: 0
        Connections { target: tidal; function onFavoritesChanged() { itemMenuPopup.favTick++ } }
        AppMenuItem { text: qsTr("Play"); iconName: "play"; enabled: itemMenuPopup.it.kind !== "link"
                      onTriggered: home.playItem(itemMenuPopup.it) }
        AppMenuItem { text: qsTr("Play next"); iconName: "queue"; enabled: itemMenuPopup.isTrack
                      onTriggered: tidal.playerObject.queueNext([itemMenuPopup.it]) }
        AppMenuItem { text: qsTr("Add to queue"); iconName: "listAdd"; enabled: itemMenuPopup.isTrack
                      onTriggered: tidal.playerObject.queueAdd([itemMenuPopup.it]) }
        AppMenuItem { text: qsTr("Open"); iconName: "open"; enabled: !itemMenuPopup.isTrack
                      onTriggered: home.open(itemMenuPopup.it) }
        AppMenuItem {
            text: itemMenuPopup.favTick >= 0 && tidal.isFavorite(itemMenuPopup.it.kind || "", String(itemMenuPopup.it.id || ""))
                  ? qsTr("Remove from collection") : qsTr("Add to collection")
            iconName: "heart"
            enabled: itemMenuPopup.favable
            onTriggered: tidal.toggleFavorite(itemMenuPopup.it.kind, String(itemMenuPopup.it.id))
        }
        AppMenuItem { text: qsTr("Add to playlist…"); iconName: "listAdd"; enabled: itemMenuPopup.isTrack
                      onTriggered: home.addToPlaylist([String(itemMenuPopup.it.id)]) }
        AppMenuItem { text: qsTr("Download"); iconName: "download"; enabled: !!itemMenuPopup.it.url
                      onTriggered: home.download([itemMenuPopup.it]) }
        AppMenuItem { text: qsTr("Save as HTML link list"); iconName: "doc"; enabled: itemMenuPopup.listable
                      onTriggered: tidal.saveLinklist(itemMenuPopup.it.kind, String(itemMenuPopup.it.id)) }
        AppMenuItem { text: qsTr("Copy link"); iconName: "link"; enabled: !!itemMenuPopup.it.url
                      onTriggered: tidal.copyLink(itemMenuPopup.it.url) }
        AppMenuItem { text: qsTr("Open in TIDAL Web"); iconName: "open"; enabled: !!itemMenuPopup.it.url
                      onTriggered: home.openInWeb(itemMenuPopup.it.url) }
        Instantiator {       // page specific extras: [{ text, action }]
            model: itemMenuPopup.extra
            delegate: AppMenuItem {
                required property var modelData
                text: modelData.text
                onTriggered: modelData.action()
            }
            onObjectAdded: (i, o) => itemMenuPopup.addItem(o)
            onObjectRemoved: (i, o) => itemMenuPopup.removeItem(o)
        }
    }
    AppMenu {
        id: listMenu
        AppMenuItem { text: qsTr("New playlist…"); iconName: "plus"
                      onTriggered: home.askName(qsTr("New playlist"), "", function (t) { tidal.createPlaylist(t, home._pickIds) }) }
        Instantiator {
            model: tidal.myPlaylists
            delegate: AppMenuItem {
                required property var modelData
                text: modelData.title || ""
                onTriggered: tidal.addToPlaylist(String(modelData.id), home._pickIds)
            }
            onObjectAdded: (i, o) => listMenu.addItem(o)
            onObjectRemoved: (i, o) => listMenu.removeItem(o)
        }
    }

    Popup {
        id: nameDialog
        property string title
        parent: Overlay.overlay
        anchors.centerIn: parent
        modal: true
        width: Math.min(parent.width - 2 * Theme.s6, 400)
        padding: Theme.s4
        background: Rectangle { radius: Theme.radius + 2; color: Theme.raised; border.width: 1; border.color: Theme.separator }
        ColumnLayout {
            anchors.fill: parent
            spacing: Theme.s3
            Text { text: nameDialog.title; color: Theme.text; font.pixelSize: Theme.headline; font.weight: Font.DemiBold; Layout.fillWidth: true }
            AppField {
                id: nameField
                Layout.fillWidth: true
                onAccepted: okName.clicked()
            }
            RowLayout {
                Layout.alignment: Qt.AlignRight
                spacing: Theme.s2
                AppButton { text: qsTr("Cancel"); kind: "plain"; onClicked: nameDialog.close() }
                AppButton {
                    id: okName
                    text: qsTr("OK"); kind: "primary"
                    enabled: nameField.text.trim() !== ""
                    onClicked: {
                        var cb = home._nameDone
                        nameDialog.close()
                        if (cb) cb(nameField.text.trim())
                    }
                }
            }
        }
    }
    Popup {
        id: confirmDialog
        parent: Overlay.overlay
        anchors.centerIn: parent
        modal: true
        width: Math.min(parent.width - 2 * Theme.s6, 400)
        padding: Theme.s4
        background: Rectangle { radius: Theme.radius + 2; color: Theme.raised; border.width: 1; border.color: Theme.separator }
        ColumnLayout {
            anchors.fill: parent
            spacing: Theme.s3
            Text { id: confirmText; color: Theme.text; font.pixelSize: Theme.body; wrapMode: Text.Wrap; Layout.fillWidth: true }
            RowLayout {
                Layout.alignment: Qt.AlignRight
                spacing: Theme.s2
                AppButton { text: qsTr("Cancel"); kind: "plain"; onClicked: confirmDialog.close() }
                AppButton {
                    text: qsTr("OK"); kind: "primary"
                    onClicked: {
                        var cb = home._confirmDone
                        confirmDialog.close()
                        if (cb) cb()
                    }
                }
            }
        }
    }

    // ---- layout of the areas (setting tidal_layout, validated in core/settings.py)
    // Playlists and queue can sit left or right, be detached into their own window or be hidden; the player bar sits
    // on top or at the bottom. Dock changes are saved at once, window moves after a short pause.
    readonly property var lay: backend.settings.tidal_layout || ({})
    readonly property bool playerTop: lay.player === "top"
    property var _pending: null          // layout waiting to be saved
    property var _prevSide: ({})         // where a hidden area comes back
    property string _order: ""
    function pane(k) {
        var d = (_pending || lay)[k] || {}
        var def = k === "playlists" ? { dock: "left", w: 220 } : { dock: "right", w: 300 }
        return { dock: d.dock || def.dock, w: d.w || def.w,
                 x: d.x === undefined ? 100 : d.x, y: d.y === undefined ? 100 : d.y, h: d.h || 600 }
    }
    function _base() { return JSON.parse(JSON.stringify(_pending || lay)) }
    function flushLayout() {
        saveTimer.stop()
        if (!_pending) return
        var l = _pending
        _pending = null
        backend.setSetting("tidal_layout", l)
    }
    function setSide(k, s) {
        var cur = pane(k)
        if (s === "hidden" && cur.dock !== "hidden") _prevSide[k] = cur.dock
        var l = _base()
        l[k] = { dock: s, w: cur.w }
        if (s === "float") { l[k].x = cur.x; l[k].y = cur.y; l[k].h = cur.h }
        _pending = l
        flushLayout()
    }
    function togglePane(k) {
        if (pane(k).dock === "hidden")
            setSide(k, _prevSide[k] && _prevSide[k] !== "hidden" ? _prevSide[k] : (k === "playlists" ? "left" : "right"))
        else
            setSide(k, "hidden")
    }
    function moveFloat(k, x, y, w, h) {
        var l = _base()
        if (!l[k] || l[k].dock !== "float") return
        l[k].x = x; l[k].y = y; l[k].w = w; l[k].h = h
        _pending = l
        saveTimer.restart()
    }
    function setPlayerTop(top) {
        var l = _base()
        l.player = top ? "top" : "bottom"
        _pending = l
        flushLayout()
    }
    function saveWidths() {
        var l = _base()
        var docks = [playlistsDock, queueDock]
        for (var i = 0; i < docks.length; ++i) {
            if (!docks[i].docked) continue
            l[docks[i].paneKey] = { dock: docks[i].side, w: Math.round(docks[i].width) }
        }
        _pending = l
        flushLayout()
    }
    function resetLayout() {
        saveTimer.stop()
        _pending = null
        _prevSide = ({})
        backend.setSetting("tidal_layout", {})
    }
    // children of a SplitView stay in declaration order, so the areas are re-parented in the wanted order
    function arrange() {
        var left = [], right = []
        var docks = [playlistsDock, queueDock]
        for (var i = 0; i < docks.length; ++i) (docks[i].side === "right" ? right : left).push(docks[i])
        var order = left.concat([center], right)
        var key = order.map(function (o) { return o === center ? "c" : o.paneKey }).join(",")
        if (key === _order) return
        _order = key
        for (var a = 0; a < order.length; ++a) order[a].parent = null
        for (var b = 0; b < order.length; ++b) order[b].parent = split
    }

    // ---- pages
    Component { id: shelfC;      TidalShelf { ctl: home; route: home.cur.route || "home"; arg: home.cur.arg || ""; title: home.cur.title || "" } }
    Component { id: feedC;       TidalFeed { ctl: home } }
    Component { id: collectionC; TidalCollection { ctl: home } }
    Component { id: detailC;     TidalDetail { ctl: home; kind: home.cur.kind || "album"; itemId: home.cur.itemId || ""; seed: home.cur.seed || ({}) } }
    Component { id: artistC;     TidalArtist { ctl: home; itemId: home.cur.itemId || ""; seed: home.cur.seed || ({}) } }
    Component { id: gridC;       TidalGrid { ctl: home; title: home.cur.title || ""; route: home.cur.route || ""; arg: home.cur.arg || ""; items: home.cur.items || [] } }

    // ---- not signed in
    Rectangle {
        anchors.fill: parent
        visible: !backend.tidalLoggedIn
        radius: Theme.radius
        color: Theme.surface
        border.width: 1
        border.color: Theme.separator
        EmptyState {
            anchors.centerIn: parent
            width: Math.min(parent.width - 2 * Theme.s6, 520)
            iconName: "music"
            title: qsTr("Sign in to TIDAL")
            subtitle: backend.tidalNotice
            actionText: qsTr("Sign in to TIDAL")
            onAction: {
                var err = backend.tidalLogin()
                if (err) backend.notify(err)
            }
        }
    }

    // ---- signed in: playlists | navigation + page | search + queue, player bar above or below
    GridLayout {
        id: shell
        anchors.fill: parent
        visible: backend.tidalLoggedIn
        columns: 1
        rowSpacing: Theme.s2

        SplitView {
            id: split
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.row: home.playerTop ? 1 : 0
            orientation: Qt.Horizontal
            handle: Rectangle {
                implicitWidth: 6
                color: SplitHandle.pressed || SplitHandle.hovered ? Theme.accentSoft : "transparent"
            }
            onResizingChanged: if (!resizing) home.saveWidths()

            TidalDock {
                id: playlistsDock
                paneKey: "playlists"
                title: qsTr("All playlists")
                defaultSide: "left"
                side: home.pane("playlists").dock
                paneWidth: home.pane("playlists").w
                floatRect: home.pane("playlists")
                maxW: 420
                onSideRequested: (s) => home.setSide("playlists", s)
                onFloatMoved: (x, y, w, h) => home.moveFloat("playlists", x, y, w, h)
                TidalPlaylists { anchors.fill: parent; ctl: home }
            }

            Rectangle {
                id: center
                SplitView.fillWidth: true
                SplitView.minimumWidth: 320
                radius: Theme.radius
                color: Theme.surface
                border.width: 1
                border.color: Theme.separator
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: Theme.s3
                    spacing: Theme.s2
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.s1
                        IconButton { iconName: "back"; tip: qsTr("Back"); enabled: home.pos > 0; onClicked: home.back() }
                        IconButton { iconName: "chevronRight"; tip: qsTr("Forward"); enabled: home.pos < home.hist.length - 1; onClicked: home.forward() }
                        Segmented {
                            current: home.tab
                            options: [{ text: qsTr("Start"), value: "home" }, { text: qsTr("Explore"), value: "explore" },
                                      { text: qsTr("Feed"), value: "feed" }, { text: qsTr("My collection"), value: "collection" }]
                            onActivated: (v) => home.goTab(v)
                        }
                        Item { Layout.fillWidth: true }
                        IconButton { iconName: "library"; tip: qsTr("Show / hide the playlists")
                                     tint: playlistsDock.side !== "hidden" ? Theme.accent : Theme.textSecondary
                                     onClicked: home.togglePane("playlists") }
                        IconButton { iconName: "queueList"; tip: qsTr("Show / hide search and queue")
                                     tint: queueDock.side !== "hidden" ? Theme.accent : Theme.textSecondary
                                     onClicked: home.togglePane("queue") }
                        IconButton { iconName: "dock"; tip: qsTr("Layout: reset the arrangement"); onClicked: home.resetLayout() }
                    }
                    Loader { id: pageLoader; Layout.fillWidth: true; Layout.fillHeight: true; clip: true }
                }
            }

            TidalDock {
                id: queueDock
                paneKey: "queue"
                title: qsTr("Search and queue")
                defaultSide: "right"
                side: home.pane("queue").dock
                paneWidth: home.pane("queue").w
                floatRect: home.pane("queue")
                maxW: 520
                onSideRequested: (s) => home.setSide("queue", s)
                onFloatMoved: (x, y, w, h) => home.moveFloat("queue", x, y, w, h)
                TidalQueue { anchors.fill: parent; ctl: home }
            }
        }

        TidalPlayerBar {
            Layout.fillWidth: true
            Layout.row: home.playerTop ? 0 : 1
            ctl: home
            onToggleQueue: home.togglePane("queue")
            TapHandler { acceptedButtons: Qt.RightButton; onTapped: playerMenu.popup() }
        }
    }
    AppMenu {
        id: playerMenu
        AppMenuItem { text: qsTr("Player bar on top"); enabled: !home.playerTop; onTriggered: home.setPlayerTop(true) }
        AppMenuItem { text: qsTr("Player bar at the bottom"); enabled: home.playerTop; onTriggered: home.setPlayerTop(false) }
    }

    Connections {
        target: backend
        function onTidalChanged() {
            if (!backend.tidalLoggedIn) return
            tidal.refreshLibrary()
            if (home.pos < 0) home.goTab("home")
        }
    }
    Timer { id: saveTimer; interval: 500; onTriggered: home.flushLayout() }
    onLayChanged: Qt.callLater(arrange)
    Component.onCompleted: {
        arrange()
        if (backend.tidalLoggedIn) { tidal.refreshLibrary(); goTab("home") }
    }
    Component.onDestruction: flushLayout()
}
