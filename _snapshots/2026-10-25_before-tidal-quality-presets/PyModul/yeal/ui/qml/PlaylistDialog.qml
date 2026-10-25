import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// A playlist link was added: list all entries as thumbnail tiles; the user ticks single / several / all and starts the download.
Popup {
    id: dlg
    objectName: "playlistDialog"
    property var queue: []          // pending {url, title, uploader, entries: [{index, title, duration, available}]}
    property var current: null
    property var sel: []            // selected flag per entry (copied on change so bindings update)
    property int count: 0
    property int lastClicked: -1

    function enqueue(info) {
        queue = queue.concat([info])
        if (!opened) next()
    }
    function next() {
        if (queue.length === 0) { current = null; close(); return }
        current = queue[0]
        queue = queue.slice(1)
        selectAll(true)
        lastClicked = -1
        open()
    }
    function recount(arr) {
        var n = 0
        for (var i = 0; i < arr.length; ++i) if (arr[i]) n++
        sel = arr
        count = n
    }
    function selectAll(on) {
        var arr = []
        var e = current ? current.entries : []
        for (var i = 0; i < e.length; ++i) arr.push(on && e[i].available)
        recount(arr)
    }
    function invert() {
        var arr = []
        var e = current ? current.entries : []
        for (var i = 0; i < e.length; ++i) arr.push(e[i].available && !sel[i])
        recount(arr)
    }
    function toggle(i, range) {      // Shift+click selects the range from the last clicked entry
        var arr = sel.slice()
        if (range && lastClicked >= 0) {
            var a = Math.min(lastClicked, i), b = Math.max(lastClicked, i), on = !arr[i]
            for (var k = a; k <= b; ++k) if (current.entries[k].available) arr[k] = on
        } else if (current.entries[i].available) {
            arr[i] = !arr[i]
        }
        lastClicked = i
        recount(arr)
    }
    function start() {
        if (!current || count === 0) return
        var picked = []
        for (var i = 0; i < sel.length; ++i) if (sel[i]) picked.push(current.entries[i].index)
        backend.confirmPlaylist(current.url, picked)
        next()
    }
    function cancel() {
        if (current) backend.confirmPlaylist(current.url, [])
        next()
    }
    function dur(s) {
        if (!s) return ""
        var h = Math.floor(s / 3600), m = Math.floor(s % 3600 / 60), x = s % 60
        return (h > 0 ? h + ":" + (m < 10 ? "0" : "") : "") + m + ":" + (x < 10 ? "0" : "") + x
    }

    modal: true
    focus: true
    parent: Overlay.overlay
    readonly property rect area: Theme.dialogArea.width > 0 ? Theme.dialogArea : Qt.rect(0, 0, Overlay.overlay ? Overlay.overlay.width : 0, Overlay.overlay ? Overlay.overlay.height : 0)
    x: area.x + (area.width - width) / 2
    y: area.y + (area.height - height) / 2
    width: Math.min(980, area.width - 2 * Theme.s4)
    height: Math.min(780, area.height - 2 * Theme.s4)
    padding: Theme.s4
    closePolicy: Popup.NoAutoClose
    Overlay.modal: Rectangle { color: Theme.dark ? "#99000000" : "#55000000" }
    background: Rectangle {
        radius: Theme.radiusCard + 4
        color: Theme.raised
        border.width: 1
        border.color: Theme.separator
    }
    Shortcut { sequence: "Escape"; enabled: dlg.opened; onActivated: dlg.cancel() }
    Shortcut { sequence: "Ctrl+A"; enabled: dlg.opened; onActivated: dlg.selectAll(true) }

    contentItem: ColumnLayout {
        spacing: Theme.s3

        Text {
            text: qsTr("Playlist")
            color: Theme.text
            font.pixelSize: Theme.title
            font.weight: Font.Medium
            Layout.fillWidth: true
        }
        Text {
            text: dlg.current ? dlg.current.title + (dlg.current.uploader ? "  ·  " + dlg.current.uploader : "") : ""
            color: Theme.textSecondary
            font.pixelSize: Theme.footnote
            elide: Text.ElideRight
            Layout.fillWidth: true
        }
        Text {
            text: qsTr("Choose what to download. Saved in the folder \"Playlists\\%1\" of your download folder.").arg(dlg.current ? dlg.current.title : "")
            color: Theme.textSecondary
            font.pixelSize: Theme.footnote
            wrapMode: Text.Wrap
            Layout.fillWidth: true
        }
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.s2
            AppButton { text: qsTr("Select all"); onClicked: dlg.selectAll(true) }
            AppButton { text: qsTr("Select none"); onClicked: dlg.selectAll(false) }
            AppButton { text: qsTr("Invert"); onClicked: dlg.invert() }
            Item { Layout.fillWidth: true }
            Text {
                text: qsTr("%1 of %2 selected").arg(dlg.count).arg(dlg.current ? dlg.current.entries.length : 0)
                color: Theme.text
                font.pixelSize: Theme.footnote
            }
        }
        GridView {
            id: list
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            readonly property int cols: Math.max(2, Math.floor(width / 190))
            cellWidth: Math.floor((width - 12) / cols)
            cellHeight: Math.round(cellWidth * 9 / 16) + 52
            model: dlg.current ? dlg.current.entries : []
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: ScrollBar {}
            delegate: Item {
                id: row
                required property var modelData
                required property int index
                readonly property bool on: dlg.sel[index] === true
                width: list.cellWidth
                height: list.cellHeight
                opacity: modelData.available ? 1 : 0.45
                Accessible.role: Accessible.CheckBox
                Accessible.name: modelData.title
                Accessible.checked: on
                Rectangle {              // the tile
                    anchors { fill: parent; margins: 4 }
                    radius: Theme.radius
                    color: tap.pressed ? Theme.pressed : hov.hovered ? Theme.hover : "transparent"
                    border.width: row.on ? 2 : 0
                    border.color: Theme.accentFill
                    HoverHandler { id: hov; cursorShape: Qt.PointingHandCursor }
                    TapHandler {
                        id: tap
                        onTapped: dlg.toggle(row.index, (Qt.application.keyboardModifiers & Qt.ShiftModifier) !== 0)
                    }
                    ColumnLayout {
                        anchors { fill: parent; margins: 4 }
                        spacing: 4
                        Rectangle {      // thumbnail 16:9
                            Layout.fillWidth: true
                            Layout.preferredHeight: Math.round(width * 9 / 16)
                            radius: Theme.radius - 2
                            color: Theme.surface
                            clip: true
                            Image {
                                anchors.fill: parent
                                source: row.modelData.thumbnail || ""
                                asynchronous: true
                                cache: true
                                fillMode: Image.PreserveAspectCrop
                                sourceSize.width: 320
                            }
                            Icon { anchors.centerIn: parent; size: 28; name: "film"; color: Theme.textTertiary; visible: !row.modelData.thumbnail }
                            Rectangle {  // check mark
                                x: 6; y: 6
                                implicitWidth: 22; implicitHeight: 22
                                width: 22; height: 22
                                radius: 6
                                color: row.on ? Theme.accentFill : "#99000000"
                                border.width: row.on ? 0 : 2
                                border.color: "white"
                                Icon { anchors.centerIn: parent; size: 14; strokeWidth: 2.5; name: "check"; visible: row.on; color: "white" }
                            }
                            Rectangle {  // number
                                anchors { right: parent.right; top: parent.top; margins: 6 }
                                width: numText.implicitWidth + 10; height: 18; radius: 5; color: "#99000000"
                                Text { id: numText; anchors.centerIn: parent; text: row.modelData.index; color: "white"; font.pixelSize: Theme.caption }
                            }
                            Rectangle {  // duration
                                visible: durText.text !== ""
                                anchors { right: parent.right; bottom: parent.bottom; margins: 6 }
                                width: durText.implicitWidth + 10; height: 18; radius: 5; color: "#cc000000"
                                Text { id: durText; anchors.centerIn: parent; color: "white"; font.pixelSize: Theme.caption
                                       text: row.modelData.available ? dlg.dur(row.modelData.duration) : qsTr("unavailable") }
                            }
                        }
                        Text {
                            text: row.modelData.title
                            color: Theme.text
                            font.pixelSize: Theme.footnote
                            wrapMode: Text.Wrap
                            maximumLineCount: 2
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                        }
                    }
                }
            }
        }
        Text {
            text: qsTr("Tip: click a tile to tick it, Shift+click selects a range, Ctrl+A selects all.")
            color: Theme.textTertiary
            font.pixelSize: Theme.footnote
            Layout.fillWidth: true
        }
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.s2
            Item { Layout.fillWidth: true }
            AppButton { text: qsTr("Cancel"); onClicked: dlg.cancel() }
            AppButton {
                text: dlg.count > 0 ? qsTr("Download %1").arg(dlg.count) : qsTr("Download")
                kind: "primary"
                enabled: dlg.count > 0
                onClicked: dlg.start()
            }
        }
    }
}
