import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// Grid (or list) of albums, playlists, mixes, artists or videos in the TIDAL DIY view. Tile size is a slider and
// is remembered (tidal_tile_size). Data comes either from a route (e.g. "more" / "favorites") or from `items`.
Item {
    id: grid
    property var ctl
    property string title: ""
    property string route: ""
    property string arg: ""
    property var items: []
    property bool listMode: false
    property string filter: ""
    TidalRequest { id: req; route: grid.route; arg: grid.arg }

    readonly property var all: route !== "" ? (req.data || []) : (items || [])
    readonly property var shown: {
        var f = filter.toLowerCase()
        return f === "" ? all : all.filter(function (it) { return ((it.title || "") + " " + (it.subtitle || "")).toLowerCase().indexOf(f) >= 0 })
    }
    readonly property bool onlyTracks: all.length > 0 && all.every(function (it) { return it.kind === "track" })

    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.s2
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.s2
            Text {
                visible: grid.title !== ""
                text: grid.title
                font.pixelSize: Theme.title
                font.weight: Font.DemiBold
                color: Theme.text
                elide: Text.ElideRight
                Layout.fillWidth: true
            }
            Item { visible: grid.title === ""; Layout.fillWidth: true }
            AppField {
                visible: !grid.onlyTracks
                placeholderText: qsTr("Filter")
                implicitHeight: 32
                Layout.preferredWidth: 180
                onTextChanged: grid.filter = text
            }
            Slider {
                visible: !grid.listMode && !grid.onlyTracks
                from: 90; to: 260; stepSize: 10
                value: grid.ctl ? grid.ctl.tileSize : 140
                Layout.preferredWidth: 110
                onMoved: grid.ctl.setTileSize(value)
                ToolTip.visible: hovered
                ToolTip.text: qsTr("Tile size")
            }
            IconButton {
                visible: !grid.onlyTracks
                iconName: grid.listMode ? "grid" : "queue"
                tip: grid.listMode ? qsTr("Show as tiles") : qsTr("Show as list")
                onClicked: grid.listMode = !grid.listMode
            }
        }
        TidalTrackList {           // a list of tracks is always a track table
            visible: grid.onlyTracks
            Layout.fillWidth: true
            Layout.fillHeight: true
            items: grid.onlyTracks ? grid.all : []
            ctl: grid.ctl
            source: grid.title
        }
        GridView {
            id: gv
            visible: !grid.onlyTracks && !grid.listMode
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            readonly property int size: grid.ctl ? grid.ctl.tileSize : 140
            readonly property bool wideTiles: grid.shown.length > 0 && grid.shown[0].kind === "video"
            cellWidth: (wideTiles ? Math.round(size * 16 / 9) : size) + Theme.s3
            cellHeight: (wideTiles ? Math.round(size * 9 / 16) : size) + 52
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
            model: visible ? grid.shown : []
            delegate: TidalTile {
                required property var modelData
                item: modelData
                ctl: grid.ctl
                size: gv.size
            }
        }
        ListView {
            id: lv
            visible: !grid.onlyTracks && grid.listMode
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
            model: visible ? grid.shown : []
            delegate: Rectangle {
                id: li
                required property var modelData
                width: lv.width - Theme.s2
                implicitHeight: 50
                radius: 8
                color: liHover.hovered ? Theme.hover : "transparent"
                RowLayout {
                    anchors.fill: parent
                    anchors.margins: Theme.s1
                    spacing: Theme.s3
                    Rectangle {
                        implicitWidth: 42; implicitHeight: 42
                        radius: li.modelData.kind === "artist" ? 21 : 6
                        color: Theme.field
                        clip: true
                        Image { anchors.fill: parent; source: li.modelData.cover || ""; sourceSize.width: 100; fillMode: Image.PreserveAspectCrop; asynchronous: true }
                    }
                    ColumnLayout {
                        spacing: 0
                        Layout.fillWidth: true
                        Text { text: li.modelData.title || ""; color: Theme.text; font.pixelSize: Theme.footnote; font.weight: Font.Medium; elide: Text.ElideRight; Layout.fillWidth: true }
                        Text { text: li.modelData.subtitle || ""; visible: text !== ""; color: Theme.textSecondary; font.pixelSize: Theme.caption; elide: Text.ElideRight; Layout.fillWidth: true }
                    }
                    Text { text: li.modelData.year || (li.modelData.tracks ? qsTr("%1 titles").arg(li.modelData.tracks) : ""); color: Theme.textTertiary; font.pixelSize: Theme.caption }
                    Badge { visible: li.modelData.quality === "MAX"; text: "MAX"; kind: "accent" }
                }
                HoverHandler { id: liHover; cursorShape: Qt.PointingHandCursor }
                TapHandler { onTapped: grid.ctl.open(li.modelData) }
                TapHandler { acceptedButtons: Qt.RightButton; onTapped: grid.ctl.itemMenu(li.modelData, []) }
            }
        }
    }
    TidalStatus { anchors.centerIn: parent; request: grid.route !== "" ? req : null; empty: grid.all.length === 0 }
}
