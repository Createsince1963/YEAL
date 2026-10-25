import QtQuick

// Makes the parent item draggable as a TIDAL link (single title, album, playlist, mix ...). Dropped on the
// workflow panel (WorkflowPanel.qml, DropArea) it is downloaded. Put it as the FIRST child of the parent so the
// parent's buttons stay on top and keep working; a click without moving never starts a drag.
Item {
    id: src
    property var item: ({})
    property var urls: []                // several links at once (e.g. a selection); default: the item's own link
    readonly property string payload: urls.length > 0 ? urls.join("\n") : (item && item.url ? item.url : "")
    anchors.fill: parent

    Drag.dragType: Drag.Automatic
    Drag.supportedActions: Qt.CopyAction
    Drag.mimeData: ({ "text/plain": src.payload })
    Drag.active: dh.active && src.payload !== ""

    DragHandler {
        id: dh
        target: null
        enabled: src.payload !== ""
        cursorShape: Qt.PointingHandCursor
    }
}
