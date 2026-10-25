import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// Download location chooser: a dropdown with the Windows Downloads folder on top (default) followed by
// the drives that were found. The user picks one, optionally edits the folder name (drives only) and confirms.
Popup {
    id: dlg
    objectName: "externalDriveDialog"
    readonly property string downloadsId: "__downloads__"
    property var drives: []            // [{root,label,free,total,id,folder}]
    property string selectedId: downloadsId
    property string errorText: ""
    property string downloadsPath: ""
    // Dropdown entries: the Downloads folder first, then the drives sorted by letter.
    readonly property var entries: {
        var list = [{ id: downloadsId, isDownloads: true, root: downloadsPath, label: "", free: 0, total: 0,
                      title: qsTr("Downloads folder"), detail: downloadsPath }]
        for (var i = 0; i < drives.length; i++) {
            var d = drives[i]
            list.push({ id: d.id, isDownloads: false, root: d.root, label: d.label, free: d.free, total: d.total,
                        folder: d.folder,
                        title: d.root + (d.label ? "  " + d.label : ""),
                        detail: qsTr("%1 free of %2").arg(gb(d.free)).arg(gb(d.total)) })
        }
        return list
    }
    readonly property int selectedIndex: {
        for (var i = 0; i < entries.length; i++)
            if (entries[i].id === selectedId) return i
        return 0
    }
    readonly property var current: entries[selectedIndex]

    // Called once per newly detected drive; merges into the list shown (also while the dialog is open).
    function enqueue(info) {
        var list = drives.filter(function (d) { return d.id !== info.id })
        list.push(info)
        list.sort(function (a, b) { return a.root < b.root ? -1 : (a.root > b.root ? 1 : 0) })
        drives = list
        if (!opened) {
            downloadsPath = backend.userDownloadsDir()
            selectEntry(entries[0])          // topmost entry = Windows Downloads folder is the default
            errorText = ""
            open()
        }
    }
    function selectEntry(e) {
        if (!e) return
        selectedId = e.id
        nameField.text = e.folder || "Yeal"
        errorText = ""
    }
    function removeSelected() {
        if (current.isDownloads) return
        drives = drives.filter(function (d) { return d.id !== selectedId })
        selectEntry(entries[0])
        if (drives.length === 0) close()
    }
    function gb(bytes) {
        if (bytes >= 1099511627776) return (bytes / 1099511627776).toFixed(2) + " TB"
        return (bytes / 1073741824).toFixed(bytes < 10737418240 ? 1 : 0) + " GB"
    }
    function accept() {
        errorText = current.isDownloads ? backend.useDownloadsFolder()
                                        : backend.useExternalDrive(current.root, nameField.text)
        if (errorText === "") { drives = []; selectedId = downloadsId; close() }
    }
    function dismissAll() { drives = []; selectedId = downloadsId; close() }

    readonly property rect area: Theme.dialogArea.width > 0 ? Theme.dialogArea
        : Qt.rect(0, 0, Overlay.overlay ? Overlay.overlay.width : 0, Overlay.overlay ? Overlay.overlay.height : 0)
    modal: true
    focus: true
    parent: Overlay.overlay
    x: area.x + (area.width - width) / 2
    y: area.y + (area.height - height) / 2
    width: Math.min(760, area.width - 2 * Theme.s4)
    padding: Theme.s4
    closePolicy: Popup.NoAutoClose
    Overlay.modal: Rectangle { color: Theme.dark ? "#99000000" : "#55000000" }
    background: Rectangle {
        radius: Theme.radiusCard + 4
        color: Theme.raised
        border.width: 1
        border.color: Theme.separator
    }
    Shortcut { sequence: "Escape"; enabled: dlg.opened; onActivated: dlg.dismissAll() }

    contentItem: ColumnLayout {
        spacing: Theme.s3
        Text {
            text: dlg.drives.length > 1 ? qsTr("External drives found") : qsTr("External drive found")
            color: Theme.text
            font.pixelSize: Theme.headline
            font.weight: Font.DemiBold
            Layout.fillWidth: true
            Accessible.role: Accessible.Heading
        }
        Text {
            text: qsTr("Where should your downloads be saved?")
            color: Theme.text
            font.pixelSize: Theme.body
            wrapMode: Text.Wrap
            Layout.fillWidth: true
        }

        ComboBox {
            id: combo
            Layout.fillWidth: true
            implicitHeight: Theme.touch + 14
            model: dlg.entries
            textRole: "title"
            currentIndex: dlg.selectedIndex
            onActivated: function (i) { dlg.selectEntry(dlg.entries[i]) }
            Accessible.name: qsTr("Download location")
            font.pixelSize: Theme.body

            background: Rectangle {
                radius: Theme.radius
                color: Theme.field
                border.width: combo.activeFocus || combo.popup.visible ? 2 : 1
                border.color: combo.activeFocus || combo.popup.visible ? Theme.accent : Theme.separator
            }
            indicator: Text {
                x: combo.width - width - Theme.s3
                y: (combo.height - height) / 2
                text: "\u25BE"
                color: Theme.textSecondary
                font.pixelSize: Theme.body
            }
            contentItem: Item {
                Column {
                    x: Theme.s3
                    width: parent.width - 2 * Theme.s3 - 20
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 2
                    Text {
                        width: parent.width
                        text: dlg.current.title
                        color: Theme.text
                        font.pixelSize: Theme.body
                        font.weight: Font.Medium
                        elide: Text.ElideRight
                    }
                    Text {
                        width: parent.width
                        text: dlg.current.detail
                        color: Theme.textSecondary
                        font.pixelSize: Theme.footnote
                        elide: Text.ElideMiddle
                    }
                }
            }
            delegate: ItemDelegate {
                id: item
                required property var modelData
                required property int index
                width: combo.width
                highlighted: combo.highlightedIndex === index
                padding: Theme.s3
                background: Rectangle {
                    color: item.highlighted ? Qt.alpha(Theme.accent, 0.14) : "transparent"
                }
                contentItem: Column {
                    spacing: 2
                    Text {
                        width: item.width - 2 * Theme.s3
                        text: item.modelData.title
                        color: Theme.text
                        font.pixelSize: Theme.body
                        font.weight: item.modelData.id === dlg.selectedId ? Font.DemiBold : Font.Normal
                        elide: Text.ElideRight
                    }
                    Text {
                        width: item.width - 2 * Theme.s3
                        text: item.modelData.detail
                        color: Theme.textSecondary
                        font.pixelSize: Theme.footnote
                        elide: Text.ElideMiddle
                    }
                }
            }
            popup: Popup {
                y: combo.height + 2
                width: combo.width
                padding: 1
                implicitHeight: Math.min(contentItem.implicitHeight + 2, 320)
                contentItem: ListView {
                    clip: true
                    implicitHeight: contentHeight
                    model: combo.popup.visible ? combo.delegateModel : null
                    currentIndex: combo.highlightedIndex
                    ScrollIndicator.vertical: ScrollIndicator {}
                }
                background: Rectangle {
                    radius: Theme.radius
                    color: Theme.raised
                    border.width: 1
                    border.color: Theme.separator
                }
            }
        }
        // Usage bar of the selected drive (not for the Downloads folder: it lives on the system drive).
        Rectangle {
            visible: !dlg.current.isDownloads && dlg.current.total > 0
            Layout.fillWidth: true
            height: 6
            radius: 3
            color: Theme.separator
            Rectangle {
                width: parent.width * (dlg.current.total > 0
                    ? Math.min(1, 1 - dlg.current.free / dlg.current.total) : 0)
                height: parent.height
                radius: 3
                color: Theme.accent
            }
        }

        Text { visible: !dlg.current.isDownloads; text: qsTr("Folder to create in the root of the drive")
               color: Theme.textSecondary; font.pixelSize: Theme.footnote; Layout.fillWidth: true }
        AppField {
            id: nameField
            visible: !dlg.current.isDownloads
            maximumLength: 60
            Layout.fillWidth: true
            Accessible.name: qsTr("Folder name")
            onAccepted: dlg.accept()
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
            AppButton {
                text: qsTr("Don't ask again")
                visible: !dlg.current.isDownloads
                onClicked: { backend.ignoreExternalDrive(dlg.current.id); dlg.removeSelected() }
            }
            Item { Layout.fillWidth: true }
            AppButton { text: qsTr("Not now"); onClicked: dlg.dismissAll() }
            AppButton { text: dlg.current.isDownloads ? qsTr("Use this folder") : qsTr("Use this drive"); kind: "primary"; onClicked: dlg.accept() }
        }
    }
}
