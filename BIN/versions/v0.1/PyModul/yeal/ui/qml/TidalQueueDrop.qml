import QtQuick

// Drop target on a queue list: titles, albums and playlists dragged here (TidalDragSource) go into the queue at the
// place of the line, or at the end. Put it over the list; it takes no mouse clicks itself.
DropArea {
    id: area
    property var list: null              // the ListView of the queue
    property var player: tidal.playerObject   // the player whose queue this is (the player for downloaded files has its own)
    property int row: -1                 // where the titles will go (-1 = end)
    property real lineY: 0
    keys: ["text/plain"]

    function locate(drag) {
        if (!list) { row = -1; return }
        var p = list.mapFromItem(area, drag.x, drag.y)
        var idx = list.indexAt(p.x, p.y + list.contentY)
        if (idx < 0) row = -1
        else {
            var it = list.itemAtIndex(idx)
            row = it && p.y + list.contentY > it.y + it.height / 2 ? idx + 1 : idx
        }
        var target = row >= 0 && row < list.count ? list.itemAtIndex(row) : null
        var inList = target ? target.y - list.contentY : Math.min(list.height - 2, Math.max(0, list.contentHeight - list.contentY))
        lineY = area.mapFromItem(list, 0, inList).y
    }
    onEntered: (drag) => { drag.accepted = tidal.dragPayload.length > 0; if (drag.accepted) locate(drag) }
    onPositionChanged: (drag) => locate(drag)
    onDropped: (drop) => {
        var items = tidal.dragPayload
        if (items.length === 0) return
        drop.accept(Qt.CopyAction)
        area.player.enqueue(items, area.row)
        tidal.setDragPayload([])
        area.row = -1
    }

    Rectangle {                          // the line where the titles will go
        visible: area.containsDrag
        x: 4; width: area.width - 8; height: 2; radius: 1
        y: Math.max(0, Math.min(area.height - 2, area.lineY - 1))
        color: Theme.accent
    }
    Rectangle {                          // frame around the whole queue
        anchors.fill: parent
        visible: area.containsDrag
        color: "transparent"
        radius: 10
        border.width: 1
        border.color: Theme.accent
        opacity: 0.6
    }
}
