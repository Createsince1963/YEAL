import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// One dense row of a TIDAL DIY track table: tick box, number, cover + title, artist, album, quality, length and
// actions on hover (play, favorite, add to playlist, add to queue, download). Double-click plays.
Rectangle {
    id: row
    property var item: ({})
    property var ctl                     // TidalHome
    property int number: 0
    property bool selected: false
    property bool playingNow: false
    property bool showAlbum: true
    property bool showCover: true
    property bool selectable: true
    property real artistW: 180
    property real albumW: 200
    signal toggleSelect(bool shift)
    signal play()

    implicitHeight: 38
    radius: 6
    color: selected ? Theme.accentSoft : hover.hovered ? Theme.hover : "transparent"
    readonly property bool fav: favTick >= 0 && !!row.ctl && tidal.isFavorite("track", row.item.id || "")
    property int favTick: 0
    Connections { target: tidal; function onFavoritesChanged() { row.favTick++ } }
    TidalDragSource { item: row.item }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.s1
        anchors.rightMargin: Theme.s2
        spacing: Theme.s2
        Rectangle {     // tick box
            visible: row.selectable
            implicitWidth: 18; implicitHeight: 18; radius: 4
            color: row.selected ? Theme.accentFill : "transparent"
            border.width: row.selected ? 0 : 1.5
            border.color: Theme.textTertiary
            Icon { anchors.centerIn: parent; visible: row.selected; name: "check"; size: 13; strokeWidth: 2.4; color: Theme.textOnAccent }
            TapHandler { onTapped: (ev) => row.toggleSelect(ev.modifiers & Qt.ShiftModifier) }
        }
        Item {
            implicitWidth: 28; implicitHeight: 20
            Text {
                anchors.fill: parent
                visible: !hover.hovered && !row.playingNow
                text: row.number > 0 ? row.number : ""
                color: Theme.textTertiary
                font.pixelSize: Theme.footnote
                horizontalAlignment: Text.AlignRight
                verticalAlignment: Text.AlignVCenter
            }
            Icon {
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                visible: hover.hovered || row.playingNow
                name: row.playingNow && !hover.hovered ? "volume" : "play"
                filled: !row.playingNow || hover.hovered
                size: 15
                color: row.playingNow ? Theme.accent : Theme.text
                TapHandler { onTapped: row.play() }
            }
        }
        Rectangle {
            visible: row.showCover
            implicitWidth: 30; implicitHeight: 30; radius: 4
            color: Theme.field
            clip: true
            Image {
                anchors.fill: parent
                source: row.showCover && row.item.cover ? row.item.cover : ""
                sourceSize.width: 80
                fillMode: Image.PreserveAspectCrop
                asynchronous: true
            }
        }
        RowLayout {     // title + explicit
            Layout.fillWidth: true
            Layout.minimumWidth: 80
            spacing: Theme.s1
            Text {
                text: row.item.title || ""
                color: row.playingNow ? Theme.accent : (row.item.streamable === false ? Theme.textTertiary : Theme.text)
                font.pixelSize: Theme.footnote
                font.weight: Font.Medium
                elide: Text.ElideRight
                Layout.fillWidth: true
                Layout.maximumWidth: implicitWidth
            }
            Rectangle {
                visible: !!row.item.explicit
                implicitWidth: 14; implicitHeight: 14; radius: 3
                color: Theme.textTertiary
                Text { anchors.centerIn: parent; text: "E"; font.pixelSize: 9; font.bold: true; color: Theme.surface }
            }
            Item { Layout.fillWidth: true }
        }
        Text {          // artist (click opens the artist)
            Layout.preferredWidth: row.artistW
            text: row.item.subtitle || ""
            color: artistHover.hovered ? Theme.accent : Theme.textSecondary
            font.pixelSize: Theme.footnote
            elide: Text.ElideRight
            HoverHandler { id: artistHover; enabled: !!row.item.artistId; cursorShape: Qt.PointingHandCursor }
            TapHandler { enabled: !!row.item.artistId; onTapped: row.ctl.open({ kind: "artist", id: row.item.artistId, title: row.item.subtitle }) }
        }
        Text {          // album (click opens the album)
            visible: row.showAlbum
            Layout.preferredWidth: row.albumW
            text: row.item.album || ""
            color: albumHover.hovered ? Theme.accent : Theme.textSecondary
            font.pixelSize: Theme.footnote
            elide: Text.ElideRight
            HoverHandler { id: albumHover; enabled: !!row.item.albumId; cursorShape: Qt.PointingHandCursor }
            TapHandler { enabled: !!row.item.albumId; onTapped: row.ctl.open({ kind: "album", id: row.item.albumId, title: row.item.album }) }
        }
        Item {
            implicitWidth: 44; implicitHeight: 20
            Badge {
                anchors.centerIn: parent
                visible: (row.item.quality || "") !== ""
                text: row.item.quality || ""
                kind: row.item.quality === "MAX" || row.item.quality === "Atmos" ? "accent" : "neutral"
            }
        }
        Text {
            Layout.preferredWidth: 42
            text: row.ctl ? row.ctl.fmt(row.item.duration) : ""
            color: Theme.textSecondary
            font.pixelSize: Theme.footnote
            font.features: { "tnum": 1 }
            horizontalAlignment: Text.AlignRight
        }
        Row {           // actions (always room reserved, shown on hover)
            spacing: 0
            opacity: hover.hovered || row.fav ? 1 : 0
            IconButton { implicitWidth: 28; implicitHeight: 28; iconName: "heart"; tip: row.fav ? qsTr("Remove from collection") : qsTr("Add to collection")
                         tint: row.fav ? Theme.accent : Theme.textSecondary
                         onClicked: tidal.toggleFavorite("track", row.item.id) }
            IconButton { implicitWidth: 28; implicitHeight: 28; iconName: "listAdd"; tip: qsTr("Add to playlist…"); visible: hover.hovered
                         onClicked: row.ctl.addToPlaylist([row.item.id]) }
            IconButton { implicitWidth: 28; implicitHeight: 28; iconName: "queue"; tip: qsTr("Play next"); visible: hover.hovered
                         onClicked: tidal.playerObject.queueNext([row.item]) }
            IconButton { implicitWidth: 28; implicitHeight: 28; iconName: "download"; tip: qsTr("Download"); visible: hover.hovered
                         onClicked: row.ctl.download([row.item]) }
            IconButton { implicitWidth: 28; implicitHeight: 28; iconName: "more"; tip: qsTr("More"); visible: hover.hovered
                         onClicked: row.ctl.itemMenu(row.item, []) }
        }
    }
    HoverHandler { id: hover }
    TapHandler { acceptedButtons: Qt.RightButton; onTapped: row.ctl.itemMenu(row.item, []) }
    TapHandler {
        onTapped: (ev) => { if (row.selectable && (ev.modifiers & (Qt.ShiftModifier | Qt.ControlModifier))) row.toggleSelect(ev.modifiers & Qt.ShiftModifier) }
        onDoubleTapped: row.play()
    }
}
