import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// Right-hand area of the TIDAL DIY view: search field, then the queue ("Played from", now playing, up next) or
// the lyrics. Up-next titles are tiles that can be dragged to change the playing order.
Item {
    id: area
    property var ctl
    property string view: "queue"        // queue | lyrics
    readonly property var player: tidal.playerObject

    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.s2
        AppField {
            id: search
            Layout.fillWidth: true
            implicitHeight: 34
            placeholderText: qsTr("Search TIDAL")
            onAccepted: if (text.trim() !== "") area.ctl.search(text.trim())
            Icon { anchors.right: parent.right; anchors.rightMargin: Theme.s2; anchors.verticalCenter: parent.verticalCenter; name: "search"; size: 16; color: Theme.textTertiary }
        }
        Segmented {
            Layout.fillWidth: true
            current: area.view
            options: [{ text: qsTr("Queue"), value: "queue" }, { text: qsTr("Lyrics"), value: "lyrics" }]
            onActivated: (v) => area.view = v
        }

        // ---- queue
        ColumnLayout {
            visible: area.view === "queue"
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: Theme.s2
            RowLayout {
                Layout.fillWidth: true
                Text {
                    text: area.player.source !== "" ? qsTr("Played from: %1").arg(area.player.source) : qsTr("Queue")
                    color: Theme.textSecondary; font.pixelSize: Theme.caption; elide: Text.ElideRight; Layout.fillWidth: true
                }
                IconButton { implicitWidth: 28; implicitHeight: 28; iconName: "listAdd"; tip: qsTr("Save the queue as a playlist…")
                             enabled: q.count > 0
                             onClicked: area.ctl.askName(qsTr("Save queue as playlist"), area.player.source, function (t) { tidal.saveQueueAsPlaylist(t) }) }
                IconButton { implicitWidth: 28; implicitHeight: 28; iconName: "trash"; tip: qsTr("Clear up next"); onClicked: area.player.clearUpcoming() }
            }
            ListView {
                id: q
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                spacing: 2
                model: area.player.queueModel
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
                moveDisplaced: Transition { NumberAnimation { properties: "y"; duration: Theme.durFast } }
                delegate: Item {
                    id: slot
                    required property int index
                    required property string itemId
                    required property string title
                    required property string subtitle
                    required property string cover
                    required property int duration
                    required property bool isCurrent
                    width: q.width - 4
                    height: 50
                    DropArea {
                        anchors.fill: parent
                        onEntered: (drag) => { if (drag.source && drag.source.row !== slot.index) area.player.move(drag.source.row, slot.index) }
                    }
                    Rectangle {
                        id: card
                        property int row: slot.index
                        width: slot.width
                        height: slot.height
                        radius: 8
                        color: slot.isCurrent ? Theme.accentSoft : grab.drag.active ? Theme.raised : cardHover.hovered ? Theme.hover : "transparent"
                        border.width: grab.drag.active ? 1 : 0
                        border.color: Theme.accent
                        Drag.active: grab.drag.active
                        Drag.source: card
                        Drag.hotSpot.y: height / 2
                        states: State {
                            when: grab.drag.active
                            ParentChange { target: card; parent: q }
                            PropertyChanges { target: card; z: 10; opacity: 0.92 }
                        }
                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 3
                            spacing: Theme.s2
                            Icon { name: "more"; size: 14; color: Theme.textTertiary; rotation: 90; opacity: cardHover.hovered ? 1 : 0.35 }
                            Rectangle {
                                implicitWidth: 42; implicitHeight: 42; radius: 5
                                color: Theme.field
                                clip: true
                                Image { anchors.fill: parent; source: slot.cover; sourceSize.width: 96; fillMode: Image.PreserveAspectCrop; asynchronous: true }
                            }
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 0
                                Text { text: slot.title; color: slot.isCurrent ? Theme.accent : Theme.text; font.pixelSize: Theme.footnote; font.weight: Font.Medium; elide: Text.ElideRight; Layout.fillWidth: true }
                                Text { text: slot.subtitle; color: Theme.textSecondary; font.pixelSize: Theme.caption; elide: Text.ElideRight; Layout.fillWidth: true }
                            }
                            IconButton { implicitWidth: 26; implicitHeight: 26; iconName: "x"; tip: qsTr("Remove"); visible: cardHover.hovered
                                         onClicked: area.player.removeAt(slot.index) }
                        }
                        HoverHandler { id: cardHover }
                        MouseArea {      // drag to change the order; click plays
                            id: grab
                            anchors.fill: parent
                            anchors.rightMargin: cardHover.hovered ? 30 : 0
                            drag.target: card
                            drag.axis: Drag.YAxis
                            cursorShape: drag.active ? Qt.ClosedHandCursor : Qt.OpenHandCursor
                            onReleased: { card.Drag.drop(); card.x = 0; card.y = 0 }
                            onDoubleClicked: area.player.playIndex(slot.index)
                        }
                    }
                }
                Text {
                    anchors.centerIn: parent
                    visible: q.count === 0
                    width: q.width - 2 * Theme.s4
                    text: qsTr("Nothing queued. Play an album or a playlist, or use \"Play next\" on a title.")
                    color: Theme.textTertiary; font.pixelSize: Theme.caption
                    wrapMode: Text.Wrap; horizontalAlignment: Text.AlignHCenter
                }
            }
        }

        // ---- lyrics (timed lines follow the music)
        ListView {
            id: ly
            visible: area.view === "lyrics"
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            readonly property var synced: area.player.lyrics && area.player.lyrics.synced ? area.player.lyrics.synced : []
            readonly property int line: {
                var pos = area.player.position, n = -1
                for (var i = 0; i < synced.length; ++i) { if (synced[i][0] <= pos) n = i; else break }
                return n
            }
            onLineChanged: if (line >= 0 && visible) positionViewAtIndex(line, ListView.Center)
            model: synced.length ? synced : (area.player.lyrics && area.player.lyrics.text ? area.player.lyrics.text.split("\n") : [])
            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
            delegate: Text {
                required property var modelData
                required property int index
                width: ly.width - Theme.s2
                text: ly.synced.length ? modelData[1] : modelData
                color: ly.synced.length && index === ly.line ? Theme.accent : (ly.synced.length && index < ly.line ? Theme.textTertiary : Theme.text)
                font.pixelSize: ly.synced.length && index === ly.line ? Theme.body : Theme.footnote
                font.weight: ly.synced.length && index === ly.line ? Font.DemiBold : Font.Normal
                wrapMode: Text.Wrap
                topPadding: 3; bottomPadding: 3
                TapHandler { enabled: ly.synced.length > 0; onTapped: area.player.seek(ly.synced[index][0]) }
            }
            Text {
                anchors.centerIn: parent
                visible: ly.count === 0
                text: area.player.currentIndex < 0 ? qsTr("Lyrics appear here while a title plays.") : qsTr("No lyrics for this title.")
                color: Theme.textTertiary; font.pixelSize: Theme.caption
            }
        }
    }
}
