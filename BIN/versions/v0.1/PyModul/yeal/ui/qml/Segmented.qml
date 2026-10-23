import QtQuick
import QtQuick.Layouts

// Pill-shaped segmented control. `options`: [{text, value}], `current`: selected value.
Rectangle {
    id: root
    property var options: []
    property var current
    signal activated(var value)

    implicitHeight: Theme.touch
    implicitWidth: Math.max(160, options.length * 72)
    radius: Theme.radius
    color: Theme.field
    border.width: 1
    border.color: Theme.separator
    activeFocusOnTab: true
    Accessible.role: Accessible.RadioButton
    Accessible.name: qsTr("Options")

    readonly property int index: {
        for (var i = 0; i < options.length; ++i)
            if (options[i].value === current) return i
        return 0
    }
    function step(delta) {
        var next = Math.max(0, Math.min(options.length - 1, index + delta))
        root.activated(options[next].value)
    }
    Keys.onLeftPressed: step(-1)
    Keys.onRightPressed: step(1)

    Rectangle {
        id: thumb
        readonly property real w: (root.width - 4) / Math.max(1, root.options.length)
        x: 2 + root.index * w
        y: 2
        width: w
        height: root.height - 4
        radius: Theme.radius - 2
        color: Theme.raised
        border.width: root.activeFocus ? 2 : (Theme.dark ? 0 : 1)
        border.color: root.activeFocus ? Theme.accent : Theme.separator
        Behavior on x { NumberAnimation { duration: Theme.dur; easing.type: Easing.OutCubic } }
    }
    RowLayout {
        anchors.fill: parent
        anchors.margins: 2
        spacing: 0
        Repeater {
            model: root.options
            delegate: Item {
                id: seg
                required property var modelData
                required property int index
                Layout.fillWidth: true
                Layout.fillHeight: true
                Text {
                    anchors.fill: parent
                    anchors.leftMargin: 4
                    anchors.rightMargin: 4
                    text: seg.modelData.text
                    elide: Text.ElideRight
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    font.pixelSize: Theme.footnote + (Theme.compact ? 0 : 1)
                    font.weight: seg.index === root.index ? Font.Medium : Font.Normal
                    color: seg.index === root.index ? Theme.text : Theme.textSecondary
                }
                TapHandler { onTapped: root.activated(seg.modelData.value) }
            }
        }
    }
}
