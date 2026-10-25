import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// Downloads page. Windows: the YouTube view fills the page and the workflow panel sits in the sidebar
// (Main.qml moves it). Without a browser the panel is shown here.
Item {
    id: page
    property bool browserMode: false     // set by Main.qml
    property bool suspendWeb: false
    property string player: "youtube"    // "youtube" | "tidal"; set by Main.qml
    property bool tidalWanted: false     // TIDAL view is created on first use, then kept alive
    property string leftPlayer: "youtube"
    // Switching players: the one that is left is paused (not reloaded), so the two never play together.
    function pausePlayer(which) {
        var l = which === "tidal" ? tidalLoader : webLoader
        if (l.item && backend.settings.single_playback)
            l.item.run("document.querySelectorAll('audio,video').forEach(function(m){m.pause()})")
    }
    onPlayerChanged: {
        if (player === "tidal") tidalWanted = true
        pausePlayer(leftPlayer)
        leftPlayer = player
    }
    property bool browserReady: false
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
                    item.videoLink.connect(function (url) { page.videoLink(url) })
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
