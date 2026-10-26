import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// Track player of TIDAL DIY (0.9.1): the player as a running track. The oval is the song: the dot is the playhead and
// runs once around while the song plays (click or drag on the loop to jump). The green band around the inner oval is
// the level of the music - the louder the music, the thicker the band. VOL turns the band yellow and shows the volume
// as a big number; the mouse wheel over the oval changes it, too. The text row below holds repeat, shuffle, like,
// the playlist panel (queue, playlists, search, lyrics), VIS (level band on / off) and VOL.
Item {
    id: root
    property var ctl                                  // TidalHome
    property var player: tidal.playerObject          // the TIDAL DIY player, or the player for downloaded files
    property bool local: false                        // downloaded files: no like, lyrics or TIDAL pages; STREAM plays on a speaker
    property int panelHeight: 300
    readonly property var cur: player.current || ({})
    readonly property bool playerTop: ctl ? ctl.playerTop : false
    property bool panelOpen: false
    property string panelTab: "queue"
    signal toggleQueue()

    // ---- geometry: everything is drawn in units of the oval height
    readonly property real ovalW: Math.max(260, Math.min(width - Theme.s4, compact ? 760 : 560))
    readonly property real ovalH: Math.round(ovalW * 0.3125)
    readonly property real u: ovalH / 150
    // the colour of the band, the loop and the dot (setting tidal_player_color); the volume colour is yellow, or orange
    // when the player itself is yellow
    readonly property color green: Theme.playerColor(backend.settings.tidal_player_color)
    readonly property color yellow: Theme.playerColor(backend.settings.tidal_player_color) === Theme.playerColor("yellow")
                                    ? Theme.playerColor("orange") : Theme.playerColor("yellow")
    property bool compact: false                       // inside the sun view: no panel buttons (the planets do that)
    function nextColor() {
        var names = Theme.playerColors.map(function (c) { return c.name })
        var i = names.indexOf(String(backend.settings.tidal_player_color))
        backend.setSetting("tidal_player_color", names[(i + 1) % names.length])
    }

    // ---- state
    readonly property string visMode: backend.settings.tidal_player_vis_mode || "song"     // song | flow | off
    property bool wheelOn: false                       // the wheel was used a moment ago
    readonly property bool volActive: volSlider.hovered || volSlider.pressed || wheelOn
    property real seekP: -1                            // >= 0 while the loop is dragged
    readonly property real progress: seekP >= 0 ? seekP : (player.duration > 0 ? Math.min(1, player.position / player.duration) : 0)
    property var hist: []                              // recent levels, newest last; the band thickness along the loop

    function mmss(ms) {
        var s = Math.max(0, Math.floor(ms / 1000))
        return Math.floor(s / 60) + ":" + ("0" + (s % 60)).slice(-2)
    }
    function setVolume(v) {
        player.setVolume(Math.max(0, Math.min(100, Math.round(v))))
    }
    function bumpVolume(delta) {
        setVolume(player.volume + delta)
        wheelOn = true
        wheelTimer.restart()
    }
    Timer { id: wheelTimer; interval: 900; onTriggered: root.wheelOn = false }

    // A point of the stadium shape with the outward normal. s = 0..1, starts at the bottom centre and runs to the right.
    function pt(s, x0, y0, w, h) {
        var r = h / 2, straight = w - 2 * r, half = straight / 2, arc = Math.PI * r
        var d = ((s % 1) + 1) % 1 * (2 * straight + 2 * arc)
        var cy = y0 + r, th
        if (d < half) return [x0 + w / 2 + d, y0 + h, 0, 1]
        d -= half
        if (d < arc) { th = Math.PI / 2 - d / r; return [x0 + w - r + r * Math.cos(th), cy + r * Math.sin(th), Math.cos(th), Math.sin(th)] }
        d -= arc
        if (d < straight) return [x0 + w - r - d, y0, 0, -1]
        d -= straight
        if (d < arc) { th = -Math.PI / 2 - d / r; return [x0 + r + r * Math.cos(th), cy + r * Math.sin(th), Math.cos(th), Math.sin(th)] }
        d -= arc
        return [x0 + r + d, y0 + h, 0, 1]
    }
    // The part of the progress loop that is nearest to a mouse point (0..1) and its distance.
    function nearest(mx, my) {
        var x0 = 17 * u, y0 = 17 * u, w = ovalW - 34 * u, h = ovalH - 34 * u
        var best = 0, bd = 1e9
        for (var i = 0; i < 240; ++i) {
            var p = pt(i / 240, x0, y0, w, h)
            var d = (p[0] - mx) * (p[0] - mx) + (p[1] - my) * (p[1] - my)
            if (d < bd) { bd = d; best = i / 240 }
        }
        return [best, Math.sqrt(bd)]
    }

    // the oval is repainted at most 20 times a second: the level (30 Hz) and the position (25 Hz) both ask for it, and a paint
    // with shadows is the most expensive thing the GUI thread does; a slow GUI thread is what makes the sound stutter
    property bool repaintPending: false
    function repaint() {
        if (!visible) return
        if (paintGate.running) repaintPending = true
        else { art.requestPaint(); paintGate.start() }
    }
    Timer {
        id: paintGate
        interval: 50
        onTriggered: if (root.repaintPending) { root.repaintPending = false; art.requestPaint(); paintGate.start() }
    }
    Connections {
        target: player
        function onLevelChanged() {
            var h = root.hist.slice(-159)
            h.push(player.level)
            root.hist = h
            root.repaint()
        }
        function onPositionChanged() { root.repaint() }
        function onProfileChanged() { root.repaint() }
        function onFadeChanged() { root.repaint() }
        function onChanged() { root.repaint() }
    }
    onVisModeChanged: root.repaint()
    readonly property real amp: Math.max(0.5, Math.min(3, (backend.settings.level_amp || 100) / 100))
    onAmpChanged: root.repaint()
    readonly property real glow: Math.max(0, Math.min(3, (backend.settings.glow_amp === undefined ? 100 : backend.settings.glow_amp) / 100))
    onGlowChanged: root.repaint()
    readonly property bool outerRing: (backend.settings.outer_ring || "list") === "list"
    onOuterRingChanged: root.repaint()
    onGreenChanged: root.repaint()
    onVolActiveChanged: root.repaint()
    onWidthChanged: root.repaint()
    Connections { target: Theme; function onDarkChanged() { root.repaint() } }

    implicitHeight: col.implicitHeight + Theme.s2

    GridLayout {
        id: col
        width: parent.width
        columns: 1
        rowSpacing: Theme.s1

        // ---- playlist panel (above the oval when the player is at the bottom, below it when on top)
        Loader {
            Layout.fillWidth: true
            Layout.row: root.playerTop ? 5 : 0
            Layout.alignment: Qt.AlignHCenter
            Layout.preferredWidth: root.ovalW
            Layout.maximumWidth: root.ovalW
            Layout.preferredHeight: root.panelHeight
            active: root.panelOpen && !root.compact
            visible: active
            sourceComponent: TidalTrackPanel { ctl: root.ctl; player: root.player; local: root.local; tab: root.panelTab; onTabChanged: root.panelTab = tab; height: root.panelHeight }
        }

        // ---- the oval
        Item {
            id: oval
            Layout.alignment: Qt.AlignHCenter
            Layout.preferredWidth: root.ovalW
            Layout.preferredHeight: root.ovalH
            Layout.row: 1

            Canvas {
                id: art
                anchors.fill: parent
                renderTarget: Canvas.Image
                onPaint: {
                    var ctx = getContext("2d")
                    ctx.reset()
                    var W = oval.width, H = oval.height, u = root.u
                    var line = Theme.text
                    // outer rings
                    ctx.lineWidth = 1
                    var rings = [[1, 0.30], [9, 0.10], [14, 0.05]]
                    for (var r = 0; r < rings.length; ++r) {
                        var k = rings[r][0] * u
                        ctx.strokeStyle = Qt.alpha(line, rings[r][1])
                        ctx.beginPath()
                        ctx.roundedRect(k, k, W - 2 * k, H - 2 * k, (H - 2 * k) / 2, (H - 2 * k) / 2)
                        ctx.stroke()
                    }
                    var accent = root.volActive ? root.yellow : root.green
                    // level band around the inner oval; it lies under the oval, so only the outside is seen
                    var px = 34 * u, py = 34 * u, pw = W - 68 * u, ph = H - 68 * u
                    var mode = root.visMode
                    if (root.volActive || mode !== "off") {
                        var n = 160, base = [], norm = [], th = []
                        var vol = player.volume / 100
                        var prof = player.profile, pn = prof ? prof.length : 0
                        var lo = 1, hi = 0, amp = root.amp
                        for (var k = 0; k < pn; ++k) { var q0 = prof[k]; if (q0 >= 0) { if (q0 < lo) lo = q0; if (q0 > hi) hi = q0 } }
                        var span = hi - lo
                        var hist = root.hist, hn = hist.length
                        for (var i = 0; i <= n; ++i) {
                            var s = i / n
                            var t = 1.5
                            if (root.volActive) t = 1.5 + 8 * vol
                            else if (mode === "song") {
                                // the loudness of the whole song, laid around the oval from the start (bottom centre) on
                                var pv = pn ? prof[Math.min(pn - 1, Math.floor(s * pn))] : -1
                                var nv = pv < 0 ? 0 : (span > 0.04 ? (pv - lo) / span : pv)     // quiet parts flat, loud parts high
                                t = 1.5 + 13 * amp * Math.pow(nv, 1.3)
                            } else {
                                // the running level: mirrored left / right, so the band is continuous where the loop closes
                                var lv = hn ? hist[Math.min(hn - 1, Math.floor(Math.abs(2 * s - 1) * hn))] : 0
                                t = 1.5 + 13 * amp * Math.pow(lv, 0.8)
                            }
                            var b = root.pt(s, px, py, pw, ph)
                            base.push([b[0], b[1]])
                            norm.push([b[2], b[3]])
                            th.push(Math.min(t, 17) * u)
                        }
                        var bandSong = !root.volActive && mode === "song"
                        var cut = bandSong ? Math.max(0, Math.min(n, Math.round(root.progress * n))) : n
                        var drawBand = function (from, to, alpha) {
                            if (to <= from) return
                            ctx.beginPath()
                            ctx.moveTo(base[from][0] + norm[from][0] * th[from], base[from][1] + norm[from][1] * th[from])
                            for (var a = from + 1; a <= to; ++a) ctx.lineTo(base[a][0] + norm[a][0] * th[a], base[a][1] + norm[a][1] * th[a])
                            for (var c = to; c >= from; --c) ctx.lineTo(base[c][0], base[c][1])
                            ctx.closePath()
                            ctx.fillStyle = Qt.alpha(accent, alpha)
                            ctx.fill()
                        }
                        ctx.shadowColor = accent
                        ctx.shadowBlur = (13.2 + 9 * Math.min(1, player.level)) * u * root.glow
                        drawBand(0, cut, root.volActive ? 0.55 : 0.85)        // song: the part that was played
                        ctx.shadowBlur = 0
                        if (bandSong) drawBand(cut, n, 0.30)                  // song: what is still to come, quieter
                    }
                    // outer ring: how far the whole list (playlist / album / folder / queue) has played
                    var lp = root.outerRing ? player.listProgress : -1
                    if (lp !== undefined && lp >= 0) {
                        var ox = 4.5 * u, ow = W - 9 * u, oh = H - 9 * u
                        var osteps = Math.max(2, Math.ceil(lp * 240))
                        ctx.lineCap = "round"
                        ctx.lineWidth = 2 * u
                        ctx.strokeStyle = Qt.alpha(line, 0.14)
                        ctx.beginPath()
                        for (var o0 = 0; o0 <= 240; ++o0) { var h0 = root.pt(o0 / 240, ox, ox, ow, oh); if (o0 === 0) ctx.moveTo(h0[0], h0[1]); else ctx.lineTo(h0[0], h0[1]) }
                        ctx.stroke()
                        if (lp > 0.002) {
                            ctx.strokeStyle = Qt.alpha(accent, 0.75)
                            ctx.beginPath()
                            for (var o1 = 0; o1 <= osteps; ++o1) { var h1 = root.pt(lp * o1 / osteps, ox, ox, ow, oh); if (o1 === 0) ctx.moveTo(h1[0], h1[1]); else ctx.lineTo(h1[0], h1[1]) }
                            ctx.stroke()
                        }
                    }
                    // seamless change: an extra ring in its own lane, from 5 s before the fade to 5 s after it began
                    var fp = player.fade
                    if (fp !== undefined && fp >= 0) {
                        var fx = 10.5 * u, fw = W - 21 * u, fh = H - 21 * u
                        var fsteps = Math.max(2, Math.ceil(fp * 200))
                        ctx.lineCap = "round"
                        ctx.lineWidth = 2 * u
                        ctx.strokeStyle = Qt.alpha(line, 0.18)
                        ctx.beginPath()
                        for (var f0 = 0; f0 <= 200; ++f0) { var g0 = root.pt(f0 / 200, fx, fx, fw, fh); if (f0 === 0) ctx.moveTo(g0[0], g0[1]); else ctx.lineTo(g0[0], g0[1]) }
                        ctx.stroke()
                        ctx.strokeStyle = fp < 0.5 ? root.yellow : root.green
                        ctx.beginPath()
                        for (var f1 = 0; f1 <= fsteps; ++f1) { var g1 = root.pt(fp * f1 / fsteps, fx, fx, fw, fh); if (f1 === 0) ctx.moveTo(g1[0], g1[1]); else ctx.lineTo(g1[0], g1[1]) }
                        ctx.stroke()
                        var mk = root.pt(0.5, fx, fx, fw, fh)                  // where the fade starts
                        ctx.fillStyle = Theme.text
                        ctx.beginPath()
                        ctx.arc(mk[0], mk[1], 2.4 * u, 0, 2 * Math.PI)
                        ctx.fill()
                    }
                    // progress loop: the played part and the dot
                    var lx = 20 * u, ly = 20 * u, lw = W - 40 * u, lh = H - 40 * u
                    var p = root.progress
                    if (p > 0.002) {
                        ctx.strokeStyle = accent
                        ctx.lineWidth = 2 * u
                        ctx.lineCap = "round"
                        ctx.beginPath()
                        var steps = Math.max(2, Math.ceil(p * 240))
                        for (var j = 0; j <= steps; ++j) {
                            var q = root.pt(p * j / steps, lx, ly, lw, lh)
                            if (j === 0) ctx.moveTo(q[0], q[1]); else ctx.lineTo(q[0], q[1])
                        }
                        ctx.stroke()
                    }
                    var d = root.pt(p, lx, ly, lw, lh)
                    ctx.fillStyle = "#ffffff"
                    ctx.shadowColor = accent
                    ctx.shadowBlur = 8 * u
                    ctx.beginPath()
                    ctx.arc(d[0], d[1], 3.6 * u, 0, 2 * Math.PI)
                    ctx.fill()
                }
            }

            // the inner oval: title and artist on the left, previous / play / next on the right
            Rectangle {
                id: pill
                x: 34 * root.u; y: 34 * root.u
                width: oval.width - 68 * root.u; height: oval.height - 68 * root.u
                radius: height / 2
                color: Theme.surface
                border.width: 1
                border.color: Qt.alpha(Theme.text, 0.35)

                Column {
                    visible: !root.volActive
                    anchors.left: parent.left; anchors.leftMargin: 26 * root.u
                    anchors.right: controls.left; anchors.rightMargin: 12 * root.u
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 2
                    Text {
                        width: parent.width
                        text: root.cur.title || qsTr("Nothing playing")
                        color: Theme.text
                        font.pixelSize: Math.max(11, Math.round(14 * root.u))
                        font.weight: Font.Bold
                        elide: Text.ElideRight
                        TapHandler { enabled: !!root.cur.albumId; onTapped: root.ctl.open({ kind: "album", id: root.cur.albumId, title: root.cur.album }) }
                    }
                    Text {
                        width: parent.width
                        text: root.cur.subtitle || ""
                        color: Theme.textSecondary
                        font.pixelSize: Math.max(9, Math.round(10 * root.u))
                        elide: Text.ElideRight
                        TapHandler { enabled: !!root.cur.artistId; onTapped: root.ctl.open({ kind: "artist", id: root.cur.artistId, title: root.cur.subtitle }) }
                    }
                }
                Row {
                    visible: root.volActive
                    anchors.left: parent.left; anchors.leftMargin: 26 * root.u
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 10 * root.u
                    Text { text: qsTr("VOLUME"); anchors.baseline: bigVol.baseline; color: Theme.textTertiary
                           font.pixelSize: Math.max(8, Math.round(9 * root.u)); font.letterSpacing: 1 }
                    Text { id: bigVol; text: player.volume + "%"; color: Theme.text; font.weight: Font.Light
                           font.pixelSize: Math.max(18, Math.round(34 * root.u)) }
                }
                Row {
                    id: controls
                    anchors.right: parent.right; anchors.rightMargin: 20 * root.u
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 12 * root.u
                    Item {
                        width: 22 * root.u; height: 22 * root.u
                        anchors.verticalCenter: parent.verticalCenter
                        Icon { anchors.centerIn: parent; name: "skipPrev"; size: Math.max(12, 16 * root.u); filled: true; color: Theme.textSecondary }
                        TapHandler { onTapped: player.previous() }
                        HoverHandler { cursorShape: Qt.PointingHandCursor }
                        Accessible.role: Accessible.Button; Accessible.name: qsTr("Previous")
                    }
                    Rectangle {
                        width: 38 * root.u; height: 38 * root.u; radius: width / 2
                        color: Theme.text
                        anchors.verticalCenter: parent.verticalCenter
                        BusyIndicator { anchors.fill: parent; running: player.loading; visible: running }
                        Icon { anchors.centerIn: parent; visible: !player.loading; name: player.playing ? "pause" : "play"
                               filled: !player.playing; strokeWidth: player.playing ? 2.6 : 1.75
                               size: Math.max(12, 18 * root.u); color: Theme.surface }
                        TapHandler { onTapped: player.toggle() }
                        HoverHandler { cursorShape: Qt.PointingHandCursor }
                        Accessible.role: Accessible.Button; Accessible.name: player.playing ? qsTr("Pause") : qsTr("Play")
                    }
                    Item {
                        width: 22 * root.u; height: 22 * root.u
                        anchors.verticalCenter: parent.verticalCenter
                        Icon { anchors.centerIn: parent; name: "skipNext"; size: Math.max(12, 16 * root.u); filled: true; color: Theme.textSecondary }
                        TapHandler { onTapped: player.next() }
                        HoverHandler { cursorShape: Qt.PointingHandCursor }
                        Accessible.role: Accessible.Button; Accessible.name: qsTr("Next")
                    }
                }
            }

            // click / drag on the loop jumps in the song; the wheel changes the volume
            MouseArea {
                id: loopArea
                anchors.fill: parent
                z: -1                       // under the buttons of the inner oval
                hoverEnabled: true
                property bool dragging: false
                cursorShape: containsMouse && root.nearest(mouseX, mouseY)[1] < 14 * root.u ? Qt.PointingHandCursor : Qt.ArrowCursor
                onPressed: (m) => {
                    var n = root.nearest(m.x, m.y)
                    if (n[1] < 16 * root.u && player.currentIndex >= 0) { dragging = true; root.seekP = n[0] }
                }
                onPositionChanged: (m) => { if (dragging) root.seekP = root.nearest(m.x, m.y)[0]; }
                onReleased: {
                    if (dragging && root.seekP >= 0) player.seek(Math.round(root.seekP * player.duration))
                    dragging = false
                    root.seekP = -1
                }
                onWheel: (w) => { root.bumpVolume(w.angleDelta.y > 0 ? 5 : -5); w.accepted = true }
            }
        }

        // ---- volume and jumping in the song: always visible
        RowLayout {
            Layout.alignment: Qt.AlignHCenter
            Layout.preferredWidth: root.ovalW
            Layout.maximumWidth: root.ovalW
            Layout.row: 2
            spacing: Theme.s3

            component TextBtn: Text {
                id: tb
                property bool active: false
                property bool hovered: hover.hovered
                signal clicked()
                color: active ? Theme.text : (hovered ? Theme.text : Theme.textSecondary)
                font.family: "Consolas"
                font.pixelSize: 11
                font.letterSpacing: 1
                font.weight: active ? Font.Bold : Font.Normal
                Accessible.role: Accessible.Button
                Accessible.name: text
                HoverHandler { id: hover; cursorShape: Qt.PointingHandCursor }
                TapHandler { onTapped: tb.clicked() }
            }

            TextBtn { text: "\u00AB 10 s"; Accessible.name: qsTr("10 seconds back"); Layout.alignment: Qt.AlignLeft | Qt.AlignVCenter
                      onClicked: player.seek(Math.max(0, player.position - 10000)) }
            Item { Layout.fillWidth: true; Layout.preferredWidth: 1 }
            Icon { name: player.volume === 0 ? "mute" : "volume"; size: 16; color: root.volActive ? root.yellow : Theme.textSecondary
                   TapHandler { onTapped: root.setVolume(player.volume > 0 ? 0 : 80) }
                   HoverHandler { cursorShape: Qt.PointingHandCursor } }
            Slider {
                id: volSlider
                Layout.fillWidth: true
                Layout.preferredWidth: 160
                Layout.maximumWidth: 220
                implicitHeight: 18
                from: 0; to: 100; stepSize: 1
                value: player.volume
                hoverEnabled: true
                onMoved: root.setVolume(value)
                Accessible.name: qsTr("Volume")
                background: Rectangle {
                    y: (volSlider.height - 3) / 2; height: 3; width: volSlider.width; radius: 1.5
                    color: Qt.alpha(Theme.text, 0.2)
                    Rectangle { width: volSlider.visualPosition * parent.width; height: 3; radius: 1.5
                                color: root.volActive ? root.yellow : root.green }
                }
                handle: Rectangle {
                    x: volSlider.visualPosition * (volSlider.width - width); y: (volSlider.height - height) / 2
                    width: 12; height: 12; radius: 6; color: Theme.text
                    border.width: 2; border.color: root.volActive ? root.yellow : root.green
                }
            }
            Text { text: player.volume + "%"; color: Theme.textSecondary; font.family: "Consolas"; font.pixelSize: 11
                   Layout.preferredWidth: 34; horizontalAlignment: Text.AlignRight }
            Item { Layout.fillWidth: true; Layout.preferredWidth: 1 }
            TextBtn { text: "10 s \u00BB"; Accessible.name: qsTr("10 seconds ahead"); Layout.alignment: Qt.AlignRight | Qt.AlignVCenter
                      onClicked: player.seek(Math.min(player.duration, player.position + 10000)) }
        }

        // ---- the other text controls; they wrap into more lines instead of running out of the window
        Flow {
            visible: !root.compact                 // as the sun these buttons are in the Settings planet
            Layout.alignment: Qt.AlignHCenter
            Layout.preferredWidth: root.ovalW
            Layout.row: 3
            spacing: Theme.s4
            layoutDirection: Qt.LeftToRight

            TextBtn {
                text: player.repeat === "one" ? qsTr("REPEAT SINGLE") : player.repeat === "all" ? qsTr("REPEAT ALL") : qsTr("REPEAT OFF")
                active: player.repeat !== "off"
                onClicked: player.cycleRepeat()
            }
            TextBtn { text: qsTr("SHUFFLE"); active: player.shuffle; onClicked: player.toggleShuffle() }
            TextBtn {
                id: likeBtn
                readonly property bool fav: favTick >= 0 && !!root.cur.id && tidal.isFavorite("track", root.cur.id)
                property int favTick: 0
                Connections { target: tidal; function onFavoritesChanged() { likeBtn.favTick++ } }
                text: fav ? qsTr("\u2665 LIKED") : qsTr("\u2661 LIKE")
                active: fav
                visible: !!root.cur.id && !root.local
                onClicked: tidal.toggleFavorite("track", root.cur.id)
            }
            TextBtn { visible: !root.compact; text: root.local ? qsTr("LIBRARY") : qsTr("PLAYLIST"); active: root.panelOpen
                      onClicked: root.panelOpen = !root.panelOpen }
            TextBtn { visible: !root.compact && root.local && backend.streamAvailable && !!root.cur.file; text: qsTr("STREAM"); active: backend.streamPlaying
                      onClicked: backend.streamFile(root.cur.file, root.cur.title)
                      ToolTip.visible: hovered; ToolTip.text: qsTr("Play this song on the speaker / TV (Stream to box)") }
            TextBtn { visible: !root.local && !root.compact; text: qsTr("LYRICS"); active: root.panelOpen && root.panelTab === "lyrics"
                      onClicked: { if (root.panelOpen && root.panelTab === "lyrics") root.panelOpen = false
                                   else { root.panelTab = "lyrics"; root.panelOpen = true } } }
            TextBtn {
                text: root.visMode === "song" ? qsTr("VIS SONG") : root.visMode === "flow" ? qsTr("VIS FLOW") : qsTr("VIS OFF")
                active: root.visMode !== "off"
                onClicked: backend.setSetting("tidal_player_vis_mode", root.visMode === "song" ? "flow" : root.visMode === "flow" ? "off" : "song")
                ToolTip.visible: hovered
                ToolTip.text: qsTr("Band around the oval: the loudness of the song / the running level / off")
            }
            TextBtn {
                text: qsTr("COLOR")
                color: root.green
                onClicked: root.nextColor()
                ToolTip.visible: hovered
                ToolTip.text: qsTr("Colour of the player: green, blue, red, yellow, purple, orange, pink, cyan, white")
            }
        }

        // ---- what plays and how far, small and quiet
        Text {
            Layout.alignment: Qt.AlignHCenter
            Layout.row: 4
            visible: player.currentIndex >= 0
            text: root.mmss(player.position) + " / " + root.mmss(player.duration) + (player.badge !== "" ? "  \u00B7  " + player.badge : "")
            color: Theme.textTertiary
            font.family: "Consolas"
            font.pixelSize: 10
            ToolTip.visible: badgeHover.hovered && player.badgeTip !== ""
            ToolTip.text: player.badgeTip
            HoverHandler { id: badgeHover }
        }
    }
}
