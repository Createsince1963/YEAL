import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import QtWebView

// Embedded YouTube (Windows: the system WebView2, no bundled browser). Opening a video
// or playlist puts its link into the download field; the user confirms the download.
Item {
    id: pane
    property string home: "https://www.youtube.com"
    property bool suspended: false      // native view cannot sit under QML popups -> hide it then
    signal videoLink(string url)

    // The native web view sits in a Loader (see webHost). While a dialog is open the view is NOT destroyed (that
    // restarted the video and lost the page): it is collapsed to 2x2 px under the dialog and expanded again
    // afterwards, so the page keeps playing. A native view can come back with a stale size (blank white box);
    // after every expand the page's inner size is measured and the geometry nudged. Only if that fails
    // repeatedly the view is re-created (rebuild) and lastUrl brings the user back to the page.
    readonly property var wv: webHost.item
    property string lastUrl: ""
    readonly property bool hidden: suspended || testSuspend
    property bool rebuilding: false
    property int pad: 1
    property int fixTries: 0
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
    // nudge: change the margin for a moment so the native view gets a new geometry
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

    // TEST HOOK (remove after testing): with --selftest a dialog is simulated 8-11 s after start.
    property bool testSuspend: false
    Timer { interval: 8000; running: Qt.application.arguments.indexOf("--selftest") >= 0; onTriggered: pane.testSuspend = true }
    Timer { interval: 11000; running: Qt.application.arguments.indexOf("--selftest") >= 0; onTriggered: pane.testSuspend = false }
    function run(js, cb) {
        if (!wv) return
        if (cb) wv.runJavaScript(js, cb)
        else wv.runJavaScript(js)
    }
    function reload() { if (wv) wv.reload() }
    function navigate(u) { if (wv) wv.url = u; else lastUrl = u }

    property string live: ""           // address read from the page itself (see the poll timer)
    property string lastPublished: ""
    readonly property string current: live !== "" ? live : (wv ? wv.url.toString() : lastUrl)
    readonly property var linkPattern: /^https?:\/\/((www|m|music)\.)?(youtube\.com\/(watch|shorts|playlist|live)|youtu\.be\/)/i

    // Follow the app theme: YouTube keeps its theme in the PREF cookie (f6 = 400 dark). The cookie is
    // merged (other YouTube settings stay) and the page is reloaded once when the value changed.
    readonly property bool dark: Theme.dark
    // The reload runs at most once per theme change: if YouTube rewrites the PREF cookie itself (signed-in account,
    // consent page) the value would never match and the page would reload forever (Back/Forward/Reload impaired).
    property int themeReloads: 0
    function applyTheme() {
        if (!/^https?:\/\/([\w-]+\.)?youtube\.com\//i.test(current) || themeReloads >= 1)
            return
        themeReloads++
        pane.run("(function(dark){var m=document.cookie.match(/(?:^|; )PREF=([^;]*)/);"
            + "var parts=m?m[1].split('&').filter(function(x){return x&&x.indexOf('f6=')!==0}):[];"
            + "var old=m?(m[1].split('&').filter(function(x){return x.indexOf('f6=')===0})[0]||''):'';"
            + "var want=dark?'f6=400':'f6=80000';if(old===want)return;parts.push(want);"
            + "document.cookie='PREF='+parts.join('&')+'; domain=.youtube.com; path=/; max-age=31536000; secure';"
            + "location.reload()})(" + (dark ? "true" : "false") + ")")
    }
    onDarkChanged: { themeReloads = 0; applyTheme() }

    // Video ads: hide ad slots, press "Skip", and jump to the end of an ad that cannot be skipped.
    // (Blocking the ad domains alone does not help: YouTube serves its own ads from its own servers.)
    function applyAdScript() {
        if (!backend.settings.adblock_experimental || !/^https?:\/\/([\w-]+\.)?youtube\.com\//i.test(current))
            return
        pane.run("(function(){if(window.__yealAds)return;window.__yealAds=1;"
            + "var s=document.createElement('style');s.textContent='ytd-ad-slot-renderer,#player-ads,"
            + "ytd-banner-promo-renderer,ytd-statement-banner-renderer,ytd-in-feed-ad-layout-renderer,"
            + ".ytp-ad-overlay-container,ytd-promoted-sparkles-web-renderer,#masthead-ad{display:none!important}';"
            + "document.documentElement.appendChild(s);"
            + "setInterval(function(){var p=document.querySelector('.html5-video-player');"
            + "if(!p||!p.classList.contains('ad-showing'))return;"
            + "var b=document.querySelector('.ytp-skip-ad-button,.ytp-ad-skip-button-modern,.ytp-ad-skip-button');"
            + "if(b){b.click();return}"
            + "var v=p.querySelector('video');if(v&&isFinite(v.duration)&&v.duration>0){v.currentTime=v.duration}"
            + "},400)})()")
    }

    // Mute while a YouTube ad runs, restore the sound when the video itself plays. The player marks an ad
    // with the class "ad-showing" on .html5-video-player; that is polled 5x per second. The mute state the
    // user had before the ad is remembered and put back (a user who muted the video stays muted).
    function applyMuteScript() {
        if (!/^https?:\/\/([\w-]+\.)?youtube\.com\//i.test(current))
            return
        pane.run("(function(){if(window.__yealMute)return;window.__yealMute=1;var ours=false,prev=false;"
            + "function isM(p,v){return typeof p.isMuted==='function'?p.isMuted():v.muted}"
            + "function setM(p,v,m){if(typeof p.mute==='function'&&typeof p.unMute==='function'){m?p.mute():p.unMute()}v.muted=m}"
            + "setInterval(function(){var p=document.querySelector('.html5-video-player');if(!p)return;"
            + "var v=p.querySelector('video');if(!v)return;"
            + "var ad=p.classList.contains('ad-showing')||p.classList.contains('ad-interrupting');"
            + "if(ad){if(!ours){prev=isM(p,v);ours=true}if(!isM(p,v)||!v.muted)setM(p,v,true)}"
            + "else if(ours){ours=false;setM(p,v,prev)}},200)})()")
    }

    // Clean link of the page: a watch page keeps only the video id (no mix/radio list, time stamp, tracking).
    function cleanLink(u) {
        var m = /^https?:\/\/(?:www\.|m\.|music\.)?youtube\.com\/watch\?(?:.*&)?v=([\w-]{6,})/i.exec(u)
        return m ? "https://www.youtube.com/watch?v=" + m[1] : u
    }
    // Own page history. The native view is destroyed while a dialog is open and created fresh afterwards, so its
    // history (and with it Back) was gone. Every address the view reports is kept here; Back/Forward use the
    // page's own history first (instant in-page navigation) and fall back to this list when that does nothing.
    property var navStack: []
    property int navIndex: -1
    function track(u) {
        u = String(u)
        if (!/^https?:\/\//i.test(u)) return
        var s = navStack, i = navIndex
        if (i >= 0 && s[i] === u) return
        if (i > 0 && s[i - 1] === u) { navIndex = i - 1; return }
        if (i >= 0 && i < s.length - 1 && s[i + 1] === u) { navIndex = i + 1; return }
        s = s.slice(0, i + 1)
        s.push(u)
        if (s.length > 60) s = s.slice(s.length - 60)
        navStack = s
        navIndex = s.length - 1
    }
    function stepStack(d) {
        var i = navIndex + d
        if (i >= 0 && i < navStack.length) pane.navigate(navStack[i])
    }
    function histStep(d) {
        pane.run("location.href", function (before) {
            pane.run(d < 0 ? "history.back()" : "history.forward()")
            stepCheck.before = String(before)
            stepCheck.dir = d
            stepCheck.restart()
        })
    }
    Timer {      // the page history did not move (fresh view, or its start) -> use the own list
        id: stepCheck
        property string before: ""
        property int dir: -1
        interval: 900
        onTriggered: pane.run("location.href", function (now) {
            if (String(now) === stepCheck.before) pane.stepStack(stepCheck.dir)
        })
    }
    function goBack() {
        if (wv && wv.canGoBack) wv.goBack()
        else histStep(-1)
    }
    function goForward() {
        if (wv && wv.canGoForward) wv.goForward()
        else histStep(1)
    }
    Shortcut { sequence: "Alt+Left"; enabled: pane.visible && !pane.suspended; onActivated: pane.goBack() }
    Shortcut { sequence: "Alt+Right"; enabled: pane.visible && !pane.suspended; onActivated: pane.goForward() }
    Shortcut { sequence: "F5"; enabled: pane.visible && !pane.suspended; onActivated: pane.reload() }

    function publish(force) {
        if (!linkPattern.test(current))
            return
        var link = cleanLink(current)
        if (force !== true && link === lastPublished)
            return
        lastPublished = link
        pane.videoLink(link)
    }

    // YouTube switches videos without a page load, and the web view does not always report the new
    // address. So the address is read from the page once a second and a changed video is published.
    Timer {
        interval: 1000
        repeat: true
        running: pane.visible && !pane.suspended
        onTriggered: pane.run("location.href", function (result) {
            var href = result
            if (typeof href === "string" && href.charAt(0) === '"') {   // some backends return the JSON text
                try { href = JSON.parse(href) } catch (e) { return }
            }
            if (typeof href === "string" && href !== "" && href !== pane.live) {
                pane.live = href
                pane.track(href)
                if (/^https?:\/\/([\w-]+\.)?youtube\.com\//i.test(href)) pane.lastUrl = href   // for the fresh view after a dialog
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
            // canGoBack/canGoForward are not reliable for YouTube's in-page navigation (it changes the address
            // without a page load), so the buttons are always on and use the page's own history.
            IconButton { iconName: "chevronLeft"; tip: qsTr("Back (Alt+Left)")
                         onClicked: pane.goBack() }
            IconButton { iconName: "chevronRight"; tip: qsTr("Forward (Alt+Right)")
                         onClicked: pane.goForward() }
            IconButton { iconName: "retry"; tip: qsTr("Reload"); onClicked: pane.reload() }
            IconButton { iconName: "play"; tip: qsTr("YouTube start page"); onClicked: pane.navigate(pane.home) }
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
            onWidthChanged: pane.relayout()      // window resized / maximized: the native view can keep its old size
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
                    // set once at creation (not a binding: later lastUrl changes must not navigate again)
                    Component.onCompleted: url = pane.lastUrl !== "" ? pane.lastUrl : pane.home
                    onUrlChanged: { pane.live = ""; pane.lastUrl = url.toString(); pane.track(pane.lastUrl); pane.publish(false) }
                    onLoadingChanged: function (req) {
                        if (req.status === WebView.LoadSucceededStatus)
                            { pane.applyTheme(); pane.applyAdScript(); pane.applyMuteScript() }
                    }
                }
            }
            Rectangle {   // thin load indicator
                visible: !!pane.wv && pane.wv.loadProgress > 0 && pane.wv.loadProgress < 100
                height: 2
                width: pane.wv ? parent.width * pane.wv.loadProgress / 100 : 0
                color: Theme.accentFill
            }
        }
    }
}
