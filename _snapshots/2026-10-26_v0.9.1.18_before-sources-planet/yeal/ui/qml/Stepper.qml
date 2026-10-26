import QtQuick
import QtQuick.Layouts

Rectangle {
    id: root
    property int value: 0
    property int from: 0
    property int to: 10
    property int stepSize: 1
    property string suffix: ""
    signal moved(int value)

    implicitWidth: 120
    implicitHeight: Theme.touch
    radius: Theme.radius
    color: Theme.field

    function set(v) {
        var n = Math.max(from, Math.min(to, v))
        if (n !== value) moved(n)
    }
    RowLayout {
        anchors.fill: parent
        spacing: 0
        IconButton {
            iconName: "chevronDown"
            enabled: root.value > root.from
            tip: qsTr("Decrease")
            onClicked: root.set(root.value - root.stepSize)
            Layout.preferredWidth: Theme.touch
        }
        Text {
            text: root.value + root.suffix
            color: Theme.text
            font.pixelSize: Theme.body
            horizontalAlignment: Text.AlignHCenter
            Layout.fillWidth: true
        }
        IconButton {
            iconName: "plus"
            enabled: root.value < root.to
            tip: qsTr("Increase")
            onClicked: root.set(root.value + root.stepSize)
            Layout.preferredWidth: Theme.touch
        }
    }
    Accessible.role: Accessible.SpinBox
    Accessible.name: qsTr("Value %1").arg(value)
}
