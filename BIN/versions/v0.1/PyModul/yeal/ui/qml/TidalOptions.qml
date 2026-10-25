import QtQuick
import QtQuick.Layouts

// Tidal download options as chips (0.9.1), like the "YouTube options". Used in the workflow panel and in
// Settings > Tidal. Every chip writes its setting at once; the values map to tiddl options (see core/tidal.py).
ColumnLayout {
    id: root
    readonly property var s: backend.settings
    property bool showQuality: true      // the workflow panel also has the quality menu; both use tidal_quality
    spacing: Theme.s2

    // one row of exclusive chips with a small caption in front
    component ChoiceRow: Flow {
        id: choice
        property string caption
        property string key
        property var options: []         // [{text, value}]
        spacing: Theme.s2
        Layout.fillWidth: true
        Text {
            text: choice.caption
            color: Theme.textSecondary
            font.pixelSize: Theme.caption
            height: 32
            verticalAlignment: Text.AlignVCenter
            rightPadding: Theme.s1
        }
        Repeater {
            model: choice.options
            delegate: Chip {
                required property var modelData
                text: modelData.text
                checked: root.s[choice.key] === modelData.value
                onToggled: backend.setSetting(choice.key, modelData.value)
            }
        }
    }

    ChoiceRow {
        visible: root.showQuality
        caption: qsTr("Quality")
        key: "tidal_quality"
        options: [{ text: qsTr("Low"), value: "low" }, { text: qsTr("Normal"), value: "normal" },
                  { text: qsTr("High (FLAC)"), value: "high" }, { text: qsTr("Max (Hi-Res)"), value: "max" }]
    }
    ChoiceRow {
        caption: qsTr("Videos")
        key: "tidal_videos"
        options: [{ text: qsTr("None"), value: "none" }, { text: qsTr("With videos"), value: "allow" },
                  { text: qsTr("Only videos"), value: "only" }]
    }
    ChoiceRow {
        visible: root.s.tidal_videos !== "none"
        caption: qsTr("Video quality")
        key: "tidal_video_quality"
        options: [{ text: "SD", value: "sd" }, { text: "HD", value: "hd" }, { text: "Full HD", value: "fhd" }]
    }
    ChoiceRow {
        caption: qsTr("Dolby Atmos")
        key: "tidal_atmos"
        options: [{ text: qsTr("Off"), value: "none" }, { text: qsTr("With Atmos"), value: "allow" },
                  { text: qsTr("Only Atmos"), value: "only" }]
    }
    ChoiceRow {
        caption: qsTr("Artist singles")
        key: "tidal_singles"
        options: [{ text: qsTr("Albums only"), value: "none" }, { text: qsTr("With singles"), value: "include" },
                  { text: qsTr("Only singles"), value: "only" }]
    }
    Flow {
        spacing: Theme.s2
        Layout.fillWidth: true
        Repeater {
            model: [
                { text: qsTr("Lyrics in file"), key: "tidal_lyrics" },
                { text: qsTr("Lyrics (.lrc)"), key: "tidal_lrc" },
                { text: qsTr("Cover in file"), key: "tidal_cover_embed" },
                { text: qsTr("Cover image"), key: "tidal_cover_file" },
                { text: qsTr("Playlist (M3U)"), key: "tidal_m3u" },
                { text: qsTr("Player page (HTML)"), key: "tidal_html" },
                { text: qsTr("Overwrite existing"), key: "tidal_no_skip" },
                { text: qsTr("Rewrite tags"), key: "tidal_rewrite" }
            ]
            delegate: Chip {
                required property var modelData
                text: modelData.text
                checked: !!root.s[modelData.key]
                onToggled: (c) => backend.setSetting(modelData.key, c)
            }
        }
    }
}
