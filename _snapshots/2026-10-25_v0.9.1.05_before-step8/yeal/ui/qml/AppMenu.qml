import QtQuick
import QtQuick.Controls.Basic

// Popup menu in Yeal's style. Its width follows the widest entry (at least 200 px, at most the window width),
// so long entries such as "Tidal Max (FLAC up to 24-bit / 192 kHz)" are never cut off.
Menu {
    id: menu
    padding: 3
    function fitWidth() {
        var w = 200
        for (var i = 0; i < count; ++i) {
            var it = itemAt(i)
            if (it && it.implicitWidth > w) w = it.implicitWidth
        }
        var room = Overlay.overlay ? Overlay.overlay.width - 16 : w
        width = Math.min(room, w + leftPadding + rightPadding)
    }
    onAboutToShow: fitWidth()
    background: Rectangle {
        implicitWidth: 200
        radius: Theme.radius + 2
        color: Theme.raised
        border.width: 1
        border.color: Theme.separator
    }
}
