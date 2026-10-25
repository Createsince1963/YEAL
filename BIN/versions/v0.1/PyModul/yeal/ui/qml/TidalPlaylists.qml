import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// Narrow playlist column of the TIDAL DIY view ("All playlists": own and favorited). Filter on top, new playlist,
// right-click for the playlist menu, Ctrl/Shift-click to pick several (e.g. to save them as HTML link lists).
Item {
    id: col
    property var ctl
    property string filter: ""
    property var picked: ({})
    property int pickedCount: 0
    readonly property var shown: {
        var f = filter.toLowerCase()
        return tidal.playlists.filter(function (p) { return f === "" || (p.title || "").toLowerCase().indexOf(f) >= 0 })
    }
    function togglePick(p) {
        var m = Object.assign({}, picked)
        m[p.id] = !m[p.id]
        var n = 0
        for (var k in m) if (m[k]) n++
        picked = m
        pickedCount = n
    }
    function pickedItems() { return tidal.playlists.filter(function (p) { return col.picked[p.id] === true }) }

    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.s2
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.s1
            Text { text: qsTr("All playlists"); color: Theme.textSecondary; font.pixelSize: Theme.caption; font.letterSpacing: 0.4; Layout.fillWidth: true }
            IconButton { implicitWidth: 28; implicitHeight: 28; iconName: "plus"; tip: qsTr("New playlist")
                         onClicked: col.ctl.askName(qsTr("New playlist"), "", function (t) { tidal.createPlaylist(t, []) }) }
            IconButton { implicitWidth: 28; implicitHeight: 28; iconName: "retry"; tip: qsTr("Reload"); onClicked: tidal.refreshLibrary() }
        }
        AppField {
            Layout.fillWidth: true
            implicitHeight: 30
            placeholderText: qsTr("Filter playlists")
            font.pixelSize: Theme.footnote
            onTextChanged: col.filter = text
        }
        RowLayout {     // several picked: actions for all of them
            visible: col.pickedCount > 0
            Layout.fillWidth: true
            Text { text: qsTr("%1 picked").arg(col.pickedCount); color: Theme.accent; font.pixelSize: Theme.caption; Layout.fillWidth: true }
            IconButton { implicitWidth: 28; implicitHeight: 28; iconName: "doc"; tip: qsTr("Save the picked playlists as HTML link lists")
                         onClicked: { tidal.saveLinklists(col.pickedItems()); col.picked = ({}); col.pickedCount = 0 } }
            IconButton { implicitWidth: 28; implicitHeight: 28; iconName: "download"; tip: qsTr("Download the picked playlists")
                         onClicked: { col.ctl.download(col.pickedItems()); col.picked = ({}); col.pickedCount = 0 } }
            IconButton { implicitWidth: 28; implicitHeight: 28; iconName: "x"; tip: qsTr("Clear"); onClicked: { col.picked = ({}); col.pickedCount = 0 } }
        }
        ListView {
            id: view
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
            model: col.shown
            delegate: Rectangle {
                id: pl
                required property var modelData
                width: view.width - 4
                implicitHeight: 44
                radius: 6
                readonly property bool open: col.ctl && col.ctl.currentId === modelData.id
                color: col.picked[modelData.id] ? Theme.accentSoft : open ? Theme.pressed : plHover.hovered ? Theme.hover : "transparent"
                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 3
                    spacing: Theme.s2
                    Rectangle {
                        implicitWidth: 38; implicitHeight: 38; radius: 5
                        color: Theme.field
                        clip: true
                        Image { anchors.fill: parent; source: pl.modelData.cover || ""; sourceSize.width: 96; fillMode: Image.PreserveAspectCrop; asynchronous: true }
                    }
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 0
                        Text { text: pl.modelData.title || ""; color: pl.open ? Theme.accent : Theme.text; font.pixelSize: Theme.footnote; font.weight: Font.Medium; elide: Text.ElideRight; Layout.fillWidth: true }
                        Text {
                            text: (pl.modelData.mine ? qsTr("%1 titles").arg(pl.modelData.tracks) : (pl.modelData.subtitle || ""))
                            color: Theme.textSecondary; font.pixelSize: Theme.caption; elide: Text.ElideRight; Layout.fillWidth: true
                        }
                    }
                }
                HoverHandler { id: plHover; cursorShape: Qt.PointingHandCursor }
                TapHandler {
                    onTapped: (ev) => { if (ev.modifiers & (Qt.ControlModifier | Qt.ShiftModifier)) col.togglePick(pl.modelData); else col.ctl.open(pl.modelData) }
                }
                TapHandler { acceptedButtons: Qt.RightButton; onTapped: col.ctl.itemMenu(pl.modelData, []) }
                ToolTip.visible: plHover.hovered && width < 200
                ToolTip.delay: 700
                ToolTip.text: pl.modelData.title || ""
            }
        }
        Text {
            visible: tidal.playlists.length === 0
            text: qsTr("No playlists yet.")
            color: Theme.textTertiary
            font.pixelSize: Theme.caption
        }
    }
}
