import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// A player as a small solar system: the oval track player is the SUN in the middle (its glow breathes with the music,
// it grows with the window), the PLANETS on the orbits around it unfold into cards and fold away again. An opened planet
// makes room: the sun and its orbits move over so that nothing is covered.
//
// The user shapes the system: the slider in the corner (or the mouse wheel on the empty sky) makes all orbits larger or
// smaller, and every planet can be dragged - around the sun to another place on its orbit, in or out to a different
// orbit of its own (it snaps onto an orbit that is already used). Everything is remembered (sun_scale, sun_layout).
// The sun button folds all planets into the sun; the retry button puts the planets back on the main orbit.
//
// planets: [{ key, icon, label, title, deg, edit }]  deg = the place on the main orbit (0 right, 90 below, 180 left, 270
// above). A card opens on the side where its planet stands NOW (also after the planet was dragged): planets on the left
// open a card in the left column, on the right in the right column, above / below in a band at the top / bottom. The cards
// of one side share it, in the order of their planets. left / right are tall columns, top / bottom are bands.
// edit: true - the card has an edit mode: it zooms to a large card (pencil button, or the card asks for it) and goes back
// to its normal size with "Done".
// cards: { key: Component } - what a card shows (declared in the file that uses the sun view).
Item {
    id: view
    property var player
    property bool local: false                         // the sun plays downloaded files
    property var ctl: null                             // TidalHome (TIDAL pages), null for downloaded files
    property bool dropPlay: false                      // titles dropped on the sun play at once (TIDAL)
    property bool canExit: false                       // a second corner button leads back to the normal pages
    property string ns: "local"                        // name of this view in sun_layout
    property var planets: []
    property var cards: ({})
    property var opened: ({})                          // planet key -> true
    signal exitRequested()

    readonly property color tint: Theme.playerColor(backend.settings.tidal_player_color)
    readonly property bool orbit: backend.settings.local_orbit !== false
    readonly property real orbitScale: backend.settings.sun_scale || 1
    readonly property var layout: backend.settings.sun_layout || ({})
    readonly property real margin: 10
    readonly property real sideW: 260                  // width of the left / right card
    readonly property real bandH: 250                  // height of the top / bottom cards
    property string zoomKey: ""                        // the planet whose card is zoomed for editing ("" = none)
    property string dragKey: ""                        // the planet that is being dragged ...
    property real dragDeg: 0                           // ... and where it is now
    property real dragR: 1

    function planetOf(key) {
        for (var i = 0; i < planets.length; ++i) if (planets[i].key === key) return planets[i]
        return null
    }
    function isOpen(key) { return orbit && opened[key] === true && planetOf(key) !== null }
    function toggle(key) { var o = Object.assign({}, opened); o[key] = !o[key]; opened = o }
    function fold(key) { var o = Object.assign({}, opened); o[key] = false; opened = o; if (zoomKey === key) zoomKey = "" }
    function setZoom(key, on) { if (on) { var o = Object.assign({}, opened); o[key] = true; opened = o; zoomKey = key } else if (zoomKey === key) zoomKey = "" }
    // the saved place of a planet (a planet that is being dragged keeps its old side until it is dropped)
    function savedPlace(p) {
        var saved = layout[ns + "." + p.key]
        return saved ? { deg: saved.deg, r: saved.r } : { deg: p.deg, r: 1 }
    }
    // the side of the sun a planet stands on = the side its card opens on
    function zoneOf(p) {
        var d = savedPlace(p).deg % 360
        if (d >= 225 && d <= 315) return "top"
        if (d >= 45 && d <= 135) return "bottom"
        return d > 135 && d < 225 ? "left" : "right"
    }
    // along the side: where the planet stands (top to bottom for the columns, left to right for the bands)
    function alongOf(p) {
        var o = savedPlace(p), a = o.deg * Math.PI / 180, z = zoneOf(p)
        return (z === "left" || z === "right") ? Math.sin(a) * o.r : Math.cos(a) * o.r
    }
    // the opened cards of a side, in the order of their planets
    function inZone(zone) {
        var out = []
        for (var i = 0; i < planets.length; ++i)
            if (isOpen(planets[i].key) && zoneOf(planets[i]) === zone) out.push(planets[i])
        out.sort(function (a, b) { return alongOf(a) - alongOf(b) })
        return out
    }

    // ---- what is left for the sun and its orbits after the opened cards
    readonly property real availX0: margin + (inZone("left").length ? sideW + margin : 0)
    readonly property real availX1: width - margin - (inZone("right").length ? sideW + margin : 0)
    readonly property real availY0: margin + (inZone("top").length ? bandH + margin : 0)
    readonly property real availY1: height - margin - (inZone("bottom").length ? bandH + margin : 0)
    readonly property real availW: Math.max(200, availX1 - availX0)
    readonly property real availH: Math.max(200, availY1 - availY0)
    property real cx: (availX0 + availX1) / 2
    property real cy: (availY0 + availY1) / 2
    Behavior on cx { NumberAnimation { duration: Theme.dur; easing.type: Easing.OutCubic } }
    Behavior on cy { NumberAnimation { duration: Theme.dur; easing.type: Easing.OutCubic } }
    // the sun grows with the window; the orbits grow with the slider, but never out of the free area
    readonly property real sunW: Math.max(260, Math.min(availW * 0.42, 720, availW - (orbit ? 2 * 92 : 2 * 12)))
    readonly property real sunH: sun.implicitHeight
    readonly property real rx: Math.max(sunW / 2 + 30, Math.min((sunW / 2 + 64) * orbitScale, availW / 2 - 40))
    readonly property real ry: Math.max(sunH / 2 + 30, Math.min((sunH / 2 + 64) * orbitScale, availH / 2 - 40))

    // the place of a planet: its saved place, else its place on the main orbit; while it is dragged, the mouse decides
    function placeOf(p) {
        if (p.key === dragKey) return { deg: dragDeg, r: dragR }
        return savedPlace(p)
    }
    function planetX(p) {
        var o = placeOf(p)
        return Math.max(availX0 + 34, Math.min(availX1 - 34, cx + rx * o.r * Math.cos(o.deg * Math.PI / 180)))
    }
    function planetY(p) {
        var o = placeOf(p)
        return Math.max(availY0 + 26, Math.min(availY1 - 44, cy + ry * o.r * Math.sin(o.deg * Math.PI / 180)))
    }
    // the sizes of the orbits that are in use (1 = the main orbit)
    function ringList() {
        var seen = {}, out = []
        for (var i = 0; i < planets.length; ++i) {
            var r = Math.round(placeOf(planets[i]).r * 100) / 100
            if (!seen[r]) { seen[r] = true; out.push(r) }
        }
        out.sort(function (a, b) { return a - b })
        return out
    }
    function dragTo(key, pt) {                         // pt: the mouse in the coordinates of this view
        var dx = (pt.x - cx) / rx, dy = (pt.y - cy) / ry
        var r = Math.max(0.45, Math.min(2.6, Math.sqrt(dx * dx + dy * dy)))
        var deg = Math.atan2(dy, dx) * 180 / Math.PI
        if (deg < 0) deg += 360
        var rings = ringList().concat([1])
        for (var i = 0; i < rings.length; ++i) if (Math.abs(rings[i] - r) < 0.07) { r = rings[i]; break }
        var step = Math.round(deg / 15) * 15
        if (Math.abs(step - deg) < 3) deg = step % 360
        dragKey = key; dragDeg = deg; dragR = r
    }
    function dropPlanet() {                            // the mouse button is released: remember the place
        if (dragKey === "") return
        var l = JSON.parse(JSON.stringify(layout))
        l[ns + "." + dragKey] = { deg: Math.round(dragDeg * 10) / 10, r: Math.round(dragR * 100) / 100 }
        dragKey = ""
        backend.setSetting("sun_layout", l)
    }
    function setOrbitScale(v) { backend.setSetting("sun_scale", Math.round(Math.max(0.5, Math.min(3, v)) * 20) / 20) }
    function resetOrbits() { backend.setSetting("sun_layout", {}); backend.setSetting("sun_scale", 1) }

    // the place of the card of a planet: on the side where the planet stands; a zoomed card (edit mode) is large and central
    function rectOf(p) {
        if (zoomKey === p.key)
            return Qt.rect(margin * 2, margin * 2, Math.max(260, width - 4 * margin), Math.max(260, height - 4 * margin))
        var zone = zoneOf(p), group = inZone(zone), idx = 0
        for (var i = 0; i < group.length; ++i) if (group[i].key === p.key) idx = i
        var n = Math.max(1, group.length)
        if (zone === "left" || zone === "right") {              // a tall column; several opened cards share it, one above the other
            var h = (height - 2 * margin - (n - 1) * margin) / n
            return Qt.rect(zone === "left" ? margin : width - margin - sideW, margin + idx * (h + margin), sideW, h)
        }
        var w = n > 1 ? (availW - (n - 1) * margin) / n : Math.min(460, availW)
        var x = n > 1 ? availX0 + idx * (w + margin) : Math.max(availX0, Math.min(availX1 - w, planetX(p) - w / 2))
        var y = zone === "top" ? margin : height - margin - bandH
        return Qt.rect(x, y, w, bandH)
    }

    onCxChanged: space.requestPaint()
    onCyChanged: space.requestPaint()
    onRxChanged: space.requestPaint()
    onRyChanged: space.requestPaint()
    onTintChanged: space.requestPaint()
    onOrbitChanged: space.requestPaint()
    onLayoutChanged: space.requestPaint()
    onDragRChanged: space.requestPaint()
    onDragKeyChanged: space.requestPaint()
    onPlanetsChanged: space.requestPaint()
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

    // ---- the sky: the glow of the sun and the orbits
    Canvas {
        id: space
        anchors.fill: parent
        renderTarget: Canvas.Image
        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            var lv = view.player ? view.player.level : 0
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
            var rings = view.ringList()
            ctx.setLineDash([])
            for (var i = 0; i < rings.length; ++i) {
                var a = view.rx * rings[i], b = view.ry * rings[i]
                ctx.strokeStyle = Qt.alpha(view.tint, view.dragKey !== "" ? 0.45 : 0.30)
                ctx.beginPath()
                ctx.ellipse(view.cx - a, view.cy - b, 2 * a, 2 * b)
                ctx.stroke()
            }
            var last = rings.length ? rings[rings.length - 1] : 1       // a faint dotted ring outside the last one
            ctx.setLineDash([3, 7])
            ctx.strokeStyle = Qt.alpha(Theme.text, 0.12)
            ctx.beginPath()
            ctx.ellipse(view.cx - view.rx * last - 26, view.cy - view.ry * last - 26, 2 * (view.rx * last + 26), 2 * (view.ry * last + 26))
            ctx.stroke()
        }
    }
    WheelHandler {                // the wheel on the empty sky: larger / smaller orbits
        enabled: view.orbit
        onWheel: (event) => view.setOrbitScale(view.orbitScale + (event.angleDelta.y > 0 ? 0.1 : -0.1))
    }

    // ---- the sun
    TidalTrackPlayer {
        id: sun
        x: view.cx - width / 2
        y: view.cy - height / 2
        width: view.sunW
        height: implicitHeight
        ctl: view.ctl
        player: view.player
        local: view.local
        compact: true
        z: 2
    }
    DropArea {                    // titles, albums, playlists dropped on the sun play at once
        enabled: view.dropPlay
        x: sun.x; y: sun.y; width: sun.width; height: sun.height
        z: 6
        keys: ["text/plain"]
        onEntered: (drag) => drag.accepted = tidal.dragPayload.length > 0
        onDropped: (drop) => {
            var items = tidal.dragPayload
            if (items.length === 0) return
            drop.accept(Qt.CopyAction)
            view.player.playNow(items)
            tidal.setDragPayload([])
        }
        Rectangle {
            anchors.fill: parent
            visible: parent.containsDrag
            radius: Theme.radius
            color: Theme.accentSoft
            border.width: 2
            border.color: Theme.accent
            Text { anchors.centerIn: parent; text: qsTr("Drop to play"); color: Theme.accent
                   font.pixelSize: Theme.headline; font.weight: Font.DemiBold }
        }
    }

    // ---- the planets: a click opens / folds the card, dragging moves the planet to another place or orbit
    Repeater {
        model: view.orbit ? view.planets : []
        delegate: Planet {
            required property var modelData
            icon: modelData.icon
            label: modelData.label
            tint: view.tint
            open: view.isOpen(modelData.key)
            x: view.planetX(modelData) - width / 2
            y: view.planetY(modelData) - 26
            z: view.dragKey === modelData.key ? 7 : 3
            onClicked: view.toggle(modelData.key)
            DragHandler {
                target: null
                cursorShape: active ? Qt.ClosedHandCursor : Qt.ArrowCursor
                onCentroidChanged: if (active) view.dragTo(modelData.key, view.mapFromItem(null, centroid.scenePosition))
                onActiveChanged: if (!active) view.dropPlanet()
            }
        }
    }
    Row {                         // corner: size of the orbits, planets back to the main orbit, back to the pages, fold
        anchors.right: parent.right; anchors.bottom: parent.bottom
        anchors.rightMargin: view.width - view.availX1 + Theme.s2        // left of the opened right cards, not on top of them
        anchors.bottomMargin: view.height - view.availY1 + Theme.s2
        spacing: Theme.s1
        z: 8
        Text {
            visible: view.orbit
            anchors.verticalCenter: parent.verticalCenter
            text: qsTr("Orbit")
            color: Theme.textSecondary; font.pixelSize: Theme.caption
        }
        Slider {
            id: orbitSlider
            visible: view.orbit
            anchors.verticalCenter: parent.verticalCenter
            width: 120
            from: 0.5; to: 3; stepSize: 0.05
            value: view.orbitScale
            onMoved: view.setOrbitScale(value)
            Accessible.name: qsTr("Size of the orbits")
            ToolTip.visible: hovered; ToolTip.text: qsTr("Size of the orbits (also the mouse wheel on the empty sky). Drag a planet to give it its own orbit.")
            background: Rectangle {
                y: (orbitSlider.height - 3) / 2; height: 3; width: orbitSlider.width; radius: 1.5
                color: Qt.alpha(Theme.text, 0.2)
                Rectangle { width: orbitSlider.visualPosition * parent.width; height: 3; radius: 1.5; color: view.tint }
            }
            handle: Rectangle {
                x: orbitSlider.visualPosition * (orbitSlider.width - width); y: (orbitSlider.height - height) / 2
                width: 12; height: 12; radius: 6; color: Theme.text
                border.width: 2; border.color: view.tint
            }
        }
        IconButton {
            visible: view.orbit
            iconName: "retry"
            tip: qsTr("Put the planets back on the main orbit")
            onClicked: view.resetOrbits()
        }
        IconButton {
            visible: view.canExit
            iconName: "home"
            tip: qsTr("Back to the TIDAL pages")
            onClicked: view.exitRequested()
        }
        IconButton {
            iconName: "sun"
            tint: view.orbit ? view.tint : Theme.textSecondary
            tip: view.orbit ? qsTr("Fold the planets into the sun") : qsTr("Show the planets")
            onClicked: backend.setSetting("local_orbit", !view.orbit)
        }
    }

    // ---- the cards
    Rectangle {                   // behind a zoomed card: the rest of the view is dimmed, a click on it ends the edit mode
        anchors.fill: parent
        radius: Theme.radius
        color: Qt.alpha("#000000", 0.55)
        opacity: view.zoomKey !== "" ? 1 : 0
        visible: opacity > 0.01
        z: 8.5
        Behavior on opacity { NumberAnimation { duration: Theme.dur } }
        MouseArea { anchors.fill: parent; onClicked: view.zoomKey = "" }
    }
    Repeater {
        model: view.planets
        delegate: PlanetCard {
            id: card
            required property var modelData
            objectName: "card-" + modelData.key
            readonly property rect place: view.rectOf(modelData)
            title: (modelData.title || modelData.label || "").toUpperCase()
            tint: view.tint
            open: view.isOpen(modelData.key)
            editable: modelData.edit === true
            zoomed: view.zoomKey === modelData.key
            x: place.x; y: place.y; width: place.width; height: place.height
            z: zoomed ? 9 : 5
            Behavior on x { enabled: card.open; NumberAnimation { duration: Theme.dur; easing.type: Easing.OutCubic } }
            Behavior on y { enabled: card.open; NumberAnimation { duration: Theme.dur; easing.type: Easing.OutCubic } }
            Behavior on width { enabled: card.open; NumberAnimation { duration: Theme.dur; easing.type: Easing.OutCubic } }
            Behavior on height { enabled: card.open; NumberAnimation { duration: Theme.dur; easing.type: Easing.OutCubic } }
            onClosed: view.fold(modelData.key)
            onZoomRequested: (on) => view.setZoom(modelData.key, on)
            Loader {
                anchors.fill: parent
                active: card.open || card.opacity > 0.01
                sourceComponent: view.cards[card.modelData.key] || null
                onLoaded: {           // cards with an edit mode: they know when they are zoomed and may ask for it (e.g. after "add")
                    if (item && item.editing !== undefined) item.editing = Qt.binding(function () { return card.zoomed })
                    if (item && item.editRequest) item.editRequest.connect(function (on) { card.zoomRequested(on) })
                }
            }
        }
    }
}
