import QtQuick
import QtQuick.Effects

// Rounded thumbnail with a media-type placeholder while there is no image.
Rectangle {
    id: root
    property string source
    property string mode: "video"
    // The software renderer cannot run shader effects; fall back to square image corners there.
    readonly property bool canMask: GraphicsInfo.api !== GraphicsInfo.Software
    radius: 8
    color: Theme.field
    Accessible.ignored: true

    Icon {
        anchors.centerIn: parent
        visible: img.status !== Image.Ready
        name: root.mode === "audio" ? "music" : "film"
        size: Math.min(root.width, root.height) * 0.42
        color: Theme.textTertiary
    }
    Image {
        id: img
        anchors.fill: parent
        source: root.source
        asynchronous: true
        fillMode: Image.PreserveAspectCrop
        sourceSize.width: 256
        sourceSize.height: 256
        visible: !root.canMask && status === Image.Ready
    }
    Rectangle {
        id: maskShape
        anchors.fill: parent
        radius: root.radius
        layer.enabled: root.canMask
        visible: false
    }
    MultiEffect {
        anchors.fill: parent
        source: img
        visible: root.canMask && img.status === Image.Ready
        maskEnabled: true
        maskSource: maskShape
    }
}
