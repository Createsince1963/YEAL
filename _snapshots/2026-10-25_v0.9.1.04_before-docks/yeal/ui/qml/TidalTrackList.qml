import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// Dense track table of the TIDAL DIY view: filter, sortable columns with draggable widths, tick boxes with
// All / None / Invert and Shift ranges (like PlaylistDialog.qml), and actions for the selection.
ColumnLayout {
    id: list
    property var items: []               // track dicts (core/tidal_api.py)
    property var ctl                     // TidalHome
    property string source: ""           // "Played from" text for the queue
    property bool showAlbum: true
    property bool showCover: true
    property string playlistId: ""       // own playlist: selected rows can be removed
    property bool header: true
    property bool albumNumbers: false    // album: show the track numbers of the album
    spacing: Theme.s1

    // ---- sorting and filtering (rows keep their original position for playlist edits)
    property string sortKey: ""          // "" = original order | title | subtitle | album | duration
    property bool sortAsc: true
    property string filter: ""
    readonly property var rows: {
        var out = []
        var f = filter.toLowerCase()
        for (var i = 0; i < items.length; ++i) {
            var it = items[i]
            if (!it || it.kind !== "track") continue
            if (f !== "" && ((it.title || "") + " " + (it.subtitle || "") + " " + (it.album || "")).toLowerCase().indexOf(f) < 0) continue
            out.push({ item: it, pos: i })
        }
        if (sortKey !== "") {
            var k = sortKey, dir = sortAsc ? 1 : -1
            out.sort(function (a, b) {
                var x = a.item[k], y = b.item[k]
                if (typeof x === "string") return dir * x.localeCompare(y || "")
                return dir * ((x || 0) - (y || 0))
            })
        }
        return out
    }
    function sortBy(k) {
        if (sortKey === k) { if (sortAsc) sortAsc = false; else { sortKey = ""; sortAsc = true } }
        else { sortKey = k; sortAsc = true }
    }

    // ---- selection (by original position)
    property var picked: ({})
    property int anchorPos: -1
    property int pickedCount: 0
    function isPicked(pos) { return picked[pos] === true }
    function setPicked(map) { picked = map; var n = 0; for (var k in map) if (map[k]) n++; pickedCount = n }
    function toggle(pos, shift) {
        var m = Object.assign({}, picked)
        if (shift && anchorPos >= 0) {
            var a = -1, b = -1
            for (var i = 0; i < rows.length; ++i) {
                if (rows[i].pos === anchorPos) a = i
                if (rows[i].pos === pos) b = i
            }
            if (a >= 0 && b >= 0) {
                for (var j = Math.min(a, b); j <= Math.max(a, b); ++j) m[rows[j].pos] = true
                setPicked(m)
                return
            }
        }
        m[pos] = !m[pos]
        anchorPos = pos
        setPicked(m)
    }
    function selectAll() { var m = {}; for (var i = 0; i < rows.length; ++i) m[rows[i].pos] = true; setPicked(m) }
    function selectNone() { setPicked({}) }
    function invert() { var m = {}; for (var i = 0; i < rows.length; ++i) m[rows[i].pos] = !picked[rows[i].pos]; setPicked(m) }
    function pickedItems() {
        var out = []
        for (var i = 0; i < rows.length; ++i) if (picked[rows[i].pos]) out.push(rows[i].item)
        return out
    }
    function pickedPositions() {
        var out = []
        for (var k in picked) if (picked[k]) out.push(parseInt(k))
        return out
    }
    function visibleItems() { return rows.map(function (r) { return r.item }) }
    onItemsChanged: { setPicked({}); anchorPos = -1 }

    property real artistW: 170
    property real albumW: 190
    readonly property string playingId: tidal.playerObject.current && tidal.playerObject.current.id ? tidal.playerObject.current.id : ""

    // ---- filter + selection bar
    RowLayout {
        visible: list.header
        Layout.fillWidth: true
        spacing: Theme.s2
        AppField {
            id: filterField
            placeholderText: qsTr("Filter titles")
            Layout.preferredWidth: 220
            implicitHeight: 32
            onTextChanged: list.filter = text
        }
        Text {
            text: list.pickedCount > 0 ? qsTr("%1 selected").arg(list.pickedCount) : qsTr("%1 titles").arg(list.rows.length)
            color: Theme.textSecondary
            font.pixelSize: Theme.footnote
        }
        Item { Layout.fillWidth: true }
        AppButton { text: qsTr("All"); kind: "plain"; implicitHeight: 30; onClicked: list.selectAll() }
        AppButton { text: qsTr("None"); kind: "plain"; implicitHeight: 30; enabled: list.pickedCount > 0; onClicked: list.selectNone() }
        AppButton { text: qsTr("Invert"); kind: "plain"; implicitHeight: 30; onClicked: list.invert() }
        Row {
            visible: list.pickedCount > 0
            spacing: 0
            IconButton { iconName: "play"; tip: qsTr("Play selection"); onClicked: tidal.playerObject.playItems(list.pickedItems(), 0, list.source) }
            IconButton { iconName: "queue"; tip: qsTr("Add selection to the queue"); onClicked: tidal.playerObject.queueAdd(list.pickedItems()) }
            IconButton { iconName: "listAdd"; tip: qsTr("Add selection to a playlist…")
                         onClicked: list.ctl.addToPlaylist(list.pickedItems().map(function (t) { return t.id })) }
            IconButton { iconName: "download"; tip: qsTr("Download selection"); onClicked: list.ctl.download(list.pickedItems()) }
            IconButton { visible: list.playlistId !== ""; iconName: "trash"; tip: qsTr("Remove selection from this playlist")
                         onClicked: { tidal.removeFromPlaylist(list.playlistId, list.pickedPositions()); list.selectNone() } }
        }
    }

    // ---- column header (click sorts, drag the edges to resize)
    component HeadCell: Item {
        id: hc
        property string label
        property string key
        property real w: -1
        implicitHeight: 24
        Layout.preferredWidth: w
        Layout.fillWidth: w < 0
        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: hc.label + (list.sortKey === hc.key && hc.key !== "" ? (list.sortAsc ? "  ↑" : "  ↓") : "")
            color: list.sortKey === hc.key && hc.key !== "" ? Theme.accent : Theme.textTertiary
            font.pixelSize: Theme.caption
            font.letterSpacing: 0.4
        }
        TapHandler { enabled: hc.key !== ""; onTapped: list.sortBy(hc.key) }
        HoverHandler { enabled: hc.key !== ""; cursorShape: Qt.PointingHandCursor }
    }
    component Grip: Item {
        id: grip
        property string which
        implicitWidth: 8; implicitHeight: 24
        Rectangle { anchors.centerIn: parent; width: 1; height: 14; color: Theme.separator }
        MouseArea {
            anchors.fill: parent
            cursorShape: Qt.SplitHCursor
            property real startX: 0
            property real startW: 0
            onPressed: (m) => { startX = mapToItem(list, m.x, 0).x; startW = grip.which === "artist" ? list.artistW : list.albumW }
            onPositionChanged: (m) => {
                var w = Math.max(80, Math.min(420, startW - (mapToItem(list, m.x, 0).x - startX)))
                if (grip.which === "artist") list.artistW = w; else list.albumW = w
            }
        }
    }
    RowLayout {
        Layout.fillWidth: true
        Layout.leftMargin: Theme.s1 + 18 + Theme.s2
        Layout.rightMargin: Theme.s2 + 5 * 28
        spacing: Theme.s2
        HeadCell { label: "#"; key: ""; w: 28 + (list.showCover ? 30 + Theme.s2 : 0) }
        HeadCell { label: qsTr("TITLE"); key: "title" }
        Grip { which: "artist" }
        HeadCell { label: qsTr("ARTIST"); key: "subtitle"; w: list.artistW - 8 - Theme.s2 }
        Grip { which: "album"; visible: list.showAlbum }
        HeadCell { visible: list.showAlbum; label: qsTr("ALBUM"); key: "album"; w: list.albumW - 8 - Theme.s2 }
        HeadCell { label: ""; key: ""; w: 44 }
        HeadCell { label: qsTr("TIME"); key: "duration"; w: 42 }
    }
    Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: Theme.separator }

    ListView {
        id: view
        Layout.fillWidth: true
        Layout.fillHeight: true
        implicitHeight: contentHeight
        clip: true
        model: list.rows
        boundsBehavior: Flickable.StopAtBounds
        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
        reuseItems: true
        delegate: TidalTrackRow {
            required property var modelData
            required property int index
            width: view.width
            item: modelData.item
            ctl: list.ctl
            number: list.albumNumbers && modelData.item.number > 0 ? modelData.item.number : modelData.pos + 1
            selected: list.picked[modelData.pos] === true
            playingNow: list.playingId !== "" && modelData.item.id === list.playingId
            showAlbum: list.showAlbum
            showCover: list.showCover
            artistW: list.artistW
            albumW: list.albumW
            onToggleSelect: (shift) => list.toggle(modelData.pos, shift)
            onPlay: tidal.playerObject.playItems(list.visibleItems(), index, list.source)
        }
    }
}
