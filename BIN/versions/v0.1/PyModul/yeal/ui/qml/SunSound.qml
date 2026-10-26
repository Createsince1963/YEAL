import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Dialogs
import QtQuick.Layouts

// Content of the "Sound" planet: the engine and its filters. "Standard" is the Qt player; "Own engine" is Yeal's chain
// (ffmpeg decodes, 32-bit float filters, the sound card / Bluetooth headphones play): 10 band equalizer with pre-amp,
// crossfeed for headphones, ReplayGain (same loudness for every song), convolution with an impulse response (WAV, room or
// headphone correction) and a soft limiter. Changes reach the running song after a moment.
Flickable {
    id: root
    property color tint: Theme.playerColor(backend.settings.tidal_player_color)
    readonly property var cfg: backend.settings.dsp || ({})
    readonly property bool own: backend.settings.audio_engine === "dsp"
    readonly property var bands: [31, 62, 125, 250, 500, 1000, 2000, 4000, 8000, 16000]
    readonly property var eq: (cfg.eq && cfg.eq.length === 10) ? cfg.eq : [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    readonly property var presets: [
        { name: qsTr("Flat"), eq: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0] },
        { name: qsTr("Bass"), eq: [5, 4, 3, 1, 0, 0, 0, 0, 0, 0] },
        { name: qsTr("Treble"), eq: [0, 0, 0, 0, 0, 0, 1, 3, 4, 5] },
        { name: qsTr("Vocal"), eq: [-2, -1, 0, 1, 3, 4, 3, 1, 0, -1] },
        { name: qsTr("Loudness"), eq: [5, 3, 0, 0, -1, 0, 0, 1, 3, 4] }]
    function label(f) { return f >= 1000 ? (f / 1000) + "k" : String(f) }
    function setBand(i, v) {
        var e = eq.slice()
        e[i] = Math.round(v * 2) / 2
        backend.setDsp({ eq: e, eq_on: true })
    }

    contentHeight: col.implicitHeight
    clip: true
    boundsBehavior: Flickable.StopAtBounds
    ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

    FileDialog {
        id: irDialog
        title: qsTr("Choose an impulse response (WAV)")
        nameFilters: [qsTr("WAV files (*.wav)"), qsTr("All files (*)")]
        onAccepted: backend.setDsp({ convolution: selectedFile.toString().replace(/^file:\/\/\//, ""), convolution_on: true })
    }

    ColumnLayout {
        id: col
        width: root.width - Theme.s2
        spacing: Theme.s2

        Text { text: qsTr("Engine"); color: Theme.textSecondary; font.pixelSize: Theme.caption }
        Flow {
            Layout.fillWidth: true
            spacing: Theme.s2
            Chip { text: qsTr("Standard"); checked: !root.own; onToggled: backend.setAudioEngine("qt") }
            Chip { text: qsTr("Own engine"); checked: root.own; enabled: backend.dspAvailable
                   onToggled: backend.setAudioEngine("dsp") }
        }
        Text {
            Layout.fillWidth: true
            visible: !backend.dspAvailable
            text: qsTr("The own engine needs numpy and ffmpeg; one of them is missing on this computer.")
            color: Theme.warning; font.pixelSize: Theme.caption; wrapMode: Text.Wrap
        }
        Text {
            Layout.fillWidth: true
            visible: backend.dspAvailable && !root.own
            text: qsTr("The own engine adds an equalizer, crossfeed, ReplayGain and convolution. Choosing it stops the song; press play again.")
            color: Theme.textTertiary; font.pixelSize: Theme.caption; wrapMode: Text.Wrap
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.preferredWidth: col.width
            Layout.maximumWidth: col.width
            visible: root.own
            spacing: Theme.s2

            RowLayout {
                Layout.fillWidth: true
                Text { text: qsTr("Equalizer"); color: Theme.textSecondary; font.pixelSize: Theme.caption; Layout.fillWidth: true }
                Chip { text: qsTr("On"); checked: !!root.cfg.eq_on; onToggled: (c) => backend.setDsp({ eq_on: c }) }
            }
            Flow {
                Layout.fillWidth: true
                spacing: Theme.s1
                Repeater {
                    model: root.presets
                    delegate: Chip {
                        required property var modelData
                        text: modelData.name
                        onToggled: backend.setDsp({ eq: modelData.eq, eq_on: true })
                    }
                }
            }
            Row {
                id: bandRow
                Layout.alignment: Qt.AlignHCenter
                Layout.minimumWidth: 0
                Layout.maximumWidth: col.width
                readonly property real bandW: Math.max(14, Math.min(26, (col.width - 9 * spacing) / 10))
                spacing: 2
                Repeater {
                    model: root.bands
                    delegate: Column {
                        required property int index
                        required property int modelData
                        spacing: 2
                        Slider {
                            id: band
                            orientation: Qt.Vertical
                            from: -12; to: 12; stepSize: 0.5
                            value: root.eq[index]
                            width: bandRow.bandW; height: 96
                            enabled: !!root.cfg.eq_on
                            onMoved: root.setBand(index, value)
                            Accessible.name: root.label(modelData) + " Hz"
                            background: Rectangle {
                                x: (band.width - 3) / 2; width: 3; height: band.height; radius: 1.5
                                color: Qt.alpha(Theme.text, 0.2)
                                Rectangle {          // from the middle to the handle
                                    width: 3; radius: 1.5; color: root.cfg.eq_on ? root.tint : Theme.textTertiary
                                    y: Math.min(band.visualPosition, 0.5) * parent.height
                                    height: Math.abs(band.visualPosition - 0.5) * parent.height
                                }
                            }
                            handle: Rectangle {
                                x: (band.width - width) / 2; y: band.visualPosition * (band.height - height)
                                width: 12; height: 12; radius: 6; color: Theme.text
                                border.width: 2; border.color: root.cfg.eq_on ? root.tint : Theme.textTertiary
                            }
                            ToolTip.visible: hovered || pressed
                            ToolTip.text: root.label(modelData) + " Hz: " + (value > 0 ? "+" : "") + value.toFixed(1) + " dB"
                        }
                        Text { text: root.label(modelData); color: Theme.textTertiary; font.pixelSize: 9
                               anchors.horizontalCenter: parent.horizontalCenter }
                    }
                }
            }
            RowLayout {
                Layout.fillWidth: true
                Text { text: qsTr("Pre-amp"); color: Theme.textSecondary; font.pixelSize: Theme.caption }
                Slider {
                    Layout.fillWidth: true
                    from: -12; to: 12; stepSize: 0.5
                    value: root.cfg.preamp || 0
                    enabled: !!root.cfg.eq_on
                    onMoved: backend.setDsp({ preamp: value })
                    Accessible.name: qsTr("Pre-amp")
                }
                Text { text: ((root.cfg.preamp || 0) > 0 ? "+" : "") + (root.cfg.preamp || 0).toFixed(1) + " dB"
                       color: Theme.textSecondary; font.pixelSize: Theme.caption; Layout.preferredWidth: 52 }
            }

            Text { text: qsTr("Crossfeed (for headphones)"); color: Theme.textSecondary; font.pixelSize: Theme.caption; Layout.fillWidth: true; wrapMode: Text.Wrap }
            Flow {
                Layout.fillWidth: true
                spacing: Theme.s2
                Repeater {
                    model: [{ v: "off", t: qsTr("Off") }, { v: "light", t: qsTr("Light") }, { v: "medium", t: qsTr("Medium") }, { v: "strong", t: qsTr("Strong") }]
                    delegate: Chip {
                        required property var modelData
                        text: modelData.t
                        checked: (root.cfg.crossfeed || "off") === modelData.v
                        onToggled: backend.setDsp({ crossfeed: modelData.v })
                    }
                }
            }

            Text { text: qsTr("Loudness (ReplayGain)"); color: Theme.textSecondary; font.pixelSize: Theme.caption; Layout.fillWidth: true; wrapMode: Text.Wrap }
            Flow {
                Layout.fillWidth: true
                spacing: Theme.s2
                Chip { text: qsTr("Off"); checked: (root.cfg.replaygain || "off") === "off"; onToggled: backend.setDsp({ replaygain: "off" }) }
                Chip { text: qsTr("Every song the same"); checked: root.cfg.replaygain === "track"; onToggled: backend.setDsp({ replaygain: "track" }) }
            }

            Text { text: qsTr("Impulse response (room / headphone correction)"); color: Theme.textSecondary; font.pixelSize: Theme.caption; Layout.fillWidth: true; wrapMode: Text.Wrap }
            Flow {
                Layout.fillWidth: true
                spacing: Theme.s2
                Chip { text: qsTr("On"); checked: !!root.cfg.convolution_on; enabled: !!root.cfg.convolution
                       onToggled: (c) => backend.setDsp({ convolution_on: c }) }
                AppButton { text: qsTr("Choose WAV ..."); kind: "plain"; implicitHeight: 30; onClicked: irDialog.open() }
                AppButton { text: qsTr("Remove"); kind: "plain"; implicitHeight: 30; visible: !!root.cfg.convolution
                            onClicked: backend.setDsp({ convolution: "", convolution_on: false }) }
            }
            Text {
                Layout.fillWidth: true
                visible: !!root.cfg.convolution
                text: root.cfg.convolution
                color: Theme.textTertiary; font.pixelSize: 10; elide: Text.ElideMiddle
            }

            RowLayout {
                Layout.fillWidth: true
                Text { text: qsTr("Limiter (no clipping when the filters make it louder)"); color: Theme.textSecondary
                       font.pixelSize: Theme.caption; Layout.fillWidth: true; wrapMode: Text.Wrap }
                Chip { text: qsTr("On"); checked: root.cfg.limiter !== false; onToggled: (c) => backend.setDsp({ limiter: c }) }
            }
            AppButton {
                Layout.minimumWidth: 0; Layout.maximumWidth: col.width
                text: qsTr("Reset all filters"); kind: "plain"; implicitHeight: 30
                onClicked: backend.setDsp({ eq_on: false, eq: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0], preamp: 0, crossfeed: "off",
                                            replaygain: "off", convolution_on: false, limiter: true })
            }
        }
    }
}
