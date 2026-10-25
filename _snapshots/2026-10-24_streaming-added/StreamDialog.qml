import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// "Stream to speaker / TV": searches the Wi-Fi/LAN for UPnP/DLNA devices (KEF LS50 Wireless, TVs, AV receivers, ...),
// lets the user pick one (it is remembered) and plays the finished download there.
Popup {
    id: dlg
    objectName: "streamDialog"
    property int jobId: -1          // the download to play; -1 = only choose the default device
    property string title: ""
    property string addError: ""

    function openFor(id, t) {
        jobId = id
        title = t || ""
        addError = ""
        open()
        backend.scanStreamDevices()      // always look again: devices come and go
    }
    function pick(deviceId) {
        if (jobId >= 0) {
            backend.streamJob(jobId, deviceId)
            close()
        } else {
            backend.selectStreamDevice(deviceId)
        }
    }

    modal: true
    focus: true
    parent: Overlay.overlay
    readonly property rect area: Theme.dialogArea.width > 0 ? Theme.dialogArea : Qt.rect(0, 0, Overlay.overlay ? Overlay.overlay.width : 0, Overlay.overlay ? Overlay.overlay.height : 0)
    x: area.x + (area.width - width) / 2
    y: area.y + (area.height - height) / 2
    width: Math.min(520, area.width - 2 * Theme.s4)
    padding: Theme.s4
    closePolicy: Popup.CloseOnEscape
    Overlay.modal: Rectangle { color: Theme.dark ? "#99000000" : "#55000000" }
    background: Rectangle {
        radius: Theme.radiusCard + 4
        color: Theme.raised
        border.width: 1
        border.color: Theme.separator
    }

    contentItem: ColumnLayout {
        spacing: Theme.s3

        RowLayout {
            spacing: Theme.s2
            Layout.fillWidth: true
            Icon { name: "cast"; size: 22; color: Theme.accent }
            Text {
                text: qsTr("Stream to speaker / TV")
                color: Theme.text
                font.pixelSize: Theme.headline
                font.weight: Font.DemiBold
                Layout.fillWidth: true
                Accessible.role: Accessible.Heading
            }
            BusyIndicator { running: backend.streamScanning; visible: running; implicitWidth: 24; implicitHeight: 24 }
        }
        Text {
            visible: dlg.title !== ""
            text: dlg.title
            color: Theme.text
            font.pixelSize: Theme.body
            wrapMode: Text.Wrap
            maximumLineCount: 2
            elide: Text.ElideRight
            Layout.fillWidth: true
        }
        Text {
            visible: backend.streamStatus !== ""
            text: backend.streamStatus
            color: Theme.textSecondary
            font.pixelSize: Theme.footnote
            wrapMode: Text.Wrap
            Layout.fillWidth: true
        }

        ListView {
            id: devices
            objectName: "streamDeviceList"
            model: backend.streamDevices
            clip: true
            spacing: Theme.s1
            interactive: contentHeight > height
            Layout.fillWidth: true
            Layout.preferredHeight: Math.min(contentHeight, 240)
            delegate: Rectangle {
                id: item
                required property var modelData
                width: ListView.view.width
                height: 54
                radius: Theme.radius
                color: item.modelData.selected ? Theme.accentSoft : tap.pressed ? Theme.pressed : hover.hovered ? Theme.hover : Theme.field
                border.width: item.modelData.selected ? 1 : 0
                border.color: Theme.accent
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: Theme.s3
                    anchors.rightMargin: Theme.s3
                    spacing: Theme.s3
                    Icon { name: "speaker"; size: 22; color: item.modelData.online ? Theme.text : Theme.textTertiary }
                    ColumnLayout {
                        spacing: 0
                        Layout.fillWidth: true
                        Text {
                            text: item.modelData.name
                            color: Theme.text
                            font.pixelSize: Theme.body
                            font.weight: Font.Medium
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                        }
                        Text {
                            text: [item.modelData.manufacturer, item.modelData.model, item.modelData.host]
                                  .filter(function (t) { return t && t !== "" }).join("  ·  ")
                            color: Theme.textSecondary
                            font.pixelSize: Theme.caption
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                        }
                    }
                    Badge { visible: item.modelData.selected; text: qsTr("Saved"); kind: "accent" }
                    Badge { visible: !item.modelData.online; text: qsTr("Not seen"); kind: "warning" }
                }
                HoverHandler { id: hover; cursorShape: Qt.PointingHandCursor }
                TapHandler { id: tap; onTapped: dlg.pick(item.modelData.id) }
                Accessible.role: Accessible.Button
                Accessible.name: qsTr("Stream to %1").arg(item.modelData.name)
            }
        }
        Text {
            visible: devices.count === 0 && !backend.streamScanning
            text: qsTr("No device found yet. Turn the speaker on, make sure the PC and the speaker use the same Wi-Fi/LAN, then search again or add its address below.")
            color: Theme.textSecondary
            font.pixelSize: Theme.footnote
            wrapMode: Text.Wrap
            Layout.fillWidth: true
        }

        RowLayout {
            spacing: Theme.s2
            Layout.fillWidth: true
            AppField {
                id: hostField
                placeholderText: qsTr("Add by address, e.g. 192.168.1.50")
                Layout.fillWidth: true
                onAccepted: addBtn.clicked()
                Accessible.name: qsTr("Device address")
            }
            AppButton {
                id: addBtn
                text: qsTr("Add")
                onClicked: {
                    dlg.addError = backend.addStreamHost(hostField.text)
                    if (dlg.addError === "") hostField.text = ""
                }
            }
        }
        Text {
            visible: dlg.addError !== ""
            text: dlg.addError
            color: Theme.danger
            font.pixelSize: Theme.footnote
            wrapMode: Text.Wrap
            Layout.fillWidth: true
        }

        RowLayout {
            visible: backend.streamPlaying
            spacing: Theme.s2
            Layout.fillWidth: true
            AppButton { text: qsTr("Pause"); iconName: "pause"; enabled: !backend.streamBusy; onClicked: backend.pauseStream() }
            AppButton { text: qsTr("Resume"); iconName: "play"; enabled: !backend.streamBusy; onClicked: backend.resumeStream() }
            AppButton { text: qsTr("Stop"); iconName: "x"; kind: "danger"; enabled: !backend.streamBusy; onClicked: backend.stopStream() }
            Item { Layout.fillWidth: true }
        }
        RowLayout {
            visible: backend.streamPlaying
            spacing: Theme.s3
            Layout.fillWidth: true
            Text { text: qsTr("Volume"); color: Theme.textSecondary; font.pixelSize: Theme.footnote }
            Slider {
                id: vol
                from: 0; to: 100; stepSize: 1
                value: backend.settings.stream_volume >= 0 ? backend.settings.stream_volume : 30
                Layout.fillWidth: true
                onPressedChanged: if (!pressed) backend.setStreamVolume(Math.round(value))
                Accessible.name: qsTr("Speaker volume")
            }
            Text { text: Math.round(vol.value) + "%"; color: Theme.textSecondary; font.pixelSize: Theme.footnote }
        }

        RowLayout {
            spacing: Theme.s2
            Layout.fillWidth: true
            AppButton { text: qsTr("Search again"); iconName: "retry"; enabled: !backend.streamScanning
                        onClicked: backend.scanStreamDevices() }
            Item { Layout.fillWidth: true }
            AppButton { text: qsTr("Close"); kind: "primary"; onClicked: dlg.close() }
        }
    }
}
