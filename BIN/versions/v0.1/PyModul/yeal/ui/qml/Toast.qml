import QtQuick
import QtQuick.Layouts

Rectangle {
    id: root
    function show(message) {
        label.text = message
        opacity = 1
        hideTimer.restart()
    }
    opacity: 0
    visible: opacity > 0
    radius: 22
    color: Theme.dark ? "#3A3A3E" : "#1D1D1F"
    implicitHeight: 44
    implicitWidth: Math.min(label.implicitWidth + 2 * Theme.s5, 520)
    Behavior on opacity { NumberAnimation { duration: Theme.dur } }
    Timer { id: hideTimer; interval: 4000; onTriggered: root.opacity = 0 }
    Text {
        id: label
        anchors.fill: parent
        anchors.leftMargin: Theme.s4
        anchors.rightMargin: Theme.s4
        verticalAlignment: Text.AlignVCenter
        horizontalAlignment: Text.AlignHCenter
        elide: Text.ElideRight
        color: "#FFFFFF"
        font.pixelSize: Theme.footnote + 1
    }
    Accessible.role: Accessible.AlertMessage
    Accessible.name: label.text
}
