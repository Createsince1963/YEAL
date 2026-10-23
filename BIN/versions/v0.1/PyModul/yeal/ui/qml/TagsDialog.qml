import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// MP3 tags. After an MP3 download the tags are already filled in from the video description; this asks
// "Edit the tags?" (default: No). "Yes" - or "Edit MP3 tags..." in a download's menu - opens the editor.
Popup {
    id: dlg
    objectName: "tagsDialog"
    property var queue: []          // pending {jobId, title, direct}
    property var current: null
    property bool editing: false
    property var loaded: ({})       // tags as read from the file
    property var edited: ({})       // what the user typed (starts as a copy of `loaded`)
    property string loadError: ""
    property string saveError: ""

    readonly property var fieldDefs: [
        { key: "title", label: qsTr("Title") },
        { key: "artist", label: qsTr("Artist") },
        { key: "album", label: qsTr("Album") },
        { key: "genre", label: qsTr("Genre (separate several with ;)") },
        { key: "year", label: qsTr("Year") },
        { key: "mood", label: qsTr("Mood") },
        { key: "keywords", label: qsTr("Keywords") },
        { key: "comment", label: qsTr("Comment"), multiline: true }
    ]

    function enqueue(info) {
        queue = queue.concat([info])
        if (!opened) next()
    }
    // from the context menu of a finished download: straight into the editor
    function edit(jobId, title) { enqueue({ jobId: jobId, title: title, direct: true }) }
    function next() {
        editing = false
        loadError = ""
        saveError = ""
        if (queue.length === 0) { current = null; close(); return }
        current = queue[0]
        queue = queue.slice(1)
        if (current.direct) startEditing()
        open()
    }
    function startEditing() {
        var data = backend.tagsRead(current.jobId)
        loadError = data.error ? data.error : ""
        loaded = loadError === "" ? data : ({})
        var copy = ({})
        for (var k in loaded) copy[k] = loaded[k]
        edited = copy
        saveError = ""
        editing = true
    }
    function save() {
        var msg = backend.tagsSave(current.jobId, edited)
        if (msg !== "") { saveError = msg; return }
        next()
    }

    modal: true
    focus: true
    parent: Overlay.overlay
    readonly property rect area: Theme.dialogArea.width > 0 ? Theme.dialogArea : Qt.rect(0, 0, Overlay.overlay ? Overlay.overlay.width : 0, Overlay.overlay ? Overlay.overlay.height : 0)
    x: area.x + (area.width - width) / 2
    y: area.y + (area.height - height) / 2
    width: Math.min(520, area.width - 2 * Theme.s4)
    padding: Theme.s4
    closePolicy: Popup.NoAutoClose
    onOpened: if (!editing) noButton.forceActiveFocus()
    Overlay.modal: Rectangle { color: Theme.dark ? "#99000000" : "#55000000" }
    background: Rectangle {
        radius: Theme.radiusCard + 4
        color: Theme.raised
        border.width: 1
        border.color: Theme.separator
    }
    // Escape means "No" in the question and "Cancel" in the editor
    Shortcut { sequence: "Escape"; enabled: dlg.opened; onActivated: dlg.next() }

    contentItem: ColumnLayout {
        spacing: Theme.s3

        Text {
            text: dlg.editing ? qsTr("Edit MP3 tags") : qsTr("MP3 tags")
            color: Theme.text
            font.pixelSize: Theme.headline
            font.weight: Font.DemiBold
            Layout.fillWidth: true
            Accessible.role: Accessible.Heading
        }
        Text {
            text: dlg.current ? dlg.current.title : ""
            color: Theme.text
            font.pixelSize: Theme.body
            wrapMode: Text.Wrap
            maximumLineCount: 2
            elide: Text.ElideRight
            Layout.fillWidth: true
        }

        // ---- question (default: No) ----
        Text {
            visible: !dlg.editing
            text: qsTr("Genre, mood, keywords and more were filled in from the video description. Do you want to edit the tags?")
            color: Theme.textSecondary
            font.pixelSize: Theme.footnote
            wrapMode: Text.Wrap
            Layout.fillWidth: true
        }
        RowLayout {
            visible: !dlg.editing
            spacing: Theme.s2
            Layout.fillWidth: true
            Item { Layout.fillWidth: true }
            AppButton { text: qsTr("Yes, edit"); iconName: "sliders"; onClicked: dlg.startEditing() }
            AppButton { id: noButton; text: qsTr("No"); kind: "primary"; onClicked: dlg.next()
                        Keys.onReturnPressed: dlg.next(); Keys.onEnterPressed: dlg.next() }
        }
        AppButton {
            visible: !dlg.editing
            kind: "plain"
            text: qsTr("Don't ask again")
            onClicked: { backend.setSetting("ask_mp3_tags", false); dlg.next() }
            Layout.alignment: Qt.AlignLeft
        }

        // ---- editor ----
        Text {
            visible: dlg.editing && dlg.loadError !== ""
            text: dlg.loadError
            color: Theme.danger
            font.pixelSize: Theme.footnote
            wrapMode: Text.Wrap
            Layout.fillWidth: true
        }
        Flickable {
            id: flick
            visible: dlg.editing && dlg.loadError === ""
            Layout.fillWidth: true
            Layout.preferredHeight: Math.min(form.implicitHeight, Math.max(160, dlg.area.height - 260))
            contentWidth: width
            contentHeight: form.implicitHeight
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: ScrollBar {}

            ColumnLayout {
                id: form
                width: flick.width
                spacing: Theme.s2
                Repeater {
                    model: dlg.editing && dlg.loadError === "" ? dlg.fieldDefs : []
                    delegate: ColumnLayout {
                        id: fld
                        required property var modelData
                        Layout.fillWidth: true
                        spacing: 2
                        Text {
                            text: fld.modelData.label
                            color: Theme.textSecondary
                            font.pixelSize: Theme.caption
                        }
                        AppField {
                            visible: !fld.modelData.multiline
                            Layout.fillWidth: true
                            text: dlg.loaded[fld.modelData.key] || ""
                            onTextEdited: dlg.edited[fld.modelData.key] = text
                            Component.onCompleted: cursorPosition = 0      // show the start of long values
                            Accessible.name: fld.modelData.label
                        }
                        Rectangle {
                            visible: !!fld.modelData.multiline
                            Layout.fillWidth: true
                            Layout.preferredHeight: 88
                            radius: Theme.radius
                            color: Theme.field
                            border.width: area.activeFocus ? 2 : 1
                            border.color: area.activeFocus ? Theme.accent : Theme.separator
                            ScrollView {
                                anchors.fill: parent
                                TextArea {
                                    id: area
                                    text: dlg.loaded[fld.modelData.key] || ""
                                    wrapMode: TextEdit.Wrap
                                    font.pixelSize: Theme.body
                                    color: Theme.text
                                    selectionColor: Theme.accentSoft
                                    selectedTextColor: Theme.text
                                    leftPadding: Theme.s3
                                    rightPadding: Theme.s3
                                    topPadding: Theme.s2
                                    bottomPadding: Theme.s2
                                    background: null
                                    onTextChanged: if (activeFocus) dlg.edited[fld.modelData.key] = text
                                    Accessible.name: fld.modelData.label
                                }
                            }
                        }
                    }
                }
            }
        }
        Text {
            visible: dlg.editing && dlg.saveError !== ""
            text: dlg.saveError
            color: Theme.danger
            font.pixelSize: Theme.footnote
            wrapMode: Text.Wrap
            Layout.fillWidth: true
        }
        RowLayout {
            visible: dlg.editing
            spacing: Theme.s2
            Layout.fillWidth: true
            Item { Layout.fillWidth: true }
            AppButton { text: qsTr("Cancel"); onClicked: dlg.next() }
            AppButton { text: qsTr("Save"); kind: "primary"; enabled: dlg.loadError === ""; onClicked: dlg.save() }
        }
    }
}
