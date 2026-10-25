import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// Details of one download tile: state, hints about skipped parts, the full error text, actions.
Popup {
    id: dlg
    property var row: null                      // the DownloadRow it was opened for
    readonly property string st: row ? row.jobState : ""

    function openFor(r) { row = r; open() }

    modal: true
    focus: true
    parent: Overlay.overlay
    readonly property rect area: Theme.dialogArea.width > 0 ? Theme.dialogArea : Qt.rect(0, 0, Overlay.overlay ? Overlay.overlay.width : 0, Overlay.overlay ? Overlay.overlay.height : 0)
    x: area.x + (area.width - width) / 2
    y: area.y + (area.height - height) / 2
    width: Math.min(560, area.width - 2 * Theme.s4)
    height: Math.min(implicitHeight, area.height - 2 * Theme.s4)
    padding: Theme.s4
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    Overlay.modal: Rectangle { color: Theme.dark ? "#99000000" : "#55000000" }
    background: Rectangle {
        radius: Theme.radiusCard + 4
        color: Theme.raised
        border.width: 1
        border.color: Theme.separator
    }

    contentItem: ColumnLayout {
        spacing: Theme.s3
        Text {
            text: dlg.row ? dlg.row.title : ""
            color: Theme.text
            font.pixelSize: Theme.headline
            font.weight: Font.DemiBold
            wrapMode: Text.Wrap
            Layout.fillWidth: true
            Accessible.role: Accessible.Heading
        }
        Text {
            text: dlg.row ? (dlg.row.stateText() || dlg.row.phase) + (dlg.row.profile ? "  ·  " + dlg.row.profile : "") : ""
            color: dlg.st === "error" ? Theme.danger : Theme.textSecondary
            font.pixelSize: Theme.footnote
            Layout.fillWidth: true
        }
        TextEdit {
            text: dlg.row ? dlg.row.url : ""
            readOnly: true
            selectByMouse: true
            color: Theme.textSecondary
            font.pixelSize: Theme.footnote
            wrapMode: TextEdit.WrapAnywhere
            Layout.fillWidth: true
        }
        Rectangle {          // hint: parts that were skipped, the download continued
            visible: dlg.row && dlg.row.note !== ""
            radius: Theme.radius
            color: Theme.field
            Layout.fillWidth: true
            implicitHeight: noteText.implicitHeight + 2 * Theme.s3
            Text {
                id: noteText
                anchors { left: parent.left; right: parent.right; verticalCenter: parent.verticalCenter; margins: Theme.s3 }
                text: dlg.row ? dlg.row.note : ""
                color: Theme.text
                font.pixelSize: Theme.footnote
                wrapMode: Text.Wrap
            }
        }
        Text {
            visible: errorBox.visible
            text: qsTr("Why it stopped")
            color: Theme.textSecondary
            font.pixelSize: Theme.caption
        }
        ScrollView {
            id: errorBox
            visible: dlg.st === "error" && dlg.row && dlg.row.error !== ""
            Layout.fillWidth: true
            Layout.preferredHeight: Math.min(180, errorEdit.implicitHeight + 2 * Theme.s2)
            clip: true
            TextEdit {
                id: errorEdit
                width: errorBox.availableWidth
                text: dlg.row ? dlg.row.error : ""
                readOnly: true
                selectByMouse: true
                color: Theme.text
                font.pixelSize: Theme.footnote
                wrapMode: TextEdit.Wrap
            }
        }
        Text {
            visible: errorBox.visible && dlg.row.errorDetail !== ""
            text: qsTr("Technical details")
            color: Theme.textSecondary
            font.pixelSize: Theme.caption
        }
        TextEdit {
            visible: errorBox.visible && dlg.row.errorDetail !== ""
            text: dlg.row ? dlg.row.errorDetail : ""
            readOnly: true
            selectByMouse: true
            color: Theme.textSecondary
            font.pixelSize: Theme.caption
            wrapMode: TextEdit.Wrap
            Layout.fillWidth: true
        }
        Text {
            visible: dlg.row && dlg.row.extrasText !== ""
            text: dlg.row ? dlg.row.extrasText : ""
            color: Theme.textSecondary
            font.pixelSize: Theme.footnote
            wrapMode: Text.Wrap
            Layout.fillWidth: true
        }
        RowLayout {
            spacing: Theme.s2
            Layout.fillWidth: true
            AppButton { text: qsTr("Copy error"); visible: errorBox.visible
                        onClicked: backend.copyText(dlg.row.error + (dlg.row.errorDetail ? "\n\n" + dlg.row.errorDetail : "")) }
            AppButton { text: qsTr("Copy link"); onClicked: backend.copyText(dlg.row.url) }
            Item { Layout.fillWidth: true }
            AppButton { text: qsTr("Retry"); visible: dlg.row && dlg.row.failed
                        onClicked: { backend.retry(dlg.row.jobId); dlg.close() } }
            AppButton { text: qsTr("Open file"); visible: dlg.row && dlg.row.done && !backend.isMobile
                        onClicked: backend.openFile(dlg.row.jobId) }
            AppButton { text: qsTr("Close"); kind: "primary"; onClicked: dlg.close() }
        }
    }
}
