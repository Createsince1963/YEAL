import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// Start / Explore / genre pages and search results of the TIDAL DIY view: rows of small tiles that can be
// collapsed, track rows as a compact list, sub pages as chips. "All" opens the full list of a row.
Item {
    id: shelf
    property var ctl                     // TidalHome
    property string route: "home"        // home | explore | page | search
    property string arg: ""
    property string title: ""
    property var collapsed: ({})         // row title -> true
    readonly property int tileSize: ctl ? Math.min(140, ctl.tileSize) : 130

    TidalRequest { id: req; route: shelf.route; arg: shelf.arg }

    function searchRows(d) {
        if (!d) return []
        var rows = []
        if (d.top) rows.push({ title: qsTr("Top result"), kind: d.top.kind, items: [d.top], more: "" })
        var parts = [["tracks", qsTr("Tracks"), "track"], ["artists", qsTr("Artists"), "artist"], ["albums", qsTr("Albums"), "album"],
                     ["playlists", qsTr("Playlists"), "playlist"], ["videos", qsTr("Videos"), "video"]]
        for (var i = 0; i < parts.length; ++i)
            if (d[parts[i][0]] && d[parts[i][0]].length) rows.push({ title: parts[i][1], kind: parts[i][2], items: d[parts[i][0]], more: "" })
        return rows
    }
    readonly property var rows: route === "search" ? searchRows(req.data) : (req.data || [])

    ListView {
        id: view
        anchors.fill: parent
        clip: true
        spacing: Theme.s4
        boundsBehavior: Flickable.StopAtBounds
        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
        model: shelf.rows
        header: Item {
            width: view.width
            height: shelf.title !== "" ? titleText.implicitHeight + Theme.s3 : 0
            Text {
                id: titleText
                visible: shelf.title !== ""
                text: shelf.title
                font.pixelSize: Theme.title
                font.weight: Font.DemiBold
                color: Theme.text
            }
        }
        delegate: ColumnLayout {
            id: rowBox
            required property var modelData
            readonly property bool closed: shelf.collapsed[modelData.title] === true
            width: view.width - Theme.s2
            spacing: Theme.s2
            RowLayout {
                Layout.fillWidth: true
                visible: rowBox.modelData.title !== ""
                Icon { name: "chevronDown"; size: 14; color: Theme.textSecondary; rotation: rowBox.closed ? -90 : 0 }
                Text {
                    text: rowBox.modelData.title
                    font.pixelSize: Theme.headline
                    font.weight: Font.DemiBold
                    color: Theme.text
                    Layout.fillWidth: true
                    TapHandler {
                        onTapped: { var c = Object.assign({}, shelf.collapsed); c[rowBox.modelData.title] = !rowBox.closed; shelf.collapsed = c }
                    }
                }
                AppButton {
                    visible: rowBox.modelData.kind !== "link" && (rowBox.modelData.more !== "" || rowBox.modelData.items.length > 6)
                    text: qsTr("All")
                    kind: "plain"
                    implicitHeight: 28
                    onClicked: shelf.ctl.openList(rowBox.modelData.title, rowBox.modelData.more, rowBox.modelData.items)
                }
            }
            // tracks: compact list
            Column {
                visible: !rowBox.closed && rowBox.modelData.kind === "track"
                Layout.fillWidth: true
                Repeater {
                    model: rowBox.modelData.kind === "track" ? rowBox.modelData.items.slice(0, 8) : []
                    delegate: TidalTrackRow {
                        required property var modelData
                        required property int index
                        width: rowBox.width
                        item: modelData
                        ctl: shelf.ctl
                        number: index + 1
                        selectable: false
                        artistW: 160
                        albumW: 180
                        onPlay: tidal.playerObject.playItems(rowBox.modelData.items, index, rowBox.modelData.title)
                    }
                }
            }
            // sub pages (genres, moods, decades): chips
            Flow {
                visible: !rowBox.closed && rowBox.modelData.kind === "link"
                Layout.fillWidth: true
                spacing: Theme.s2
                Repeater {
                    model: rowBox.modelData.kind === "link" ? rowBox.modelData.items : []
                    delegate: Chip {
                        required property var modelData
                        text: modelData.title
                        onToggled: shelf.ctl.open(modelData)
                    }
                }
            }
            // everything else: a horizontal row of tiles
            ListView {
                id: strip
                visible: !rowBox.closed && rowBox.modelData.kind !== "track" && rowBox.modelData.kind !== "link"
                Layout.fillWidth: true
                implicitHeight: visible ? (contentItem.childrenRect.height || shelf.tileSize + 40) : 0
                orientation: ListView.Horizontal
                spacing: Theme.s3
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                model: visible ? rowBox.modelData.items : []
                delegate: TidalTile {
                    required property var modelData
                    item: modelData
                    ctl: shelf.ctl
                    size: rowBox.modelData.kind === "promo" ? Math.round(shelf.tileSize * 1.2) : shelf.tileSize
                    wide: rowBox.modelData.kind === "promo" || modelData.kind === "video"
                }
                IconButton {
                    visible: strip.contentX > 0
                    anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter
                    iconName: "chevronLeft"
                    onClicked: strip.contentX = Math.max(0, strip.contentX - strip.width * 0.8)
                    background: Rectangle { radius: width / 2; color: Theme.raised; opacity: 0.92 }
                }
                IconButton {
                    visible: strip.contentX + strip.width < strip.contentWidth - 2
                    anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
                    iconName: "chevronRight"
                    onClicked: strip.contentX = Math.min(strip.contentWidth - strip.width, strip.contentX + strip.width * 0.8)
                    background: Rectangle { radius: width / 2; color: Theme.raised; opacity: 0.92 }
                }
            }
        }
    }
    TidalStatus { anchors.centerIn: parent; request: req; empty: shelf.rows.length === 0 }
}
