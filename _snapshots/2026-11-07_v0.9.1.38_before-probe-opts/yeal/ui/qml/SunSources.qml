import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Dialogs
import QtQuick.Layouts

// Content of the "Folders" planet: your own music folders as a small moon system. The planet is in the middle, every music
// folder circles around it as a moon - folders of this PC and of the network (\\server\share, a mapped drive). A click on a
// moon fills the Library with its songs ("Downloads" = the finished downloads); a moon can be dragged into the queue (the
// whole folder, with all albums in it). The "+" moon and the pencil button open the edit mode: the card grows, folders are
// added (dialog or a typed path, also a network path), renamed and removed; "Done" brings the card back to its size.
GridLayout {
    id: root
    property var player
    property color tint: Theme.accent
    property bool editing: false                       // set by the planet view: the card is zoomed for editing
    signal editRequest(bool on)

    columns: width < 420 ? 1 : 2
    columnSpacing: Theme.s3
    rowSpacing: Theme.s2

    readonly property string chosen: String(backend.settings.library_source || "")
    readonly property var sources: backend.settings.music_sources || []
    readonly property var lists: backend.settings.queue_lists || []
    property string message: ""
    // moons: the downloads, every folder, and the "+" at the end
    readonly property var moons: {
        var out = [{ id: "", name: qsTr("Downloads"), icon: "download", kind: "downloads", path: "", tip: qsTr("The finished downloads") }]
        for (var i = 0; i < sources.length; ++i)
            out.push({ id: sources[i].id, name: sources[i].name, icon: sources[i].kind === "network" ? "network" : "folder",
                       kind: sources[i].kind, path: sources[i].path,
                       tip: sources[i].path + "  ·  " + (sources[i].kind === "network" ? qsTr("network") : qsTr("this PC")) })
        for (var j = 0; j < lists.length; ++j)
            out.push({ id: "list:" + lists[j].name, name: lists[j].name, icon: "listAdd", kind: "list", path: "", items: lists[j].items,
                       tip: qsTr("Saved list, %1 songs. Click to play, drag into the queue to add it.").arg(lists[j].items.length) })
        out.push({ id: "+", name: qsTr("Add"), icon: "plus", kind: "add", path: "", tip: qsTr("Add a music folder") })
        return out
    }
    readonly property int ringCount: Math.max(1, Math.ceil(moons.length / 6))
    function moonPlace(index) {                        // [ring, position on the ring, moons on that ring]
        var left = moons.length, start = 0
        for (var k = 0; k < ringCount; ++k) {
            var n = Math.ceil(left / (ringCount - k))
            if (index < start + n) return [k, index - start, n]
            start += n
            left -= n
        }
        return [0, 0, 1]
    }
    function add(value) {
        var err = backend.addMusicSource(value, nameField.text)
        message = err
        if (err === "") { nameField.text = ""; pathField.text = "" }
    }
    function chosenName() {
        for (var i = 0; i < moons.length; ++i) if (moons[i].id === chosen) return moons[i].name
        return qsTr("Downloads")
    }

    FolderDialog {
        id: dialog
        title: qsTr("Choose a music folder")
        onAccepted: { root.editRequest(true); root.add(selectedFolder.toString()) }
    }

    // ---- the chosen folder, and in the edit mode the list of folders with the fields to add one
    ColumnLayout {
        Layout.preferredWidth: root.columns === 1 ? -1 : (root.editing ? 300 : 190)
        Layout.maximumWidth: root.columns === 1 ? 100000 : (root.editing ? 360 : 230)
        Layout.fillWidth: root.columns === 1
        Layout.fillHeight: root.columns === 2
        spacing: Theme.s2
        Text {
            Layout.fillWidth: true
            text: qsTr("Library shows")
            color: Theme.textSecondary; font.pixelSize: Theme.caption
        }
        Text {
            Layout.fillWidth: true
            text: root.chosenName()
            color: root.tint; font.pixelSize: Theme.footnote; font.weight: Font.Bold
            wrapMode: Text.Wrap; maximumLineCount: 2; elide: Text.ElideRight
        }
        Text {
            Layout.fillWidth: true
            visible: !root.editing
            text: qsTr("Click a moon to fill the library with it. Drag a moon into the queue to queue the whole folder.")
            color: Theme.textTertiary; font.pixelSize: Theme.caption; wrapMode: Text.Wrap
        }
        Flow {                                          // never cut off: the buttons wrap
            Layout.fillWidth: true
            spacing: Theme.s1
            AppButton { text: qsTr("Add folder ..."); iconName: "folder"; onClicked: dialog.open() }
            AppButton { visible: !root.editing; text: qsTr("Edit"); iconName: "pencil"; onClicked: root.editRequest(true) }
        }
        ColumnLayout {                                  // edit mode: a typed path (network paths too) and the folders
            Layout.fillWidth: true
            visible: root.editing
            spacing: Theme.s2
            AppField {
                id: pathField
                Layout.fillWidth: true
                placeholderText: qsTr("Folder or network path, e.g. \\\\nas\\music")
                onAccepted: root.add(text)
            }
            AppField {
                id: nameField
                Layout.fillWidth: true
                placeholderText: qsTr("Name (optional)")
                onAccepted: root.add(pathField.text)
            }
            Flow {
                Layout.fillWidth: true
                spacing: Theme.s1
                AppButton { text: qsTr("Add"); kind: "primary"; iconName: "plus"; enabled: pathField.text.trim() !== ""; onClicked: root.add(pathField.text) }
            }
            Text {
                Layout.fillWidth: true
                visible: root.message !== ""
                text: root.message
                color: Theme.danger; font.pixelSize: Theme.caption; wrapMode: Text.Wrap
            }
        }
        ListView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: root.editing
            clip: true
            spacing: 2
            model: root.sources
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
            delegate: Rectangle {
                id: line
                required property var modelData
                width: ListView.view.width - 6
                height: 44
                radius: 10
                color: Qt.alpha(Theme.text, 0.06)
                RowLayout {
                    anchors.fill: parent; anchors.leftMargin: 8; anchors.rightMargin: 6
                    spacing: Theme.s2
                    Icon { name: line.modelData.kind === "network" ? "network" : "folder"; size: 16; color: root.tint }
                    ColumnLayout {
                        Layout.fillWidth: true; spacing: 0
                        Text { text: line.modelData.name; Layout.fillWidth: true; elide: Text.ElideRight; color: Theme.text
                               font.pixelSize: Theme.footnote; font.weight: Font.Medium }
                        Text { text: line.modelData.path; Layout.fillWidth: true; elide: Text.ElideMiddle; color: Theme.textSecondary
                               font.pixelSize: Theme.caption }
                    }
                    IconButton { implicitWidth: 26; implicitHeight: 26; iconName: "trash"; tip: qsTr("Remove this folder from the list (the files stay)")
                                 onClicked: { if (root.chosen === line.modelData.id) root.player.chooseSource(""); backend.removeMusicSource(line.modelData.id) } }
                }
            }
        }
        Item { Layout.fillHeight: !root.editing }
    }

    // ---- the moon system
    Item {
        id: sky
        Layout.fillWidth: true
        Layout.fillHeight: true
        Layout.minimumHeight: 150
        Layout.minimumWidth: 150
        readonly property real cx: width / 2
        readonly property real cy: height / 2
        readonly property real rx: Math.max(40, width / 2 - 46)
        readonly property real ry: Math.max(34, height / 2 - 34)
        function ringFactor(k) { return root.ringCount === 1 ? 1 : 0.62 + 0.38 * k / (root.ringCount - 1) }

        Canvas {
            id: orbits
            anchors.fill: parent
            onPaint: {
                var ctx = getContext("2d")
                ctx.reset()
                ctx.lineWidth = 1
                for (var k = 0; k < root.ringCount; ++k) {
                    var f = sky.ringFactor(k)
                    ctx.strokeStyle = Qt.alpha(root.tint, 0.35)
                    ctx.beginPath()
                    ctx.ellipse(sky.cx - sky.rx * f, sky.cy - sky.ry * f, 2 * sky.rx * f, 2 * sky.ry * f)
                    ctx.stroke()
                }
            }
            Connections { target: sky; function onWidthChanged() { orbits.requestPaint() }
                                       function onHeightChanged() { orbits.requestPaint() } }
            Connections { target: root; function onRingCountChanged() { orbits.requestPaint() } }
            onVisibleChanged: requestPaint()
        }
        Rectangle {                  // the folders planet in the middle
            x: sky.cx - 24; y: sky.cy - 24; width: 48; height: 48; radius: 24
            color: Theme.surface
            border.width: 1.5; border.color: Qt.alpha(Theme.text, 0.4)
            Icon { anchors.centerIn: parent; name: "library"; size: 22; color: Theme.text }
        }
        Repeater {
            model: root.moons
            delegate: Item {
                id: moon
                objectName: "moon"
                required property var modelData
                required property int index
                readonly property var place: root.moonPlace(index)
                readonly property real f: sky.ringFactor(place[0])
                readonly property bool isAdd: modelData.kind === "add"
                readonly property bool selected: !isAdd && modelData.id === root.chosen
                readonly property real angle: -Math.PI / 2 + 2 * Math.PI * place[1] / place[2] + (place[0] % 2) * Math.PI / place[2]
                x: sky.cx + sky.rx * f * Math.cos(angle) - width / 2
                y: sky.cy + sky.ry * f * Math.sin(angle) - 17
                width: 84; height: 52
                Accessible.role: Accessible.Button
                Accessible.name: modelData.name
                Accessible.checked: selected
                Rectangle {
                    id: ball
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: 34; height: 34; radius: 17
                    color: moon.selected ? root.tint : Theme.surface
                    border.width: 2
                    border.color: moon.selected ? root.tint : moon.isAdd ? Qt.alpha(Theme.text, 0.35)
                                  : moon.modelData.kind === "network" ? Theme.warning : moon.modelData.kind === "list" ? Theme.accent : Theme.success
                    scale: hover.hovered ? 1.12 : 1
                    Behavior on scale { NumberAnimation { duration: Theme.durFast } }
                    Icon { anchors.centerIn: parent; name: moon.modelData.icon; size: 16; color: moon.selected ? "#0b0b0c" : Theme.text }
                }
                Text {
                    anchors.top: ball.bottom; anchors.topMargin: 1
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: parent.width
                    horizontalAlignment: Text.AlignHCenter
                    text: modelData.name
                    elide: Text.ElideRight
                    color: moon.selected ? root.tint : Theme.textSecondary
                    font.pixelSize: 10
                    font.weight: moon.selected ? Font.Bold : Font.Normal
                }
                HoverHandler { id: hover; cursorShape: Qt.PointingHandCursor }
                TapHandler { onTapped: {
                    if (moon.isAdd) { root.editRequest(true); dialog.open() }
                    else if (moon.modelData.kind === "list") root.player.playQueueList(moon.modelData.name)
                    else root.player.chooseSource(modelData.id) } }
                TapHandler {              // right click on a saved list: delete it
                    acceptedButtons: Qt.RightButton
                    onTapped: if (moon.modelData.kind === "list") backend.deleteQueueList(moon.modelData.name)
                }
                TidalDragSource {                         // a folder moon can be dragged into the queue: the whole folder
                    item: moon.modelData.kind === "local" || moon.modelData.kind === "network"
                          ? { kind: "folder", id: moon.modelData.id, title: moon.modelData.name, path: moon.modelData.path, url: "" }
                          : moon.modelData.kind === "list"
                            ? { kind: "group", id: moon.modelData.id, title: moon.modelData.name, tracks: moon.modelData.items, url: "" } : ({})
                }
                ToolTip.visible: hover.hovered
                ToolTip.delay: 500
                ToolTip.text: modelData.tip
            }
        }
    }
}
