import QtQuick
import QtQuick.Layouts

Rectangle {
    id: root
    property string iconName
    property string text
    property bool selected: false
    property int badge: 0
    property bool tight: false        // less padding, for three buttons in one row
    signal clicked()

    implicitHeight: 40
    radius: Theme.radius
    color: selected ? Theme.accentSoft : mouse.hovered ? Theme.hover : "transparent"
    border.width: activeFocus ? 2 : 0
    border.color: Theme.accent
    activeFocusOnTab: true
    Keys.onReturnPressed: root.clicked()
    Keys.onSpacePressed: root.clicked()
    Accessible.role: Accessible.PageTab
    Accessible.name: text
    Accessible.selected: selected

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: root.tight ? Theme.s2 : Theme.s3
        anchors.rightMargin: root.tight ? Theme.s2 : Theme.s3
        spacing: root.tight ? Theme.s2 : Theme.s3
        Icon { name: root.iconName; size: 20; color: root.selected ? Theme.accent : Theme.textSecondary }
        Text {
            text: root.text
            font.pixelSize: Theme.body
            font.weight: root.selected ? Font.Medium : Font.Normal
            color: root.selected ? Theme.accent : Theme.text
            elide: Text.ElideRight
            Layout.fillWidth: true
        }
        Badge { visible: root.badge > 0; text: String(root.badge); kind: "accent" }
    }
    HoverHandler { id: mouse }
    TapHandler { onTapped: root.clicked() }
}
