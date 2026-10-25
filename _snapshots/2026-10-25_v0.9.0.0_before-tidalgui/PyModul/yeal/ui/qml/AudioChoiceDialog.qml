import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// Shown before an audio download starts when the source offers very high audio quality:
// pick the target format: MP3 (default, 320 kbps), AAC, original stream, FLAC.
Popup {
    id: dlg
    objectName: "audioChoiceDialog"
    property var queue: []          // pending {url, title, thumbnail, abr, codec, choices}
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
    function answer(fmt, bitrate) {
        if (current) backend.confirmAudio(current.url, fmt, bitrate)
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
    Shortcut { sequence: "Escape"; enabled: dlg.opened; onActivated: dlg.answer("", 0) }

    contentItem: ColumnLayout {
        spacing: Theme.s3

        Text {
            text: qsTr("High audio quality available")
            color: Theme.text
            font.pixelSize: Theme.title
            font.weight: Font.Medium
            Layout.fillWidth: true
        }
        Text {
            text: dlg.current
                ? qsTr("%1\nBest source: %2 %3 kbps. Choose how to save it:")
                      .arg(dlg.current.title).arg(String(dlg.current.codec).toUpperCase()).arg(dlg.current.abr)
                : ""
            color: Theme.textSecondary
            font.pixelSize: Theme.footnote
            wrapMode: Text.Wrap
            maximumLineCount: 3
            elide: Text.ElideRight
            Layout.fillWidth: true
        }
        Repeater {
            model: dlg.current ? dlg.current.choices : []
            delegate: Rectangle {
                id: card
                required property var modelData
                required property int index
                Layout.fillWidth: true
                implicitHeight: col.implicitHeight + 2 * Theme.s3
                radius: Theme.radius
                color: tap.pressed ? Theme.pressed : hov.hovered || activeFocus ? Theme.hover : Theme.field
                border.width: index === 0 || activeFocus ? 2 : 1
                border.color: index === 0 || activeFocus ? Theme.accentFill : Theme.separator
                activeFocusOnTab: true
                Accessible.role: Accessible.Button
                Accessible.name: modelData.title
                Keys.onReturnPressed: dlg.answer(modelData.format, modelData.bitrate)
                Keys.onSpacePressed: dlg.answer(modelData.format, modelData.bitrate)
                HoverHandler { id: hov; cursorShape: Qt.PointingHandCursor }
                TapHandler { id: tap; onTapped: dlg.answer(card.modelData.format, card.modelData.bitrate) }
                ColumnLayout {
                    id: col
                    anchors { left: parent.left; right: parent.right; verticalCenter: parent.verticalCenter
                              margins: Theme.s3 }
                    spacing: 2
                    RowLayout {
                        spacing: Theme.s2
                        Layout.fillWidth: true
                        Text {
                            text: card.modelData.title
                            color: Theme.text
                            font.pixelSize: Theme.body
                            font.weight: Font.Medium
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                        }
                        Badge { visible: card.index === 0; kind: "success"; text: qsTr("Recommended") }
                    }
                    Text {
                        text: card.modelData.detail
                        color: Theme.textSecondary
                        font.pixelSize: Theme.footnote
                        wrapMode: Text.Wrap
                        Layout.fillWidth: true
                    }
                }
            }
        }
        RowLayout {
            Layout.fillWidth: true
            Item { Layout.fillWidth: true }
            AppButton { text: qsTr("Cancel"); onClicked: dlg.answer("", 0) }
        }
    }
}
