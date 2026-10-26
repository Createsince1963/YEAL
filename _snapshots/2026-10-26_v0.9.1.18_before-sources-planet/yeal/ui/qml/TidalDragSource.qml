import QtQuick

// Makes the parent item draggable (single title, album, playlist, mix ... or a whole selection). Two kinds of targets:
//  - the workflow panel (WorkflowPanel.qml, DropArea): the links are downloaded;
//  - the queue (TidalQueueDrop.qml): the titles are queued, albums and playlists with all their titles.
// The link text travels in the drag itself; the real items (cover, title ...) are handed over through tidal.dragPayload.
// Put it as the FIRST child of the parent so the parent's buttons stay on top and keep working; a click without moving
// never starts a drag.
Item {
    id: src
    property var item: ({})
    property var provider: null          // function returning the items to carry (e.g. the selection); asked when the mouse goes down
    property var carried: item && item.kind ? [item] : []
    readonly property string payload: carried.map(function (i) { return i.url || "" })
                                             .filter(function (u) { return u !== "" }).join("\n")
    anchors.fill: parent

    function refresh() {
        var list = provider ? provider() : (item && item.kind ? [item] : [])
        carried = list || []
    }

    Drag.dragType: Drag.Automatic
    Drag.supportedActions: Qt.CopyAction
    Drag.mimeData: ({ "text/plain": src.payload })
    Drag.active: dh.active && src.payload !== ""
    Drag.onActiveChanged: if (Drag.active) { tidal.setDragPayload(src.carried); clearLater.restart() }

    DragHandler {
        id: dh
        target: null
        enabled: src.payload !== "" || src.provider !== null
        cursorShape: Qt.PointingHandCursor
    }
    TapHandler {                          // the mouse button goes down: the selection may have changed since the last drag
        onPressedChanged: if (pressed) src.refresh()
    }
    Timer { id: clearLater; interval: 120000; onTriggered: tidal.setDragPayload([]) }     // safety net; targets clear it at once
}
