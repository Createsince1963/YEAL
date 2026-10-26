import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// Tidal download options (0.9.1), like the "YouTube options". Used in the workflow panel and in Settings > Tidal.
// Compact: the groups are small tiles in two columns (caption + current value); a click on a tile opens a pulldown with
// its choices (the extras can be ticked one after the other). Every choice writes its setting at once, so the
// values are also the defaults for the next start; they map to tiddl options (see core/tidal.py).
ColumnLayout {
    id: root
    readonly property var s: backend.settings
    property bool showQuality: true      // Settings has its own quality item; the workflow panel shows it here
    property int columns: 2
    spacing: Theme.s1

    readonly property var groups: [
        { key: "tidal_quality", caption: qsTr("Quality"), show: showQuality,
          options: [{ text: qsTr("Normal · MP3 320 kbps"), sub: qsTr("from AAC 320"), icon: "music", value: "normal" },
                    { text: qsTr("High · FLAC 1411 kbps"), sub: qsTr("16-bit / 44.1 kHz"), icon: "headphones", value: "high" },
                    { text: qsTr("Max · FLAC up to 9216 kbps"), sub: qsTr("24-bit / 192 kHz"), icon: "sparkle", value: "max" }] },
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
    function iconOf(g) {
        for (var i = 0; i < g.options.length; ++i) if (g.options[i].icon && s[g.key] === g.options[i].value) return g.options[i].icon
        return ""
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
                readonly property bool open: pop.opened
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                implicitHeight: 44
                radius: Theme.radius
                color: open ? Theme.accentSoft : hover.hovered ? Theme.hover : Theme.field
                border.width: open ? 1 : 0
                border.color: Theme.accent
                activeFocusOnTab: true
                Keys.onSpacePressed: open ? pop.close() : pop.open()
                Keys.onReturnPressed: open ? pop.close() : pop.open()
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
                        RowLayout {              // the icon first, then the format with its bitrate
                            Layout.fillWidth: true
                            spacing: 5
                            Icon { visible: root.iconOf(tile.modelData) !== ""; name: root.iconOf(tile.modelData); size: 14
                                   color: tile.open ? Theme.accent : Theme.textSecondary }
                            Text { text: root.summary(tile.modelData); color: tile.open ? Theme.accent : Theme.text
                                   font.pixelSize: Theme.footnote; font.weight: Font.Medium
                                   elide: Text.ElideRight; Layout.fillWidth: true }
                        }
                    }
                    Icon { name: "chevronDown"; size: 14; color: Theme.textSecondary; rotation: tile.open ? 180 : 0 }
                }
                HoverHandler { id: hover; cursorShape: Qt.PointingHandCursor }
                TapHandler { onTapped: tile.open ? pop.close() : pop.open() }
                Popup {                       // the pulldown of this group
                    id: pop
                    y: tile.height + 4
                    width: tile.width
                    padding: 3
                    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutsideParent
                    background: Rectangle { radius: Theme.radius + 2; color: Theme.raised; border.width: 1; border.color: Theme.separator }
                    contentItem: Column {
                        spacing: 0
                        Repeater {
                            model: tile.modelData.options
                            delegate: Rectangle {
                                id: choice
                                required property var modelData
                                readonly property bool on: modelData.key ? !!root.s[modelData.key] : root.s[tile.modelData.key] === modelData.value
                                width: pop.width - 2 * pop.padding
                                height: Theme.compact ? 44 : 34
                                radius: 6
                                color: ch.hovered ? Theme.hover : "transparent"
                                RowLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: Theme.s3; anchors.rightMargin: Theme.s3
                                    spacing: Theme.s2
                                    Icon { visible: !!choice.modelData.icon; name: choice.modelData.icon || "music"; size: 16
                                           color: choice.on ? Theme.accent : Theme.textSecondary }
                                    Text { text: choice.modelData.text; Layout.fillWidth: true; elide: Text.ElideRight
                                           color: choice.on ? Theme.accent : Theme.text; font.pixelSize: Theme.body }
                                    Text { visible: !!choice.modelData.sub; text: choice.modelData.sub || ""
                                           color: Theme.textTertiary; font.pixelSize: Theme.caption }
                                    Icon { visible: choice.on; name: "check"; size: 16; color: Theme.accent }
                                }
                                HoverHandler { id: ch; cursorShape: Qt.PointingHandCursor }
                                TapHandler {
                                    onTapped: {
                                        if (choice.modelData.key) backend.setSetting(choice.modelData.key, !choice.on)      // extras: tick one after the other
                                        else { backend.setSetting(tile.modelData.key, choice.modelData.value); pop.close() }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
