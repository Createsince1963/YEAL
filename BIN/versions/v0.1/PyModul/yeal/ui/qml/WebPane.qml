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

    property string live: ""           // address read from the page itself (see the poll timer)
    property string lastPublished: ""
    readonly property string current: live !== "" ? live : web.url.toString()
    readonly property var linkPattern: /^https?:\/\/((www|m|music)\.)?(youtube\.com\/(watch|shorts|playlist|live)|youtu\.be\/)/i

    // Follow the app theme: YouTube keeps its theme in the PREF cookie (f6 = 400 dark). The cookie is
    // merged (other YouTube settings stay) and the page is reloaded once when the value changed.
    readonly property bool dark: Theme.dark
    function applyTheme() {
        if (!/^https?:\/\/([\w-]+\.)?youtube\.com\//i.test(current))
            return
        web.runJavaScript("(function(dark){var m=document.cookie.match(/(?:^|; )PREF=([^;]*)/);"
            + "var parts=m?m[1].split('&').filter(function(x){return x&&x.indexOf('f6=')!==0}):[];"
            + "var old=m?(m[1].split('&').filter(function(x){return x.indexOf('f6=')===0})[0]||''):'';"
            + "var want=dark?'f6=400':'f6=80000';if(old===want)return;parts.push(want);"
            + "document.cookie='PREF='+parts.join('&')+'; domain=.youtube.com; path=/; max-age=31536000; secure';"
            + "location.reload()})(" + (dark ? "true" : "false") + ")")
    }
    onDarkChanged: applyTheme()

    // Video ads: hide ad slots, press "Skip", and jump to the end of an ad that cannot be skipped.
    // (Blocking the ad domains alone does not help: YouTube serves its own ads from its own servers.)
    function applyAdScript() {
        if (!backend.settings.adblock_experimental || !/^https?:\/\/([\w-]+\.)?youtube\.com\//i.test(current))
            return
        web.runJavaScript("(function(){if(window.__yealAds)return;window.__yealAds=1;"
            + "var s=document.createElement('style');s.textContent='ytd-ad-slot-renderer,#player-ads,"
            + "ytd-banner-promo-renderer,ytd-statement-banner-renderer,ytd-in-feed-ad-layout-renderer,"
            + ".ytp-ad-overlay-container,ytd-promoted-sparkles-web-renderer,#masthead-ad{display:none!important}';"
            + "document.documentElement.appendChild(s);"
            + "setInterval(function(){var p=document.querySelector('.html5-video-player');"
            + "if(!p||!p.classList.contains('ad-showing'))return;"
            + "var b=document.querySelector('.ytp-skip-ad-button,.ytp-ad-skip-button-modern,.ytp-ad-skip-button');"
            + "if(b){b.click();return}"
            + "var v=p.querySelector('video');if(v&&isFinite(v.duration)&&v.duration>0){v.muted=true;v.currentTime=v.duration}"
            + "},400)})()")
    }

    // Clean link of the page: a watch page keeps only the video id (no mix/radio list, time stamp, tracking).
    function cleanLink(u) {
        var m = /^https?:\/\/(?:www\.|m\.|music\.)?youtube\.com\/watch\?(?:.*&)?v=([\w-]{6,})/i.exec(u)
        return m ? "https://www.youtube.com/watch?v=" + m[1] : u
    }
    function goBack() {
        if (web.canGoBack) web.goBack()
        else web.runJavaScript("history.back()")
    }
    function goForward() {
        if (web.canGoForward) web.goForward()
        else web.runJavaScript("history.forward()")
    }
    Shortcut { sequence: "Alt+Left"; enabled: pane.visible && !pane.suspended; onActivated: pane.goBack() }
    Shortcut { sequence: "Alt+Right"; enabled: pane.visible && !pane.suspended; onActivated: pane.goForward() }
    Shortcut { sequence: "F5"; enabled: pane.visible && !pane.suspended; onActivated: web.reload() }

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
        onTriggered: web.runJavaScript("location.href", function (result) {
            var href = result
            if (typeof href === "string" && href.charAt(0) === '"') {   // some backends return the JSON text
                try { href = JSON.parse(href) } catch (e) { return }
            }
            if (typeof href === "string" && href !== "" && href !== pane.live) {
                pane.live = href
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
            IconButton { iconName: "chevronRight"; tip: qsTr("Back (Alt+Left)"); rotation: 180
                         onClicked: pane.goBack() }
            IconButton { iconName: "chevronRight"; tip: qsTr("Forward (Alt+Right)")
                         onClicked: pane.goForward() }
            IconButton { iconName: "retry"; tip: qsTr("Reload"); onClicked: web.reload() }
            IconButton { iconName: "play"; tip: qsTr("YouTube start page"); onClicked: web.url = pane.home }
            Text {
                text: web.title !== "" ? web.title : pane.current
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
            WebView {
                id: web
                anchors.fill: parent
                anchors.margins: 1
                url: pane.home
                visible: !pane.suspended
                onUrlChanged: { pane.live = ""; pane.publish(false) }
                onLoadingChanged: function (req) {
                    if (req.status === WebView.LoadSucceededStatus)
                        { pane.applyTheme(); pane.applyAdScript() }
                }
            }
            Rectangle {   // thin load indicator
                visible: web.loadProgress > 0 && web.loadProgress < 100
                height: 2
                width: parent.width * web.loadProgress / 100
                color: Theme.accentFill
            }
        }
    }
}
