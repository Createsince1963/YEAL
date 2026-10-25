import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// Loading spinner / error with retry / empty hint for one TidalRequest. A failing area shows this note
// instead of a blank page and never blocks the rest of the view.
ColumnLayout {
    id: st
    property var request
    property bool empty: false
    property string emptyText: qsTr("Nothing here yet.")
    visible: !!request && (request.loading || request.error !== "" || (empty && !request.loading))
    width: Math.min(420, parent ? parent.width - 2 * Theme.s4 : 420)
    spacing: Theme.s3
    BusyIndicator {
        visible: !!st.request && st.request.loading
        running: visible
        Layout.alignment: Qt.AlignHCenter
    }
    Text {
        visible: !!st.request && !st.request.loading
        text: st.request && st.request.error !== "" ? st.request.error : st.emptyText
        color: st.request && st.request.error !== "" ? Theme.danger : Theme.textSecondary
        font.pixelSize: Theme.footnote
        wrapMode: Text.Wrap
        horizontalAlignment: Text.AlignHCenter
        Layout.fillWidth: true
    }
    AppButton {
        visible: !!st.request && !st.request.loading && st.request.error !== ""
        text: qsTr("Try again")
        iconName: "retry"
        Layout.alignment: Qt.AlignHCenter
        onClicked: st.request.reload()
    }
}
