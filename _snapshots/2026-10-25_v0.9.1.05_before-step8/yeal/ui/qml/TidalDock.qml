import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import QtQuick.Window

// One side area of the TIDAL DIY view (playlists, queue). Docked it is a column of the SplitView in TidalHome; it
// can be moved to the other side, detached into its own window (frame follows the user: position and size are
// reported) or hidden. Closing the own window docks the area again. The content is declared as children.
Item {
    id: dock
    property string paneKey: ""
    property string title: ""
    property string side: "left"          // left | right | float | hidden
    property string defaultSide: "left"   // where the area goes when its own window is closed
    property int paneWidth: 220
    property int minW: 140
    property int maxW: 520
    property var floatRect: ({ x: 100, y: 100, w: 360, h: 600 })
    default property alias content: body.data
    readonly property bool docked: side === "left" || side === "right"
    signal sideRequested(string side)
    signal floatMoved(int x, int y, int w, int h)

    visible: docked
    SplitView.preferredWidth: paneWidth
    SplitView.minimumWidth: minW
    SplitView.maximumWidth: maxW

    // the frame lives in the dock, or in the own window while detached
    Rectangle {
        id: frame
        parent: dock.side === "float" ? win.contentItem : dock
        anchors.fill: parent
        radius: dock.side === "float" ? 0 : Theme.radius
        color: Theme.surface
        border.width: dock.side === "float" ? 0 : 1
        border.color: Theme.separator

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: Theme.s2
            spacing: Theme.s1
            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.s1
                Text {
                    text: dock.title
                    color: Theme.textSecondary
                    font.pixelSize: Theme.caption
                    font.letterSpacing: 0.4
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
                IconButton {
                    implicitWidth: 26; implicitHeight: 26
                    iconName: "dock"
                    tip: qsTr("Move or detach this area")
                    onClicked: menu.popup()
                }
            }
            Item { id: body; Layout.fillWidth: true; Layout.fillHeight: true }
        }
        TapHandler { acceptedButtons: Qt.RightButton; onTapped: menu.popup() }
    }

    AppMenu {
        id: menu
        AppMenuItem { text: qsTr("Dock on the left"); iconName: "dock"; enabled: dock.side !== "left"
                      onTriggered: dock.sideRequested("left") }
        AppMenuItem { text: qsTr("Dock on the right"); iconName: "dock"; enabled: dock.side !== "right"
                      onTriggered: dock.sideRequested("right") }
        AppMenuItem { text: qsTr("Detach into its own window"); iconName: "open"; enabled: dock.side !== "float"
                      onTriggered: dock.sideRequested("float") }
        AppMenuItem { text: qsTr("Hide"); iconName: "x"; onTriggered: dock.sideRequested("hidden") }
    }

    Window {
        id: win
        property bool placing: false
        visible: dock.side === "float"
        title: "TIDAL – " + dock.title
        color: Theme.surface
        transientParent: dock.Window.window
        minimumWidth: 200
        minimumHeight: 200
        onClosing: dock.sideRequested(dock.defaultSide)
        onVisibleChanged: if (visible) place()
        onXChanged: report()
        onYChanged: report()
        onWidthChanged: report()
        onHeightChanged: report()

        function report() {
            if (visible && !placing) dock.floatMoved(x, y, width, height)
        }
        // A window that was left on a screen that is gone is brought back to the main screen.
        function visibleOnAScreen(px, py) {
            var screens = Qt.application.screens
            for (var i = 0; i < screens.length; ++i) {
                var s = screens[i]
                if (px + 60 > s.virtualX && px < s.virtualX + s.width - 60 && py >= s.virtualY && py < s.virtualY + s.height - 60)
                    return true
            }
            return false
        }
        function place() {
            placing = true
            var r = dock.floatRect
            var px = r.x, py = r.y
            if (!visibleOnAScreen(px, py)) {
                var s0 = Qt.application.screens.length ? Qt.application.screens[0] : null
                px = s0 ? s0.virtualX + 100 : 100
                py = s0 ? s0.virtualY + 100 : 100
            }
            width = Math.max(200, r.w)
            height = Math.max(200, r.h)
            x = px
            y = py
            placing = false
        }
    }
}
