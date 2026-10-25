import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// Downloads page. Windows: the YouTube view fills the page and the workflow panel sits in the sidebar
// (Main.qml moves it). Without a browser the panel is shown here.
Item {
    id: page
    property bool browserMode: false     // set by Main.qml
    property bool suspendWeb: false
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
                active: page.browserMode && page.browserReady
                source: "WebPane.qml"
                onLoaded: {
                    item.suspended = Qt.binding(function () { return page.suspendWeb })
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
