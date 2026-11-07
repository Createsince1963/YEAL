import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// The link is a running live stream: ask whether to record it and for how long.
Popup {
    id: dlg
    objectName: "liveStreamDialog"
    property var queue: []          // pending {url, title, thumbnail}
    property var current: null
    property int minutes: 0         // chosen preset: 0 = until the stream ends
    property bool custom: false
    readonly property bool canLimit: backend.ffmpegAvailable     // a time limit needs ffmpeg to cut the recording
    readonly property int customMinutes: parseInt(minutesField.text) || 0
    readonly property int chosen: custom ? customMinutes : minutes

    function enqueue(info) {
        queue = queue.concat([info])
        if (!opened) next()
    }
    function next() {
        if (queue.length === 0) { current = null; close(); return }
        current = queue[0]
        queue = queue.slice(1)
        minutes = 0
        custom = false
        minutesField.text = "60"
        open()
    }
    function answer(record) {
        if (current) backend.confirmLive(current.url, record ? chosen : -1)
        next()
    }

    modal: true
    focus: true
    parent: Overlay.overlay
    readonly property rect area: Theme.dialogArea.width > 0 ? Theme.dialogArea : Qt.rect(0, 0, Overlay.overlay ? Overlay.overlay.width : 0, Overlay.overlay ? Overlay.overlay.height : 0)
    x: area.x + (area.width - width) / 2
    y: area.y + (area.height - height) / 2
    width: Math.min(720, area.width - 2 * Theme.s4)
    padding: Theme.s4
    closePolicy: Popup.NoAutoClose
    Overlay.modal: Rectangle { color: Theme.dark ? "#99000000" : "#55000000" }
    background: Rectangle {
        radius: Theme.radiusCard + 4
        color: Theme.raised
        border.width: 1
        border.color: Theme.separator
    }
    Shortcut { sequence: "Escape"; enabled: dlg.opened; onActivated: dlg.answer(false) }

    contentItem: ColumnLayout {
        spacing: Theme.s3

        Text {
            text: qsTr("Live stream")
            color: Theme.text
            font.pixelSize: Theme.title
            font.weight: Font.Medium
            Layout.fillWidth: true
        }
        Text {
            text: dlg.current ? dlg.current.title : ""
            color: Theme.textSecondary
            font.pixelSize: Theme.footnote
            wrapMode: Text.Wrap
            maximumLineCount: 2
            elide: Text.ElideRight
            Layout.fillWidth: true
        }
        Text {
            text: qsTr("This video is live right now. Record it?")
            color: Theme.text
            font.pixelSize: Theme.body
            wrapMode: Text.Wrap
            Layout.fillWidth: true
        }
        Text {
            text: qsTr("Recording time")
            color: Theme.textSecondary
            font.pixelSize: Theme.footnote
            Layout.fillWidth: true
        }
        Flow {
            Layout.fillWidth: true
            spacing: Theme.s2
            Repeater {
                model: dlg.canLimit
                    ? [{ t: qsTr("Until it ends"), m: 0 }, { t: qsTr("15 min"), m: 15 }, { t: qsTr("30 min"), m: 30 },
                       { t: qsTr("1 hour"), m: 60 }, { t: qsTr("2 hours"), m: 120 }, { t: qsTr("Custom"), m: -1 }]
                    : [{ t: qsTr("Until it ends"), m: 0 }]
                delegate: Chip {
                    required property var modelData
                    text: modelData.t
                    checked: modelData.m < 0 ? dlg.custom : (!dlg.custom && dlg.minutes === modelData.m)
                    onToggled: {
                        if (modelData.m < 0) dlg.custom = true
                        else { dlg.custom = false; dlg.minutes = modelData.m }
                    }
                }
            }
        }
        RowLayout {
            visible: dlg.custom
            spacing: Theme.s2
            Layout.fillWidth: true
            AppField {
                id: minutesField
                implicitWidth: 120
                maximumLength: 4
                inputMethodHints: Qt.ImhDigitsOnly
                validator: IntValidator { bottom: 1; top: 1440 }
                Accessible.name: qsTr("Minutes")
                onAccepted: if (dlg.chosen > 0) dlg.answer(true)
            }
            Text { text: qsTr("minutes (1 to 1440)"); color: Theme.textSecondary; font.pixelSize: Theme.footnote }
        }
        Text {
            visible: !dlg.canLimit
            text: qsTr("A time limit needs ffmpeg; the recording runs until the stream ends. You can cancel it in the list.")
            color: Theme.textSecondary
            font.pixelSize: Theme.footnote
            wrapMode: Text.Wrap
            Layout.fillWidth: true
        }
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.s2
            Item { Layout.fillWidth: true }
            AppButton { text: qsTr("Don't record"); onClicked: dlg.answer(false) }
            AppButton {
                text: qsTr("Record")
                kind: "primary"
                enabled: !dlg.custom || dlg.customMinutes > 0
                onClicked: dlg.answer(true)
            }
        }
    }
}
