import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

Item {
    id: page
    signal useProfile()

    function describe(p) {
        var parts = [p.mode === "audio" ? qsTr("Audio · %1").arg(p.audio_format === "best" ? qsTr("original") : p.audio_format.toUpperCase())
                                         : (p.max_height === 0 ? qsTr("Video · best quality") : qsTr("Video · up to %1p").arg(p.max_height))]
        if (p.subtitles && p.mode === "video") parts.push(qsTr("subtitles"))
        if (p.playlist) parts.push(qsTr("playlists"))
        if (p.save_description) parts.push(qsTr("description"))
        if (p.save_transcript) parts.push(qsTr("transcript"))
        if (p.online_player) parts.push(qsTr("online player"))
        if (p.save_lyrics) parts.push(qsTr("lyrics"))
        if (p.split_chapters) parts.push(qsTr("album tracks"))
        if (p.embed_metadata) parts.push(qsTr("metadata"))
        return parts.join("  ·  ")
    }

    ProfileEditor { id: editor }
    ColumnLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.compact ? Theme.s4 : Theme.s6
        anchors.rightMargin: Theme.compact ? Theme.s4 : Theme.s6
        anchors.topMargin: Theme.compact ? Theme.s4 : Theme.s5
        spacing: Theme.s4

        RowLayout {
            Layout.fillWidth: true
            ColumnLayout {
                spacing: 2
                Layout.fillWidth: true
                Text {
                    text: qsTr("Profiles")
                    font.pixelSize: Theme.compact ? Theme.title : Theme.largeTitle
                    font.weight: Font.DemiBold
                    color: Theme.text
                    Accessible.role: Accessible.Heading
                }
                Text {
                    text: qsTr("A profile bundles format, quality and extras. Pick one on the Downloads page.")
                    color: Theme.textSecondary
                    font.pixelSize: Theme.footnote + 1
                    wrapMode: Text.Wrap
                    Layout.fillWidth: true
                }
            }
            AppButton { text: Theme.compact ? "" : qsTr("New profile"); iconName: "plus"; kind: "primary"
                        onClicked: editor.openFor(null) }
        }

        ListView {
            id: list
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.maximumWidth: 880
            model: backend.settings.profiles
            spacing: Theme.s2
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
            delegate: Rectangle {
                id: card
                required property var modelData
                readonly property bool active: modelData.name === backend.settings.active_profile
                width: ListView.view.width - (ListView.view.ScrollBar.vertical.visible ? 10 : 0)
                implicitHeight: Math.max(64, rowContent.implicitHeight + 2 * Theme.s3)
                radius: Theme.radiusCard
                color: Theme.surface
                border.width: active ? 1.5 : (Theme.dark ? 0 : 1)
                border.color: active ? Theme.accent : Theme.separator

                AppMenu {
                    id: menu
                    AppMenuItem { text: qsTr("Edit"); iconName: "pencil"; onTriggered: editor.openFor(card.modelData) }
                    AppMenuItem { text: qsTr("Duplicate"); iconName: "copy"
                                  onTriggered: backend.duplicateProfile(card.modelData.name) }
                    MenuSeparator {}
                    AppMenuItem {
                        text: qsTr("Delete"); iconName: "trash"; destructive: true
                        enabled: backend.settings.profiles.length > 1
                        onTriggered: { var e = backend.deleteProfile(card.modelData.name); if (e) toastRequest(e) }
                    }
                }
                TapHandler { acceptedButtons: Qt.RightButton; onTapped: menu.popup() }
                TapHandler { onDoubleTapped: { backend.setActiveProfile(card.modelData.name); page.useProfile() } }

                RowLayout {
                    id: rowContent
                    anchors.fill: parent
                    anchors.margins: Theme.s3
                    spacing: Theme.s3
                    Rectangle {
                        implicitWidth: 40
                        implicitHeight: 40
                        radius: 10
                        color: card.active ? Theme.accentSoft : Theme.field
                        Icon { anchors.centerIn: parent; size: 22
                               name: card.modelData.mode === "audio" ? "music" : "film"
                               color: card.active ? Theme.accent : Theme.textSecondary }
                    }
                    ColumnLayout {
                        spacing: 2
                        Layout.fillWidth: true
                        RowLayout {
                            spacing: Theme.s2
                            Text {
                                text: card.modelData.name
                                color: Theme.text
                                font.pixelSize: Theme.body
                                font.weight: Font.Medium
                                elide: Text.ElideRight
                                Layout.fillWidth: true
                            }
                            Badge { visible: card.active; text: qsTr("In use"); kind: "accent" }
                        }
                        Text {
                            text: page.describe(card.modelData)
                            color: Theme.textSecondary
                            font.pixelSize: Theme.footnote
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                        }
                    }
                    AppButton {
                        visible: !card.active && !Theme.compact
                        text: qsTr("Use")
                        onClicked: backend.setActiveProfile(card.modelData.name)
                    }
                    IconButton { iconName: "more"; tip: qsTr("More"); onClicked: menu.popup() }
                }
            }
        }
    }
    signal toastRequest(string message)
}
