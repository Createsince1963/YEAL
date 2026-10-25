import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

Popup {
    id: dlg
    property string editing: ""        // original profile name, "" = new profile
    property string errorText: ""
    readonly property var qualities: [
        { text: qsTr("Best"), value: 0 }, { text: "4K", value: 2160 }, { text: "1440p", value: 1440 },
        { text: "1080p", value: 1080 }, { text: "720p", value: 720 }, { text: "480p", value: 480 },
        { text: "360p", value: 360 }]
    property int quality: 1080
    property string mode: "video"
    property string audioFormat: "mp3"
    property string albumMode: "whole"   // whole | split | both

    function openFor(profile) {
        editing = profile ? profile.name : ""
        nameField.text = profile ? profile.name : ""
        mode = profile ? profile.mode : "video"
        quality = profile ? profile.max_height : 1080
        audioFormat = profile ? profile.audio_format : "mp3"
        metaSwitch.checked = profile ? profile.embed_metadata : true
        subsSwitch.checked = profile ? profile.subtitles : false
        listSwitch.checked = profile ? profile.playlist : false
        descSwitch.checked = profile ? profile.save_description : false
        transSwitch.checked = profile ? profile.save_transcript : false
        playerSwitch.checked = profile ? profile.online_player : false
        albumMode = !profile || !profile.split_chapters ? "whole" : (profile.keep_whole === false ? "split" : "both")
        lyricsSwitch.checked = profile ? profile.save_lyrics : false
        errorText = ""
        open()
    }
    function save() {
        errorText = backend.saveProfile(editing, {
            name: nameField.text, mode: mode, max_height: quality, audio_format: audioFormat,
            embed_metadata: metaSwitch.checked, subtitles: subsSwitch.checked, playlist: listSwitch.checked,
            save_description: descSwitch.checked, save_transcript: transSwitch.checked,
            online_player: playerSwitch.checked, split_chapters: albumMode !== "whole", keep_whole: albumMode !== "split", save_lyrics: lyricsSwitch.checked })
        if (errorText === "")
            close()
    }

    modal: true
    focus: true
    parent: Overlay.overlay
    anchors.centerIn: parent
    width: Math.min(480, parent.width - 2 * Theme.s4)
    height: Math.min(content.implicitHeight + 2 * padding, parent.height - 2 * Theme.s4)
    padding: Theme.s5
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: Theme.dur } }
    exit: Transition { NumberAnimation { property: "opacity"; to: 0; duration: Theme.durFast } }
    Overlay.modal: Rectangle { color: Theme.dark ? "#99000000" : "#55000000" }
    background: Rectangle {
        radius: Theme.radiusCard + 4
        color: Theme.raised
        border.width: 1
        border.color: Theme.separator
    }

    Flickable {
        anchors.fill: parent
        contentHeight: content.implicitHeight
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        ColumnLayout {
            id: content
            width: parent.width
            spacing: Theme.s4

            Text {
                text: dlg.editing === "" ? qsTr("New profile") : qsTr("Edit profile")
                font.pixelSize: Theme.title
                font.weight: Font.DemiBold
                color: Theme.text
                Accessible.role: Accessible.Heading
            }
            AppField {
                id: nameField
                placeholderText: qsTr("Profile name")
                maximumLength: 40
                Layout.fillWidth: true
                onAccepted: dlg.save()
            }
            Segmented {
                Layout.fillWidth: true
                current: dlg.mode
                options: [{ text: qsTr("Video"), value: "video" }, { text: qsTr("Audio only"), value: "audio" }]
                onActivated: (v) => dlg.mode = v
            }
            ColumnLayout {
                visible: dlg.mode === "video"
                spacing: Theme.s2
                Layout.fillWidth: true
                Text { text: qsTr("Maximum quality"); color: Theme.textSecondary; font.pixelSize: Theme.footnote }
                Flow {
                    spacing: Theme.s2
                    Layout.fillWidth: true
                    Repeater {
                        model: dlg.qualities
                        delegate: Rectangle {
                            required property var modelData
                            readonly property bool on: dlg.quality === modelData.value
                            width: chipText.implicitWidth + 2 * Theme.s4
                            height: Theme.touch
                            radius: height / 2
                            color: on ? Theme.accentSoft : Theme.field
                            border.width: on ? 1.5 : 0
                            border.color: Theme.accent
                            activeFocusOnTab: true
                            Keys.onSpacePressed: dlg.quality = modelData.value
                            Text {
                                id: chipText
                                anchors.centerIn: parent
                                text: modelData.text
                                font.pixelSize: Theme.footnote + 1
                                color: parent.on ? Theme.accent : Theme.text
                            }
                            TapHandler { onTapped: dlg.quality = modelData.value }
                            Accessible.role: Accessible.RadioButton
                            Accessible.name: modelData.text
                            Accessible.checked: on
                        }
                    }
                }
            }
            ColumnLayout {
                visible: dlg.mode === "audio"
                spacing: Theme.s2
                Layout.fillWidth: true
                Text { text: qsTr("Audio format"); color: Theme.textSecondary; font.pixelSize: Theme.footnote }
                Segmented {
                    Layout.fillWidth: true
                    current: dlg.audioFormat
                    options: [{ text: "MP3", value: "mp3" }, { text: "AAC (M4A)", value: "m4a" },
                              { text: "Opus", value: "opus" }, { text: "FLAC", value: "flac" },
                              { text: qsTr("Original"), value: "best" }]
                    onActivated: (v) => dlg.audioFormat = v
                }
                Text {
                    visible: dlg.mode === "audio" && dlg.audioFormat === "mp3"
                    text: qsTr("MP3 is encoded at up to 320 kbps, as high as the source allows.")
                    color: Theme.textSecondary; font.pixelSize: Theme.footnote
                    wrapMode: Text.Wrap; Layout.fillWidth: true
                }
            }
            SettingsGroup {
                Layout.fillWidth: true
                SettingsRow { stacked: false; label: qsTr("Embed metadata and cover")
                              AppSwitch { id: metaSwitch } }
                SettingsRow { stacked: false; label: qsTr("Download subtitles"); visible: dlg.mode === "video"
                              AppSwitch { id: subsSwitch } }
                SettingsRow { stacked: false; label: qsTr("Download whole playlists")
                              hint: qsTr("Playlist links are always downloaded completely.")
                              AppSwitch { id: listSwitch } }
                SettingsRow { stacked: false; label: qsTr("Save description as HTML")
                              hint: qsTr("If the video has one. Links are clickable.")
                              AppSwitch { id: descSwitch } }
                SettingsRow { stacked: false; label: qsTr("Online player in the HTML page")
                              hint: qsTr("YouTube/Vimeo player like on the site (needs internet). The HTML page follows the app theme.")
                              AppSwitch { id: playerSwitch } }
                SettingsRow { stacked: true; label: qsTr("Album (tracklist in the description)")
                              hint: qsTr("Whole = one file with track markers. Tracks = one file per song in its own folder, named and tagged from the tracklist, plus a playlist. Both = keep the full file too.")
                              Segmented {
                                  Layout.fillWidth: true
                                  current: dlg.albumMode
                                  options: [{ text: qsTr("Whole"), value: "whole" }, { text: qsTr("Tracks"), value: "split" },
                                            { text: qsTr("Both"), value: "both" }]
                                  onActivated: (v) => dlg.albumMode = v
                              } }
                SettingsRow { stacked: false; label: qsTr("Find song lyrics")
                              hint: qsTr("Looks the text up online (LRCLIB), else uses the captions. Saved as TXT (and LRC with timing), written into MP3/M4A tags, and shown in the HTML page with the player.")
                              AppSwitch { id: lyricsSwitch } }
                SettingsRow { stacked: false; label: qsTr("Save transcript as TXT")
                              hint: qsTr("If subtitles exist (German or English).")
                              AppSwitch { id: transSwitch } }
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
                spacing: Theme.s2
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                AppButton { text: qsTr("Cancel"); onClicked: dlg.close() }
                AppButton { text: qsTr("Save"); kind: "primary"; onClicked: dlg.save() }
            }
        }
    }
}
