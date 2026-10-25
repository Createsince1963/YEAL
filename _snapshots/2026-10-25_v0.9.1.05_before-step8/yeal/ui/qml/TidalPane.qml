import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import QtWebView

// Embedded TIDAL web player (Windows: the system WebView2, like the YouTube view). Each user signs in
// inside the player itself; the session stays in the web view profile. The view is created once and then
// only hidden / shown, so switching back and forth does not reload the page or stop the music.
Item {
    id: pane
    property string home: "https://listen.tidal.com"
    property bool suspended: false      // native view cannot sit under QML popups / the other player -> collapse it
    signal videoLink(string url)

    // Same technique as WebPane: the native view is collapsed to 2x2 px instead of being destroyed, expanded
    // again afterwards, and the geometry nudged if it comes back with a stale size.
    readonly property var wv: webHost.item
    property string lastUrl: ""
    readonly property bool hidden: suspended
    property bool rebuilding: false
    property int pad: 1
    property int fixTries: 0
    function run(js, cb) {
        if (!wv) return
        if (cb) wv.runJavaScript(js, cb)
        else wv.runJavaScript(js)
    }
    function measure(cb) {
        pane.run("window.innerWidth+','+window.innerHeight", function (r) {
            var a = String(r).replace(/"/g, "").split(",")
            var w = parseFloat(a[0]), h = parseFloat(a[1])
            cb(w > 0 && h > 0 && !!pane.wv && pane.wv.width > 0 && pane.wv.height > 0
               && w >= pane.wv.width * 0.94 && w <= pane.wv.width * 1.06
               && h >= pane.wv.height * 0.94 && h <= pane.wv.height * 1.06)
        })
    }
    function relayout() { if (hidden || rebuilding) return; fixTries = 0; nudge.restart(); fixTimer.restart() }
    function rebuild() { rebuilding = true; rebuildTimer.restart() }
    Timer { id: rebuildTimer; interval: 80; onTriggered: pane.rebuilding = false }
    Timer { id: nudge; interval: 120; onTriggered: { pane.pad = 3; nudgeBack.restart() } }
    Timer { id: nudgeBack; interval: 80; onTriggered: pane.pad = 1 }
    Timer {
        id: fixTimer
        interval: 600
        onTriggered: pane.measure(function (ok) {
            if (ok || pane.hidden) return
            if (pane.fixTries++ < 5) { nudge.restart(); fixTimer.restart() }
            else pane.rebuild()
        })
    }
    onHiddenChanged: if (!hidden) relayout()

    function reload() { if (wv) wv.reload() }
    function navigate(u) { if (wv) wv.url = u; else lastUrl = u }
    function goBack() { if (wv && wv.canGoBack) wv.goBack(); else pane.run("history.back()") }
    function goForward() { if (wv && wv.canGoForward) wv.goForward(); else pane.run("history.forward()") }
    Shortcut { sequence: "Alt+Left"; enabled: pane.visible && !pane.suspended; onActivated: pane.goBack() }
    Shortcut { sequence: "Alt+Right"; enabled: pane.visible && !pane.suspended; onActivated: pane.goForward() }
    Shortcut { sequence: "F5"; enabled: pane.visible && !pane.suspended; onActivated: pane.reload() }

    // The player is a single-page app: the address is read from the page itself.
    property string live: ""
    readonly property string current: live !== "" ? live : (wv ? wv.url.toString() : lastUrl)
    readonly property var linkPattern: /^https?:\/\/(listen\.|www\.)?tidal\.com\/(browse\/)?(track|album|playlist|mix|video|artist)\/[\w-]+/i
    // Canonical link for the download field (tiddl understands tidal.com/browse/...).
    function cleanLink(u) {
        var m = /^https?:\/\/(?:listen\.|www\.)?tidal\.com\/(?:browse\/)?(track|album|playlist|mix|video|artist)\/([\w-]+)/i.exec(u)
        return m ? "https://tidal.com/browse/" + m[1].toLowerCase() + "/" + m[2] : u
    }
    // Like the YouTube view: a track / album / playlist / video page that is opened puts its link into the
    // download field by itself (once per link); "Use this link" repeats it on demand.
    property string lastPublished: ""
    function publish(force) {
        if (!linkPattern.test(current)) return
        var link = cleanLink(current)
        if (force !== true && link === lastPublished) return
        lastPublished = link
        pane.videoLink(link)
    }
    Timer {
        interval: 1000
        repeat: true
        running: pane.visible && !pane.suspended
        onTriggered: pane.run("location.href", function (result) {
            var href = result
            if (typeof href === "string" && href.charAt(0) === '"') {
                try { href = JSON.parse(href) } catch (e) { return }
            }
            if (typeof href === "string" && href !== "" && href !== pane.live) {
                pane.live = href
                if (/^https?:\/\/([\w-]+\.)?tidal\.com\//i.test(href)) pane.lastUrl = href
                pane.publish(false)
            }
        })
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.s2

        RowLayout {
            spacing: Theme.s1
            Layout.fillWidth: true
            IconButton { iconName: "chevronLeft"; tip: qsTr("Back (Alt+Left)"); onClicked: pane.goBack() }
            IconButton { iconName: "chevronRight"; tip: qsTr("Forward (Alt+Right)"); onClicked: pane.goForward() }
            IconButton { iconName: "retry"; tip: qsTr("Reload"); onClicked: pane.reload() }
            IconButton { iconName: "music"; tip: qsTr("TIDAL start page"); onClicked: pane.navigate(pane.home) }
            IconButton {
                iconName: "open"
                tip: qsTr("Open in your browser")
                onClicked: backend.openLink(pane.current !== "" ? pane.current : pane.home)
            }
            Text {
                text: (pane.wv && pane.wv.title !== "") ? pane.wv.title : pane.current
                color: Theme.textSecondary
                font.pixelSize: Theme.footnote
                elide: Text.ElideRight
                Layout.fillWidth: true
                Layout.leftMargin: Theme.s2
            }
            AppButton {
                text: qsTr("Use this link")
                iconName: "link"
                kind: "secondary"
                visible: pane.linkPattern.test(pane.current)
                onClicked: pane.publish(true)
            }
        }
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            radius: Theme.radius
            color: Theme.surface
            clip: true
            border.width: 1
            border.color: Theme.separator
            onWidthChanged: pane.relayout()
            onHeightChanged: pane.relayout()
            Loader {
                id: webHost
                x: pane.pad
                y: pane.pad
                width: pane.hidden ? 2 : parent.width - 2 * pane.pad
                height: pane.hidden ? 2 : parent.height - 2 * pane.pad
                active: !pane.rebuilding
                sourceComponent: webComp
            }
            Component {
                id: webComp
                WebView {
                    anchors.fill: parent
                    Component.onCompleted: url = pane.lastUrl !== "" ? pane.lastUrl : pane.home
                    onUrlChanged: { pane.live = ""; pane.lastUrl = url.toString() }
                }
            }
            Rectangle {
                visible: !!pane.wv && pane.wv.loadProgress > 0 && pane.wv.loadProgress < 100
                height: 2
                width: pane.wv ? parent.width * pane.wv.loadProgress / 100 : 0
                color: Theme.accentFill
            }
        }
    }
}
