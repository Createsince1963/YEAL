import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// Settings > Admin: stored logins, locked with the admin password. Content is only requested while unlocked.
ColumnLayout {
    id: root
    spacing: 0
    Layout.fillWidth: true
    property int version: 0                      // bumped to refresh the list
    property string editId: ""
    readonly property var entries: { root.version; return backend.vaultUnlocked ? backend.vaultEntries() : [] }

    Connections { target: backend; function onVaultChanged() { root.version++ } }

    // ---- locked ----
    SettingsRow {
        visible: !backend.vaultUnlocked
        label: qsTr("Admin password")
        hint: backend.vaultDefaultPassword ? qsTr("Still the initial password. Unlock and change it.") : qsTr("Unlock to see the stored logins.")
        stacked: true
        RowLayout {
            spacing: Theme.s2
            Layout.fillWidth: true
            AppField {
                id: pw
                Layout.fillWidth: true
                echoMode: TextInput.Password
                placeholderText: qsTr("Password")
                onAccepted: unlockBtn.clicked()
            }
            AppButton {
                id: unlockBtn
                text: qsTr("Unlock")
                kind: "primary"
                onClicked: { err.text = backend.vaultUnlock(pw.text); pw.clear() }
            }
        }
    }
    SettingsRow {
        visible: !backend.vaultUnlocked && err.text !== ""
        label: ""
        Text { id: err; color: Theme.danger; font.pixelSize: Theme.footnote; Layout.fillWidth: true; wrapMode: Text.Wrap }
    }

    // ---- unlocked: list ----
    Repeater {
        model: root.entries
        delegate: SettingsRow {
            required property var modelData
            label: modelData.service
            hint: modelData.user + (modelData.note ? "  ·  " + modelData.note : "")
            stacked: false
            RowLayout {
                spacing: Theme.s1
                IconButton { iconName: "clipboard"; tip: qsTr("Copy user name"); onClicked: backend.vaultCopy(modelData.id, true) }
                AppButton { text: qsTr("Copy password"); onClicked: backend.vaultCopy(modelData.id, false) }
                IconButton { iconName: "sliders"; tip: qsTr("Edit")
                             onClicked: { root.editId = modelData.id; svc.text = modelData.service; usr.text = modelData.user
                                          note.text = modelData.note; pass.text = "" } }
                IconButton { iconName: "trash"; tip: qsTr("Delete"); onClicked: backend.vaultDelete(modelData.id) }
            }
        }
    }
    SettingsRow {
        visible: backend.vaultUnlocked && root.entries.length === 0
        label: qsTr("No logins stored yet")
        hint: qsTr("Add one below. Sign-ins you do in the browser view stay in the browser profile; Yeal cannot read them.")
        stacked: true
    }

    // ---- unlocked: add / edit ----
    SettingsRow {
        visible: backend.vaultUnlocked
        label: root.editId ? qsTr("Edit login") : qsTr("Add login")
        hint: root.editId ? qsTr("Leave the password empty to keep the stored one.") : ""
        stacked: true
        ColumnLayout {
            spacing: Theme.s2
            Layout.fillWidth: true
            AppField { id: svc; Layout.fillWidth: true; placeholderText: qsTr("Service (e.g. YouTube)") }
            AppField { id: usr; Layout.fillWidth: true; placeholderText: qsTr("User / e-mail") }
            AppField { id: pass; Layout.fillWidth: true; echoMode: TextInput.Password; placeholderText: qsTr("Password") }
            AppField { id: note; Layout.fillWidth: true; placeholderText: qsTr("Note (optional)") }
            Text { id: saveErr; color: Theme.danger; font.pixelSize: Theme.footnote; visible: text !== ""; wrapMode: Text.Wrap; Layout.fillWidth: true }
            RowLayout {
                spacing: Theme.s2
                AppButton {
                    text: root.editId ? qsTr("Save") : qsTr("Add"); kind: "primary"
                    onClicked: {
                        saveErr.text = backend.vaultSave({ id: root.editId, service: svc.text, user: usr.text,
                                                           password: pass.text, note: note.text })
                        if (saveErr.text === "") { root.editId = ""; svc.clear(); usr.clear(); pass.clear(); note.clear() }
                    }
                }
                AppButton { visible: root.editId !== ""; text: qsTr("Cancel")
                            onClicked: { root.editId = ""; svc.clear(); usr.clear(); pass.clear(); note.clear() } }
            }
        }
    }

    // ---- unlocked: password / lock / wipe ----
    SettingsRow {
        visible: backend.vaultUnlocked
        label: qsTr("Change admin password")
        hint: backend.vaultDefaultPassword ? qsTr("Recommended: the initial password is publicly known.") : qsTr("At least 8 characters.")
        stacked: true
        ColumnLayout {
            spacing: Theme.s2
            Layout.fillWidth: true
            AppField { id: oldPw; Layout.fillWidth: true; echoMode: TextInput.Password; placeholderText: qsTr("Current password") }
            AppField { id: newPw; Layout.fillWidth: true; echoMode: TextInput.Password; placeholderText: qsTr("New password") }
            Text { id: pwMsg; font.pixelSize: Theme.footnote; visible: text !== ""; wrapMode: Text.Wrap; Layout.fillWidth: true
                   color: text === qsTr("Password changed.") ? Theme.textSecondary : Theme.danger }
            AppButton {
                text: qsTr("Change password")
                onClicked: {
                    var e = backend.vaultChangePassword(oldPw.text, newPw.text)
                    pwMsg.text = e === "" ? qsTr("Password changed.") : e
                    if (e === "") { oldPw.clear(); newPw.clear() }
                }
            }
        }
    }
    SettingsRow {
        visible: backend.vaultUnlocked
        label: qsTr("Lock now")
        hint: qsTr("Locks itself after 5 minutes.")
        stacked: false
        AppButton { text: qsTr("Lock"); onClicked: backend.vaultLock() }
    }
    SettingsRow {
        visible: backend.vaultUnlocked
        label: qsTr("Delete all logins")
        hint: qsTr("Removes the vault now and the YouTube sign-in of the browser view at the next start. Use this before you hand the PC or the app on.")
        stacked: false
        AppButton {
            text: qsTr("Delete everything"); kind: "danger"
            onClicked: { if (backend.wipeLogins()) { root.editId = ""; saveErr.text = "" } }
        }
    }
}
