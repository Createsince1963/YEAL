import QtQuick

// Start screen with the Yeal logo; fades out by itself or on click/key.
Rectangle {
    id: root
    signal finished()
    gradient: Gradient {
        GradientStop { position: 0; color: "#060A14" }
        GradientStop { position: 1; color: "#06070C" }
    }
    Accessible.ignored: true

    Image {
        id: logo
        anchors.centerIn: parent
        width: Math.min(parent.width * 0.9, 760)
        height: width * 2 / 3
        source: "assets/logo_splash.png"
        fillMode: Image.PreserveAspectFit
        sourceSize.width: 1152
        smooth: true
        opacity: 0
        scale: 0.96
    }
    SequentialAnimation {
        running: true
        ParallelAnimation {
            NumberAnimation { target: logo; property: "opacity"; to: 1; duration: Theme.reducedMotion ? 0 : 450 }
            NumberAnimation { target: logo; property: "scale"; to: 1; duration: Theme.reducedMotion ? 0 : 450
                              easing.type: Easing.OutCubic }
        }
        PauseAnimation { duration: 1100 }
        NumberAnimation { target: root; property: "opacity"; to: 0; duration: Theme.reducedMotion ? 0 : 350 }
        ScriptAction { script: { root.visible = false; root.finished() } }
    }
    TapHandler { onTapped: { root.opacity = 0; root.visible = false; root.finished() } }
}
