import QtQuick
import QtQuick.Controls.Basic

// Cover tile of the TIDAL DIY view (album, playlist, mix, artist, video). Click opens, the round button plays,
// right-click opens the item menu of TidalHome.
Item {
    id: tile
    property var item: ({})
    property var ctl                    // TidalHome
    property int size: 140
    property bool wide: item && (item.kind === "video" || item.kind === "promo")
    width: wide ? Math.round(size * 16 / 9) : size
    height: (wide ? Math.round(size * 9 / 16) : size) + caption.implicitHeight + Theme.s2

    Rectangle {
        id: art
        width: tile.width
        height: tile.wide ? Math.round(tile.size * 9 / 16) : tile.size
        radius: tile.item && tile.item.kind === "artist" ? width / 2 : 8
        color: Theme.field
        clip: true
        Image {
            anchors.fill: parent
            source: tile.item && tile.item.cover ? tile.item.cover : ""
            sourceSize.width: 320
            fillMode: Image.PreserveAspectCrop
            asynchronous: true
            cache: true
            visible: status === Image.Ready
        }
        Icon {
            anchors.centerIn: parent
            visible: !tile.item || !tile.item.cover
            name: tile.item && tile.item.kind === "artist" ? "user" : tile.item && tile.item.kind === "link" ? "compass" : "music"
            size: 28
            color: Theme.textTertiary
        }
        Rectangle {     // play button on hover (not for artists / links)
            visible: hover.hovered && tile.item && ["album", "playlist", "mix", "track"].indexOf(tile.item.kind) >= 0
            width: 36; height: 36; radius: 18
            anchors { right: parent.right; bottom: parent.bottom; margins: Theme.s2 }
            color: Theme.accentFill
            Icon { anchors.centerIn: parent; name: "play"; size: 16; filled: true; color: Theme.textOnAccent }
            TapHandler { onTapped: tile.ctl.playItem(tile.item) }
        }
        Badge {
            visible: tile.item && (tile.item.quality === "MAX" || tile.item.quality === "Atmos")
            text: tile.item ? tile.item.quality : ""
            kind: "accent"
            anchors { left: parent.left; top: parent.top; margins: Theme.s1 }
        }
    }
    Column {
        id: caption
        anchors.top: art.bottom
        anchors.topMargin: Theme.s1
        width: tile.width
        Text {
            width: parent.width
            text: tile.item ? tile.item.title || "" : ""
            color: Theme.text
            font.pixelSize: Theme.footnote
            font.weight: Font.Medium
            elide: Text.ElideRight
        }
        Text {
            width: parent.width
            text: tile.item ? (tile.item.subtitle || "") + (tile.item.year ? (tile.item.subtitle ? " · " : "") + tile.item.year : "") : ""
            visible: text !== ""
            color: Theme.textSecondary
            font.pixelSize: Theme.caption
            elide: Text.ElideRight
        }
    }
    HoverHandler { id: hover; cursorShape: Qt.PointingHandCursor }
    TapHandler { onTapped: tile.ctl.open(tile.item) }
    TapHandler { acceptedButtons: Qt.RightButton; onTapped: tile.ctl.itemMenu(tile.item, []) }
    ToolTip.visible: hover.hovered && caption.children[0].truncated
    ToolTip.delay: 800
    ToolTip.text: tile.item ? (tile.item.title || "") : ""
}
