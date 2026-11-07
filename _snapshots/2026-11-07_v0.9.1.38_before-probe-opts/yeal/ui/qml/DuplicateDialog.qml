import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// "Already downloaded": shown when a link is added that finished before (and its file still exists).
Popup {
    id: dlg
    objectName: "duplicateDialog"
    property var queue: []          // pending {url, title, date, mode, jobId}
    property var current: null

    function enqueue(info) {
        queue = queue.concat([info])
        if (!opened) next()
    }
    function next() {
        if (queue.length === 0) { current = null; close(); return }
        current = queue[0]
        queue = queue.slice(1)
        open()
    }
    function answer(again) {
        if (current) backend.confirmDuplicate(current.url, again)
        next()
    }

    modal: true
    focus: true
    parent: Overlay.overlay
    readonly property rect area: Theme.dialogArea.width > 0 ? Theme.dialogArea : Qt.rect(0, 0, Overlay.overlay ? Overlay.overlay.width : 0, Overlay.overlay ? Overlay.overlay.height : 0)
    x: area.x + (area.width - width) / 2
    y: area.y + (area.height - height) / 2
    width: Math.min(480, area.width - 2 * Theme.s4)
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
            text: qsTr("Already downloaded")
            color: Theme.text
            font.pixelSize: Theme.headline
            font.weight: Font.DemiBold
            Layout.fillWidth: true
            Accessible.role: Accessible.Heading
        }
        Text {
            text: dlg.current ? dlg.current.title : ""
            color: Theme.text
            font.pixelSize: Theme.body
            wrapMode: Text.Wrap
            maximumLineCount: 3
            elide: Text.ElideRight
            Layout.fillWidth: true
        }
        Text {
            text: dlg.current ? qsTr("You downloaded this %1 on %2. Download it again?")
                                  .arg(dlg.current.mode === "audio" ? qsTr("audio") : qsTr("video")).arg(dlg.current.date) : ""
            color: Theme.textSecondary
            font.pixelSize: Theme.footnote
            wrapMode: Text.Wrap
            Layout.fillWidth: true
        }
        RowLayout {
            spacing: Theme.s2
            Layout.fillWidth: true
            AppButton { text: qsTr("Open existing"); iconName: "open"; visible: !backend.isMobile
                        onClicked: if (dlg.current) backend.openFile(dlg.current.jobId) }
            Item { Layout.fillWidth: true }
            AppButton { text: qsTr("Skip"); onClicked: dlg.answer(false) }
            AppButton { text: qsTr("Download again"); kind: "primary"; onClicked: dlg.answer(true) }
        }
    }
}
