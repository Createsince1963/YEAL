import QtQuick
import QtQuick.Layouts

Rectangle {
    id: root
    property var items: []
    property int currentIndex: 0
    signal selected(int index)

    implicitHeight: 58
    color: Theme.sidebar

    Rectangle { width: parent.width; height: 1; color: Theme.separator }
    RowLayout {
        anchors.fill: parent
        spacing: 0
        Repeater {
            model: root.items
            delegate: Item {
                id: tab
                required property var modelData
                required property int index
                readonly property bool on: root.currentIndex === index
                Layout.fillWidth: true
                Layout.fillHeight: true
                activeFocusOnTab: true
                Keys.onReturnPressed: root.selected(index)
                Keys.onSpacePressed: root.selected(index)
                Accessible.role: Accessible.PageTab
                Accessible.name: modelData.text
                Accessible.selected: on

                Column {
                    anchors.centerIn: parent
                    spacing: 3
                    Item {
                        width: 24
                        height: 24
                        anchors.horizontalCenter: parent.horizontalCenter
                        Icon { anchors.centerIn: parent; name: tab.modelData.icon; size: 24
                               color: tab.on ? Theme.accent : Theme.textSecondary }
                        Badge {
                            visible: (tab.modelData.badge || 0) > 0
                            text: String(tab.modelData.badge || 0)
                            kind: "accent"
                            x: 14
                            y: -8
                        }
                    }
                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: tab.modelData.text
                        font.pixelSize: 11
                        font.weight: tab.on ? Font.Medium : Font.Normal
                        color: tab.on ? Theme.accent : Theme.textSecondary
                    }
                }
                TapHandler { onTapped: root.selected(tab.index) }
            }
        }
    }
}
