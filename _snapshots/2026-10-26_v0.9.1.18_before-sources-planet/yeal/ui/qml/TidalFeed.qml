import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// Feed of the TIDAL DIY view: new releases of followed artists and monthly mixes as a compact list,
// grouped into "New", "Last week", "This month" and "Earlier".
Item {
    id: feed
    property var ctl
    TidalRequest { id: req; route: "feed" }

    function group(it) {
        if (it.seen === false) return qsTr("New")
        var d = new Date(it.date + "T00:00:00")
        var days = (Date.now() - d.getTime()) / 86400000
        if (days <= 7) return qsTr("Last week")
        if (days <= 31) return qsTr("This month")
        return qsTr("Earlier")
    }
    readonly property var rows: (req.data || []).map(function (it) { return Object.assign({ group: feed.group(it) }, it) })

    ListView {
        id: view
        anchors.fill: parent
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
        model: feed.rows
        header: Text {
            text: qsTr("Feed")
            font.pixelSize: Theme.title
            font.weight: Font.DemiBold
            color: Theme.text
            bottomPadding: Theme.s2
        }
        section.property: "modelData.group"
        section.delegate: Text {
            required property string section
            text: section
            font.pixelSize: Theme.headline
            font.weight: Font.DemiBold
            color: Theme.text
            topPadding: Theme.s3
            bottomPadding: Theme.s1
        }
        delegate: Rectangle {
            id: line
            required property var modelData
            width: view.width - Theme.s2
            implicitHeight: 56
            radius: 8
            color: lineHover.hovered ? Theme.hover : "transparent"
            RowLayout {
                anchors.fill: parent
                anchors.margins: Theme.s1
                spacing: Theme.s3
                Rectangle {
                    implicitWidth: 46; implicitHeight: 46; radius: 6
                    color: Theme.field
                    clip: true
                    Image { anchors.fill: parent; source: line.modelData.cover || ""; sourceSize.width: 120; fillMode: Image.PreserveAspectCrop; asynchronous: true }
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 0
                    Text { text: line.modelData.title || ""; color: Theme.text; font.pixelSize: Theme.footnote; font.weight: Font.Medium; elide: Text.ElideRight; Layout.fillWidth: true }
                    Text {
                        text: (line.modelData.kind === "album" ? (line.modelData.type === "SINGLE" ? qsTr("Single") : line.modelData.type === "EP" ? "EP" : qsTr("Album")) + qsTr(" by ") : "")
                              + (line.modelData.subtitle || "")
                        color: Theme.textSecondary; font.pixelSize: Theme.caption; elide: Text.ElideRight; Layout.fillWidth: true
                    }
                }
                Badge { visible: (line.modelData.quality || "") === "MAX"; text: "MAX"; kind: "accent" }
                Text { text: line.modelData.date || ""; color: Theme.textTertiary; font.pixelSize: Theme.caption }
                IconButton { iconName: "play"; tip: qsTr("Play"); onClicked: feed.ctl.playItem(line.modelData) }
            }
            HoverHandler { id: lineHover; cursorShape: Qt.PointingHandCursor }
            TapHandler { onTapped: feed.ctl.open(line.modelData) }
            TapHandler { acceptedButtons: Qt.RightButton; onTapped: feed.ctl.itemMenu(line.modelData, []) }
        }
    }
    TidalStatus { anchors.centerIn: parent; request: req; empty: feed.rows.length === 0; emptyText: qsTr("No news from the artists you follow.") }
}
