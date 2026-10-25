import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// Yeal's own player for the DOWNLOADED songs, as a small solar system: the oval player is the SUN in the middle, the
// planets on the orbits around it open and fold away: Library (left), Queue (right), Played (below), Settings and Speaker
// (above). An opened planet makes room: the sun and its orbits move over so that nothing is covered. The sun button in
// the corner folds all planets into the sun and brings them back.
Item {
    id: view
    readonly property var player: backend.localPlayerObject
    readonly property color tint: Theme.playerColor(backend.settings.tidal_player_color)
    readonly property bool orbit: backend.settings.local_orbit !== false
    property var opened: ({})                         // planet key -> true
    readonly property real margin: 10
    readonly property real sideW: 260                 // width of the library / queue card
    readonly property real bandH: 250                 // height of the played / settings / speaker card

    function isOpen(key) { return orbit && opened[key] === true }
    function toggle(key) { var o = Object.assign({}, opened); o[key] = !o[key]; opened = o }
    function fold(key) { var o = Object.assign({}, opened); o[key] = false; opened = o }

    // ---- what is left for the sun and its orbits after the opened cards
    readonly property real availX0: margin + (isOpen("library") ? sideW + margin : 0)
    readonly property real availX1: width - margin - (isOpen("queue") ? sideW + margin : 0)
    readonly property real availY0: margin + (isOpen("settings") || isOpen("stream") ? bandH + margin : 0)
    readonly property real availY1: height - margin - (isOpen("played") ? bandH + margin : 0)
    readonly property real availW: Math.max(200, availX1 - availX0)
    readonly property real availH: Math.max(200, availY1 - availY0)
    property real cx: (availX0 + availX1) / 2
    property real cy: (availY0 + availY1) / 2
    Behavior on cx { NumberAnimation { duration: Theme.dur; easing.type: Easing.OutCubic } }
    Behavior on cy { NumberAnimation { duration: Theme.dur; easing.type: Easing.OutCubic } }
    readonly property real sunW: Math.max(260, Math.min(480, availW - (orbit ? 2 * 92 : 2 * 12)))
    readonly property real sunH: sun.implicitHeight
    readonly property real rx: Math.max(sunW / 2 + 30, Math.min(sunW / 2 + 64, availW / 2 - 38))
    readonly property real ry: Math.max(sunH / 2 + 30, Math.min(sunH / 2 + 64, availH / 2 - 38))
    function px(deg) { return cx + rx * Math.cos(deg * Math.PI / 180) }
    function py(deg) { return cy + ry * Math.sin(deg * Math.PI / 180) }

    onCxChanged: space.requestPaint()
    onCyChanged: space.requestPaint()
    onRxChanged: space.requestPaint()
    onRyChanged: space.requestPaint()
    onTintChanged: space.requestPaint()
    onOrbitChanged: space.requestPaint()
    Connections {
        target: view.player
        function onLevelChanged() { space.requestPaint() }
    }

    Rectangle {
        anchors.fill: parent
        radius: Theme.radius
        color: Theme.window
        border.width: 1
        border.color: Theme.separator
    }

    // ---- the sky: the glow of the sun (it breathes with the music) and the orbits
    Canvas {
        id: space
        anchors.fill: parent
        renderTarget: Canvas.Image
        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            var lv = view.player.level
            var r = Math.max(view.sunW, view.sunH) * (0.75 + 0.12 * lv)
            ctx.save()
            ctx.translate(view.cx, view.cy)
            ctx.scale(1, view.sunH / view.sunW * 1.05)
            var g = ctx.createRadialGradient(0, 0, view.sunW * 0.18, 0, 0, r)
            g.addColorStop(0, Qt.alpha(view.tint, 0.22 + 0.30 * lv))
            g.addColorStop(0.55, Qt.alpha(view.tint, 0.07 + 0.08 * lv))
            g.addColorStop(1, Qt.alpha(view.tint, 0))
            ctx.fillStyle = g
            ctx.beginPath()
            ctx.arc(0, 0, r, 0, 2 * Math.PI)
            ctx.fill()
            ctx.restore()
            if (!view.orbit) return
            ctx.lineWidth = 1
            var rings = [[0, 0.30], [26, 0.12]]
            for (var i = 0; i < rings.length; ++i) {
                var extra = rings[i][0]
                ctx.strokeStyle = Qt.alpha(i === 0 ? view.tint : Theme.text, rings[i][1])
                ctx.setLineDash(i === 0 ? [] : [3, 7])
                ctx.beginPath()
                ctx.ellipse(view.cx - view.rx - extra, view.cy - view.ry - extra, 2 * (view.rx + extra), 2 * (view.ry + extra))
                ctx.stroke()
            }
        }
    }

    // ---- the sun
    TidalTrackPlayer {
        id: sun
        x: view.cx - width / 2
        y: view.cy - height / 2
        width: view.sunW
        height: implicitHeight
        player: view.player
        local: true
        compact: true
        z: 2
    }

    // ---- the planets
    Repeater {
        model: view.orbit ? [
            { key: "library", icon: "library", label: qsTr("Library"), deg: 180 },
            { key: "queue", icon: "queueList", label: qsTr("Queue"), deg: 0 },
            { key: "played", icon: "clock", label: qsTr("Played"), deg: 90 },
            { key: "settings", icon: "sliders", label: qsTr("Settings"), deg: 225 },
            { key: "stream", icon: "cast", label: qsTr("Speaker"), deg: 315 }] : []
        delegate: Planet {
            required property var modelData
            icon: modelData.icon
            label: modelData.label
            tint: view.tint
            open: view.isOpen(modelData.key)
            x: view.px(modelData.deg) - width / 2
            y: view.py(modelData.deg) - 26
            z: 3
            onClicked: view.toggle(modelData.key)
        }
    }
    IconButton {            // fold all planets into the sun / bring them back
        anchors.right: parent.right; anchors.bottom: parent.bottom
        anchors.margins: Theme.s2
        iconName: "sun"
        tint: view.orbit ? view.tint : Theme.textSecondary
        tip: view.orbit ? qsTr("Fold the planets into the sun") : qsTr("Show the planets")
        z: 4
        onClicked: backend.setSetting("local_orbit", !view.orbit)
    }

    // ---- the cards
    PlanetCard {                  // library: left
        title: qsTr("LIBRARY")
        tint: view.tint
        open: view.isOpen("library")
        x: view.margin; y: view.margin; width: view.sideW; height: view.height - 2 * view.margin
        z: 5
        onClosed: view.fold("library")
        Loader {
            anchors.fill: parent
            active: parent.parent.parent.open || opacity > 0
            sourceComponent: TidalTrackPanel { local: true; player: view.player; tab: "library"; showTabs: false
                                               color: "transparent"; border.width: 0 }
        }
    }
    PlanetCard {                  // queue: right
        title: qsTr("QUEUE")
        tint: view.tint
        open: view.isOpen("queue")
        x: view.width - view.margin - view.sideW; y: view.margin; width: view.sideW; height: view.height - 2 * view.margin
        z: 5
        onClosed: view.fold("queue")
        Loader {
            anchors.fill: parent
            active: parent.parent.parent.open || opacity > 0
            sourceComponent: TidalTrackPanel { local: true; player: view.player; tab: "queue"; showTabs: false; showSearch: false
                                               color: "transparent"; border.width: 0 }
        }
    }
    PlanetCard {                  // played songs: below
        title: qsTr("PLAYED")
        tint: view.tint
        open: view.isOpen("played")
        x: view.availX0; width: view.availW
        y: view.height - view.margin - view.bandH; height: view.bandH
        z: 5
        onClosed: view.fold("played")
        Loader {
            anchors.fill: parent
            active: parent.parent.parent.open || opacity > 0
            sourceComponent: TidalTrackPanel { local: true; player: view.player; tab: "played"; showTabs: false; showSearch: false
                                               color: "transparent"; border.width: 0 }
        }
    }
    PlanetCard {                  // settings: above
        id: settingsCard
        title: qsTr("SETTINGS")
        tint: view.tint
        open: view.isOpen("settings")
        readonly property bool both: view.isOpen("stream")
        width: both ? (view.availW - view.margin) / 2 : Math.min(460, view.availW)
        x: both ? view.availX0 : view.cx - width / 2
        y: view.margin; height: view.bandH
        z: 5
        onClosed: view.fold("settings")
        Flickable {
            anchors.fill: parent
            contentHeight: settingsCol.implicitHeight
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
            ColumnLayout {
                id: settingsCol
                width: parent.width - Theme.s2
                spacing: Theme.s2
                Text { text: qsTr("Colour"); color: Theme.textSecondary; font.pixelSize: Theme.caption }
                Flow {
                    Layout.fillWidth: true
                    spacing: Theme.s2
                    Repeater {
                        model: Theme.playerColors
                        delegate: Rectangle {
                            required property var modelData
                            readonly property bool picked: String(backend.settings.tidal_player_color) === modelData.name
                            width: 26; height: 26; radius: 13
                            color: modelData.value
                            border.width: picked ? 3 : 0
                            border.color: Theme.text
                            Accessible.role: Accessible.Button; Accessible.name: modelData.name
                            HoverHandler { cursorShape: Qt.PointingHandCursor }
                            TapHandler { onTapped: backend.setSetting("tidal_player_color", modelData.name) }
                        }
                    }
                }
                Text { text: qsTr("Band around the oval"); color: Theme.textSecondary; font.pixelSize: Theme.caption }
                Flow {
                    Layout.fillWidth: true
                    spacing: Theme.s2
                    Chip { text: qsTr("Song"); checked: backend.settings.tidal_player_vis_mode === "song"
                           onToggled: backend.setSetting("tidal_player_vis_mode", "song") }
                    Chip { text: qsTr("Running level"); checked: backend.settings.tidal_player_vis_mode === "flow"
                           onToggled: backend.setSetting("tidal_player_vis_mode", "flow") }
                    Chip { text: qsTr("Off"); checked: backend.settings.tidal_player_vis_mode === "off"
                           onToggled: backend.setSetting("tidal_player_vis_mode", "off") }
                }
                Text { text: qsTr("Playing"); color: Theme.textSecondary; font.pixelSize: Theme.caption }
                Flow {
                    Layout.fillWidth: true
                    spacing: Theme.s2
                    Chip { text: qsTr("Shuffle"); checked: view.player.shuffle; onToggled: view.player.toggleShuffle() }
                    Chip { text: view.player.repeat === "one" ? qsTr("Repeat: single") : view.player.repeat === "all" ? qsTr("Repeat: all") : qsTr("Repeat: off")
                           checked: view.player.repeat !== "off"; onToggled: view.player.cycleRepeat() }
                }
                RowLayout {
                    Layout.fillWidth: true
                    Icon { name: "volume"; size: 16; color: Theme.textSecondary }
                    Slider {
                        Layout.fillWidth: true
                        from: 0; to: 100; stepSize: 1
                        value: view.player.volume
                        onMoved: view.player.setVolume(Math.round(value))
                        Accessible.name: qsTr("Volume")
                    }
                    Text { text: view.player.volume + "%"; color: Theme.textSecondary; font.pixelSize: Theme.caption }
                }
            }
        }
    }
    PlanetCard {                  // speaker: above, right of the settings
        id: streamCard
        title: qsTr("SPEAKER / TV")
        tint: view.tint
        open: view.isOpen("stream")
        readonly property bool both: view.isOpen("settings")
        width: both ? (view.availW - view.margin) / 2 : Math.min(460, view.availW)
        x: both ? view.availX0 + width + view.margin : view.cx - width / 2
        y: view.margin; height: view.bandH
        z: 5
        onClosed: view.fold("stream")
        onOpenChanged: if (open) backend.scanStreamDevices()
        ColumnLayout {
            anchors.fill: parent
            spacing: Theme.s2
            Text {
                Layout.fillWidth: true
                text: view.player.current && view.player.current.title ? qsTr("Song: %1").arg(view.player.current.title) : qsTr("Pick a song in the library first.")
                color: Theme.text; font.pixelSize: Theme.footnote; elide: Text.ElideRight
            }
            Flow {
                Layout.fillWidth: true
                spacing: Theme.s2
                AppButton {
                    text: qsTr("Play on speaker"); kind: "primary"; iconName: "cast"
                    enabled: backend.streamAvailable && !!(view.player.current && view.player.current.file) && !backend.streamBusy
                    onClicked: backend.streamFile(view.player.current.file, view.player.current.title)
                }
                IconButton { iconName: "pause"; tip: qsTr("Pause on the speaker"); enabled: backend.streamPlaying; onClicked: backend.pauseStream() }
                IconButton { iconName: "play"; tip: qsTr("Continue on the speaker"); onClicked: backend.resumeStream() }
                IconButton { iconName: "x"; tip: qsTr("Stop the speaker"); onClicked: backend.stopStream() }
                IconButton { iconName: "retry"; tip: qsTr("Search for speakers again"); onClicked: backend.scanStreamDevices() }
            }
            Text {
                Layout.fillWidth: true
                text: backend.streamStatus
                visible: text !== ""
                color: Theme.textSecondary; font.pixelSize: Theme.caption; elide: Text.ElideRight
            }
            ListView {
                id: devices
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                spacing: 2
                model: backend.streamDevices
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
                delegate: Rectangle {
                    required property var modelData
                    width: devices.width - 6
                    height: 36
                    radius: 8
                    color: modelData.selected ? Qt.alpha(view.tint, 0.18) : devHover.hovered ? Theme.hover : "transparent"
                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: Theme.s2; anchors.rightMargin: Theme.s2
                        spacing: Theme.s2
                        Rectangle { width: 8; height: 8; radius: 4; color: modelData.online ? Theme.success : Theme.textTertiary }
                        Text { text: modelData.name || modelData.host || ""; Layout.fillWidth: true; elide: Text.ElideRight
                               color: Theme.text; font.pixelSize: Theme.footnote; font.weight: modelData.selected ? Font.Bold : Font.Normal }
                        Icon { visible: modelData.selected; name: "check"; size: 14; color: view.tint }
                    }
                    HoverHandler { id: devHover; cursorShape: Qt.PointingHandCursor }
                    TapHandler { onTapped: backend.selectStreamDevice(modelData.id) }
                }
                Text {
                    anchors.centerIn: parent
                    visible: devices.count === 0
                    text: backend.streamScanning ? qsTr("Searching ...") : qsTr("No speaker found yet.")
                    color: Theme.textTertiary; font.pixelSize: Theme.caption
                }
            }
        }
    }
}
