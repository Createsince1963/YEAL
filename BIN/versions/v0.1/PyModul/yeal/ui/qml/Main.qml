import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

ApplicationWindow {
    id: win
    width: 1060
    height: 720
    minimumWidth: 340
    minimumHeight: 520
    visible: true
    title: "Yeal"
    // window icon is set from Python (main.py)
    color: Theme.window

    property int page: 0

    Component.onCompleted: {
        var g = backend.settings.window
        if (g && g.w >= minimumWidth && g.h >= minimumHeight) {
            width = Math.min(g.w, Screen.desktopAvailableWidth)
            height = Math.min(g.h, Screen.desktopAvailableHeight)
            // restore the position only if it is still on a visible screen
            if (g.x > -width + 80 && g.y >= 0
                    && g.x < Screen.desktopAvailableWidth - 80 && g.y < Screen.desktopAvailableHeight - 80) {
                x = g.x; y = g.y
            }
            if (g.max) visibility = Window.Maximized
        }
    }
    onClosing: {
        // save the normal (non-maximized) geometry
        if (visibility === Window.Maximized) {
            var g = backend.settings.window || {}
            backend.saveWindow(g.x || x, g.y || y, g.w || width, g.h || height, true)
        } else {
            backend.saveWindow(x, y, width, height, false)
        }
    }
    readonly property var navItems: [
        { icon: "download", text: qsTr("Downloads"), badge: backend.stats.active + backend.stats.queued },
        { icon: "stack", text: qsTr("Profiles") },
        { icon: "sliders", text: qsTr("Settings") }
    ]

    Binding {
        target: Theme
        property: "dark"
        value: backend.settings.theme === "dark"
            || (backend.settings.theme === "system" && Qt.styleHints.colorScheme === Qt.ColorScheme.Dark)
    }
    Binding { target: Theme; property: "compact"; value: win.width < 720 }

    Connections {
        target: backend
        function onToast(message) { toast.show(message) }
    }

    // Windows with the YouTube view: our workflow lives in the (wider) sidebar, the page is the browser.
    readonly property bool browserMode: !Theme.compact && backend.browserAvailable && backend.settings.show_browser

    // one bar: navigation on top, our workflow below (Downloads page). Its width is the user's choice.
    readonly property bool panelInSidebar: browserMode && page === 0
    readonly property bool barRight: backend.settings.panel_right && panelInSidebar
    readonly property int barMax: Math.max(300, width - 360)
    Binding { target: Theme; property: "dialogArea"
              value: Qt.rect(pages.x, 0, pages.width, win.height) }
    readonly property int barWidth: !sidebarLoader.active ? 0
        : (panelInSidebar ? Math.min(barMax, Math.max(300, backend.settings.panel_width)) : 224)
    property real dragWidth: -1          // live value while the divider is dragged

    Loader {
        id: sidebarLoader
        active: !Theme.compact
        width: win.dragWidth > 0 ? win.dragWidth : win.barWidth
        x: win.barRight ? win.width - width : 0
        anchors { top: parent.top; bottom: parent.bottom }
        sourceComponent: Sidebar {
            items: win.navItems
            currentIndex: win.page
            onRight: win.barRight
            rowNav: win.browserMode
            onSelected: (i) => win.page = i
        }
    }

    Item {
        id: pages
        x: win.barRight ? 0 : sidebarLoader.width
        width: win.width - sidebarLoader.width
        anchors { top: parent.top; bottom: bottomLoader.top }
        readonly property alias currentIndex: stack.currentIndex
    StackLayout {
        id: stack
        anchors.fill: parent
        currentIndex: win.page

        DownloadsPage {
            id: downloads
            browserMode: win.browserMode
            suspendWeb: panel.overlayOpen
            onVideoLink: (url) => panel.browserLink(url)
        }
        ProfilesPage {
            onUseProfile: win.page = 0
            onToastRequest: (m) => toast.show(m)
        }
        SettingsPage {
            onToastRequest: (m) => toast.show(m)
        }
    }
    }

    // drag handle on the edge between the bar and the page
    Item {
        id: barHandle
        visible: win.panelInSidebar
        width: 8
        anchors { top: parent.top; bottom: parent.bottom }
        x: win.barRight ? sidebarLoader.x - width / 2 : sidebarLoader.width - width / 2
        z: 20
        Rectangle { anchors.fill: parent; color: Theme.accent; opacity: handleArea.pressed || handleHover.hovered ? 0.6 : 0 }
        HoverHandler { id: handleHover; cursorShape: Qt.SplitHCursor }
        MouseArea {
            id: handleArea
            anchors.fill: parent
            cursorShape: Qt.SplitHCursor
            onPositionChanged: (m) => {
                var edge = barHandle.mapToItem(win.contentItem, m.x, 0).x
                var w = win.barRight ? win.width - edge : edge
                win.dragWidth = Math.min(win.barMax, Math.max(300, Math.round(w)))
            }
            onReleased: {
                if (win.dragWidth > 0) backend.setSetting("panel_width", win.dragWidth)
                win.dragWidth = -1
            }
        }
    }

    // one workflow panel for the whole app; only its parent changes
    WorkflowPanel {
        id: panel
        objectName: "workflowPanel"
        inSidebar: win.browserMode
        parent: win.panelInSidebar && sidebarLoader.item ? sidebarLoader.item.slot : downloads.slot
        anchors.fill: parent
        visible: win.page === 0
        onManageProfiles: win.page = 1
    }

    Loader {
        id: bottomLoader
        active: Theme.compact
        height: active ? 58 : 0
        anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
        sourceComponent: BottomBar {
            items: win.navItems
            currentIndex: win.page
            onSelected: (i) => win.page = i
        }
    }

    Toast {
        id: toast
        anchors.horizontalCenter: pages.horizontalCenter
        anchors.bottom: pages.bottom
        anchors.bottomMargin: Theme.s5
        z: 10
    }

    Splash {
        anchors.fill: parent
        z: 100
        onFinished: destroy()
    }

    Shortcut { sequence: "Ctrl+1"; onActivated: win.page = 0 }
    Shortcut { sequence: "Ctrl+2"; onActivated: win.page = 1 }
    Shortcut { sequence: "Ctrl+3"; onActivated: win.page = 2 }
    Shortcut { sequence: "Ctrl+L"; onActivated: { win.page = 0; panel.focusInput() } }
}
