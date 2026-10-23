import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// Our workflow in one place: link -> options -> download -> list. Sits in the sidebar next to the
// YouTube view (inSidebar) or fills the Downloads page when there is no browser.
Item {
    id: panel
    property bool inSidebar: false
    signal manageProfiles()
    readonly property var stats: backend.stats
    readonly property string profileName: backend.settings.active_profile
    readonly property var activeProfile: {
        var list = backend.settings.profiles
        for (var i = 0; i < list.length; ++i)
            if (list[i].name === profileName) return list[i]
        return ({ save_description: false, save_transcript: false, online_player: false, split_chapters: false, save_lyrics: false, keep_whole: true })
    }
    readonly property var formatOptions: [
        { text: qsTr("Video"), value: "video" },
        { text: qsTr("Audio (MP3)"), value: "audio" }
    ]
    readonly property bool overlayOpen: framesDialog.opened || audioChoice.opened || liveDialog.opened || playlistDialog.opened || details.opened || duplicates.opened || driveDialog.opened || tagsDialog.opened

    function submit() {
        if (backend.addUrls(urlField.text) > 0) {
            urlField.clear()
            fromBrowser = false
        }
    }
    // Tracklist suggestion: the description of the linked video has timestamps -> offer an album.
    property string tracklistUrl: ""
    property int tracklistCount: 0
    property var tracklistDismissed: ({})
    readonly property bool showTracklistHint: tracklistUrl !== "" && urlField.text.indexOf(tracklistUrl) >= 0
                                              && !activeProfile.split_chapters && !tracklistDismissed[tracklistUrl]
    function dismissTracklist() { var d = tracklistDismissed; d[tracklistUrl] = true; tracklistDismissed = d }
    Timer {
        id: tracklistTimer
        interval: 700
        onTriggered: {
            var links = backend.extractLinks(urlField.text)
            if (links.length === 1 && !panel.activeProfile.split_chapters) backend.checkTracklist(links[0])
        }
    }
    function focusInput() { urlField.forceActiveFocus() }
    // Paste / drop only fill the link field; the download starts when the user confirms.
    property bool fromBrowser: false      // the link in the field came from the YouTube view
    function browserLink(url) {
        if (fillLinks(url))
            fromBrowser = true
    }
    function fillLinks(text) {
        fromBrowser = false
        var links = backend.extractLinks(text)
        if (links.length === 0) return false
        urlField.text = links.join("  ")
        urlField.forceActiveFocus()
        return true
    }
    function pasteLink() {
        if (!fillLinks(backend.clipboardText())) backend.notify(qsTr("No valid http(s) link in the clipboard."))
    }

    FramesDialog { id: framesDialog }
    AudioChoiceDialog { id: audioChoice }
    LiveStreamDialog { id: liveDialog }
    PlaylistDialog { id: playlistDialog }
    DownloadDetails { id: details }
    DuplicateDialog { id: duplicates }
    ExternalDriveDialog { id: driveDialog }
    TagsDialog { id: tagsDialog }
    Connections {
        target: backend
        function onTagsPrompt(info) { tagsDialog.enqueue(info) }
        function onAudioChoice(info) { audioChoice.enqueue(info) }
        function onLiveChoice(info) { liveDialog.enqueue(info) }
        function onPlaylistChoice(info) { playlistDialog.enqueue(info) }
        function onDuplicateFound(info) { duplicates.enqueue(info) }
        function onExternalDrive(info) { driveDialog.enqueue(info) }
        function onTracklistFound(url, count) { panel.tracklistUrl = url; panel.tracklistCount = count }
    }
    DropArea {
        anchors.fill: parent
        keys: ["text/plain"]
        onDropped: (drop) => { if (drop.hasText) panel.fillLinks(drop.text) }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.leftMargin: panel.inSidebar ? Theme.s2 : (Theme.compact ? Theme.s4 : Theme.s6)
        anchors.rightMargin: panel.inSidebar ? Theme.s2 : (Theme.compact ? Theme.s4 : Theme.s6)
        anchors.topMargin: panel.inSidebar ? Theme.s2 : (Theme.compact ? Theme.s4 : Theme.s5)
        anchors.bottomMargin: Theme.s2
        spacing: panel.inSidebar ? Theme.s3 : Theme.s4

        RowLayout {
            Layout.fillWidth: true
            Text {
                text: panel.inSidebar ? qsTr("Workflow") : qsTr("Downloads")
                font.pixelSize: panel.inSidebar ? Theme.headline : (Theme.compact ? Theme.title : Theme.largeTitle)
                font.weight: Font.DemiBold
                color: Theme.text
                Layout.fillWidth: true
                Accessible.role: Accessible.Heading
            }
            IconButton { iconName: "play"; tip: qsTr("Show / hide the YouTube browser")
                         visible: backend.browserAvailable
                         tint: backend.settings.show_browser ? Theme.accent : Theme.textSecondary
                         onClicked: backend.setSetting("show_browser", !backend.settings.show_browser) }
            IconButton { iconName: "stack"; tip: qsTr("Swap sides (drag the divider to resize)")
                         visible: panel.inSidebar
                         onClicked: backend.setSetting("panel_right", !backend.settings.panel_right) }
            IconButton { iconName: "grid"; tip: qsTr("Split video into images…")
                         visible: !backend.isMobile && backend.ffmpegAvailable
                         onClicked: framesDialog.openEmpty() }
            IconButton { iconName: "folder"; tip: qsTr("Open download folder"); visible: !backend.isMobile
                         onClicked: backend.openDownloadFolder() }
            AppButton {
                visible: panel.stats.done + panel.stats.failed > 0
                text: (Theme.compact || panel.inSidebar) ? "" : qsTr("Clear finished")
                iconName: "trash"
                kind: "plain"
                onClicked: backend.clearFinished()
            }
        }

        // Add card
        Rectangle {
            Layout.fillWidth: true
            Layout.maximumWidth: panel.inSidebar ? 100000 : 880
            implicitHeight: addCol.implicitHeight + 2 * Theme.s3
            radius: Theme.radiusCard
            color: Theme.surface
            border.width: Theme.dark ? 0 : 1
            border.color: Theme.separator

            ColumnLayout {
                id: addCol
                anchors.fill: parent
                anchors.margins: Theme.s3
                spacing: Theme.s3

                RowLayout {
                    spacing: Theme.s2
                    Layout.fillWidth: true
                    AppField {
                        id: urlField
                        placeholderText: qsTr("Paste a video or playlist link")
                        inputMethodHints: Qt.ImhUrlCharactersOnly | Qt.ImhNoPredictiveText
                        Layout.fillWidth: true
                        onAccepted: panel.submit()
                        onTextEdited: panel.fromBrowser = false
                        onTextChanged: tracklistTimer.restart()
                        Accessible.name: qsTr("Link")
                    }
                    IconButton { iconName: "clipboard"; tip: qsTr("Paste link from clipboard")
                                 onClicked: panel.pasteLink() }
                }
                Text {      // the browser view follows every video you open; nothing downloads until you confirm
                    visible: panel.fromBrowser && urlField.text !== ""
                    text: qsTr("Link of the video in the browser. Press Download to confirm, or open another video to switch.")
                    color: Theme.textSecondary
                    font.pixelSize: Theme.footnote
                    wrapMode: Text.Wrap
                    Layout.fillWidth: true
                }
                Segmented {
                    visible: Theme.compact
                    Layout.fillWidth: true
                    current: backend.settings.active_mode
                    options: panel.formatOptions
                    onActivated: (v) => backend.setFormatMode(v)
                }
                Flow {
                    spacing: Theme.s2
                    Layout.fillWidth: true
                    Chip {
                        text: qsTr("Description (HTML)")
                        checked: panel.activeProfile.save_description
                        onToggled: (c) => backend.setProfileFlag("save_description", c)
                    }
                    Chip {
                        text: qsTr("Transcript (TXT)")
                        checked: panel.activeProfile.save_transcript
                        onToggled: (c) => backend.setProfileFlag("save_transcript", c)
                    }
                    Chip {
                        text: qsTr("Online player (HTML)")
                        checked: panel.activeProfile.online_player
                        onToggled: (c) => backend.setProfileFlag("online_player", c)
                    }
                    Chip {
                        text: qsTr("Lyrics")
                        checked: panel.activeProfile.save_lyrics
                        onToggled: (c) => backend.setProfileFlag("save_lyrics", c)
                    }
                    Chip {
                        text: qsTr("Album tracks")
                        checked: panel.activeProfile.split_chapters
                        onToggled: (c) => backend.setAlbumMode(c ? "both" : "whole")
                    }
                }
                Flow {
                    visible: panel.activeProfile.split_chapters
                    spacing: Theme.s2
                    Layout.fillWidth: true
                    Chip {
                        text: qsTr("Tracks only")
                        checked: !panel.activeProfile.keep_whole
                        onToggled: (c) => backend.setAlbumMode("split")
                    }
                    Chip {
                        text: qsTr("Tracks + full file")
                        checked: panel.activeProfile.keep_whole
                        onToggled: (c) => backend.setAlbumMode("both")
                    }
                }
                Rectangle {     // suggestion: a tracklist was found in the description
                    visible: panel.showTracklistHint
                    Layout.fillWidth: true
                    implicitHeight: hintCol.implicitHeight + 2 * Theme.s2
                    radius: Theme.radius
                    color: Theme.accentSoft
                    ColumnLayout {
                        id: hintCol
                        anchors.fill: parent
                        anchors.margins: Theme.s2
                        spacing: Theme.s2
                        Text {
                            text: qsTr("Tracklist found (%1 tracks). Save it as an album with the song names?").arg(panel.tracklistCount)
                            color: Theme.text
                            font.pixelSize: Theme.footnote
                            wrapMode: Text.Wrap
                            Layout.fillWidth: true
                        }
                        Flow {
                            spacing: Theme.s2
                            Layout.fillWidth: true
                            Chip { text: qsTr("Tracks only"); onToggled: (c) => backend.setAlbumMode("split") }
                            Chip { text: qsTr("Tracks + full file"); onToggled: (c) => backend.setAlbumMode("both") }
                            Chip { text: qsTr("No thanks"); onToggled: (c) => panel.dismissTracklist() }
                        }
                    }
                }
                GridLayout {
                    columns: panel.inSidebar ? 2 : 3
                    columnSpacing: Theme.s2
                    rowSpacing: Theme.s2
                    Layout.fillWidth: true
                    AppButton {
                        id: profileButton
                        text: panel.profileName
                        iconName: "sliders"
                        Layout.fillWidth: panel.inSidebar
                        Layout.maximumWidth: panel.inSidebar ? 100000 : (Theme.compact ? 180 : 260)
                        onClicked: profileMenu.popup(profileButton, 0, profileButton.height + 4)
                        AppMenu {
                            id: profileMenu
                            Repeater {
                                model: backend.settings.profile_names
                                delegate: AppMenuItem {
                                    required property string modelData
                                    text: modelData
                                    marked: modelData === panel.profileName
                                    onTriggered: backend.setActiveProfile(modelData)
                                }
                            }
                            MenuSeparator {}
                            AppMenuItem { text: qsTr("Manage profiles…"); iconName: "stack"
                                          onTriggered: panel.manageProfiles() }
                        }
                    }
                    Segmented {
                        visible: !Theme.compact
                        Layout.fillWidth: !panel.inSidebar
                        Layout.maximumWidth: 280
                        Layout.alignment: Qt.AlignHCenter
                        current: backend.settings.active_mode
                        options: panel.formatOptions
                        onActivated: (v) => backend.setFormatMode(v)
                    }
                    ProgressButton {
                        text: showing ? qsTr("Downloading %1%").arg(Math.round(progress * 100)) : qsTr("Download")
                        iconName: showing ? "" : "download"
                        progress: urlField.text.trim() === "" ? panel.stats.progress : -1
                        enabled: urlField.text.trim() !== ""
                        Layout.columnSpan: panel.inSidebar ? 2 : 1
                        Layout.fillWidth: panel.inSidebar
                        onClicked: panel.submit()
                    }
                }
            }
        }

        Segmented {
            Layout.fillWidth: true
            Layout.maximumWidth: 520
            current: backend.settings.list_group
            options: [
                { text: qsTr("All"), value: "all" },
                { text: qsTr("Active"), value: "active" },
                { text: qsTr("Queued"), value: "queued" },
                { text: qsTr("Done"), value: "done" },
                { text: qsTr("Failed"), value: "failed" }
            ]
            onActivated: (value) => backend.setListGroup(value)
        }

        // List / empty state
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            // Subtle logo watermark, scaled to fit the field (decorative)
            Image {
                anchors.fill: parent
                anchors.margins: Theme.s2
                // as large as the field allows; subtle enough to sit behind the hint text and the rows
                source: "assets/logo_mark.png"
                sourceSize.width: 960
                fillMode: Image.PreserveAspectFit
                smooth: true
                opacity: Theme.dark ? 0.10 : 0.07
                Accessible.ignored: true
            }

            ListView {
                id: list
                anchors.fill: parent
                visible: count > 0
                model: backend.filteredModel
                spacing: Theme.s2
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                section.property: "section"
                section.criteria: ViewSection.FullString
                section.labelPositioning: ViewSection.InlineLabels
                section.delegate: Item {
                    id: head
                    required property string section
                    readonly property bool open: backend.settings.ui_collapsed.indexOf(section) < 0
                    width: ListView.view.width
                    height: 34
                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: Theme.s1
                        spacing: Theme.s2
                        Icon { name: "chevronRight"; size: 16; color: Theme.textSecondary
                               rotation: head.open ? 90 : 0
                               Behavior on rotation { NumberAnimation { duration: Theme.durFast } } }
                        Text {
                            text: head.section + "  (" + backend.sectionCount(head.section, panel.stats.all) + ")"
                            color: Theme.textSecondary
                            font.pixelSize: Theme.footnote
                            font.weight: Font.Medium
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                        }
                        IconButton { iconName: "trash"; tip: qsTr("Clear finished downloads of this group")
                                     onClicked: backend.clearSection(head.section) }
                    }
                    TapHandler { onTapped: backend.toggleSection(head.section) }
                    Accessible.role: Accessible.Button
                    Accessible.name: head.section
                }
                ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
                delegate: DownloadRow {
                    width: ListView.view.width - (ListView.view.ScrollBar.vertical.visible ? 10 : 0)
                    onFramesRequested: (id, t) => framesDialog.openForJob(id)
                    onTagsRequested: (id, t) => tagsDialog.edit(id, t)
                    onDetailsRequested: (r) => details.openFor(r)
                }
                add: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: Theme.dur } }
                remove: Transition { NumberAnimation { property: "opacity"; to: 0; duration: Theme.durFast } }
                displaced: Transition { NumberAnimation { properties: "y"; duration: Theme.dur; easing.type: Easing.OutCubic } }
            }
            EmptyState {
                id: emptyHint
                visible: list.count === 0 && list.height > implicitHeight + Theme.s4
                anchors { horizontalCenter: parent.horizontalCenter; bottom: parent.bottom; bottomMargin: Theme.s3 }
                iconName: panel.stats.all === 0 ? "" : "search"
                title: panel.stats.all === 0 ? qsTr("Nothing here yet") : qsTr("No downloads in this view")
                subtitle: panel.stats.all === 0
                    ? qsTr("Paste a link above, or drop one onto this window, to start your first download.")
                    : qsTr("Choose another filter to see the rest of your downloads.")
                actionText: panel.stats.all === 0 ? qsTr("Paste from clipboard") : ""
                onAction: panel.pasteLink()
            }
        }

        // Status footer
        RowLayout {
            spacing: Theme.s2
            Layout.fillWidth: true
            Layout.bottomMargin: Theme.s1
            Text {
                text: {
                    var p = []
                    if (panel.stats.active) p.push(qsTr("%1 active").arg(panel.stats.active))
                    if (panel.stats.queued) p.push(qsTr("%1 waiting").arg(panel.stats.queued))
                    if (panel.stats.speed) p.push(panel.stats.speed)
                    return p.length ? p.join("  ·  ") : qsTr("Ready")
                }
                color: Theme.textSecondary
                font.pixelSize: Theme.footnote
                Layout.fillWidth: true
                elide: Text.ElideRight
            }
            Badge { visible: !backend.ffmpegAvailable && !Theme.compact; kind: "warning"; text: qsTr("No ffmpeg") }
            Badge { visible: !backend.jsRuntimeAvailable && !Theme.compact; kind: "warning"; text: qsTr("No JS runtime") }
        }
    }
}
