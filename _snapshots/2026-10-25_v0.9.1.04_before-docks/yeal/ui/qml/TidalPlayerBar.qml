import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// Player bar of the TIDAL DIY view. Left: cover, title, artist, "played from", favorite; right next to it the
// queue button, volume and the quality badge (as in Tidal, but moved to the left); then the transport buttons and
// the progress bar, which take the remaining width.
Rectangle {
    id: bar
    property var ctl
    readonly property var player: tidal.playerObject
    readonly property var cur: player.current || ({})
    signal toggleQueue()
    implicitHeight: 72
    radius: Theme.radius
    color: Theme.surface
    border.width: 1
    border.color: Theme.separator
    property int favTick: 0
    Connections { target: tidal; function onFavoritesChanged() { bar.favTick++ } }
    readonly property bool fav: favTick >= 0 && !!bar.cur.id && tidal.isFavorite("track", bar.cur.id)

    function mmss(ms) {
        var s = Math.max(0, Math.floor(ms / 1000))
        return Math.floor(s / 60) + ":" + ("0" + (s % 60)).slice(-2)
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.s2
        anchors.rightMargin: Theme.s3
        spacing: Theme.s3

        // ---- now playing
        Rectangle {
            implicitWidth: 52; implicitHeight: 52; radius: 6
            color: Theme.field
            clip: true
            Image { anchors.fill: parent; source: bar.cur.cover || ""; sourceSize.width: 120; fillMode: Image.PreserveAspectCrop; asynchronous: true }
            Icon { anchors.centerIn: parent; visible: !bar.cur.cover; name: "music"; size: 20; color: Theme.textTertiary }
            TapHandler { enabled: !!bar.cur.albumId; onTapped: bar.ctl.open({ kind: "album", id: bar.cur.albumId, title: bar.cur.album }) }
        }
        ColumnLayout {
            Layout.preferredWidth: 200
            Layout.maximumWidth: 260
            spacing: 0
            Text { text: bar.cur.title || qsTr("Nothing playing"); color: Theme.text; font.pixelSize: Theme.footnote; font.weight: Font.Medium; elide: Text.ElideRight; Layout.fillWidth: true }
            Text {
                text: bar.cur.subtitle || ""
                color: artistHover.hovered ? Theme.accent : Theme.textSecondary
                font.pixelSize: Theme.caption; elide: Text.ElideRight; Layout.fillWidth: true
                HoverHandler { id: artistHover; enabled: !!bar.cur.artistId; cursorShape: Qt.PointingHandCursor }
                TapHandler { enabled: !!bar.cur.artistId; onTapped: bar.ctl.open({ kind: "artist", id: bar.cur.artistId, title: bar.cur.subtitle }) }
            }
            Text { visible: bar.player.source !== ""; text: "♫ " + bar.player.source; color: Theme.textTertiary; font.pixelSize: Theme.caption; elide: Text.ElideRight; Layout.fillWidth: true }
        }
        IconButton { iconName: "heart"; enabled: !!bar.cur.id; tint: bar.fav ? Theme.accent : Theme.textSecondary
                     tip: bar.fav ? qsTr("Remove from collection") : qsTr("Add to collection")
                     onClicked: tidal.toggleFavorite("track", bar.cur.id) }

        // ---- queue, volume, quality (moved to the left, next to the title)
        Rectangle { implicitWidth: 1; implicitHeight: 36; color: Theme.separator }
        IconButton { iconName: "queue"; tip: qsTr("Show / hide the queue"); onClicked: bar.toggleQueue() }
        IconButton {
            iconName: bar.player.volume === 0 ? "mute" : "volume"
            tip: qsTr("Mute")
            property int before: 80
            onClicked: { if (bar.player.volume > 0) { before = bar.player.volume; bar.player.setVolume(0) } else bar.player.setVolume(before || 80) }
        }
        Slider {
            from: 0; to: 100; stepSize: 1
            value: bar.player.volume
            Layout.preferredWidth: 90
            onMoved: bar.player.setVolume(value)
            ToolTip.visible: hovered || pressed
            ToolTip.text: Math.round(value) + " %"
        }
        Rectangle {     // quality badge as in Tidal: what is playing right now
            visible: bar.player.badge !== ""
            implicitWidth: badgeText.implicitWidth + 2 * Theme.s3
            implicitHeight: 26
            radius: 13
            color: Theme.accentSoft
            border.width: 1
            border.color: Theme.accent
            Text { id: badgeText; anchors.centerIn: parent; text: bar.player.badge; color: Theme.accent; font.pixelSize: Theme.caption; font.weight: Font.DemiBold }
            HoverHandler { id: badgeHover }
            ToolTip.visible: badgeHover.hovered
            ToolTip.text: bar.player.badgeTip
        }
        Rectangle { implicitWidth: 1; implicitHeight: 36; color: Theme.separator }

        // ---- transport + progress (remaining width)
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 0
            RowLayout {
                Layout.alignment: Qt.AlignHCenter
                spacing: Theme.s1
                IconButton { iconName: "shuffle"; tint: bar.player.shuffle ? Theme.accent : Theme.textSecondary
                             tip: bar.player.shuffle ? qsTr("Shuffle on") : qsTr("Shuffle off"); onClicked: bar.player.toggleShuffle() }
                IconButton { iconName: "skipPrev"; tip: qsTr("Previous"); onClicked: bar.player.previous() }
                Rectangle {
                    implicitWidth: 40; implicitHeight: 40; radius: 20
                    color: playHover.hovered ? Theme.accent : Theme.accentFill
                    BusyIndicator { anchors.fill: parent; running: bar.player.loading; visible: running }
                    Icon { anchors.centerIn: parent; visible: !bar.player.loading; name: bar.player.playing ? "pause" : "play"
                           filled: !bar.player.playing; strokeWidth: bar.player.playing ? 2.6 : 1.75; size: 18; color: Theme.textOnAccent }
                    HoverHandler { id: playHover; cursorShape: Qt.PointingHandCursor }
                    TapHandler { onTapped: bar.player.toggle() }
                    Accessible.role: Accessible.Button
                    Accessible.name: bar.player.playing ? qsTr("Pause") : qsTr("Play")
                }
                IconButton { iconName: "skipNext"; tip: qsTr("Next"); onClicked: bar.player.next() }
                IconButton { iconName: bar.player.repeat === "one" ? "repeatOne" : "repeat"
                             tint: bar.player.repeat !== "off" ? Theme.accent : Theme.textSecondary
                             tip: bar.player.repeat === "off" ? qsTr("Repeat off") : bar.player.repeat === "all" ? qsTr("Repeat all") : qsTr("Repeat one")
                             onClicked: bar.player.cycleRepeat() }
            }
            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.s2
                Text { text: bar.mmss(seek.pressed ? seek.value : bar.player.position); color: Theme.textSecondary; font.pixelSize: Theme.caption; font.features: { "tnum": 1 } }
                Slider {
                    id: seek
                    Layout.fillWidth: true
                    from: 0
                    to: Math.max(1, bar.player.duration)
                    enabled: bar.player.currentIndex >= 0
                    onPressedChanged: if (!pressed) bar.player.seek(value)
                    Binding on value { value: bar.player.position; when: !seek.pressed }
                }
                Text { text: bar.mmss(bar.player.duration); color: Theme.textSecondary; font.pixelSize: Theme.caption; font.features: { "tnum": 1 } }
            }
        }
    }
}
