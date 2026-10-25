import QtQuick
import QtQuick.Layouts

// Tidal download options (0.9.1), like the "YouTube options". Used in the workflow panel and in Settings > Tidal.
// Every group is one collapsed line (caption + current value); the chips of a group appear below it only when the
// user opens it, one group at a time. Every chip writes its setting at once; the values map to tiddl options
// (see core/tidal.py).
ColumnLayout {
    id: root
    readonly property var s: backend.settings
    property bool showQuality: true      // the workflow panel also has the quality menu; both use tidal_quality
    property string openKey: ""          // the one expanded group ("" = all collapsed)
    spacing: 2

    // collapsed header line: caption, current value, chevron
    component GroupHeader: Rectangle {
        id: head
        property string caption
        property string summary
        property bool expanded: false
        signal clicked()
        Layout.fillWidth: true
        implicitHeight: 34
        radius: Theme.radius
        color: hover.hovered ? Theme.hover : (expanded ? Theme.pressed : "transparent")
        activeFocusOnTab: true
        Keys.onSpacePressed: head.clicked()
        Keys.onReturnPressed: head.clicked()
        Accessible.role: Accessible.Button
        Accessible.name: caption + ": " + summary
        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: Theme.s2
            anchors.rightMargin: Theme.s2
            spacing: Theme.s2
            Text {
                text: head.caption
                color: Theme.textSecondary
                font.pixelSize: Theme.caption
                Layout.preferredWidth: 96
            }
            Text {
                text: head.summary
                color: Theme.text
                font.pixelSize: Theme.footnote
                elide: Text.ElideRight
                Layout.fillWidth: true
            }
            Icon { name: "chevronDown"; size: 14; color: Theme.textSecondary; rotation: head.expanded ? 180 : 0 }
        }
        HoverHandler { id: hover; cursorShape: Qt.PointingHandCursor }
        TapHandler { onTapped: head.clicked() }
    }

    // one group of exclusive chips
    component ChoiceGroup: ColumnLayout {
        id: grp
        property string caption
        property string key
        property var options: []         // [{text, value}]
        readonly property bool expanded: root.openKey === key
        readonly property string summary: {
            for (var i = 0; i < options.length; ++i)
                if (root.s[key] === options[i].value) return options[i].text
            return ""
        }
        Layout.fillWidth: true
        spacing: 0
        GroupHeader {
            caption: grp.caption
            summary: grp.summary
            expanded: grp.expanded
            onClicked: root.openKey = grp.expanded ? "" : grp.key
        }
        Flow {
            visible: grp.expanded
            spacing: Theme.s2
            Layout.fillWidth: true
            Layout.leftMargin: Theme.s2
            Layout.topMargin: Theme.s1
            Layout.bottomMargin: Theme.s2
            Repeater {
                model: grp.options
                delegate: Chip {
                    required property var modelData
                    text: modelData.text
                    checked: root.s[grp.key] === modelData.value
                    onToggled: backend.setSetting(grp.key, modelData.value)
                }
            }
        }
    }

    ChoiceGroup {
        visible: root.showQuality
        caption: qsTr("Quality")
        key: "tidal_quality"
        options: [{ text: qsTr("Low"), value: "low" }, { text: qsTr("Normal"), value: "normal" },
                  { text: qsTr("High (FLAC)"), value: "high" }, { text: qsTr("Max (Hi-Res)"), value: "max" }]
    }
    ChoiceGroup {
        caption: qsTr("Videos")
        key: "tidal_videos"
        options: [{ text: qsTr("None"), value: "none" }, { text: qsTr("With videos"), value: "allow" },
                  { text: qsTr("Only videos"), value: "only" }]
    }
    ChoiceGroup {
        visible: root.s.tidal_videos !== "none"
        caption: qsTr("Video quality")
        key: "tidal_video_quality"
        options: [{ text: "SD", value: "sd" }, { text: "HD", value: "hd" }, { text: "Full HD", value: "fhd" }]
    }
    ChoiceGroup {
        caption: qsTr("Dolby Atmos")
        key: "tidal_atmos"
        options: [{ text: qsTr("Off"), value: "none" }, { text: qsTr("With Atmos"), value: "allow" },
                  { text: qsTr("Only Atmos"), value: "only" }]
    }
    ChoiceGroup {
        caption: qsTr("Artist singles")
        key: "tidal_singles"
        options: [{ text: qsTr("Albums only"), value: "none" }, { text: qsTr("With singles"), value: "include" },
                  { text: qsTr("Only singles"), value: "only" }]
    }

    // switches: lyrics, cover, playlist files, overwrite
    ColumnLayout {
        id: extras
        readonly property var items: [
            { text: qsTr("Lyrics in file"), key: "tidal_lyrics" },
            { text: qsTr("Lyrics (.lrc)"), key: "tidal_lrc" },
            { text: qsTr("Cover in file"), key: "tidal_cover_embed" },
            { text: qsTr("Cover image"), key: "tidal_cover_file" },
            { text: qsTr("Playlist (M3U)"), key: "tidal_m3u" },
            { text: qsTr("Player page (HTML)"), key: "tidal_html" },
            { text: qsTr("Overwrite existing"), key: "tidal_no_skip" },
            { text: qsTr("Rewrite tags"), key: "tidal_rewrite" }
        ]
        readonly property bool expanded: root.openKey === "_extras"
        readonly property string summary: {
            var on = items.filter(function (it) { return !!root.s[it.key] }).map(function (it) { return it.text })
            if (on.length === 0) return qsTr("None")
            return on.length <= 2 ? on.join(", ") : qsTr("%1 on").arg(on.length)
        }
        Layout.fillWidth: true
        spacing: 0
        GroupHeader {
            caption: qsTr("Extras")
            summary: extras.summary
            expanded: extras.expanded
            onClicked: root.openKey = extras.expanded ? "" : "_extras"
        }
        Flow {
            visible: extras.expanded
            spacing: Theme.s2
            Layout.fillWidth: true
            Layout.leftMargin: Theme.s2
            Layout.topMargin: Theme.s1
            Layout.bottomMargin: Theme.s2
            Repeater {
                model: extras.items
                delegate: Chip {
                    required property var modelData
                    text: modelData.text
                    checked: !!root.s[modelData.key]
                    onToggled: (c) => backend.setSetting(modelData.key, c)
                }
            }
        }
    }
}
