import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// TIDAL DIY: Yeal's own TIDAL view (0.9.1). Created on first use by DownloadsPage.qml, then kept alive.
// Not signed in -> sign-in prompt with the subscription notice.
Item {
    id: home
    signal videoLink(string url)
    function pausePlayback() {}

    Rectangle {
        anchors.fill: parent
        radius: Theme.radius
        color: Theme.surface
        border.width: 1
        border.color: Theme.separator
    }
    EmptyState {
        anchors.centerIn: parent
        width: Math.min(parent.width - 2 * Theme.s6, 520)
        iconName: "music"
        title: backend.tidalLoggedIn ? qsTr("TIDAL DIY") : qsTr("Sign in to TIDAL")
        subtitle: backend.tidalLoggedIn ? qsTr("Yeal's own TIDAL view is being built.") : backend.tidalNotice
        actionText: backend.tidalLoggedIn ? "" : qsTr("Sign in to TIDAL")
        onAction: {
            var err = backend.tidalLogin()
            if (err) backend.notify(err)
        }
    }
}
