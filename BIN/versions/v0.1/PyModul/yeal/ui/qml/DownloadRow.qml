import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

Rectangle {
    id: row

    // Roles exposed by JobModel (`jobState`, not `state`: Item already has `state`).
    signal framesRequested(int jobId, string title)
    signal tagsRequested(int jobId, string title)
    signal detailsRequested(var row)

    required property int jobId
    required property string title
    required property string url
    required property string filename
    required property string jobState
    required property real progress
    required property string speed
    required property string eta
    required property string error
    required property string playlistText
    required property string thumbnail
    required property string uploader
    required property string duration
    required property string size
    required property string profile
    required property string mode
    required property string extrasText
    required property string phase
    required property bool hasPage
    required property real dlProgress
    required property real ppProgress
    required property string convLabel
    required property string note
    required property string errorDetail
    required property string section
    readonly property bool groupCollapsed: backend.settings.ui_collapsed.indexOf(section) >= 0

    readonly property bool active: jobState === "fetching" || jobState === "downloading" || jobState === "processing"
    readonly property bool queued: jobState === "queued"
    readonly property bool failed: jobState === "error" || jobState === "canceled"
    readonly property bool done: jobState === "done"
    readonly property bool canFrames: done && mode === "video" && backend.ffmpegAvailable && !backend.isMobile
    readonly property bool canTags: done && mode === "audio" && backend.mp3TagsAvailable
                                    && filename.toLowerCase().endsWith(".mp3")
    readonly property bool indeterminate: false   // always a real percentage, every phase
    readonly property string percent: Math.round(progress * 100) + "%"
    readonly property string meta: [uploader, duration, size].filter(function (s) { return s !== "" }).join("  ·  ")

    function stateText() {
        switch (jobState) {
        case "queued": return qsTr("Waiting")
        case "fetching":
        case "downloading":
        case "processing": return ""   // shown by the two step bars
        case "done": return qsTr("Done")
        case "canceled": return qsTr("Canceled")
        case "error": return qsTr("Failed")
        }
        return jobState
    }

    implicitHeight: groupCollapsed ? 0 : content.implicitHeight + 2 * Theme.s3
    visible: !groupCollapsed
    radius: Theme.radiusCard
    color: Theme.surface
    border.width: Theme.dark ? 0 : 1
    border.color: Theme.separator

    TapHandler { acceptedButtons: Qt.RightButton; onTapped: ctxMenu.popup() }
    TapHandler { acceptedButtons: Qt.LeftButton; onLongPressed: ctxMenu.popup() }
    TapHandler {
        acceptedButtons: Qt.LeftButton
        gesturePolicy: TapHandler.ReleaseWithinBounds
        onTapped: row.detailsRequested(row)
        onDoubleTapped: if (row.done && !backend.isMobile) backend.openFile(row.jobId)
    }

    AppMenu {
        id: ctxMenu
        AppMenuItem { text: qsTr("Open file"); iconName: "open"; enabled: row.done && !backend.isMobile
                      onTriggered: backend.openFile(row.jobId) }
        AppMenuItem { text: qsTr("Play in VLC (fullscreen)"); iconName: "play"
                      enabled: row.done && backend.vlcAvailable; onTriggered: backend.openFileInVlc(row.jobId) }
        AppMenuItem { text: qsTr("Open page (with online player)"); iconName: "link"
                      enabled: row.hasPage && !backend.isMobile; onTriggered: backend.openPage(row.jobId) }
        AppMenuItem { text: qsTr("Show in folder"); iconName: "folder"; enabled: row.done && !backend.isMobile
                      onTriggered: backend.showInFolder(row.jobId) }
        AppMenuItem { text: qsTr("Split into images…"); iconName: "grid"
                      enabled: row.canFrames; onTriggered: row.framesRequested(row.jobId, row.title) }
        AppMenuItem { text: qsTr("Edit MP3 tags…"); iconName: "sliders"
                      enabled: row.canTags; onTriggered: row.tagsRequested(row.jobId, row.title) }
        AppMenuItem { text: qsTr("Details…"); iconName: "search"; onTriggered: row.detailsRequested(row) }
        MenuSeparator {}
        AppMenuItem { text: qsTr("Copy link"); iconName: "link"; onTriggered: backend.copyText(row.url) }
        AppMenuItem { text: qsTr("Copy error message"); iconName: "copy"; enabled: row.jobState === "error"
                      onTriggered: backend.copyText(row.error + (row.errorDetail ? "\n\n" + row.errorDetail : "")) }
        MenuSeparator {}
        AppMenuItem { text: qsTr("Retry"); iconName: "retry"; enabled: row.failed
                      onTriggered: backend.retry(row.jobId) }
        AppMenuItem { text: qsTr("Cancel"); iconName: "x"; enabled: row.active || row.queued
                      onTriggered: backend.cancel(row.jobId) }
        AppMenuItem { text: qsTr("Remove from list"); iconName: "trash"; destructive: true
                      enabled: !row.active && !row.queued; onTriggered: backend.remove(row.jobId) }
    }

    RowLayout {
        id: content
        anchors.fill: parent
        anchors.margins: Theme.s3
        spacing: Theme.s3

        Thumb {
            source: row.thumbnail
            mode: row.mode
            Layout.preferredWidth: Theme.compact ? 72 : 112
            Layout.preferredHeight: Theme.compact ? 48 : 63
            Layout.alignment: Qt.AlignTop
        }
        ColumnLayout {
            spacing: 3
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignVCenter

            Text {
                text: row.title
                color: Theme.text
                font.pixelSize: Theme.body
                font.weight: Font.Medium
                wrapMode: Text.Wrap
                maximumLineCount: 2
                elide: Text.ElideRight
                Layout.fillWidth: true
            }
            Text {
                visible: row.meta !== ""
                text: row.meta
                color: Theme.textSecondary
                font.pixelSize: Theme.footnote
                elide: Text.ElideRight
                Layout.fillWidth: true
            }
            StepBar {
                visible: row.active || row.queued
                Layout.fillWidth: true
                Layout.topMargin: 3
                caption: qsTr("Download")
                value: row.dlProgress
                waiting: row.queued
                detail: row.jobState === "fetching" ? qsTr("Preparing…")
                      : row.jobState === "downloading"
                        ? [row.playlistText ? qsTr("item %1").arg(row.playlistText) : "", row.speed,
                           row.eta ? qsTr("%1 left").arg(row.eta) : ""].filter(function (t) { return t !== "" }).join("  ·  ")
                        : ""
            }
            StepBar {
                visible: row.active || row.queued
                Layout.fillWidth: true
                caption: row.convLabel
                value: row.ppProgress
                waiting: row.queued || row.dlProgress < 1
                detail: row.jobState === "processing" ? row.phase : qsTr("Starts after the download")
            }
            RowLayout {
                spacing: Theme.s2
                Layout.fillWidth: true
                Icon {
                    visible: row.done || row.jobState === "error"
                    name: row.done ? "check" : "alert"
                    size: 15
                    color: row.done ? Theme.success : Theme.danger
                    strokeWidth: 2
                }
                Text {
                    text: row.stateText()
                    color: row.done ? Theme.success : row.jobState === "error" ? Theme.danger : Theme.textSecondary
                    font.pixelSize: Theme.footnote
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
                Badge { visible: row.profile !== "" && !Theme.compact; text: row.profile }
            }
            Text {
                visible: row.extrasText !== ""
                text: row.extrasText
                color: Theme.textSecondary
                font.pixelSize: Theme.caption
                elide: Text.ElideRight
                Layout.fillWidth: true
            }
            Text {
                visible: row.jobState === "error" && row.error !== ""
                text: row.error
                color: Theme.textSecondary
                font.pixelSize: Theme.caption
                wrapMode: Text.Wrap
                maximumLineCount: 3
                elide: Text.ElideRight
                Layout.fillWidth: true
            }
            Text {      // something optional was skipped; tap the tile for details
                visible: row.note !== "" && row.jobState !== "error"
                text: "\u26A0 " + row.note.split("\n")[0]
                color: Theme.textSecondary
                font.pixelSize: Theme.caption
                elide: Text.ElideRight
                Layout.fillWidth: true
            }
        }
        // Wide layout: explicit actions. Compact layout: one button (cancel, or the menu).
        RowLayout {
            spacing: 0
            Layout.alignment: Qt.AlignVCenter
            RingButton { visible: row.active || row.queued; tip: qsTr("Cancel")
                         progress: row.progress; indeterminate: row.indeterminate
                         onClicked: backend.cancel(row.jobId) }
            IconButton { visible: !Theme.compact && row.failed; iconName: "retry"; tip: qsTr("Retry")
                         onClicked: backend.retry(row.jobId) }
            IconButton { visible: !Theme.compact && row.done && !backend.isMobile; iconName: "open"; tip: qsTr("Open file")
                         onClicked: backend.openFile(row.jobId) }
            IconButton { visible: !Theme.compact && row.canFrames; iconName: "grid"; tip: qsTr("Split into images…")
                         onClicked: row.framesRequested(row.jobId, row.title) }
            IconButton { visible: !Theme.compact && row.hasPage && !backend.isMobile; iconName: "link"; tip: qsTr("Open page (with online player)")
                         onClicked: backend.openPage(row.jobId) }
            IconButton { visible: !Theme.compact && row.done && !backend.isMobile; iconName: "folder"; tip: qsTr("Show in folder")
                         onClicked: backend.showInFolder(row.jobId) }
            IconButton { visible: !Theme.compact && !row.active && !row.queued; iconName: "trash"; tip: qsTr("Remove from list")
                         onClicked: backend.remove(row.jobId) }
            IconButton { visible: Theme.compact && !row.active && !row.queued; iconName: "more"; tip: qsTr("More")
                         onClicked: ctxMenu.popup() }
        }
    }
}
