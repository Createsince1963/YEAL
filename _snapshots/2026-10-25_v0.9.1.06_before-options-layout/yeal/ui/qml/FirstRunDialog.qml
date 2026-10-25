import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Dialogs
import QtQuick.Layouts

// First start: choose the browser whose YouTube cookies yt-dlp may use, then the download folder.
Popup {
    id: dlg
    objectName: "firstRunDialog"
    property string browser: "chrome"
    property string folderValue: backend.settings.download_dir
    property string errorText: ""

    function displayPath(value) {
        var s = String(value || "")
        if (s.indexOf("file:") === 0) {
            s = decodeURIComponent(s.replace(/^file:\/\/\/?/, ""))
            if (Qt.platform.os === "windows") s = s.replace(/\//g, "\\")
        }
        return s
    }
    function finish() {
        errorText = backend.completeSetup(browser, folderValue)
        if (errorText === "") close()
    }

    FolderDialog {
        id: folderDialog
        title: qsTr("Choose your download folder")
        onAccepted: dlg.folderValue = selectedFolder.toString()
    }

    readonly property rect area: Theme.dialogArea.width > 0 ? Theme.dialogArea
        : Qt.rect(0, 0, Overlay.overlay ? Overlay.overlay.width : 0,
                  Overlay.overlay ? Overlay.overlay.height : 0)
    modal: true
    focus: true
    parent: Overlay.overlay
    x: area.x + (area.width - width) / 2
    y: area.y + (area.height - height) / 2
    width: Math.min(680, area.width - 2 * Theme.s4)
    padding: Theme.s5
    closePolicy: Popup.NoAutoClose
    Overlay.modal: Rectangle { color: Theme.dark ? "#B0000000" : "#66000000" }
    background: Rectangle {
        radius: Theme.radiusCard + 4
        color: Theme.raised
        border.width: 1
        border.color: Theme.separator
    }

    contentItem: ColumnLayout {
        spacing: Theme.s4
        Text {
            text: qsTr("Set up Yeal")
            color: Theme.text
            font.pixelSize: Theme.largeTitle
            font.weight: Font.DemiBold
            Layout.fillWidth: true
            Accessible.role: Accessible.Heading
        }
        Text {
            text: qsTr("Choose the browser used for protected YouTube downloads and where downloaded files are saved.")
            color: Theme.textSecondary
            font.pixelSize: Theme.body
            wrapMode: Text.Wrap
            Layout.fillWidth: true
        }

        Text { text: qsTr("1. Browser login"); color: Theme.text; font.pixelSize: Theme.headline; font.weight: Font.Medium }
        Text {
            text: qsTr("Chrome is selected by default. Sign in to YouTube in the selected browser; Google may refuse sign-in inside Yeal.")
            color: Theme.textSecondary
            font.pixelSize: Theme.footnote
            wrapMode: Text.Wrap
            Layout.fillWidth: true
        }
        Segmented {
            current: dlg.browser
            options: [{ text: "Chrome", value: "chrome" }, { text: "Edge", value: "edge" },
                      { text: "Firefox", value: "firefox" }, { text: qsTr("Off"), value: "" }]
            Layout.fillWidth: true
            onActivated: (v) => dlg.browser = v
        }

        Text { text: qsTr("2. Download folder"); color: Theme.text; font.pixelSize: Theme.headline; font.weight: Font.Medium }
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.s2
            AppField {
                Layout.fillWidth: true
                text: dlg.displayPath(dlg.folderValue)
                readOnly: true
                Accessible.name: qsTr("Selected download folder")
            }
            AppButton { text: qsTr("Choose…"); iconName: "folder"; onClicked: folderDialog.open() }
        }

        Rectangle { Layout.fillWidth: true; height: 1; color: Theme.separator }
        Text {
            text: qsTr("Admin login vault: initial password 1234. Yeal requires you to replace it with a private password before stored YouTube/browser logins can be used.")
            color: Theme.warning
            font.pixelSize: Theme.footnote
            wrapMode: Text.Wrap
            Layout.fillWidth: true
        }
        Text {
            visible: dlg.errorText !== ""
            text: dlg.errorText
            color: Theme.danger
            font.pixelSize: Theme.footnote
            wrapMode: Text.Wrap
            Layout.fillWidth: true
        }
        AppButton {
            text: qsTr("Save and start Yeal")
            iconName: "check"
            kind: "primary"
            Layout.alignment: Qt.AlignRight
            onClicked: dlg.finish()
        }
    }
}
