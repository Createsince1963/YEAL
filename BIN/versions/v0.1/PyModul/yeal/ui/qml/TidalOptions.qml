import QtQuick
import QtQuick.Layouts

// Tidal download options (0.9.1), like the "YouTube options". Used in the workflow panel and in Settings > Tidal.
// Compact: the groups are small tiles in two columns (caption + current value); the chips of a group appear
// below the tiles only when the user opens it, one group at a time. Every chip writes its setting at once, so the
// values are also the defaults for the next start; they map to tiddl options (see core/tidal.py).
ColumnLayout {
    id: root
    readonly property var s: backend.settings
    property bool showQuality: true      // Settings has its own quality item; the workflow panel shows it here
    property int columns: 2
    property string openKey: ""          // the one expanded group ("" = all collapsed)
    spacing: Theme.s1

    readonly property var groups: [
        { key: "tidal_quality", caption: qsTr("Quality"), show: showQuality,
          options: [{ text: qsTr("Low"), value: "low" }, { text: qsTr("Normal"), value: "normal" },
                    { text: qsTr("High (FLAC)"), value: "high" }, { text: qsTr("Max (Hi-Res)"), value: "max" }] },
        { key: "tidal_videos", caption: qsTr("Videos"), show: true,
          options: [{ text: qsTr("None"), value: "none" }, { text: qsTr("With videos"), value: "allow" },
                    { text: qsTr("Only videos"), value: "only" }] },
        { key: "tidal_video_quality", caption: qsTr("Video quality"), show: s.tidal_videos !== "none",
          options: [{ text: "SD", value: "sd" }, { text: "HD", value: "hd" }, { text: "Full HD", value: "fhd" }] },
        { key: "tidal_atmos", caption: qsTr("Dolby Atmos"), show: true,
          options: [{ text: qsTr("Off"), value: "none" }, { text: qsTr("With Atmos"), value: "allow" },
                    { text: qsTr("Only Atmos"), value: "only" }] },
        { key: "tidal_singles", caption: qsTr("Artist singles"), show: true,
          options: [{ text: qsTr("Albums only"), value: "none" }, { text: qsTr("With singles"), value: "include" },
                    { text: qsTr("Only singles"), value: "only" }] },
        { key: "_extras", caption: qsTr("Extras"), show: true,
          options: [{ text: qsTr("Lyrics in file"), key: "tidal_lyrics" }, { text: qsTr("Lyrics (.lrc)"), key: "tidal_lrc" },
                    { text: qsTr("Cover in file"), key: "tidal_cover_embed" }, { text: qsTr("Cover image"), key: "tidal_cover_file" },
                    { text: qsTr("Playlist (M3U)"), key: "tidal_m3u" }, { text: qsTr("Player page (HTML)"), key: "tidal_html" },
                    { text: qsTr("Overwrite existing"), key: "tidal_no_skip" }, { text: qsTr("Rewrite tags"), key: "tidal_rewrite" }] }
    ]
    readonly property var shown: groups.filter(function (g) { return g.show })
    readonly property var openGroup: {
        for (var i = 0; i < shown.length; ++i) if (shown[i].key === openKey) return shown[i]
        return null
    }
    function summary(g) {
        if (g.key === "_extras") {
            var on = g.options.filter(function (o) { return !!s[o.key] }).map(function (o) { return o.text })
            return on.length === 0 ? qsTr("None") : on.length <= 2 ? on.join(", ") : qsTr("%1 on").arg(on.length)
        }
        for (var i = 0; i < g.options.length; ++i) if (s[g.key] === g.options[i].value) return g.options[i].text
        return ""
    }
    // one line for the collapsed header of the workflow panel
    readonly property string overview: {
        var parts = []
        for (var i = 0; i < groups.length; ++i)
            if (groups[i].key === "tidal_quality" || groups[i].key === "_extras" || groups[i].key === "tidal_videos")
                parts.push(summary(groups[i]))
        return parts.join(" · ")
    }

    GridLayout {
        Layout.fillWidth: true
        columns: root.columns
        columnSpacing: Theme.s1
        rowSpacing: Theme.s1
        Repeater {
            model: root.shown
            delegate: Rectangle {
                id: tile
                required property var modelData
                readonly property bool open: root.openKey === modelData.key
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                implicitHeight: 44
                radius: Theme.radius
                color: open ? Theme.accentSoft : hover.hovered ? Theme.hover : Theme.field
                border.width: open ? 1 : 0
                border.color: Theme.accent
                activeFocusOnTab: true
                Keys.onSpacePressed: root.openKey = open ? "" : modelData.key
                Keys.onReturnPressed: root.openKey = open ? "" : modelData.key
                Accessible.role: Accessible.Button
                Accessible.name: modelData.caption + ": " + root.summary(modelData)
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: Theme.s2
                    anchors.rightMargin: Theme.s2
                    spacing: Theme.s1
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 0
                        Text { text: tile.modelData.caption; color: Theme.textSecondary; font.pixelSize: Theme.caption
                               elide: Text.ElideRight; Layout.fillWidth: true }
                        Text { text: root.summary(tile.modelData); color: tile.open ? Theme.accent : Theme.text
                               font.pixelSize: Theme.footnote; font.weight: Font.Medium
                               elide: Text.ElideRight; Layout.fillWidth: true }
                    }
                    Icon { name: "chevronDown"; size: 14; color: Theme.textSecondary; rotation: tile.open ? 180 : 0 }
                }
                HoverHandler { id: hover; cursorShape: Qt.PointingHandCursor }
                TapHandler { onTapped: root.openKey = tile.open ? "" : tile.modelData.key }
            }
        }
    }

    // the chips of the opened group, across the full width
    Flow {
        visible: root.openGroup !== null
        spacing: Theme.s2
        Layout.fillWidth: true
        Layout.topMargin: Theme.s1
        Layout.bottomMargin: Theme.s1
        Repeater {
            model: root.openGroup ? root.openGroup.options : []
            delegate: Chip {
                required property var modelData
                text: modelData.text
                checked: modelData.key ? !!root.s[modelData.key] : root.s[root.openGroup.key] === modelData.value
                onToggled: (c) => modelData.key ? backend.setSetting(modelData.key, c)
                                                : backend.setSetting(root.openGroup.key, modelData.value)
            }
        }
    }
}
