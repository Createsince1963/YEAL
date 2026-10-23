import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// Image extractor workflow: pick a video tile on the left (drag it onto the extractor, or click it),
// choose the range on the film strip (red frame) and the interval, create the images.
// Own folder per video under <downloads>/Frames. Intervals below 1 s are for Shorts only.
Popup {
    id: dlg
    objectName: "framesDialog"
    property string videoPath: ""
    property string videoTitle: ""
    property string errorText: ""
    property string previewError: ""
    property string resultText: ""
    property string resultFolder: ""
    property string format: "png"
    property real duration: 0
    property var stripUrls: []
    property bool loading: false
    property bool dragOver: false
    readonly property bool wide: width >= 760
    readonly property bool isShort: duration > 0 && duration <= 180
    readonly property var intervals: ["0.1", "0.5", "1", "2", "5", "10", "30", "60"]

    function fmt(sec) {
        var s = Math.round(sec), h = Math.floor(s / 3600), m = Math.floor(s % 3600 / 60), r = s % 60
        var mm = (h > 0 && m < 10 ? "0" : "") + m
        return (h > 0 ? h + ":" : "") + mm + ":" + (r < 10 ? "0" : "") + r
    }
    function parse(text) {
        var t = text.trim().replace(",", ".")
        if (t === "") return NaN
        var parts = t.split(":"), v = 0
        for (var i = 0; i < parts.length; ++i) {
            var n = Number(parts[i])
            if (isNaN(n)) return NaN
            v = v * 60 + n
        }
        return v
    }
    function syncFields() {
        fromField.text = fmt(strip.startSec)
        toField.text = fmt(strip.endSec)
    }
    function reload() {
        library.clear()
        var items = backend.libraryVideos()
        for (var i = 0; i < items.length; ++i) library.append(items[i])
    }
    // Videos dropped from any folder (Explorer): add a tile and load the first usable one.
    function addDropped(urls) {
        var first = ""
        for (var i = 0; i < urls.length; ++i) {
            var it = backend.addExternalVideo(urls[i].toString())
            if (!it.path) continue
            var found = false
            for (var j = 0; j < library.count; ++j)
                if (library.get(j).path === it.path) { found = true; break }
            if (!found) library.insert(0, it)
            if (first === "") first = it.path
        }
        if (first !== "") loadVideo(first)
        else errorText = qsTr("This is not a video file (mp4, mkv, webm, mov, m4v, avi).")
    }
    function openEmpty() {
        videoPath = ""
        duration = 0
        errorText = ""
        reload()
        open()
    }
    function openForJob(id) {
        reload()
        loadVideo(backend.jobVideoPath(id))
        open()
    }
    function loadVideo(path) {
        if (!path) return
        var title = path.replace(/^.*[\\\/]/, "").replace(/\.[^.]+$/, "")
        videoPath = path
        videoTitle = title
        errorText = ""
        resultText = ""
        resultFolder = ""
        previewError = ""
        duration = 0
        stripUrls = []
        loading = true
        stepField.text = "5"
        fromField.text = ""
        toField.text = ""
        backend.loadFilmstrip(path)
    }
    function setInterval(v) {
        if (Number(v) < 1 && !isShort) return
        stepField.text = v
    }
    function start() {
        errorText = backend.extractFrames(videoPath, fromField.text, dlg.duration > 0 && toField.text === fmt(dlg.duration) ? "" : toField.text,
                                          stepField.text, format)
        // the dialog stays open: the user closes it; the result is shown in the footer
        resultText = ""
        resultFolder = ""
    }
    readonly property real stepValue: { var v = Number(stepField.text.replace(",", ".")); return isNaN(v) ? 0 : v }
    readonly property int imageCount: stepValue > 0 && duration > 0
        ? Math.floor((strip.endSec - strip.startSec) / stepValue) + 1 : 0

    Connections {
        target: backend
        function onFilmstripReady(path, seconds, urls, error) {
            if (path !== dlg.videoPath) return
            dlg.loading = false
            dlg.duration = seconds
            dlg.previewError = error
            dlg.stripUrls = urls
            strip.startSec = 0
            strip.endSec = seconds
            // shorts: default 1 s, everything else 5 s
            stepField.text = (seconds > 0 && seconds <= 180) ? "1" : "5"
            dlg.syncFields()
        }
        function onFramesDone(count, folder, error) {
            if (error !== "") { dlg.errorText = error; dlg.resultText = ""; return }
            dlg.errorText = ""
            dlg.resultFolder = folder
            dlg.resultText = count > 0 ? qsTr("%1 images saved to: %2").arg(count).arg(folder)
                                       : qsTr("No images were created - check the time range.")
        }
        function onLibraryThumb(path, url) {
            for (var i = 0; i < library.count; ++i)
                if (library.get(i).path === path) { library.setProperty(i, "thumb", url); break }
        }
    }

    ListModel { id: library }

    modal: true
    focus: true
    parent: Overlay.overlay
    anchors.centerIn: parent
    width: Math.min(1040, parent.width - 2 * Theme.s4)
    height: Math.min(700, parent.height - 2 * Theme.s4)
    padding: Theme.s4
    closePolicy: Popup.CloseOnEscape
    Overlay.modal: Rectangle { color: Theme.dark ? "#99000000" : "#55000000" }
    background: Rectangle {
        radius: Theme.radiusCard + 4
        color: Theme.raised
        border.width: 1
        border.color: Theme.separator
    }

    contentItem: Item {
        id: root

        // files dragged in from Explorer (any folder); images still go to the app's Frames folder
        DropArea {
            anchors.fill: parent
            keys: ["text/uri-list"]
            onEntered: (drag) => { dlg.dragOver = drag.hasUrls }
            onExited: dlg.dragOver = false
            onDropped: (drop) => { dlg.dragOver = false; if (drop.hasUrls) dlg.addDropped(drop.urls) }
        }

        // ---- header
        RowLayout {
            id: header
            anchors { left: parent.left; right: parent.right; top: parent.top }
            Text {
                text: qsTr("Split video into images")
                font.pixelSize: Theme.title
                font.weight: Font.DemiBold
                color: Theme.text
                Layout.fillWidth: true
                Accessible.role: Accessible.Heading
            }
            IconButton { iconName: "x"; tip: qsTr("Close"); onClicked: dlg.close() }
        }

        // ---- video tiles
        Rectangle {
            id: libPane
            anchors {
                left: parent.left; top: header.bottom; topMargin: Theme.s2
                bottom: dlg.wide ? parent.bottom : undefined
            }
            width: dlg.wide ? 340 : parent.width
            height: dlg.wide ? undefined : 150
            radius: Theme.radiusCard
            color: Theme.surface
            border.width: 1
            border.color: Theme.separator

            RowLayout {
                id: libHead
                anchors { left: parent.left; right: parent.right; top: parent.top; margins: Theme.s3 }
                Text {
                    text: qsTr("Your videos")
                    font.pixelSize: Theme.footnote
                    font.weight: Font.DemiBold
                    color: Theme.textSecondary
                    Layout.fillWidth: true
                }
                Text {
                    text: qsTr("Drag a tile – or a file from any folder")
                    visible: dlg.wide
                    font.pixelSize: Theme.caption
                    color: Theme.textTertiary
                }
                IconButton { iconName: "retry"; tip: qsTr("Refresh"); implicitWidth: 28; implicitHeight: 28; onClicked: dlg.reload() }
            }
            GridView {
                id: tiles
                anchors { left: parent.left; right: parent.right; top: libHead.bottom; bottom: parent.bottom; margins: Theme.s2 }
                clip: true
                model: library
                flow: dlg.wide ? GridView.FlowLeftToRight : GridView.FlowTopToBottom
                cellWidth: dlg.wide ? Math.floor(width / 2) : 150
                cellHeight: dlg.wide ? 138 : height
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: ScrollBar { policy: dlg.wide ? ScrollBar.AsNeeded : ScrollBar.AlwaysOff }
                ScrollBar.horizontal: ScrollBar { policy: dlg.wide ? ScrollBar.AlwaysOff : ScrollBar.AsNeeded }
                delegate: Item {
                    id: cell
                    required property string path
                    required property string title
                    required property string size
                    required property string thumb
                    width: tiles.cellWidth
                    height: tiles.cellHeight
                    readonly property bool selected: dlg.videoPath === path

                    Rectangle {
                        anchors.fill: parent
                        anchors.margins: Theme.s1
                        radius: Theme.radius
                        color: tileMouse.containsMouse ? Theme.hover : "transparent"
                        border.width: cell.selected || cell.activeFocus ? 2 : 0
                        border.color: Theme.accent

                        Thumb {
                            id: tileThumb
                            anchors { left: parent.left; right: parent.right; top: parent.top; margins: Theme.s1 + 2 }
                            height: Math.round(width * 9 / 16)
                            source: cell.thumb
                        }
                        Text {
                            anchors { left: parent.left; right: parent.right; top: tileThumb.bottom; margins: Theme.s1 + 2; topMargin: Theme.s1 }
                            text: cell.title
                            font.pixelSize: Theme.caption
                            color: Theme.text
                            wrapMode: Text.Wrap
                            elide: Text.ElideRight
                            maximumLineCount: 2
                        }
                        Text {
                            anchors { right: tileThumb.right; bottom: tileThumb.bottom; margins: 4 }
                            text: cell.size
                            font.pixelSize: 11
                            color: "#FFFFFF"
                            style: Text.Outline
                            styleColor: "#99000000"
                        }
                    }
                    activeFocusOnTab: true
                    Keys.onReturnPressed: dlg.loadVideo(cell.path)
                    Accessible.role: Accessible.Button
                    Accessible.name: cell.title

                    MouseArea {
                        id: tileMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.OpenHandCursor
                        property bool dragging: false
                        property point press
                        onPressed: (e) => { press = Qt.point(e.x, e.y); dragging = false }
                        onPositionChanged: (e) => {
                            if (!pressed) return
                            if (!dragging && Math.hypot(e.x - press.x, e.y - press.y) > 8) {
                                dragging = true
                                ghost.source = cell.thumb
                                ghost.label = cell.title
                                ghost.visible = true
                            }
                            if (dragging) {
                                var p = tileMouse.mapToItem(root, e.x, e.y)
                                ghost.x = p.x - ghost.width / 2
                                ghost.y = p.y - ghost.height / 2
                                var q = root.mapToItem(extractor, p.x, p.y)
                                dlg.dragOver = q.x >= 0 && q.y >= 0 && q.x <= extractor.width && q.y <= extractor.height
                            }
                        }
                        onReleased: {
                            if (!dragging) dlg.loadVideo(cell.path)           // simple click also works
                            else if (dlg.dragOver) dlg.loadVideo(cell.path)   // dropped on the extractor
                            dragging = false
                            ghost.visible = false
                            dlg.dragOver = false
                        }
                    }
                }
            }
            EmptyState {
                visible: library.count === 0
                anchors.centerIn: parent
                iconName: "film"
                title: qsTr("No videos yet")
                subtitle: qsTr("Downloaded videos appear here.")
            }
        }

        // ---- extractor
        Rectangle {
            id: extractor
            anchors {
                left: dlg.wide ? libPane.right : parent.left
                leftMargin: dlg.wide ? Theme.s3 : 0
                right: parent.right; bottom: parent.bottom
                top: dlg.wide ? libPane.top : libPane.bottom
                topMargin: dlg.wide ? 0 : Theme.s3
            }
            radius: Theme.radiusCard
            color: dlg.dragOver ? Theme.accentSoft : Theme.surface
            border.width: dlg.dragOver || dlg.videoPath === "" ? 2 : 1
            border.color: dlg.dragOver ? Theme.accent : Theme.separator
            Accessible.name: qsTr("Extractor")

            // empty state: drop zone
            ColumnLayout {
                visible: dlg.videoPath === ""
                anchors.centerIn: parent
                spacing: Theme.s2
                Icon { name: "grid"; size: 40; color: dlg.dragOver ? Theme.accent : Theme.textTertiary; Layout.alignment: Qt.AlignHCenter }
                Text {
                    text: dlg.dragOver ? qsTr("Drop the video here") : qsTr("Drag a video here")
                    font.pixelSize: Theme.headline
                    font.weight: Font.DemiBold
                    color: Theme.text
                    Layout.alignment: Qt.AlignHCenter
                }
                Text {
                    text: qsTr("Drop a video tile here – or drag a video file from any folder into this window. Images are always saved in the Frames folder of your download folder.")
                    font.pixelSize: Theme.footnote
                    color: Theme.textSecondary
                    wrapMode: Text.Wrap
                    horizontalAlignment: Text.AlignHCenter
                    Layout.preferredWidth: 300
                    Layout.alignment: Qt.AlignHCenter
                }
            }

            // fixed footer: error + actions stay visible while the settings scroll
            ColumnLayout {
                id: footer
                visible: dlg.videoPath !== "" || dlg.errorText !== ""
                anchors { left: parent.left; right: parent.right; bottom: parent.bottom; margins: Theme.s3 }
                spacing: Theme.s2
                Text {
                    visible: dlg.resultText !== ""
                    text: dlg.resultText
                    color: Theme.success
                    font.pixelSize: Theme.footnote
                    wrapMode: Text.WrapAnywhere
                    Layout.fillWidth: true
                }
                Text {
                    visible: dlg.errorText !== ""
                    text: dlg.errorText
                    color: Theme.danger
                    font.pixelSize: Theme.footnote
                    wrapMode: Text.Wrap
                    Layout.fillWidth: true
                }
                RowLayout {
                    visible: dlg.videoPath !== ""
                    spacing: Theme.s2
                    Layout.fillWidth: true
                    Item { Layout.fillWidth: true }
                    AppButton { visible: dlg.resultFolder !== "" && dlg.resultText !== ""
                                text: qsTr("Open folder"); iconName: "folder"
                                onClicked: backend.openFolder(dlg.resultFolder) }
                    AppButton { text: qsTr("Close"); onClicked: dlg.close() }
                    AppButton { text: backend.framesBusy ? qsTr("Working…") : qsTr("Create images")
                                kind: "primary"; enabled: !backend.framesBusy; onClicked: dlg.start() }
                }
            }

            Flickable {
                id: scroller
                visible: dlg.videoPath !== ""
                anchors { left: parent.left; right: parent.right; top: parent.top; bottom: footer.top
                          margins: Theme.s3; bottomMargin: Theme.s2 }
                contentHeight: content.implicitHeight
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

                ColumnLayout {
                    id: content
                    width: scroller.width - 8
                    spacing: Theme.s3

                    Text {
                        text: dlg.videoTitle
                        font.pixelSize: Theme.body
                        font.weight: Font.DemiBold
                        color: Theme.text
                        elide: Text.ElideRight
                        maximumLineCount: 2
                        wrapMode: Text.Wrap
                        Layout.fillWidth: true
                    }

                    Loader {
                        id: previewLoader
                        active: dlg.opened && dlg.duration > 0
                        source: "VideoPreview.qml"
                        Layout.fillWidth: true
                        Layout.preferredHeight: status === Loader.Ready ? Math.min(width * 9 / 16, 200) : 0
                        visible: status === Loader.Ready
                        onLoaded: {
                            item.source = backend.videoUrl(dlg.videoPath)
                            item.startSec = Qt.binding(() => strip.startSec)
                            item.endSec = Qt.binding(() => strip.endSec)
                        }
                    }
                    RowLayout {
                        visible: previewLoader.status === Loader.Ready
                        Layout.fillWidth: true
                        AppButton {
                            text: previewLoader.item && previewLoader.item.playing ? qsTr("Pause") : qsTr("Play selection")
                            iconName: previewLoader.item && previewLoader.item.playing ? "pause" : "play"
                            kind: "secondary"
                            onClicked: previewLoader.item.toggle()
                        }
                        Item { Layout.fillWidth: true }
                    }

                    Item {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 72
                        FilmStrip {
                            id: strip
                            anchors.fill: parent
                            visible: dlg.duration > 0
                            duration: dlg.duration
                            urls: dlg.stripUrls
                            onScrubbed: (sec) => { if (previewLoader.item) previewLoader.item.seek(sec) }
                            onEdited: dlg.syncFields()
                        }
                        Text {
                            anchors.centerIn: parent
                            visible: dlg.duration <= 0
                            horizontalAlignment: Text.AlignHCenter
                            text: dlg.loading ? qsTr("Creating preview…")
                                              : qsTr("Preview not available - enter the times below.") + (dlg.previewError ? "\n" + dlg.previewError : "")
                            color: Theme.textSecondary
                            font.pixelSize: Theme.footnote
                        }
                    }
                    Text {
                        visible: dlg.duration > 0
                        text: qsTr("Drag the red handles to choose the range. Selection: %1 – %2 (%3)")
                              .arg(fmt(strip.startSec)).arg(fmt(strip.endSec)).arg(fmt(strip.endSec - strip.startSec))
                        color: Theme.textSecondary
                        font.pixelSize: Theme.caption
                        wrapMode: Text.Wrap
                        Layout.fillWidth: true
                    }

                    RowLayout {
                        spacing: Theme.s3
                        Layout.fillWidth: true
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 4
                            Text { text: qsTr("From"); color: Theme.textSecondary; font.pixelSize: Theme.footnote }
                            AppField {
                                id: fromField
                                placeholderText: "0:00"
                                Layout.fillWidth: true
                                Accessible.name: qsTr("Start time")
                                onEditingFinished: {
                                    var v = dlg.parse(text)
                                    if (dlg.duration > 0 && !isNaN(v)) { strip.startSec = Math.max(0, Math.min(v, strip.endSec - strip.minSpan)); dlg.syncFields()
                                        if (previewLoader.item) previewLoader.item.seek(strip.startSec) }
                                }
                            }
                        }
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 4
                            Text { text: qsTr("To"); color: Theme.textSecondary; font.pixelSize: Theme.footnote }
                            AppField {
                                id: toField
                                placeholderText: qsTr("End of video")
                                Layout.fillWidth: true
                                Accessible.name: qsTr("End time")
                                onEditingFinished: {
                                    var v = dlg.parse(text)
                                    if (dlg.duration > 0 && !isNaN(v)) { strip.endSec = Math.min(dlg.duration, Math.max(v, strip.startSec + strip.minSpan)); dlg.syncFields()
                                        if (previewLoader.item) previewLoader.item.seek(strip.endSec) }
                                }
                            }
                        }
                    }

                    // interval
                    Text { text: qsTr("One image every … seconds"); color: Theme.textSecondary; font.pixelSize: Theme.footnote }
                    Flow {
                        spacing: Theme.s2
                        Layout.fillWidth: true
                        Repeater {
                            model: dlg.intervals
                            delegate: Chip {
                                required property string modelData
                                text: modelData + " s"
                                checked: stepField.text === modelData
                                enabled: Number(modelData) >= 1 || dlg.isShort
                                opacity: enabled ? 1 : 0.4
                                onToggled: dlg.setInterval(modelData)
                            }
                        }
                        AppField {
                            id: stepField
                            text: "5"
                            width: 84
                            inputMethodHints: Qt.ImhFormattedNumbersOnly
                            onAccepted: dlg.start()
                            Accessible.name: qsTr("Seconds between images")
                        }
                    }
                    Text {
                        text: qsTr("0.1 s and 0.5 s are available for Shorts only (up to 3 minutes). Longer videos: 1 second or more.")
                        color: Theme.textTertiary
                        font.pixelSize: Theme.caption
                        wrapMode: Text.Wrap
                        Layout.fillWidth: true
                    }
                    Text {
                        visible: dlg.imageCount > 0
                        text: qsTr("About %1 images").arg(dlg.imageCount)
                        color: dlg.imageCount > 5000 ? Theme.danger : Theme.textSecondary
                        font.pixelSize: Theme.footnote
                    }

                    Segmented {
                        Layout.fillWidth: true
                        current: dlg.format
                        options: [{ text: qsTr("PNG (lossless)"), value: "png" }, { text: qsTr("JPG (best quality)"), value: "jpg" }]
                        onActivated: (v) => dlg.format = v
                    }
                    Text {
                        text: qsTr("Images have the resolution of the video. Saved in the folder “Frames” of your download folder, in their own sub-folder for this video.")
                        color: Theme.textSecondary
                        font.pixelSize: Theme.caption
                        wrapMode: Text.Wrap
                        Layout.fillWidth: true
                    }
                }
            }
        }

        // ---- drag ghost
        Rectangle {
            id: ghost
            property string source
            property string label
            visible: false
            z: 100
            width: 150
            height: 100
            radius: Theme.radius
            color: Theme.raised
            border.width: 2
            border.color: Theme.accent
            opacity: 0.92
            Thumb {
                anchors { fill: parent; margins: 4; bottomMargin: 22 }
                source: ghost.source
            }
            Text {
                anchors { left: parent.left; right: parent.right; bottom: parent.bottom; margins: 5 }
                text: ghost.label
                elide: Text.ElideRight
                font.pixelSize: 11
                color: Theme.text
            }
        }
    }
}
