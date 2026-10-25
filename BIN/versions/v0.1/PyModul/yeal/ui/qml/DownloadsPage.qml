import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// Downloads page. Windows: the YouTube view fills the page and the workflow panel sits in the sidebar
// (Main.qml moves it). Without a browser the panel is shown here.
Item {
    id: page
    property bool browserMode: false     // set by Main.qml
    property bool suspendWeb: false
    property string player: "youtube"    // "youtube" | "tidal" (TIDAL Web) | "tidaldiy" (own view); set by Main.qml
    property bool tidalWanted: false     // TIDAL Web view is created on first use, then kept alive
    property bool tidalDiyWanted: false  // same for the own TIDAL view
    property string leftPlayer: "youtube"
    // Switching players: the one that is left is paused (not reloaded), so two never play together.
    function pausePlayer(which) {
        if (!backend.settings.single_playback) return
        if (which === "tidaldiy") {
            if (tidalDiyLoader.item) tidalDiyLoader.item.pausePlayback()
            return
        }
        var l = which === "tidal" ? tidalLoader : webLoader
        if (l.item) l.item.run("document.querySelectorAll('audio,video').forEach(function(m){m.pause()})")
    }
    onPlayerChanged: {
        if (player === "tidal") tidalWanted = true
        if (player === "tidaldiy") tidalDiyWanted = true
        pausePlayer(leftPlayer)
        leftPlayer = player
    }
    signal playerRequested(string which)
    // Show a TIDAL link in the TIDAL Web view (e.g. from the TIDAL DIY context menu)
    function openTidalWeb(url) {
        tidalWanted = true
        playerRequested("tidal")
        if (tidalLoader.item) tidalLoader.item.navigate(url)
        else pendingLogin = url
    }
    property bool browserReady: false
    // Tidal download login: tiddl prints a device-login link; it is shown in the embedded TIDAL view, where the
    // user signs in / confirms. tiddl notices the confirmation by itself, Yeal never touches the Tidal session.
    property string pendingLogin: ""
    property bool tidalLoginOpen: false
    function openTidalLogin(url) {
        tidalLoginOpen = true
        tidalWanted = true
        if (tidalLoader.item) tidalLoader.item.navigate(url)
        else pendingLogin = url              // view is created first, then opens the link (see onLoaded)
    }
    function closeTidalLogin() {
        if (!tidalLoginOpen) return
        tidalLoginOpen = false
        pendingLogin = ""
        if (tidalLoader.item) tidalLoader.item.navigate(tidalLoader.item.home)
    }
    readonly property alias slot: inlineSlot
    signal videoLink(string url)

    Timer { interval: 1600; running: true; onTriggered: page.browserReady = true }   // after the splash

    Item { id: inlineSlot; anchors.fill: parent; visible: !page.browserMode }

    // Windows: the page is the YouTube view; our workflow sits in the sidebar (Main.qml).
    Item {
        id: webPane
        anchors.fill: parent
        visible: page.browserMode
        Item {
            anchors.fill: parent
            Loader {
                id: webLoader
                anchors.fill: parent
                anchors.margins: Theme.s3
                visible: page.player === "youtube"
                active: page.browserMode && page.browserReady
                source: "WebPane.qml"
                onLoaded: {
                    item.suspended = Qt.binding(function () { return page.suspendWeb || page.player !== "youtube" })
                    item.videoLink.connect(function (url) { page.videoLink(url) })
                }
            }
            Loader {
                id: tidalLoader
                anchors.fill: parent
                anchors.margins: Theme.s3
                visible: page.player === "tidal"
                active: page.browserMode && page.browserReady && page.tidalWanted
                source: "TidalPane.qml"
                onLoaded: {
                    item.suspended = Qt.binding(function () { return page.suspendWeb || page.player !== "tidal" })
                    if (page.pendingLogin !== "") { item.navigate(page.pendingLogin); page.pendingLogin = "" }
                    item.videoLink.connect(function (url) { page.videoLink(url) })
                }
            }
            Loader {
                id: tidalDiyLoader
                anchors.fill: parent
                anchors.margins: Theme.s3
                visible: page.player === "tidaldiy"
                active: page.browserMode && page.browserReady && page.tidalDiyWanted
                source: "TidalHome.qml"
                onLoaded: {
                    item.videoLink.connect(function (url) { page.videoLink(url) })
                    item.webRequested.connect(function (url) { page.openTidalWeb(url) })
                }
            }
            Text {
                visible: page.browserMode && webLoader.status === Loader.Error
                anchors.centerIn: parent
                width: parent.width - 2 * Theme.s6
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.Wrap
                color: Theme.textSecondary
                font.pixelSize: Theme.footnote
                text: qsTr("The browser view is not available on this PC (Microsoft Edge WebView2 is missing). You can still paste links.")
            }
        }
    }
}
