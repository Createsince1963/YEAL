import QtQuick

// A planet of the player view: a round button on an orbit around the sun (the player). Open = filled and glowing.
Item {
    id: planet
    property string icon
    property string label
    property bool open: false
    property color tint: Theme.accent
    signal clicked()

    width: 64
    height: 52 + 18
    Accessible.role: Accessible.Button
    Accessible.name: label
    Accessible.checked: open

    Rectangle {          // glow of an open planet
        anchors.horizontalCenter: parent.horizontalCenter
        width: 70; height: 70; radius: 35; y: -9
        color: Qt.alpha(planet.tint, 0.20)
        visible: planet.open
    }
    Rectangle {
        id: disc
        anchors.horizontalCenter: parent.horizontalCenter
        width: 52; height: 52; radius: 26
        color: planet.open ? planet.tint : Theme.surface
        border.width: 1.5
        border.color: planet.open ? planet.tint : Qt.alpha(Theme.text, hover.hovered ? 0.7 : 0.35)
        scale: hover.hovered ? 1.08 : 1.0
        Behavior on scale { NumberAnimation { duration: Theme.durFast } }
        Icon { anchors.centerIn: parent; name: planet.icon; size: 22; color: planet.open ? "#0b0b0c" : Theme.text }
    }
    Text {
        anchors.top: disc.bottom; anchors.topMargin: 2
        anchors.horizontalCenter: parent.horizontalCenter
        text: planet.label
        color: planet.open ? planet.tint : Theme.textSecondary
        font.pixelSize: 11
        font.weight: planet.open ? Font.Bold : Font.Normal
    }
    HoverHandler { id: hover; cursorShape: Qt.PointingHandCursor }
    TapHandler { onTapped: planet.clicked() }
}
